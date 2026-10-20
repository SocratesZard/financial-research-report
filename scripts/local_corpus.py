"""Offline, source-bound text/OCR indexing. No network requests or original modification."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import unicodedata
import zipfile
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def normalized_map(text):
    chars, positions = [], []
    for offset, character in enumerate(text):
        for normalized in unicodedata.normalize('NFKC', character).casefold():
            chars.append(normalized)
            positions.append(offset)
    value = ''.join(chars)
    # Windows OCR may insert spaces between every Chinese character. Preserve raw OCR;
    # collapse only whitespace between CJK characters in the searchable representation.
    removed = set()
    for match in re.finditer(r'(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])', value):
        removed.update(range(match.start(), match.end()))
    return ''.join(c for i,c in enumerate(chars) if i not in removed), [p for i,p in enumerate(positions) if i not in removed]


def fold(text):
    return normalized_map(text)[0]


def run(command, timeout=120):
    result = subprocess.run([str(x) for x in command], capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace')[-900:] or 'Local command failed')
    return result.stdout.decode('utf-8-sig', errors='replace')


def tools_state(poppler=None, tesseract=None):
    renderer = poppler or os.environ.get('RESEARCH_PDFTOPPM') or shutil.which('pdftoppm')
    if not renderer:
        bundled = Path(sys.executable).resolve().parents[1] / 'native/poppler/Library/bin/pdftoppm.exe'
        if bundled.is_file():
            renderer = str(bundled)
    tess = tesseract or shutil.which('tesseract')
    tess_info = None
    if tess:
        try:
            languages = run([tess, '--list-langs']).splitlines()[1:]
            tess_info = dict(path=str(tess), languages=languages)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            tess_info = dict(path=str(tess), error=str(exc))
    ps = shutil.which('powershell.exe') if os.name == 'nt' else None
    windows = None
    if ps:
        try:
            windows = json.loads(run([ps, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', HERE/'windows_ocr.ps1', '-Probe'], 30))
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
            windows = dict(error=str(exc))
    return dict(pdftoppm=renderer, powershell=ps, windows_ocr=windows, tesseract=tess_info)


def text_quality(text, image_fraction=0):
    useful = sum(c.isalnum() for c in text)
    invalid = sum(c == '\ufffd' or unicodedata.category(c) == 'Co' for c in text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fragments = sum(len(line) <= 2 for line in lines) / max(1, len(lines))
    flags = []
    if useful < 40:
        flags.append('EMPTY_OR_SPARSE_TEXT')
    if image_fraction >= .35 and useful < 120:
        flags.append('IMAGE_WITH_LITTLE_TEXT')
    if invalid > max(3, len(text) * .02):
        flags.append('INVALID_GLYPHS')
    if len(lines) >= 30 and fragments > .45:
        flags.append('FRAGMENTED_TEXT')
    return dict(useful_characters=useful, image_fraction=round(image_fraction, 3), invalid_glyphs=invalid, short_line_fraction=round(fragments, 3), flags=flags)


def page_numbers(value):
    if not value:
        return set()
    pages = set()
    for part in value.split(','):
        match = re.fullmatch(r'(\d+)(?:-(\d+))?', part.strip())
        if not match:
            raise ValueError('Use physical PDF pages such as 1,4-7')
        start, end = int(match[1]), int(match[2] or match[1])
        if start < 1 or end < start:
            raise ValueError('Invalid page range')
        pages.update(range(start, end + 1))
    return pages


def choose_engine(requested, state):
    win = state.get('windows_ocr') or {}
    tess = state.get('tesseract') or {}
    if requested == 'off':
        return None
    if requested in ('auto', 'windows') and win.get('languages'):
        return 'windows'
    if requested in ('auto', 'tesseract') and tess.get('languages') and not tess.get('error'):
        return 'tesseract'
    return None


def recognize(image, output, engine, language, state):
    if engine == 'windows':
        run([state['powershell'], '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', HERE/'windows_ocr.ps1', '-ImagePath', image, '-OutputPath', output, '-Language', language])
        return read(output)
    if language == 'auto':
        available = state['tesseract']['languages']
        language = '+'.join(lang for lang in ('chi_sim', 'eng') if lang in available)
        if not language:
            raise RuntimeError('Set an installed Tesseract language explicitly')
    raw = run([state['tesseract']['path'], image, 'stdout', '-l', language, '--psm', '3', 'tsv'])
    words, lines = [], {}
    for row in csv.DictReader(io.StringIO(raw), delimiter='\t'):
        if row.get('level') != '5' or not row.get('text', '').strip():
            continue
        word = dict(text=row['text'], confidence=float(row['conf']), box=[int(row[k]) for k in ('left', 'top', 'width', 'height')])
        words.append(word)
        key = tuple(row[k] for k in ('page_num', 'block_num', 'par_num', 'line_num'))
        lines.setdefault(key, []).append(word)
    record = dict(engine='Tesseract', language=language, text='\n'.join(' '.join(w['text'] for w in line) for line in lines.values()), words=words, confidence=sum(w['confidence'] for w in words)/len(words) if words else None, review_status='OCR_UNVERIFIED')
    write(output, record)
    return record


def non_pdf_units(path):
    suffix = path.suffix.lower()
    if suffix in ('.txt', '.md', '.csv'):
        raw = path.read_bytes()
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = raw.decode('gb18030')
        return [('paragraph', n, line) for n, line in enumerate(text.splitlines(), 1)]
    if suffix == '.docx':
        with zipfile.ZipFile(path) as archive:
            body = ET.fromstring(archive.read('word/document.xml'))
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        return [('paragraph', n, ''.join(t.text or '' for t in para.findall('.//w:t', ns))) for n, para in enumerate(body.findall('.//w:body//w:p', ns), 1)]
    raise ValueError('Unsupported type; route spreadsheets, slides, legacy Office or notes to their matching extractor: '+suffix)


def visual_supplements(path):
    if not path:
        return {}
    records = {}
    for item in read(path).get('supplements', []):
        key = (item.get('source_sha256'), item.get('page'))
        if not re.fullmatch(r'[0-9a-fA-F]{64}', key[0] or '') or not isinstance(key[1], int) or key[1] < 1:
            raise ValueError('Visual supplement needs original SHA-256 and physical page')
        if key in records:
            raise ValueError('Duplicate visual supplement page')
        if item.get('extent') not in ('full_page', 'body_only', 'selected_regions'):
            raise ValueError('Visual extent must be full_page, body_only or selected_regions')
        if not item.get('text','').strip() or not item.get('review_note') or not item.get('reviewed_by'):
            raise ValueError('Visual supplement needs actual transcription and review record')
        if datetime.fromisoformat(item.get('reviewed_at','').replace('Z','+00:00')).tzinfo is None:
            raise ValueError('Visual review time needs timezone')
        image = Path(item.get('image_path',''))
        if not image.is_absolute():
            image = path.resolve().parent/image
        if digest(image.read_bytes()) != item.get('image_sha256'):
            raise ValueError('Visual supplement image SHA-256 mismatch')
        records[(key[0].lower(),key[1])] = {**item,'image_path':str(image.resolve())}
    return records


def render_page(original, number, out, sid, dpi, state):
    if not state.get('pdftoppm'):
        raise RuntimeError('Local PDF renderer unavailable')
    folder=out/'pages'/sid
    folder.mkdir(parents=True,exist_ok=True)
    prefix=folder/f'p{number}'
    image=prefix.with_suffix('.png')
    if not image.exists():
        run([state['pdftoppm'],'-f',number,'-l',number,'-singlefile','-r',dpi,'-png',original,prefix])
    return image


def build(args):
    evidence = read(args.evidence)
    files = evidence.get('files', [])
    if not files:
        raise ValueError('Evidence JSON needs an explicitly selected files list')
    out = args.out.resolve()
    source_paths = [(Path(f['path']) if Path(f.get('path', '')).is_absolute() else args.evidence.resolve().parent/str(f.get('path', ''))).resolve() for f in files]
    if any(src == out or out in src.parents for src in source_paths):
        raise ValueError('Output must not contain or overwrite any source original')
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use a new or empty output directory')
    if not 100 <= args.dpi <= 600:
        raise ValueError('DPI must be 100–600')
    forced_pages = page_numbers(args.ocr_pages)
    supplements = visual_supplements(getattr(args,'supplements',None))
    used_supplements = set()
    out.mkdir(parents=True, exist_ok=True)
    (out/'text').mkdir()
    state = tools_state(args.poppler, args.tesseract)
    engine = choose_engine(args.ocr, state)
    con = sqlite3.connect(out/'corpus.sqlite')
    con.execute('CREATE TABLE sources (id TEXT PRIMARY KEY, title TEXT, path TEXT, sha256 TEXT, metadata TEXT)')
    con.execute('CREATE TABLE segments (source_id TEXT, unit_kind TEXT, unit_number INTEGER, variant TEXT, text TEXT, normalized TEXT, text_sha256 TEXT, review_status TEXT, PRIMARY KEY(source_id,unit_kind,unit_number,variant))')
    result = dict(corpus_version=1, created_at=stamp(), scope='Selected originals only. Native text, recorded visual transcriptions and unverified OCR have separate provenance; indexing does not establish source truth, full-library coverage or full chart transcription.', ocr_policy=args.ocr, tools=state, sources=[], failure_count=0)
    ocr_calls = 0
    def add(sid, kind, number, variant, text):
        if text.strip():
            review = 'OCR_UNVERIFIED' if variant == 'ocr' else 'VISUAL_REVIEW_RECORDED' if variant == 'visual' else 'NOT_REVIEWED'
            con.execute('INSERT INTO segments VALUES (?,?,?,?,?,?,?,?)', (sid,kind,number,variant,text,fold(text),digest(text.encode('utf-8')),review))
    for i, (item, original) in enumerate(zip(files, source_paths), 1):
        sid = f'S{i:03d}'
        entry = dict(id=sid, title=item.get('title') or original.name, path=str(original), sha256=None, media_id=item.get('media_id'), publication_date=None, publication_status='VERIFY_IN_ORIGINAL', read_status='EXTRACTED_NOT_READ', status='PENDING', units=[])
        result['sources'].append(entry)
        try:
            raw = original.read_bytes()
            sha = digest(raw)
            if item.get('sha256') and sha != item['sha256'].lower():
                raise ValueError('Source SHA-256 does not match evidence record')
            entry['sha256'] = sha
            con.execute('INSERT INTO sources VALUES (?,?,?,?,?)', (sid,entry['title'],str(original),sha,json.dumps(item,ensure_ascii=False)))
            if original.suffix.lower() == '.pdf':
                import pdfplumber
                logging.getLogger('pdfminer').setLevel(logging.ERROR)
                with pdfplumber.open(original) as pdf:
                    for number, page in enumerate(pdf.pages, 1):
                        native = page.extract_text(layout=False) or ''
                        area = sum(max(0,x['x1']-x['x0'])*max(0,x['bottom']-x['top']) for x in page.images)
                        quality = text_quality(native, min(1, area/(page.width*page.height)))
                        unit = dict(kind='page', number=number, native_characters=len(native), quality=quality, ocr_status='NOT_NEEDED', review_status='NOT_REVIEWED')
                        entry['units'].append(unit)
                        add(sid,'page',number,'native',native)
                        (out/'text'/f'{sid}-p{number}-native.txt').write_text(native, encoding='utf-8')
                        supplement = supplements.get((sha,number))
                        if supplement:
                            used_supplements.add((sha,number))
                            visual_image=out/'pages'/sid/f'p{number}-visual{Path(supplement["image_path"]).suffix}'
                            visual_image.parent.mkdir(parents=True,exist_ok=True)
                            shutil.copy2(supplement['image_path'],visual_image)
                            unit['visual_review']={**supplement,'image_path':visual_image.relative_to(out).as_posix(),'status':'VISUAL_REVIEW_RECORDED'}
                            add(sid,'page',number,'visual',supplement['text'])
                            (out/'text'/f'{sid}-p{number}-visual.txt').write_text(supplement['text'],encoding='utf-8')
                            if supplement['extent']=='full_page':
                                unit['ocr_status']='NOT_NEEDED_VISUAL_RECORD'
                                continue
                        if not (quality['flags'] or number in forced_pages):
                            continue
                        if getattr(args,'render_review_pages',False):
                            try:
                                image=render_page(original,number,out,sid,args.dpi,state)
                                unit.update(image_path=image.relative_to(out).as_posix(),image_sha256=digest(image.read_bytes()),render_status='READY_FOR_VISUAL_REVIEW')
                            except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
                                unit.update(render_status='FAILED',render_error=str(exc))
                        if args.ocr == 'off':
                            unit['ocr_status'] = 'STANDBY_VISUAL_REVIEW_FIRST'
                            continue
                        if not engine or not state['pdftoppm']:
                            unit['ocr_status'] = 'LOCAL_ENGINE_OR_RENDERER_UNAVAILABLE'
                            continue
                        if args.ocr_max_pages is not None and ocr_calls >= args.ocr_max_pages:
                            unit['ocr_status'] = 'DEFERRED_BUDGET'
                            continue
                        unit['ocr_status'] = 'PENDING'
                        ocr_calls += 1
                        try:
                            image = render_page(original,number,out,sid,args.dpi,state)
                            output = image.with_suffix('.ocr.json')
                            rec = recognize(image,output,engine,args.ocr_language,state)
                            unit.update(image_path=image.relative_to(out).as_posix(),image_sha256=digest(image.read_bytes()),ocr_path=output.relative_to(out).as_posix(),ocr_engine=rec['engine'],ocr_language=rec['language'],ocr_characters=len(rec['text']),ocr_confidence=rec.get('confidence'),ocr_status='OCR_UNVERIFIED' if rec['text'].strip() else 'OCR_EMPTY')
                            add(sid,'page',number,'ocr',rec['text'])
                            (out/'text'/f'{sid}-p{number}-ocr.txt').write_text(rec['text'],encoding='utf-8')
                        except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as exc:
                            unit.update(ocr_status='OCR_FAILED',error=str(exc))
            else:
                for kind, number, text in non_pdf_units(original):
                    add(sid,kind,number,'native',text)
                    entry['units'].append(dict(kind=kind,number=number,native_characters=len(text),review_status='NOT_REVIEWED'))
            unresolved = [u for u in entry['units'] if (u.get('quality',{}).get('flags') or u.get('ocr_status','NOT_NEEDED') != 'NOT_NEEDED') and u.get('ocr_status') not in ('OCR_UNVERIFIED','NOT_NEEDED_VISUAL_RECORD')]
            entry['status'] = 'PARTIAL_INDEX' if unresolved else 'INDEXED_REVIEW_PENDING'
            if any(u.get('ocr_status') == 'OCR_UNVERIFIED' for u in entry['units']):
                entry['contains_unverified_ocr'] = True
        except Exception as exc:
            # Independent local sources can still be extracted; failed source remains explicit.
            entry.update(status='EXTRACTION_FAILED',error=str(exc))
            result['failure_count'] += 1
        con.commit()
    result.update(finished_at=stamp(),ocr_calls=ocr_calls,status='PARTIAL' if any(s['status'] in ('PARTIAL_INDEX','EXTRACTION_FAILED') for s in result['sources']) else 'INDEXED_REVIEW_PENDING')
    unmatched = set(supplements)-used_supplements
    if unmatched:
        result.update(status='PARTIAL',unmatched_visual_supplements=[dict(source_sha256=s,page=p) for s,p in sorted(unmatched)])
        result['failure_count'] += len(unmatched)
    con.close()
    write(out/'corpus-manifest.json',result)
    queue=[dict(source_id=s['id'],original_path=s['path'],original_sha256=s['sha256'],page=u['number'],quality=u.get('quality'),image_path=u.get('image_path'),ocr_status=u.get('ocr_status'),visual_review=u.get('visual_review'),next_step='Read rendered page; local OCR is optional fallback. Record actual transcription extent.') for s in result['sources'] for u in s['units'] if u.get('quality',{}).get('flags') or u.get('ocr_status') not in (None,'NOT_NEEDED')]
    write(out/'review-queue.json',dict(scope='Potential extraction gaps, not a complete list of research reading obligations',pages=queue))
    print(json.dumps(dict(status=result['status'],sources=len(result['sources']),ocr_calls=ocr_calls,failures=result['failure_count'],out=str(out)),ensure_ascii=False))
    return 1 if result['failure_count'] else 0


def search(args):
    manifest = read(args.corpus/'corpus-manifest.json')
    source_map = {s['id']:s for s in manifest['sources']}
    db = args.corpus.resolve()/'corpus.sqlite'
    con = sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
    results = []
    for query in args.query:
        if not query.strip():
            raise ValueError('Query must not be blank')
        rows = con.execute('SELECT source_id,unit_kind,unit_number,variant,text,text_sha256,review_status FROM segments WHERE instr(normalized,?)>0 ORDER BY source_id,unit_number,variant',(fold(query),)).fetchall()
        hits = []
        for sid,kind,num,variant,text,sha,review in rows[:args.limit]:
            source=source_map[sid]
            normalized, offsets=normalized_map(text)
            match_at=normalized.find(fold(query))
            at=offsets[match_at]
            hits.append(dict(source_id=sid,title=source['title'],original_path=source['path'],original_sha256=source['sha256'],locator=f'{"PDF p." if kind=="page" else "paragraph "}{num}',variant=variant,review_status=review,text_sha256=sha,snippet=text[max(0,at-100):at+len(query)+260]))
        results.append(dict(query=query,total_variant_hits=len(rows),unique_units=len({(r[0],r[1],r[2]) for r in rows}),returned=len(hits),truncated=len(rows)>args.limit,hits=hits))
    con.close()
    record=dict(scope=manifest['scope'],corpus_status=manifest['status'],searched_at=stamp(),results=results)
    if args.out:
        if args.out.exists():
            raise ValueError('Search output exists; use a new path')
        write(args.out,record)
    print(json.dumps(record,ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    doctor=commands.add_parser('doctor')
    doctor.add_argument('--out',type=Path)
    make=commands.add_parser('build')
    make.add_argument('--evidence',required=True,type=Path,help='IMA ima-evidence.json or explicit {files:[{path,title,sha256?}]}')
    make.add_argument('--out',required=True,type=Path)
    make.add_argument('--ocr',choices=['auto','off','windows','tesseract'],default='off',help='Standby by default. Explicit auto enables an available local OCR engine for suspect pages.')
    make.add_argument('--ocr-language',default='auto')
    make.add_argument('--ocr-pages',help='Also OCR these physical PDF pages, e.g. 4,7; native text is retained')
    make.add_argument('--render-review-pages',action='store_true',help='Render suspect pages for visual reading without enabling OCR')
    make.add_argument('--supplements',type=Path,help='Actual visual transcriptions bound to original SHA-256, page and rendered image hash')
    make.add_argument('--ocr-max-pages',type=int,help='Optional per-run budget; deferred pages remain partial, not complete')
    make.add_argument('--dpi',type=int,default=300)
    make.add_argument('--poppler')
    make.add_argument('--tesseract')
    find=commands.add_parser('search')
    find.add_argument('--corpus',required=True,type=Path)
    find.add_argument('--query',required=True,action='append')
    find.add_argument('--limit',type=int,default=100,help='Display limit per query; total matches remain recorded')
    find.add_argument('--out',type=Path)
    args=parser.parse_args()
    if args.command=='doctor':
        state=tools_state()
        if args.out:
            if args.out.exists():
                parser.error('Doctor output exists')
            write(args.out,state)
        print(json.dumps(state,ensure_ascii=False,indent=2))
    elif args.command=='build':
        if args.ocr_max_pages is not None and args.ocr_max_pages<0:
            parser.error('OCR budget must be nonnegative')
        return build(args)
    else:
        if args.limit<1:
            parser.error('Limit must be positive')
        search(args)
    return 0


if __name__=='__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(json.dumps(dict(error=str(error)),ensure_ascii=False),file=sys.stderr)
        sys.exit(1)

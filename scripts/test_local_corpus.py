"""Local extraction invariants; real OCR is opt-in with --ocr-smoke."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import zipfile

spec=importlib.util.spec_from_file_location('local_corpus',Path(__file__).with_name('local_corpus.py'))
corpus=importlib.util.module_from_spec(spec)
spec.loader.exec_module(corpus)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ocr-smoke',action='store_true')
    args=parser.parse_args()
    checks=[]
    with tempfile.TemporaryDirectory(prefix='research-corpus-') as tmp:
        root=Path(tmp)
        text=root/'source.txt';text.write_text('光通信 ＣＰＯ 2026\n第七页检索不能依赖第一页\nSQL literal test: x%_y',encoding='utf-8')
        doc=root/'source.docx'
        with zipfile.ZipFile(doc,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>表格之前</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>表格单元格 42</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
        originals=[dict(path=str(p),title=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [text,doc]]
        evidence=root/'evidence.json';corpus.write(evidence,dict(files=originals))
        opts=SimpleNamespace(evidence=evidence,out=root/'index',dpi=300,ocr_pages=None,ocr='off',ocr_language='auto',ocr_max_pages=None,poppler=None,tesseract=None)
        with contextlib.redirect_stdout(io.StringIO()):
            assert corpus.build(opts)==0
        con=sqlite3.connect(opts.out/'corpus.sqlite')
        assert con.execute("SELECT count(*) FROM segments WHERE instr(normalized,?)>0",('cpo',)).fetchone()[0]==1
        assert con.execute("SELECT count(*) FROM segments WHERE instr(normalized,?)>0",('表格单元格',)).fetchone()[0]==1
        assert con.execute("SELECT count(*) FROM segments WHERE instr(normalized,?)>0",("' OR 1=1 --",)).fetchone()[0]==0
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok';con.close()
        checks+=['Chinese and NFKC English retrieval','DOCX table paragraph preservation','SQL query treated as data','SQLite integrity']
        for item in originals:
            assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256']
        checks.append('Originals unchanged')
        try:
            corpus.build(opts)
            raise AssertionError('Old output overwritten')
        except ValueError:
            checks.append('New output guard')
        corrupt=root/'bad.json';corpus.write(corrupt,dict(files=[{**originals[0],'sha256':'0'*64}]))
        opts.evidence=corrupt;opts.out=root/'bad-index'
        with contextlib.redirect_stdout(io.StringIO()):
            assert corpus.build(opts)==1
        assert corpus.read(opts.out/'corpus-manifest.json')['sources'][0]['status']=='EXTRACTION_FAILED'
        checks.append('Hash mismatch cannot silently enter index')
        if args.ocr_smoke:
            from PIL import Image,ImageDraw,ImageFont
            font_paths=[Path('C:/Windows/Fonts/msyh.ttc'),Path('C:/Windows/Fonts/simsun.ttc')]
            font=next((p for p in font_paths if p.exists()),None)
            if not font:
                raise SystemExit('OCR smoke needs a local Chinese font; use real source test instead')
            image=Image.new('RGB',(1800,750),'white');draw=ImageDraw.Draw(image)
            draw.text((60,100),'光通信产业研究',font=ImageFont.truetype(str(font),80),fill='black')
            draw.text((60,260),'LOCAL OCR 2026 REVENUE 42',font=ImageFont.truetype(str(font),65),fill='black')
            pdf=root/'image-only.pdf';image.save(pdf,'PDF',resolution=150)
            evidence=root/'ocr-evidence.json';corpus.write(evidence,dict(files=[dict(path=str(pdf),title='Synthetic image-only source')]))
            opts.evidence=evidence;opts.out=root/'ocr-index';opts.ocr='auto';opts.ocr_language='zh-Hans-CN'
            with contextlib.redirect_stdout(io.StringIO()):
                assert corpus.build(opts)==0
            rec=corpus.read(opts.out/'corpus-manifest.json')['sources'][0]
            assert rec['units'][0]['native_characters']==0
            assert rec['units'][0]['ocr_status']=='OCR_UNVERIFIED'
            con=sqlite3.connect(opts.out/'corpus.sqlite');ocr=con.execute("SELECT text FROM segments WHERE variant='ocr'").fetchone()[0];con.close()
            assert '光通信' in corpus.fold(ocr) and '2026' in ocr,ocr
            con=sqlite3.connect(opts.out/'corpus.sqlite');assert con.execute('SELECT count(*) FROM segments WHERE instr(normalized,?)>0',('光通信',)).fetchone()[0]==1;con.close()
            checks.append('Actual local Chinese/English OCR recovers image-only PDF; remains unverified')
            opts.out=root/'visual-first';opts.ocr='off';opts.render_review_pages=True
            with contextlib.redirect_stdout(io.StringIO()):
                assert corpus.build(opts)==0
            visual_source=corpus.read(opts.out/'corpus-manifest.json')['sources'][0]
            assert corpus.read(opts.out/'corpus-manifest.json')['ocr_calls']==0
            rendered=opts.out/visual_source['units'][0]['image_path']
            supplement=root/'visual.json'
            corpus.write(supplement,dict(supplements=[dict(source_sha256=visual_source['sha256'],page=1,image_path=str(rendered),image_sha256=hashlib.sha256(rendered.read_bytes()).hexdigest(),text='Synthetic visual transcription 光通信产业研究',extent='selected_regions',reviewed_by='synthetic-test',reviewed_at=corpus.stamp(),review_note='Synthetic fixture; only title was transcribed')]))
            opts.out=root/'visual-index';opts.supplements=supplement;opts.render_review_pages=False
            with contextlib.redirect_stdout(io.StringIO()):
                assert corpus.build(opts)==0
            visual_manifest=corpus.read(opts.out/'corpus-manifest.json')
            assert visual_manifest['ocr_calls']==0 and visual_manifest['status']=='PARTIAL'
            con=sqlite3.connect(opts.out/'corpus.sqlite');assert con.execute("SELECT review_status FROM segments WHERE variant='visual'").fetchone()[0]=='VISUAL_REVIEW_RECORDED';con.close()
            checks.append('Visual-first render and hash-bound partial supplement work with zero OCR calls')
            wrong=corpus.read(supplement);wrong['supplements'][0]['image_sha256']='0'*64;corpus.write(root/'wrong-visual.json',wrong)
            try:
                corpus.visual_supplements(root/'wrong-visual.json')
                raise AssertionError('Incorrect visual image accepted')
            except ValueError:
                checks.append('Visual supplement image hash mismatch is rejected')
            opts.supplements=None;opts.ocr='auto'
            opts.out=root/'ocr-budget';opts.ocr_max_pages=0
            with contextlib.redirect_stdout(io.StringIO()):
                assert corpus.build(opts)==0
            assert corpus.read(opts.out/'corpus-manifest.json')['status']=='PARTIAL'
            checks.append('OCR budget exhaustion remains partial')
    print(json.dumps(dict(ok=True,checks=checks),ensure_ascii=False))


if __name__=='__main__':
    main()

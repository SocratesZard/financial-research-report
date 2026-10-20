"""Read-only PDF intake: text, geometry, styles, thumbnails and source hash.

Requires pdfplumber, Pillow and Poppler's pdftoppm on PATH. Does not execute
embedded PDF actions, follow URLs, overwrite the source or infer OCR text.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pdfplumber
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('pdf', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--dpi', type=int, default=80)
    args = ap.parse_args()
    src, out = args.pdf.resolve(), args.out.resolve()
    if out == src or src in out.parents:
        ap.error('Output must be separate from the source PDF.')
    out.mkdir(parents=True, exist_ok=True)
    pages, fonts, colors = [], Counter(), Counter()
    fulltext = []
    with pdfplumber.open(src) as pdf:
        metadata = {str(k): str(v) for k, v in (pdf.metadata or {}).items()}
        for i, page in enumerate(pdf.pages, 1):
            txt = page.extract_text(layout=False) or ''
            fulltext.append(f'\n\n===== PDF PAGE {i} =====\n{txt}')
            for char in page.chars:
                fonts[(char.get('fontname', ''), round(char.get('size', 0), 1))] += 1
                colors[str(char.get('non_stroking_color'))] += 1
            suspected_ocr = bool(page.chars) and all('Glyphless' in c.get('fontname', '') for c in page.chars)
            pages.append({'page': i, 'width_pt': page.width, 'height_pt': page.height,
                          'text': txt, 'image_count': len(page.images),
                          'text_extraction': ('suspected_OCR_layer_VERIFY_VISUALLY' if suspected_ocr else 'text_layer') if txt.strip() else 'OCR_REQUIRED',
                          'links': [{'uri': l.get('uri'), 'bbox': [l.get(k) for k in ('x0','top','x1','bottom')]}
                                    for l in page.hyperlinks]})
    result = {'path': str(src), 'sha256': hashlib.sha256(src.read_bytes()).hexdigest(),
              'bytes': src.stat().st_size, 'metadata': metadata, 'page_count': len(pages),
              'fonts': [{'font': k[0], 'size_pt': k[1], 'characters': v} for k,v in fonts.most_common(30)],
              'text_colors': colors.most_common(20), 'pages': pages}
    (out/'intake.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (out/'text.txt').write_text(''.join(fulltext), encoding='utf-8')
    poppler = shutil.which('pdftoppm')
    if not poppler:
        raise SystemExit('Text extracted; pdftoppm unavailable. Add Poppler to PATH, rerun for visual review.')
    render = out/'pages'
    render.mkdir(exist_ok=True)
    subprocess.run([poppler, '-r', str(args.dpi), '-png', str(src), str(render/'page')], check=True)
    files = sorted(render.glob('page-*.png'), key=lambda p: int(p.stem.split('-')[-1]))
    for start in range(0, len(files), 9):
        sheet = Image.new('RGB', (1500, 3*312), '#d9dfe5')
        draw = ImageDraw.Draw(sheet)
        for j, path in enumerate(files[start:start+9]):
            with Image.open(path) as im:
                im.thumbnail((488, 280))
                x, y = (j%3)*500+6, (j//3)*312+25
                sheet.paste(im, (x,y))
                draw.text((x,y-20), f'PDF PAGE {start+j+1}', fill='#111111')
        sheet.save(out/f'contact-{start//9+1:02}.png')
    print(json.dumps({'page_count': len(pages), 'sha256': result['sha256'], 'out': str(out)}, ensure_ascii=False))


if __name__ == '__main__':
    main()

"""Validate a research ledger and render editable HTML + Markdown. Standard library only."""
import argparse
from datetime import date, datetime
from html import escape
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('report_visuals', ROOT/'scripts'/'visuals.py')
visuals = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(visuals)
_outlook_spec = importlib.util.spec_from_file_location('weekly_outlook', ROOT/'scripts'/'weekly_outlook.py')
outlook = importlib.util.module_from_spec(_outlook_spec)
_outlook_spec.loader.exec_module(outlook)
_ima_spec = importlib.util.spec_from_file_location('ima_source_record', ROOT/'scripts'/'ima_source_record.py')
ima_record = importlib.util.module_from_spec(_ima_spec)
_ima_spec.loader.exec_module(ima_record)


def instant(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError(f'Timezone required: {value}')
    return dt


def validate(d, base_dir=None):
    errors, warnings = [], []
    def need(test, msg):
        if not test:
            errors.append(msg)
    for key in ('schema_version','report_id','title','mode','status','period_start','period_end','cutoff_at','timezone','universe','sources','claims','events','theses','calendar','slides','limitations'):
        need(key in d, f'Missing {key}')
    if errors:
        return errors, warnings
    need(d['schema_version'] in (1, 2), 'Unsupported schema_version')
    need(d['mode'] in ('daily','weekly','reference-demo'), 'Invalid mode')
    need(d['status'] in ('DEMO_REFERENCE_ONLY','DRAFT','REVIEW_READY'), 'Invalid status')
    try:
        start, end, cutoff = date.fromisoformat(d['period_start']), date.fromisoformat(d['period_end']), instant(d['cutoff_at'])
        need(start <= end <= cutoff.date(), 'Invalid period/cutoff ordering')
    except (ValueError, TypeError) as exc:
        return [str(exc)], warnings
    def unique(items, field, label):
        vals = [x.get(field) for x in items]
        need(all(isinstance(v,str) and v for v in vals), f'{label}: missing {field}')
        need(len(vals) == len(set(vals)), f'{label}: duplicate {field}')
    unique(d['sources'], 'id', 'sources')
    unique(d['claims'], 'id', 'claims')
    unique(d['events'], 'event_key', 'events')
    unique(d['theses'], 'thesis_key', 'theses')
    if errors:
        return errors, warnings
    sources = {s['id']:s for s in d['sources']}
    claims = {c['id']:c for c in d['claims']}
    need(bool(sources) and bool(claims) and bool(d['slides']), 'Empty sources/claims/slides')
    for s in d['sources']:
        errors += ima_record.errors(s, base_dir)
        need(s.get('kind') in ('primary','secondary','channel','reference'), f"{s['id']}: invalid kind")
        need(s.get('access') in ('opened','excerpt_only','inaccessible','not_accessed'), f"{s['id']}: invalid access")
        need(bool(s.get('url') or s.get('path')), f"{s['id']}: source location missing")
        need(bool(s.get('title')), f"{s['id']}: source title missing")
        if s.get('access') == 'opened':
            try:
                instant(s.get('accessed_at', ''))
            except (ValueError,TypeError):
                errors.append(f"{s['id']}: opened source needs accessed_at with timezone")
        if s.get('url'):
            need(s['url'].startswith(('https://','http://')), f"{s['id']}: unsafe URL")
    for c in d['claims']:
        cid, refs = c['id'], c.get('source_refs', [])
        need(c.get('kind') in ('fact','company_report','inference','scenario','calendar'), f'{cid}: invalid kind')
        need(c.get('verification') in ('supported','corroborated','reference_only','unverified'), f'{cid}: invalid verification')
        need(bool(c.get('text')) and bool(refs), f'{cid}: empty text/evidence')
        usable = set()
        for ref in refs:
            sid = ref.get('source_id')
            need(sid in sources, f'{cid}: unknown source {sid}')
            need(bool(ref.get('locator')) and bool(ref.get('evidence')), f'{cid}: missing locator/evidence')
            s = sources.get(sid, {})
            if s.get('access') == 'opened' and s.get('kind') != 'reference':
                usable.add(sid)
            if s.get('published_at') and d['mode'] != 'reference-demo':
                try:
                    need(instant(s['published_at']) <= cutoff, f'{cid}: post-cutoff source')
                except ValueError as exc:
                    errors.append(str(exc))
        if c.get('verification') in ('supported','corroborated'):
            need(len(usable) >= (2 if c['verification'] == 'corroborated' else 1), f'{cid}: insufficient opened non-reference sources')
        if c.get('kind') in ('inference','scenario'):
            need(bool(c.get('assumptions')), f'{cid}: assumptions required')
        if d['status'] == 'REVIEW_READY':
            need(c.get('verification') in ('supported','corroborated'), f'{cid}: unresolved evidence in REVIEW_READY')
    if d['mode'] == 'reference-demo':
        need(d['status'] == 'DEMO_REFERENCE_ONLY', 'reference-demo must be DEMO_REFERENCE_ONLY')
    if any(c.get('verification') in ('reference_only','unverified') for c in d['claims']):
        warnings.append('Evidence contains reference-only or unverified claims; no live fact verification implied.')
    def check_refs(obj, label):
        need(bool(obj.get('claim_ids')), f'{label}: missing claim_ids')
        for cid in obj.get('claim_ids', []):
            need(cid in claims, f'{label}: unknown claim {cid}')
    for e in d['events']:
        check_refs(e, e.get('id','event'))
        try:
            raw = e['occurred_at']
            if len(raw) == 10:
                event_day = date.fromisoformat(raw)
                need(start <= event_day <= end and event_day <= cutoff.date(), f"{e['id']}: outside reporting period/cutoff")
            else:
                dt = instant(raw)
                need(start <= dt.astimezone(cutoff.tzinfo).date() <= end and dt <= cutoff, f"{e['id']}: outside reporting period/cutoff")
        except (KeyError,ValueError) as exc:
            errors.append(str(exc))
    for t in d['theses']:
        check_refs(t, t.get('id','thesis'))
        need(t.get('stance') in ('new','maintained','upgraded','downgraded','withdrawn','pending'), 'Invalid thesis stance')
        need(bool(t.get('next_validation')), 'Thesis needs next_validation')
    for c in d['calendar']:
        check_refs(c, c.get('item','calendar'))
        need(c.get('confirmation') in ('confirmed','tentative','reference_only'), 'Invalid calendar confirmation')
        try:
            date.fromisoformat(c['date'][:10])
            if len(c['date']) > 10:
                instant(c['date'])
        except (ValueError,KeyError) as exc:
            errors.append(str(exc))
        for cid in c.get('claim_ids', []):
            need(claims.get(cid,{}).get('kind') == 'calendar', 'Calendar must link calendar claims')
    for i, s in enumerate(d['slides'], 1):
        label = f'Slide {i}'
        check_refs(s, label)
        view_label = s.get('takeaway_label', '研究判断')
        need(view_label in ('研究判断','投资观点','后续观察'), f'{label}: invalid takeaway_label')
        if view_label == '投资观点':
            tm = {t.get('id'):t for t in d['theses']}
            tids = s.get('thesis_ids', [])
            need(bool(s.get('takeaway')) and bool(tids), f'{label}: investment view needs takeaway and thesis_ids')
            for tid in tids:
                need(tid in tm, f'{label}: unknown investment thesis {tid}')
                t = tm.get(tid, {})
                need(all(t.get(k) for k in ('target','horizon','invalidation')), f'{label}: investment thesis needs target/horizon/invalidation')
                need(t.get('valuation_status') in ('not_assessed','qualitative','modeled'), f'{label}: valuation status required')
                linked = set(t.get('claim_ids', []))
                if t.get('valuation_status') == 'modeled':
                    need(bool(t.get('valuation_claim_ids')), f'{label}: modeled valuation needs evidence claims')
                    linked.update(t.get('valuation_claim_ids', []))
                need(linked.issubset(s.get('claim_ids', [])) and linked.issubset(claims), f'{label}: investment view evidence missing from page')
        need(s.get('type') in ('cover','table','two_column','bars','calendar','visual_analysis'), f'{label}: unknown layout')
        need(bool(s.get('title')), f'{label}: no title')
        need(len(s.get('blocks',[])) <= 2, f'{label}: at most two blocks; split page')
        need(len(s.get('toc',[])) <= 6 and len(s.get('metrics',[])) <= 11, f'{label}: cover too dense')
        for b in s.get('blocks', []):
            bt = b.get('type')
            need(bt in ('table','text','bars','visual','brief'), f'{label}: unknown block')
            if bt == 'table':
                cols = b.get('columns',[])
                need(bool(cols), f'{label}: empty columns')
                need(all(len(r)==len(cols) for r in b.get('rows',[])), f'{label}: ragged table')
                need(len(b.get('rows',[])) <= 12, f'{label}: table exceeds 12 rows; split')
            elif bt == 'text':
                need(len(b.get('items',[])) <= 8, f'{label}: too many text items; split')
            elif bt == 'bars':
                vals = b.get('values',[])
                need(0 < len(vals) <= 10, f'{label}: bars require 1–10 values')
                need(all(isinstance(v.get('value'),(int,float)) and not isinstance(v.get('value'),bool) and math.isfinite(v['value']) for v in vals), f'{label}: non-finite bar values')
        if s.get('type') == 'visual_analysis':
            need(d['schema_version'] == 2, f'{label}: visual layout requires schema 2')
            need(len(s.get('blocks',[])) == 2 and s['blocks'][0]['type'] == 'visual', f'{label}: put substantive visualization on the left')
    if d['schema_version'] == 2:
        errors += visuals.validate(d)
        for i,s in enumerate(d['slides'],1):
            if s['type']=='visual_analysis':
                need(bool(s.get('headline')), f'Slide {i}: evidence-bound factual headline required')
    elif any(b['type'] in ('visual','brief') for s in d['slides'] for b in s.get('blocks',[])):
        need(False, 'New visual blocks require schema_version 2')
    errors += outlook.validate(d)
    return errors, warnings


def E(v):
    return escape(str(v), quote=True)


def bars(b):
    values = b['values']
    lo, hi = min(0, min(v['value'] for v in values)), max(0, max(v['value'] for v in values))
    span = hi-lo or 1
    if b.get('orientation') == 'vertical':
        count, height, baseline = len(values), 330, 365
        zero = baseline-(0-lo)/span*height
        parts = [f'<svg role="img" aria-label="{E(b["heading"])}" viewBox="0 0 1000 450">',f'<line x1="40" x2="960" y1="{zero}" y2="{zero}" stroke="#718096"/>']
        for i,v in enumerate(values):
            val=v['value']; x=100+i*(800/count); pos=baseline-(val-lo)/span*height
            y,h=min(zero,pos),abs(pos-zero);w=min(140,560/count)
            color='#c45137' if val<0 else ('#102745' if i==count-1 else '#aebbd0')
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"/><text x="{x+w/2}" y="{pos-14 if val>=0 else pos+30}" text-anchor="middle">{val:g}{E(b.get("unit",""))}</text><text x="{x+w/2}" y="418" text-anchor="middle">{E(v["label"])}</text>')
        return ''.join(parts)+'</svg>'
    left, width, row = 460, 650, 66
    zero = left + (-lo/span)*width
    parts = [f'<svg role="img" aria-label="{E(b["heading"])}" viewBox="0 0 1350 {len(values)*row+55}">', f'<line x1="{zero}" x2="{zero}" y1="10" y2="{len(values)*row+10}" stroke="#718096"/>']
    for i,v in enumerate(values):
        val, y = v['value'], 15+i*row
        pos = left+(val-lo)/span*width
        x, w = min(zero,pos), abs(pos-zero)
        color = '#c45137' if val<0 else ('#102745' if i==len(values)-1 else '#8196b5')
        parts.append(f'<text x="440" y="{y+31}" text-anchor="end">{E(v["label"])}</text><rect x="{x}" y="{y}" width="{w}" height="42" fill="{color}"/><text x="1130" y="{y+31}">{val:g}{E(b.get("unit",""))}</text>')
    return ''.join(parts)+'</svg>'


def block(b, d=None):
    if b['type'] == 'visual':
        source_map={s['id']:s for s in d['sources']}
        claim_map={c['id']:c for c in d['claims']}
        vmap={v['id']:v for v in d['visuals']};ms={m['id']:m for m in d['measures']}
        figures=[];count=len(b['visual_ids'])
        for vid in b['visual_ids']:
            v=vmap[vid];links=[];seen=set()
            for kid in v.get('claim_ids',[]):
                for ref in claim_map[kid]['source_refs']:
                    sid=ref['source_id']
                    if sid in seen:continue
                    seen.add(sid);s=source_map[sid]
                    target=s.get('url') or Path(s['path']).as_uri()
                    links.append(f'<a href="{E(target)}" target="_blank" rel="noopener" title="{E(ref["locator"])}">{E(s.get("short_title",sid))}</a>')
            note=visuals.display_note(v,ms)
            figures.append(f'<figure class="research-figure"><h3>{E(v["title"])}</h3>{visuals.render(v,ms,575 if count==1 else 270)}<figcaption>{E(note)} <span class="figure-sources">资料：{" / ".join(links)}</span></figcaption></figure>')
        return f'<article class="block visual-block {"stack" if count==2 else "single"}">'+''.join(figures)+'</article>'
    if b['type'] == 'brief':
        ms={m['id']:m for m in d['measures']};parts=[]
        if b.get('kpis'):
            parts.append('<div class="kpi-strip">'+''.join(f'<div><span>{E(k["label"])}</span><strong>{E(visuals.metric(ms[k["measure_id"]],True))}</strong></div>' for k in b['kpis'])+'</div>')
        for item in b.get('sections',[]):
            parts.append(f'<div class="brief-section"><h3>{E(item["label"])}</h3><p>{E(item["text"])}</p></div>')
        return '<article class="block brief-block">'+''.join(parts)+'</article>'
    head = f'<h3>{E(b["heading"])}</h3>'
    if b['type'] == 'table':
        rows = []
        for i, r in enumerate(b['rows']):
            rows.append(f'<tr class="{"focus" if i in b.get("focus_rows",[]) else ""}">'+''.join(f'<td>{E(x)}</td>' for x in r)+'</tr>')
        body = '<table><thead><tr>'+''.join(f'<th>{E(x)}</th>' for x in b['columns'])+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table>'
    elif b['type'] == 'bars':
        body = bars(b)
    else:
        body = ''.join(f'<p>{E(x)}</p>' for x in b.get('items',[]))
    return '<article class="block">'+head+body+'</article>'


def source_label(d, slide):
    claims = {c['id']:c for c in d['claims']}
    pairs = []
    for cid in slide['claim_ids']:
        for ref in claims[cid]['source_refs']:
            pair = f'{ref["source_id"]} {ref["locator"]}'
            if pair not in pairs:
                pairs.append(pair)
    return '；'.join(pairs)


def source_links(d, slide, compact=False):
    source_map={s['id']:s for s in d['sources']}
    claim_map={c['id']:c for c in d['claims']}
    if compact:
        grouped={}
        for cid in slide['claim_ids']:
            for ref in claim_map[cid]['source_refs']:
                locations=grouped.setdefault(ref['source_id'],[])
                if ref['locator'] not in locations:
                    locations.append(ref['locator'])
        short=[]
        for sid,locations in grouped.items():
            source=source_map[sid];target=source.get('url') or Path(source['path']).as_uri()
            name=source.get('short_title',source['title'])
            name=name if len(name)<=10 else name[:9]+'…'
            label=sid+' '+name if len(grouped)<=3 else sid
            title=source['title']+' / '+'；'.join(locations)
            short.append(f'<a class="source-short" href="{E(target)}" target="_blank" rel="noopener" title="{E(title)}" aria-label="{E(title)}">{E(label)}</a>')
        if not grouped:
            return ''
        detail=source_links(d,slide,False)
        return ''.join(short)+f'<details class="source-details"><summary>定位·{len(grouped)}源</summary><div class="source-panel">{detail}</div></details>'
    links=[];seen=set()
    for cid in slide['claim_ids']:
        for ref in claim_map[cid]['source_refs']:
            sid=ref['source_id'];loc=ref['locator'];pair=(sid,loc)
            if pair in seen: continue
            seen.add(pair);s=source_map[sid];target=s.get('url') or Path(s['path']).as_uri()
            if s.get('path') and re.search(r'\bp\.(\d+)',loc):target+='#page='+re.search(r'\bp\.(\d+)',loc).group(1)
            label=sid+' '+loc
            links.append(f'<a href="{E(target)}" target="_blank" rel="noopener" title="{E(s["title"]+" / "+loc)}">{E(label)}</a>')
    return '\n'.join(links)


def render_html(d):
    css = (ROOT/'assets'/'viewport-base.css').read_text(encoding='utf-8')+'\n'+(ROOT/'assets'/'report.css').read_text(encoding='utf-8')
    js = (ROOT/'assets'/'deck.js').read_text(encoding='utf-8')
    slides = []
    badge = {'DEMO_REFERENCE_ONLY':'参考稿重建 · 未经外部核验','DRAFT':'研究草稿 · 存在待核验项','REVIEW_READY':'研究复核稿'}[d['status']]
    for i,s in enumerate(d['slides'],1):
        footer = f'<footer><span class="footer-sources">{source_links(d,s,True)}</span><span>{E(d["period_start"])} 至 {E(d["period_end"])}　{i:02d}</span></footer>'
        if s['type'] == 'cover':
            toc = ''.join(f'<div class="toc-row"><b>{E(x["number"])}</b><strong>{E(x["label"])}</strong><span>{E(x["detail"])}</span></div>' for x in s.get('toc',[]))
            metrics = ''.join(f'<tr><td>{E(x["label"])}</td><td>{E(x["value"])}</td><td>{E(x.get("change",""))}</td></tr>' for x in s.get('metrics',[]))
            content = f'<div class="cover-main"><div class="eyebrow">{E(s.get("section","产业研究"))}</div><h1>{E(s["title"])}</h1><p class="subtitle">{E(s.get("subtitle",""))}</p><div class="toc">{toc}</div><p class="cover-note">{E("；".join(d["limitations"]))}</p></div><aside><h3>本期关键变量</h3><table>{metrics}</table><p>{E(badge)}</p></aside>'
        else:
            page_blocks = outlook.blocks(d,s)
            body = ''.join(block(b,d) for b in page_blocks)
            content = f'<header><div class="eyebrow">{E(s.get("section",""))}</div><h2>{E(s["title"])}</h2></header><div class="body-grid {"two" if len(page_blocks)==2 else "one"}">{body}</div><div class="takeaway"><b>{E(s.get("takeaway_label","研究判断"))}</b><p>{E(s.get("takeaway",""))}</p></div>'
        slides.append(f'<section class="slide {E(s["type"])} {"active visible" if i==1 else ""}" data-index="{i-1}"><div class="status">{E(badge)}</div>{content}{footer}</section>')
    return f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(d["title"])}</title><style>{css}</style></head><body class="schema-v{d["schema_version"]}"><div class="deck-viewport"><main class="deck-stage" id="deckStage">{"".join(slides)}</main></div><nav class="deck-controls"><button id="prev" aria-label="上一页">←</button><span id="counter"></span><button id="next" aria-label="下一页">→</button><button id="edit" title="E 编辑，Ctrl+S 另存">编辑</button><button id="save">另存</button><button id="exportPdf" title="打开打印界面，选择另存为 PDF；导出全部页面" aria-label="导出全部页面为 PDF">导出 PDF</button></nav><script>{js}</script></body></html>'


def render_md(d):
    lines = [f'# {d["title"]}', '', f'状态：{d["status"]}；覆盖：{d["period_start"]} 至 {d["period_end"]}；截止：{d["cutoff_at"]}（{d["timezone"]}）', '', *['- '+x for x in d['limitations']]]
    for i,s in enumerate(d['slides'],1):
        lines += ['',f'## {i:02d} {s["title"]}','']
        if s['type']=='cover':
            lines += [s.get('subtitle',''),'',*['- '+x['label']+'：'+x['detail'] for x in s.get('toc',[])]]
            if s.get('metrics'):
                lines += ['', '| 关键变量 | 数值/状态 | 变化 |','|---|---|---|']
                lines += ['| '+' | '.join(x.get(k,'') for k in ('label','value','change'))+' |' for x in s['metrics']]
        for b in outlook.blocks(d,s):
            lines += ['',f'### {b["heading"]}','']
            if b['type']=='visual':
                vm={v['id']:v for v in d['visuals']};mm={m['id']:m for m in d['measures']}
                for vid in b['visual_ids']:
                    v=vm[vid];lines += ['- 图形：'+v['title']+' ['+v.get('chart_type','unavailable')+']','- 口径：'+visuals.display_note(v,mm)]
                    lines += ['- '+mm[mid]['label']+'：'+visuals.metric(mm[mid],True)+'（'+mm[mid]['period']+'；'+mm[mid]['basis']+'）' for mid in v.get('measure_ids',[])]
                    if v.get('steps'):lines += ['- '+x['when']+' '+x['label']+('：'+visuals.metric(mm[x['measure_id']],True) if x.get('measure_id') else '')+' ['+visuals.STATES[x['status']]+']' for x in v['steps']]
                    if v.get('nodes'):lines += ['- '+x['label']+('：'+visuals.metric(mm[x['measure_id']],True) if x.get('measure_id') else '')+' ['+visuals.STATES[x['status']]+']' for x in v['nodes']]
            elif b['type']=='brief':
                mm={m['id']:m for m in d['measures']}
                lines += ['- '+k['label']+'：'+visuals.metric(mm[k['measure_id']],True) for k in b.get('kpis',[])]
                lines += ['- '+x['label']+'：'+x['text'] for x in b.get('sections',[])]
            elif b['type']=='table':
                cell = lambda x: str(x).replace('|','\\|').replace('\n','<br>')
                lines += ['| '+' | '.join(map(cell,b['columns']))+' |','|'+'|'.join(['---']*len(b['columns']))+'|']
                lines += ['| '+' | '.join(map(cell,r))+' |' for r in b['rows']]
            elif b['type']=='bars':
                lines += [f'- {v["label"]}：{v["value"]:g}{b.get("unit","")}' for v in b['values']]
            else:
                lines += ['- '+x for x in b.get('items',[])]
        lines += ['', '**'+s.get('takeaway_label','研究判断')+'**：'+s.get('takeaway',''), '', '证据：'+', '.join(s['claim_ids'])+'；'+source_label(d,s)]
    lines += ['', '## 主张与证据台账','']
    for c in d['claims']:
        lines += [f'### {c["id"]} [{c["kind"]} / {c["verification"]}]', c['text'], '']
        lines += [f'- {r["source_id"]}，{r["locator"]}：{r["evidence"]}' for r in c['source_refs']]
        if c.get('assumptions'):
            lines += ['- 假设：'+c['assumptions']]
    lines += ['', '## 来源索引','']
    for s in d['sources']:
        target = s.get('url') or Path(s['path']).as_uri()
        lines += [f'- {s["id"]} [{s["title"]}]({target})；{s["kind"]}/{s["access"]}；访问 {s.get("accessed_at") or "未知"}。{s.get("notes","")}']
    return '\n'.join(lines)+'\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    d = json.loads(a.input.read_text(encoding='utf-8-sig'))
    errors,warnings = validate(d, a.input.parent)
    if errors:
        raise SystemExit(json.dumps({'ok':False,'errors':errors,'warnings':warnings}, ensure_ascii=False, indent=2))
    if a.out.exists() and any(a.out.iterdir()):
        raise SystemExit('Output directory must be empty or new; previous editions are preserved.')
    a.out.mkdir(parents=True,exist_ok=True)
    for source in d['sources']:
        if source.get('provider') != 'ima':
            continue
        relative = Path(source['snapshot']['path'])
        origin = (a.input.parent/relative).resolve()
        target = (a.out/relative).resolve()
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            if target.read_bytes() != origin.read_bytes():
                raise SystemExit('Conflicting IMA evidence destinations')
        else:
            shutil.copy2(origin,target)
        source['path'] = str(target)
    (a.out/'report.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (a.out/'report.html').write_text(render_html(d),encoding='utf-8')
    (a.out/'report.md').write_text(render_md(d),encoding='utf-8')
    qa = {'ok':True,'errors':[],'warnings':warnings,'slides':len(d['slides']),'visual_qa':'NOT_RUN','semantic_fact_check':'NOT_ESTABLISHED_BY_BUILDER'}
    (a.out/'qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest = {'report_id':d['report_id'],'built_at':datetime.now().astimezone().isoformat(),'files':{f.relative_to(a.out).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in a.out.rglob('*') if f.is_file()}}
    (a.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'out':str(a.out.resolve()),**qa},ensure_ascii=False))


if __name__=='__main__':
    main()

"""Offline regression checks for evidence boundaries and authoring behavior."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('builder',root/'scripts/build_report.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
base=json.loads((root/'assets/example-report.json').read_text(encoding='utf-8'))
results=[]


def rejected(name, mutate):
    d=deepcopy(base)
    mutate(d)
    errors,_=builder.validate(d)
    assert errors, name
    results.append({'check':name,'passed':True,'rejection':errors[0]})


assert not builder.validate(base)[0]
results.append({'check':'reference demo accepted without pretending live verification','passed':True})
rejected('reference material cannot establish supported fact',lambda d:d['claims'][0].update(verification='supported'))
rejected('unverified report cannot be REVIEW_READY',lambda d:d.update(status='REVIEW_READY',mode='weekly'))
rejected('unknown claim breaks evidence chain',lambda d:d['slides'][0].update(claim_ids=['NO_SUCH_CLAIM']))
rejected('duplicate event key',lambda d:d['events'].append(deepcopy(d['events'][0])))
rejected('ragged table',lambda d:d['slides'][1]['blocks'][0]['rows'].append(['incomplete']))
rejected('nonfinite chart value',lambda d:d['slides'][4]['blocks'][0]['values'][0].update(value=float('nan')))
rejected('unsafe source URL',lambda d:d['sources'][0].update(url='javascript:alert(1)'))
rejected('post cutoff event',lambda d:d['events'][0].update(occurred_at='2026-10-20'))
rejected('inference without assumptions',lambda d:d['claims'][2].pop('assumptions'))
def future(d):
    d.update(mode='weekly',status='DRAFT')
    d['sources'][0]['published_at']='2026-10-20T00:00:00+08:00'
rejected('post cutoff source including calendar',future)
hostile=deepcopy(base);hostile['slides'][1]['title']='<script>throw 123</script>'
html=builder.render_html(hostile)
assert '<script>throw 123</script>' not in html and '&lt;script&gt;throw 123&lt;/script&gt;' in html
results.append({'check':'input content is escaped','passed':True})
for vals in ([0,0],[-4,2],[-5,-2]):
    for orientation in ('vertical','horizontal'):
        svg=builder.bars({'heading':'edge cases','unit':'%','orientation':orientation,'values':[{'label':str(i),'value':v} for i,v in enumerate(vals)]})
        assert 'nan' not in svg.lower() and '<svg' in svg
results.append({'check':'signed and zero chart domains render','passed':True})
with tempfile.TemporaryDirectory(prefix='financial-skill-check-') as td:
    temp=Path(td);inp=temp/'input.json';inp.write_text(json.dumps(base,ensure_ascii=False),encoding='utf-8')
    command=[sys.executable,'-X','utf8',str(root/'scripts/build_report.py'),str(inp),'--out',str(temp/'edition')]
    subprocess.run(command,check=True,capture_output=True)
    before=(temp/'edition/report.html').read_bytes()
    second=subprocess.run(command,capture_output=True)
    assert second.returncode!=0 and before==(temp/'edition/report.html').read_bytes()
results.append({'check':'real build succeeds; edition overwrite refused','passed':True})
print(json.dumps({'ok':True,'checks':results},ensure_ascii=False,indent=2))

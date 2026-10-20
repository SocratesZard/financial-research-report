"""Resolve visual measurements and choose chart types before report rendering."""
import argparse
import json
from pathlib import Path
from visuals import prepare

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('input',type=Path)
 ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--plan',type=Path,required=True)
 a=ap.parse_args()
 if len({a.input.resolve(),a.out.resolve(),a.plan.resolve()})!=3 or a.out.exists() or a.plan.exists():
  ap.error('Input, prepared output and plan must be distinct; outputs must be new.')
 data=prepare(json.loads(a.input.read_text(encoding='utf-8-sig')))
 plan={'report_id':data['report_id'],'measures':data['measures'],'visuals':data['visuals'],'missing_policy':'No estimates or series completion; unavailable visuals carry explicit reasons.'}
 for path,value in ((a.out,data),(a.plan,plan)):
  path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'prepared':str(a.out),'plan':str(a.plan),'visuals':len(data['visuals'])},ensure_ascii=False))

if __name__=='__main__':main()

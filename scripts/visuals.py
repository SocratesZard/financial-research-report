"""Evidence-bound visualization planning and native SVG rendering (standard library)."""
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html import escape
import math
import re
import unicodedata

CHARTS={'bar','grouped_bar','line','stacked_bar','dumbbell','timeline','flow','matrix'}
INTENTS={'comparison','time','composition','revision','milestones','mechanism','ranking','matrix'}
PALETTE=['#102745','#718aaa','#b5c4d8','#3869a6']
STATES={'confirmed':'已披露','ongoing':'进行中','planned':'计划/预计','conditional':'附条件','unknown':'未核实','inference':'推断'}

def E(x):return escape(str(x),quote=True)
def finite(v):
 if isinstance(v,bool):raise ValueError('Boolean is not a measurement')
 d=Decimal(str(v))
 if not d.is_finite():raise ValueError('Non-finite measurement')
 return d
def fmt(x,p=None):
 if isinstance(x,float):x=f'{x:.8g}'
 d=finite(x)
 if p is not None:d=d.quantize(Decimal(1).scaleb(-p),rounding=ROUND_HALF_UP)
 s=f'{d:,.{p}f}' if p is not None else f'{d:,f}'.rstrip('0').rstrip('.') if '.' in str(d) else f'{d:,f}'
 return s
def _claim(pool,kid):
 if kid not in pool:raise ValueError('Unknown claim '+str(kid))
 c=pool[kid]
 if c['verification'] not in ('supported','corroborated'):raise ValueError('Visual fact requires supported claim '+kid)
 return c
def unit_signature(unit,currency):
 names={'USD':'美元','HKD':'港元','TWD':'新台币','KRW':'韩元','CNY':'人民币'}
 for code,name in names.items():
  if unit.endswith(code):unit=unit[:-len(code)];currency=code
  if unit.endswith(name):unit=unit[:-len(name)];currency=code
 for prefix,factor in [('万亿','1e12'),('十亿','1e9'),('百万','1e6'),('亿','1e8'),('万','1e4')]:
  if unit.startswith(prefix):return unit[len(prefix):],currency,Decimal(factor)
 return unit,currency,Decimal(1)
def measurements(d):
 """Resolve requested values before page writing. No estimates or missing-value fills."""
 claims={c['id']:c for c in d['claims']}
 numbers={n['id']:(n,c) for c in d['claims'] for n in c.get('numbers',[]) if n.get('id')}
 calcs={c['id']:c for c in d.get('calculations',[])}
 result={}
 for spec in d.get('measure_specs',[]):
  mid=spec['id']
  if mid in result:raise ValueError('Duplicate measurement '+mid)
  binding=spec['binding'];kind=binding['kind'];factor=finite(binding.get('factor','1'))
  if factor<=0:raise ValueError('Unit conversion factor must be positive')
  if kind=='number':
   n,c=numbers[binding['id']];_claim(claims,c['id'])
   value=finite(n['normalized_value']);unit=n['unit'];currency=n.get('currency')
   provenance={'number_id':n['id'],'claim_ids':[c['id']],'source_refs':c['source_refs'],'raw_value':str(value),'raw_unit':unit,'raw_currency':currency}
   basis=n['basis'];period=n['period']
  elif kind=='calculation':
   calc=calcs[binding['id']]
   if calc['operation'] not in ('ratio_pct','change_pct','difference'):raise ValueError('Unsupported calculation binding')
   vals=[];kids=[]
   for nid in calc['input_ids']:
    n,c=numbers[nid];_claim(claims,c['id']);vals.append(finite(n['normalized_value']));kids.append(c['id'])
   input_records=[numbers[nid][0] for nid in calc['input_ids']]
   if len({(n['unit'],n['currency']) for n in input_records})!=1:raise ValueError('Mixed calculation input units')
   if calc['operation']=='ratio_pct' and len({n['period'] for n in input_records})!=1:raise ValueError('Ratio input periods differ')
   if len(vals)!=2:raise ValueError('Calculation needs two inputs')
   a,b=vals
   if calc['operation']!='difference' and b==0:raise ValueError('Zero denominator')
   actual=a-b if calc['operation']=='difference' else (a/b-(1 if calc['operation']=='change_pct' else 0))*100
   if actual.quantize(Decimal(1).scaleb(-calc['decimals']),rounding=ROUND_HALF_UP)!=finite(calc['result']):raise ValueError('Unverified calculation '+calc['id'])
   value=finite(calc['result']);unit=calc['unit'];currency=None;basis='researcher_calculation';period=calc['scope']
   provenance={'calculation_id':calc['id'],'claim_ids':sorted(set(kids)),'formula':calc['formula'],'raw_value':str(value),'raw_unit':unit,'raw_currency':None,'input_bases':[n['basis'] for n in input_records]}
  elif kind=='claim_literal':
   c=_claim(claims,binding['claim_id']);literal=binding['literal']
   if literal not in c['text']:raise ValueError('Literal absent from claim')
   token=str(binding['value'])
   if not re.search(r'(?<![\d.])'+re.escape(token)+r'(?![\d.])',literal):raise ValueError('Value not present in literal')
   value=finite(token);unit=binding['unit'];currency=binding.get('currency');basis=binding['basis'];period=binding['period']
   provenance={'claim_ids':[c['id']],'literal':literal,'source_refs':c['source_refs'],'raw_value':token,'raw_unit':unit,'raw_currency':currency}
  else:raise ValueError('Unsupported binding '+kind)
  if factor!=1 and not binding.get('conversion_note'):raise ValueError('Explicit unit conversion note required')
  target=spec.get('unit',unit)
  if target!=unit and not binding.get('conversion_note'):raise ValueError('Relabelled units need conversion note')
  old_dim,old_currency,old_scale=unit_signature(unit,currency)
  new_dim,new_currency,new_scale=unit_signature(target,currency)
  if (old_dim,old_currency)!=(new_dim,new_currency) or factor!=old_scale/new_scale:raise ValueError('Unapproved dimensional conversion '+mid)
  result[mid]={'id':mid,'label':spec['label'],'value':str(value*factor),'unit':target,'currency':currency,'period':period,'basis':basis,'precision':spec.get('precision'),'provenance':provenance,'conversion_note':binding.get('conversion_note'),'approximate':spec.get('approximate',False)}
  result[mid]['certainty']=next((x for x in ('company_forecast','third_party_estimate','media_report') if x in provenance.get('input_bases',[basis])),basis)
 return result

def select_chart(v,ms):
 intent=v['intent'];ids=v.get('measure_ids',[])
 if intent=='time':
  # Few independent dates carry no evidence of continuous change.
  return ('line','至少4个实际观测点，按记录时间轴连接；不补缺期。') if len(ids)>=4 and v.get('time_axis') else ('bar','仅少量观测点；采用离散比较，不伪装连续趋势。')
 if intent in ('comparison','ranking'):
  return ('grouped_bar','同口径多指标分组比较。') if v.get('series') else ('bar','同口径数值直接比较；长标签优先水平条形。')
 return {'composition':('stacked_bar','已核占比；余段仅标未覆盖，不补造用途。'),'revision':('dumbbell','同期间前后预测版本，用连接点表示修订。'),'milestones':('timeline','披露日期和状态分开，未知日期使用有序节点。'),'mechanism':('flow','有来源的主体/范围/阶段关系；推断显式标注。'),'matrix':('matrix','按列明确单位与期间，不跨列混排大小。')}[intent]

def validate_visual(v,ms,claims):
 vid=v['id']
 if v.get('status')=='unavailable':
  if not v.get('reason'):raise ValueError(vid+': unavailable needs reason')
  return
 if v.get('chart_type') not in CHARTS:raise ValueError(vid+': unknown chart type')
 if not v.get('title') or not v.get('scope_note') or not v.get('claim_ids'):raise ValueError(vid+': title/scope/evidence required')
 for kid in v['claim_ids']:_claim(claims,kid)
 ids=v.get('measure_ids',[])
 extra=[a.get('measure_id') for a in v.get('annotations',[])]+[n.get('measure_id') for n in v.get('nodes',[])]+[s.get('measure_id') for s in v.get('steps',[])]
 for mid in [m for m in extra if m]:
  if mid not in ms or not set(ms[mid]['provenance']['claim_ids'])<=set(v['claim_ids']):raise ValueError(vid+': annotation/node measure evidence missing')
 for mid in ids:
  if mid not in ms:raise ValueError(vid+': missing measurement '+mid)
  if not set(ms[mid]['provenance']['claim_ids'])<=set(v['claim_ids']):raise ValueError(vid+': measurement claim missing')
 typ=v['chart_type']
 if typ in ('bar','grouped_bar','line','stacked_bar','dumbbell'):
  if not ids:raise ValueError(vid+': numeric chart has no values')
  if len({(ms[i]['unit'],ms[i]['currency']) for i in ids})!=1:raise ValueError(vid+': mixed units/currencies')
  if not v.get('comparison_basis'):raise ValueError(vid+': numeric comparison needs economic scope')
 if typ=='line':
  if len(ids)<4 or len(v.get('time_axis',[]))!=len(ids):raise ValueError(vid+': sparse/missing time axis cannot be a line')
  axis=v['time_axis']
  if len(set(axis))!=len(axis) or axis!=sorted(axis):raise ValueError(vid+': time axis not strictly ordered')
  def key(period):
   if re.fullmatch(r'\d{4}Q[1-4]|\d{4}-\d{2}(?:-\d{2})?',period):return period
   match=re.fullmatch(r'(\d{4})年(\d{1,2})月',period)
   return f'{match[1]}-{int(match[2]):02d}' if match else None
  if any(key(ms[mid]['period'])!=t for mid,t in zip(ids,axis)):raise ValueError(vid+': time key must match observed period')
 if v.get('intent')=='ranking' and len({ms[mid]['period'] for mid in ids})>1 and not v.get('comparability_note'):raise ValueError(vid+': cross-period ranking needs comparability note')
 if typ=='dumbbell':
  if len(ids)!=2 or ms[ids[0]]['period']!=ms[ids[1]]['period']:raise ValueError(vid+': revision must compare same period')
 if v.get('axis_domain'):
  a,b=map(float,v['axis_domain'])
  if typ not in ('line','dumbbell') or not a<b or any(not a<=float(ms[mid]['value'])<=b for mid in ids):raise ValueError(vid+': invalid/truncated axis domain')
 if typ=='grouped_bar':
  series=v.get('series',[]);rows=v.get('groups',[])
  if not 1<len(series)<=3 or not rows or len(ids)!=len(series)*len(rows):raise ValueError(vid+': grouped chart dimensions')
 if typ=='stacked_bar':
  vals=[finite(ms[i]['value']) for i in ids]
  if ms[ids[0]]['unit']!='%' or any(x<0 for x in vals) or sum(vals)>Decimal('100'):raise ValueError(vid+': invalid percentage parts')
 if typ=='timeline':
  steps=v.get('steps',[])
  if not 2<=len(steps)<=6:raise ValueError(vid+': 2–6 meaningful milestones')
  for x in steps:
   if x.get('status') not in STATES or not x.get('when'):raise ValueError(vid+': milestone state/date label missing')
   for kid in x.get('claim_ids',[]):_claim(claims,kid)
   if not set(x.get('claim_ids',[]))<=set(v['claim_ids']):raise ValueError(vid+': step evidence omitted')
   if not x.get('claim_ids'):raise ValueError(vid+': milestone evidence missing')
   if x.get('measure_id') and x['measure_id'] not in ms:raise ValueError(vid+': milestone measure missing')
  if v.get('calendar_axis') and not all(isinstance(x.get('year'),(int,float)) for x in steps):raise ValueError(vid+': calendar timeline needs known years, not fabricated dates')
 if typ=='flow':
  nodes=v.get('nodes',[]);nodeids={x['id'] for x in nodes}
  if not 2<=len(nodes)<=9 or len(nodeids)!=len(nodes):raise ValueError(vid+': flow nodes 2–9 unique')
  for x in nodes:
   if not x.get('claim_ids') or x.get('status') not in STATES:raise ValueError(vid+': node source/state required')
   for kid in x['claim_ids']:_claim(claims,kid)
   if not set(x['claim_ids'])<=set(v['claim_ids']):raise ValueError(vid+': node evidence omitted')
   if x.get('measure_id') and x['measure_id'] not in ms:raise ValueError(vid+': unknown node measure')
  for edge in v.get('edges',[]):
   if edge['from'] not in nodeids or edge['to'] not in nodeids:raise ValueError(vid+': dangling edge')
   if edge.get('kind') not in ('scope','sequence','conditional','inference'):raise ValueError(vid+': relation kind required')
   if not edge.get('claim_ids'):raise ValueError(vid+': relationship evidence required')
   for kid in edge['claim_ids']:_claim(claims,kid)
   if not set(edge['claim_ids'])<=set(v['claim_ids']):raise ValueError(vid+': relation evidence omitted')
   if edge['kind']=='inference' and not edge.get('assumption'):raise ValueError(vid+': inference edge needs assumption')
 if typ=='matrix':
  cols=v.get('columns',[])
  if not cols or not v.get('rows'):raise ValueError(vid+': empty matrix')
  for row in v['rows']:
   if len(row['measure_ids'])!=len(cols):raise ValueError(vid+': ragged matrix')
   for mid in row['measure_ids']:
    if mid not in ids:raise ValueError(vid+': matrix evidence absent')
  for j,col in enumerate(cols):
   if any(ms[row['measure_ids'][j]]['unit']!=col['unit'] for row in v['rows']):raise ValueError(vid+': matrix column unit mismatch')

def prepare(d):
 ms=measurements(d);claims={c['id']:c for c in d['claims']}
 d['measures']=list(ms.values())
 for v in d.get('visuals',[]):
  if v.get('status')=='unavailable':validate_visual(v,ms,claims);continue
  if v['intent'] not in INTENTS:raise ValueError('Unknown research intent')
  if v['intent']=='ranking':v['measure_ids']=sorted(v['measure_ids'],key=lambda mid:finite(ms[mid]['value']),reverse=v.get('sort_order','descending')!='ascending')
  chosen,reason=select_chart(v,ms)
  if v.get('chart_type') and v['chart_type']!=chosen:
   if not v.get('override_reason'):raise ValueError('Chart override needs reason')
  else:v['chart_type']=chosen
  v['selection_reason']=reason;v['status']='ready'
  validate_visual(v,ms,claims)
 for slide in d['slides']:
  h=slide.get('headline')
  if h:slide['title']=headline(h,ms)
  for metric_ in slide.get('metrics',[]):
   if metric_.get('measure_id'):
    m=ms[metric_['measure_id']];metric_['value']=fmt(m['value'],metric_.get('precision',m.get('precision')))+m['unit']
 return d

def headline(h,ms):
 title=h['subject']+h['event']
 for part in h.get('facts',[]):
  m=ms[part['measure_id']]
  if part.get('suffix') is not None and m['unit'] not in part['suffix'] and m['unit'] not in part.get('prefix','')+h['event']:raise ValueError('Headline number must retain its unit')
  value=finite(m['value']);direction=''
  if part.get('directional'):
   direction='增长' if value>0 else '下降' if value<0 else '持平'
   value=abs(value)
  title+=part.get('prefix','')+direction+('约' if m.get('approximate') else '')+fmt(value,part.get('precision',m.get('precision')))+part.get('suffix',m['unit'])
 return title+h.get('suffix','')

def validate(d):
 errors=[];ms={m['id']:m for m in d.get('measures',[])};vs={}
 try:
  expected=measurements(d)
  if set(ms)!=set(expected):raise ValueError('Prepared measure IDs differ from requested data')
  for mid,m in expected.items():
   if ms[mid]!=m:raise ValueError('Prepared measure/provenance tampered: '+mid)
  for v in d.get('visuals',[]):
   if v['id'] in vs:raise ValueError('Duplicate visual id')
   vs[v['id']]=v;validate_visual(v,ms,{c['id']:c for c in d['claims']})
  for s in d['slides']:
   if s.get('headline') and s['title']!=headline(s['headline'],ms):raise ValueError('Headline differs from evidence-bound values')
   for part in s.get('headline',{}).get('facts',[]):
    if not set(ms[part['measure_id']]['provenance']['claim_ids'])<=set(s['claim_ids']):raise ValueError('Headline evidence omitted')
   for metric_ in s.get('metrics',[]):
    if metric_.get('measure_id'):
     m=ms[metric_['measure_id']]
     if metric_['value']!=fmt(m['value'],metric_.get('precision',m.get('precision')))+m['unit'] or not set(m['provenance']['claim_ids'])<=set(s['claim_ids']):raise ValueError('Cover metric differs from bound evidence')
   for b in s.get('blocks',[]):
    if b['type']=='visual':
     if not 1<=len(b.get('visual_ids',[]))<=2:raise ValueError('Visual block needs 1–2 figures')
     for vid in b['visual_ids']:
      if vid not in vs:raise ValueError('Unknown visual '+vid)
      if not set(vs[vid].get('claim_ids',[]))<=set(s['claim_ids']):raise ValueError('Slide omits visual evidence')
    if b['type']=='brief':
     for item in b.get('kpis',[]):
      if item['measure_id'] not in ms:raise ValueError('Unknown KPI measure')
     if len(b.get('sections',[]))>4:raise ValueError('At most four concise analysis sections')
 except (KeyError,TypeError,ValueError,InvalidOperation) as exc:errors.append('Visualization: '+str(exc))
 return errors

# SVG building blocks. Sizes refer to the fixed 1920px stage, not device pixels.
def width_units(s):return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in str(s))
def wrapped(s,max_units):
 out=[];line=''
 for c in str(s):
  if c=='\n' or width_units(line+c)>max_units:
   out.append(line);line='' if c=='\n' else c
  else:line+=c
 if line:out.append(line)
 return out or ['']
def text(x,y,s,size=26,anchor='start',color='#102745',weight='400',units=None,css=''):
 lines=wrapped(s,units) if units else str(s).split('\n')
 return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{color}" font-weight="{weight}" class="{css}">'+''.join(f'<tspan x="{x}" dy="{0 if i==0 else size*1.35}">{E(line)}</tspan>' for i,line in enumerate(lines))+'</text>'
def line(x1,y1,x2,y2,stroke='#cbd4df',dash='',width=1.3):
 return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}" '+(f'stroke-dasharray="{dash}"' if dash else '')+'/>'
def rect(x,y,w,h,fill,stroke='none',dash=''):
 return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" '+(f'stroke-dasharray="{dash}"' if dash else '')+'/>'
def nice_scale(values):
 lo=min(0,min(values));hi=max(0,max(values))
 if lo==hi:hi=lo+1
 raw=(hi-lo)/5;power=10**math.floor(math.log10(raw));step=next((n*power for n in [1,2,2.5,5,10] if n*power>=raw),10*power)
 lo=math.floor(lo/step)*step;hi=math.ceil(hi/step)*step
 return lo,hi,[lo+i*step for i in range(round((hi-lo)/step)+1)]
def metric(m,unit=False):
 return ('约' if m.get('approximate') else '')+fmt(m['value'],m.get('precision'))+(m['unit'] if unit else '')
def display_note(v,ms):
 note=v.get('scope_note',v.get('reason',''))
 if v.get('chart_type') in ('bar','grouped_bar') and 'E' not in note:
  bases={ms[mid].get('certainty',ms[mid]['basis']) for mid in v.get('measure_ids',[])}
  if bases & {'company_forecast','third_party_estimate'}:note+=' E：公司初估/预测或机构估计。'
 return note

def numeric(v,ms,height):
 ids=v['measure_ids'];values=[float(ms[i]['value']) for i in ids];lo,hi,ticks=nice_scale(values)
 if v.get('axis_domain'):
  lo,hi=map(float,v['axis_domain']);ticks=[lo+i*(hi-lo)/4 for i in range(5)]
 x0,x1=225,850;y0,y1=72,height-96
 scale=lambda a:x0+(a-lo)/(hi-lo)*(x1-x0)
 out=[text(970,32,ms[ids[0]]['unit'],21,'end',color='#65748a')]
 for t in ticks:
  x=scale(t);out+=[line(x,y0,x,y1),text(x,y1+39,fmt(t),21,'middle',color='#65748a')]
 if lo<=0<=hi:out.append(line(scale(0),y0,scale(0),y1,'#718aaa',width=1.8))
 typ=v['chart_type']
 if typ=='dumbbell':
  y=(y0+y1)/2
  a,b=[scale(val) for val in values]
  out+=[line(a,y,b,y,'#3869a6',width=8)]
  for j,(mid,x) in enumerate(zip(ids,[a,b])):
   m=ms[mid];out += [f'<circle cx="{x}" cy="{y}" r="13" fill="{PALETTE[1-j]}" stroke="#fff" stroke-width="3"/>',text(x,y-58 if j==0 else y+67,metric(m),35,'middle',weight='700'),text(x,y-112 if j==0 else y+120,m['label'],24,'middle',color='#65748a')]
  for j,call in enumerate(v.get('annotations',[])):out.append(text(40,65+j*45,call['label']+metric(ms[call['measure_id']],True),25,weight='700'))
 elif typ=='line':
  # Time geometry uses supplied observed indices. Never creates new observations.
  axis=v['time_axis']
  def time_pos(t):
   if re.fullmatch(r'\d{4}-\d{2}',t):return int(t[:4])*12+int(t[-2:])
   if re.fullmatch(r'\d{4}Q[1-4]',t):return int(t[:4])*4+int(t[-1])
   return datetime.fromisoformat(t).timestamp()/86400
  pos=[time_pos(t) for t in axis]
  if pos!=sorted(set(pos)):raise ValueError('Invalid observed time coordinates')
  # A line needs numeric y-axis, rather than reuse horizontal value-axis grid.
  out=[];left,right,top,bottom=110,880,65,height-105
  yy=lambda a:bottom-(a-lo)/(hi-lo)*(bottom-top)
  for t in ticks:out += [line(left,yy(t),right,yy(t)),text(left-16,yy(t)+8,fmt(t),22,'end',color='#65748a')]
  xx=lambda a:left+(a-pos[0])/(pos[-1]-pos[0])*(right-left)
  pts=[(xx(p),yy(val)) for p,val in zip(pos,values)]
  out += [f'<polyline points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="#102745" stroke-width="3"/>',text(left,32,ms[ids[0]]['unit'],21)]
  for i,((x,y),mid) in enumerate(zip(pts,ids)):
   out += [f'<circle cx="{x}" cy="{y}" r="5" fill="#102745"/>',text(x,bottom+38,axis[i],20,'middle')]
   if i in (0,len(ids)-1):out.append(text(x,y-17,metric(ms[mid]),23,'middle',weight='700'))
 else:
  groups=v.get('groups',[]) if typ=='grouped_bar' else [ms[i]['label'] for i in ids]
  series=v.get('series',[]) if typ=='grouped_bar' else ['value']
  n=len(groups);row=(y1-y0)/n;bar_h=min(42,(row-30)/len(series))
  for i,label in enumerate(groups):
   cy=y0+row*(i+.5);out.append(text(x0-20,cy+7,label,25,'end',units=15))
   for j,_ in enumerate(series):
    k=i*len(series)+j;m=ms[ids[k]];value=values[k]
    y=cy+(j-(len(series)-1)/2)*(bar_h+9)-bar_h/2
    xx=scale(value);xx0=scale(0);color=PALETTE[j if len(series)>1 else (0 if i==n-1 else 1)]
    forecast=m.get('certainty',m['basis']) in ('company_forecast','third_party_estimate')
    out.append(rect(min(xx,xx0),y,max(abs(xx-xx0),1),bar_h,color,color,'6 4' if forecast else ''))
    if forecast:out.append(rect(min(xx,xx0),y,max(abs(xx-xx0),1),bar_h,f'url(#hatch-{E(v["id"])})'))
    out.append(text(xx+(12 if value>=0 else -12),y+bar_h*.77,metric(m)+(' E' if forecast else ''),24,'start' if value>=0 else 'end',weight='600'))
  if len(series)>1:
   for j,label in enumerate(series):out += [rect(240+j*230,14,28,15,PALETTE[j]),text(280+j*230,30,label,23)]
 return ''.join(out)

def stacked(v,ms,height):
 ids=v['measure_ids'];out=[];x,y,w,h=55,(45 if height<400 else 90),890,64;used=0
 for j,mid in enumerate(ids):
  m=ms[mid];value=float(m['value']);part=w*value/100
  out.append(rect(x+used*w/100,y,part,h,PALETTE[j]))
  if part>100:out.append(text(x+(used+value/2)*w/100,y+43,metric(m,True),29,'middle','#fff','700'))
  out += [rect(60,(152 if height<400 else 202)+j*58,24,16,PALETTE[j]),text(100,(170 if height<400 else 220)+j*58,m['label'],25)]
  used+=value
 if used<100:
  out += [rect(x+used*w/100,y,w*(100-used)/100,h,'#edf1f6','#b5c4d8'),text(x+(used+100)/2*w/100,y+41,'未细分',24,'middle',color='#65748a'),text(60,(235 if height<400 else 278),'浅灰余段仅表示未列示占比，不新增用途拆分。',22,color='#65748a')]
 return ''.join(out)

def timeline(v,ms,height):
 steps=v['steps'];n=len(steps);x0,x1=90,900
 if v.get('orientation')=='vertical':
  if v.get('calendar_axis'):raise ValueError('Vertical ordinal timeline must not claim scaled calendar spacing')
  ys=[60+i*(height-245)/(n-1) for i in range(n)];out=[];x=285
  for i in range(n-1):out.append(line(x,ys[i]+10,x,ys[i+1]-10,'#718aaa','7 6',3))
  for y,step in zip(ys,steps):
   known=step['status'] in ('confirmed','ongoing')
   out += [f'<circle cx="{x}" cy="{y}" r="11" fill="{"#102745" if known else "#fff"}" stroke="#718aaa" stroke-width="3"/>',text(x-30,y+8,step['when'],26,'end'),text(x+42,y+8,step['label'],29,weight='600',units=38),text(x+42,y+87,STATES[step['status']],23,color='#65748a')]
   if step.get('measure_id'):out.append(text(x+42,y+130,metric(ms[step['measure_id']],True),31,weight='700'))
  return ''.join(out)
 if v.get('calendar_axis'):
  vals=[s['year'] for s in steps];lo=min(vals);hi=max(vals)
  xs=[x0+(a-lo)/(hi-lo or 1)*(x1-x0) for a in vals]
 else:xs=[x0+i*(x1-x0)/(n-1) for i in range(n)]
 y=height*(.30 if height<400 else .43)
 out=[]
 for i in range(n-1):out.append(line(xs[i],y,xs[i+1],y,'#718aaa','7 6' if steps[i+1]['status']!='confirmed' else '',3))
 for i,(x,step) in enumerate(zip(xs,steps)):
  known=step['status'] in ('confirmed','ongoing')
  anchor='start' if i==0 else 'end' if i==n-1 else 'middle'
  date_lines=len(wrapped(step['when'],18))
  if v.get('calendar_axis') and step.get('year_end'):
   xe=x0+(step['year_end']-lo)/(hi-lo or 1)*(x1-x0)
   out.append(rect(x,y-8,xe-x,16,'#b5c4d8'))
  out += [f'<circle cx="{x}" cy="{y}" r="10" fill="{"#102745" if known else "#fff"}" stroke="#718aaa" stroke-width="3"/>',text(x,max(28,y-32-(date_lines-1)*25*1.35),step['when'],25,anchor,weight='700',units=18),text(x,y+48,step['label'],25,anchor,units=16),text(x,y+121,STATES[step['status']],21,anchor,color='#65748a')]
  if step.get('measure_id'):out.append(text(x,y+(158 if height<400 else 168),metric(ms[step['measure_id']],True),25,anchor,weight='700'))
 return ''.join(out)

def flow(v,ms,height):
 nodes=v['nodes'];columns=max(x['column'] for x in nodes)+1;rows=max(x['row'] for x in nodes)+1
 bw=min(260,850/columns);bh=min(132,(height-50)/rows-22)
 positions={}
 for n in nodes:positions[n['id']]=(48+n['column']*(895-bw)/(columns-1 or 1),30+n['row']*(height-70-bh)/(rows-1 or 1))
 out=[]
 for edge in v.get('edges',[]):
  a,b=positions[edge['from']],positions[edge['to']];x1,y1=a[0]+bw,a[1]+bh/2;x2,y2=b[0],b[1]+bh/2
  mid=(x1+x2)/2;dash=' stroke-dasharray="7 5"' if edge['kind'] in ('conditional','inference') else ''
  out.append(f'<path d="M{x1},{y1} C{mid},{y1} {mid},{y2} {x2-8},{y2}" fill="none" stroke="#718aaa" stroke-width="2.5" marker-end="url(#arrow-{E(v["id"])})"{dash}/>')
  if edge['kind']=='inference':out.append(text(mid,(y1+y2)/2-9,'推断',20,'middle',color='#8a5b38'))
 for n in nodes:
  x,y=positions[n['id']];known=n['status'] in ('confirmed','ongoing')
  out += [rect(x,y,bw,bh,'#edf2f8' if known else '#fff','#718aaa','' if known else '7 5'),text(x+18,y+34,n['label'],25,weight='600',units=17)]
  if n.get('measure_id'):out.append(text(x+18,y+bh-46,metric(ms[n['measure_id']],True),29,weight='700'))
  out.append(text(x+18,y+bh-13,STATES[n['status']],19,color='#65748a'))
 return ''.join(out)

def matrix(v,ms,height):
 rows=v['rows'];cols=v['columns'];left=40;top=50;labelw=260;colw=(930-labelw)/len(cols);rowh=min(90,(height-100)/(len(rows)+1));out=[]
 for j,col in enumerate(cols):out.append(text(left+labelw+j*colw+colw/2,top,col['label']+'\n'+col['unit'],22,'middle',weight='700',units=20))
 for i,row in enumerate(rows):
  y=top+rowh*(i+1)+20;out += [line(left,y+25,970,y+25),text(left,y,row['label'],25,units=18)]
  for j,mid in enumerate(row['measure_ids']):out.append(text(left+labelw+j*colw+colw/2,y,metric(ms[mid]),27,'middle',weight='600'))
 return ''.join(out)

def render(v,ms,height=575):
 if v['status']=='unavailable':return '<div class="visual-unavailable">'+E(v['reason'])+'</div>'
 typ=v['chart_type'];vid=E(v['id'])
 defs=f'<defs><pattern id="hatch-{vid}" width="9" height="9" patternUnits="userSpaceOnUse"><path d="M-2,2 L2,-2 M0,9 L9,0 M7,11 L11,7" stroke="white" stroke-opacity=".3" stroke-width="2"/></pattern><marker id="arrow-{vid}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 1 L9 5 L0 9" fill="none" stroke="#718aaa" stroke-width="1.5"/></marker></defs>'
 draw=(numeric(v,ms,height) if typ in ('bar','grouped_bar','line','dumbbell') else stacked(v,ms,height) if typ=='stacked_bar' else timeline(v,ms,height) if typ=='timeline' else flow(v,ms,height) if typ=='flow' else matrix(v,ms,height))
 return f'<svg class="research-chart" data-chart-id="{vid}" data-chart-type="{typ}" role="img" aria-label="{E(v["title"]+"；"+v["scope_note"])}" viewBox="0 0 1000 {height}"><title>{E(v["title"])}</title><desc>{E(v["scope_note"])}</desc>{defs}{draw}</svg>'


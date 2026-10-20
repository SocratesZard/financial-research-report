"""Synthetic offline tests. Values are test fixtures, never research inputs."""
import unittest
import xml.etree.ElementTree as ET
from copy import deepcopy
from visuals import prepare,validate,render

def fixture(values,unit='%',periods=None):
 d={'claims':[],'measure_specs':[],'visuals':[],'slides':[]}
 for i,value in enumerate(values):
  kid=f'K{i}';nid=f'N{i}';mid=f'M{i}';period=periods[i] if periods else '2026Q1'
  d['claims'].append(dict(id=kid,text=f'测试值{value}',verification='supported',kind='company_report',source_refs=[dict(source_id='DEMO',locator='synthetic fixture',evidence='Not real research')],numbers=[dict(id=nid,normalized_value=str(value),unit=unit,currency='不适用',period=period,basis='realized')]))
  d['measure_specs'].append(dict(id=mid,label=f'样本{i}',binding=dict(kind='number',id=nid),unit=unit))
 v=dict(id='fixture',intent='comparison',title='合成数据验证',scope_note='内部测试，非真实新闻',claim_ids=[c['id'] for c in d['claims']],measure_ids=[m['id'] for m in d['measure_specs']],comparison_basis='相同测试单位与期间')
 d['visuals']=[v]
 return d

class VisualTests(unittest.TestCase):
 def assertSVG(self,d):
  d=prepare(d);self.assertEqual(validate(d),[])
  for v in d['visuals']:
   svg=render(v,{m['id']:m for m in d['measures']})
   ET.fromstring(svg);self.assertNotIn('NaN',svg);self.assertNotIn('Infinity',svg)
  return d
 def test_supported_families(self):
  d=fixture([5,8,6]);self.assertEqual(self.assertSVG(d)['visuals'][0]['chart_type'],'bar')
  d=fixture([1,2,3,4]);d['visuals'][0].update(groups=['甲','乙'],series=['收入','利润'])
  self.assertEqual(self.assertSVG(d)['visuals'][0]['chart_type'],'grouped_bar')
  d=fixture([1,3,2,6],periods=['2026-01','2026-02','2026-04','2026-05']);d['visuals'][0].update(intent='time',time_axis=['2026-01','2026-02','2026-04','2026-05'])
  self.assertEqual(self.assertSVG(d)['visuals'][0]['chart_type'],'line')
  d=fixture([70,20,10]);d['visuals'][0]['intent']='composition'
  self.assertEqual(self.assertSVG(d)['visuals'][0]['chart_type'],'stacked_bar')
  d=fixture([18,20]);d['visuals'][0].update(intent='revision',axis_domain=[14,22])
  self.assertEqual(self.assertSVG(d)['visuals'][0]['chart_type'],'dumbbell')
  d=fixture([1,2]);d['visuals'][0].update(intent='milestones',measure_ids=[],steps=[dict(label='已披露',when='已知日期',status='confirmed',claim_ids=['K0']),dict(label='下一节点',when='日期未核',status='planned',claim_ids=['K1'])])
  self.assertEqual(self.assertSVG(d)['visuals'][0]['chart_type'],'timeline')
  d=fixture([1,2]);d['visuals'][0].update(intent='mechanism',measure_ids=[],nodes=[dict(id='a',label='起点',column=0,row=0,status='confirmed',claim_ids=['K0']),dict(id='b',label='终点',column=1,row=0,status='planned',claim_ids=['K1'])],edges=[{'from':'a','to':'b','kind':'conditional','claim_ids':['K0','K1']}])
  self.assertEqual(self.assertSVG(d)['visuals'][0]['chart_type'],'flow')
  d=fixture([1,2,3,4]);d['visuals'][0].update(intent='matrix',columns=[dict(label='指标一',unit='%'),dict(label='指标二',unit='%')],rows=[dict(label='样本甲',measure_ids=['M0','M1']),dict(label='样本乙',measure_ids=['M2','M3'])])
  self.assertEqual(self.assertSVG(d)['visuals'][0]['chart_type'],'matrix')
 def test_sparse_time_stays_discrete(self):
  d=fixture([1,2,3]);d['visuals'][0].update(intent='time')
  self.assertEqual(prepare(d)['visuals'][0]['chart_type'],'bar')
  d['visuals'][0].update(chart_type='line',override_reason='should still fail')
  with self.assertRaises(ValueError):prepare(d)
 def test_mixed_units_rejected(self):
  d=fixture([1,2]);d['claims'][1]['numbers'][0]['unit']='MW';d['measure_specs'][1]['unit']='MW'
  with self.assertRaises(ValueError):prepare(d)
 def test_unverified_input_rejected(self):
  d=fixture([1,2]);d['claims'][0]['verification']='reference_only'
  with self.assertRaises(ValueError):prepare(d)
 def test_missing_datum_is_not_estimated(self):
  d=fixture([1,2]);d['visuals'][0]['measure_ids'].append('M_missing')
  with self.assertRaises((ValueError,KeyError)):prepare(d)
 def test_unavailable_has_visible_reason(self):
  d=fixture([1]);d['visuals'][0].update(status='unavailable',reason='没有足够已核数值')
  d=prepare(d);self.assertIn('没有足够已核数值',render(d['visuals'][0],{}))
 def test_percentage_overflow_rejected(self):
  d=fixture([70,40]);d['visuals'][0]['intent']='composition'
  with self.assertRaises(ValueError):prepare(d)
 def test_revision_period_mismatch_rejected(self):
  d=fixture([18,20],periods=['FY28','FY29']);d['visuals'][0]['intent']='revision'
  with self.assertRaises(ValueError):prepare(d)
 def test_prepared_tampering_rejected(self):
  d=prepare(fixture([1,2]));d['measures'][0]['value']='999'
  self.assertTrue(validate(d))
 def test_currency_and_factor_cannot_be_laundered(self):
  d=fixture([1]);d['measure_specs'][0].update(unit='MW');d['measure_specs'][0]['binding'].update(conversion_note='fake conversion')
  with self.assertRaises(ValueError):prepare(d)
  d=fixture([1]);d['measure_specs'][0]['binding'].update(factor='10',conversion_note='fake multiplier')
  with self.assertRaises(ValueError):prepare(d)
 def test_observed_time_key_required(self):
  d=fixture([1,2,3,4],periods=['2026-01']*4);d['visuals'][0].update(intent='time',time_axis=['2026-01','2026-02','2026-03','2026-04'])
  with self.assertRaises(ValueError):prepare(d)
 def test_ranking_is_sorted_without_new_values(self):
  d=fixture([2,8,3]);d['visuals'][0]['intent']='ranking'
  self.assertEqual(prepare(d)['visuals'][0]['measure_ids'],['M1','M2','M0'])
 def test_inference_edge_needs_assumption(self):
  d=fixture([1,2]);d['visuals'][0].update(intent='mechanism',measure_ids=[],nodes=[dict(id='a',label='a',column=0,row=0,status='confirmed',claim_ids=['K0']),dict(id='b',label='b',column=1,row=0,status='planned',claim_ids=['K1'])],edges=[{'from':'a','to':'b','kind':'inference','claim_ids':['K0']}])
  with self.assertRaises(ValueError):prepare(d)
 def test_signed_and_zero_scales(self):
  for vals in ([0,0],[-3,2],[-5,-2]):self.assertSVG(fixture(vals))
 def test_headline_cannot_drop_units(self):
  d=fixture([42]);d['slides']=[dict(headline=dict(subject='测试主体',event='披露',facts=[dict(measure_id='M0',suffix='项目')]))]
  with self.assertRaises(ValueError):prepare(d)
 def test_bound_cover_metric(self):
  d=fixture([42]);d['slides']=[dict(claim_ids=['K0'],metrics=[dict(label='测量',measure_id='M0')],blocks=[])]
  d=prepare(d);self.assertEqual(d['slides'][0]['metrics'][0]['value'],'42%')
  d['slides'][0]['metrics'][0]['value']='420%';self.assertTrue(validate(d))

if __name__=='__main__':unittest.main(verbosity=2)


"""Synthetic behavior checks for view labels/evidence and flexible calendar composition."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
B=load('editorial_builder','build_report.py')
W=load('editorial_outlook_fixture','test_weekly_outlook.py')


def view_fixture():
    d=json.loads((ROOT/'assets/example-report.json').read_text(encoding='utf-8'))
    t=d['theses'][0]
    t.update(target='虚构行业（仅合成测试）',horizon='未来一个季度',invalidation='合成反证条件，不是真实预测',valuation_status='not_assessed')
    s=d['slides'][1]
    s.update(takeaway='合成投资观点，不是真实投资建议。',takeaway_label='投资观点',thesis_ids=[t['id']])
    s['claim_ids']=list(dict.fromkeys(s['claim_ids']+t['claim_ids']))
    return d


class EditorialTests(unittest.TestCase):
    def test_original_example_compatible(self):
        d=json.loads((ROOT/'assets/example-report.json').read_text(encoding='utf-8'))
        self.assertFalse(B.validate(d)[0],B.validate(d))
    def test_linked_view_label_renders_in_html_and_markdown(self):
        d=view_fixture();self.assertFalse(B.validate(d)[0],B.validate(d))
        self.assertIn('<b>投资观点</b>',B.render_html(d));self.assertIn('**投资观点**',B.render_md(d))
    def test_renaming_alone_is_not_an_investment_view(self):
        d=view_fixture();d['slides'][1].pop('thesis_ids')
        self.assertTrue(any('thesis_ids' in x for x in B.validate(d)[0]))
    def test_unknown_thesis_rejected(self):
        d=view_fixture();d['slides'][1]['thesis_ids']=['unknown']
        self.assertTrue(any('unknown investment thesis' in x for x in B.validate(d)[0]))
    def test_horizon_and_invalidation_required_for_investment_label(self):
        d=view_fixture();d['theses'][0].pop('horizon')
        self.assertTrue(any('target/horizon/invalidation' in x for x in B.validate(d)[0]))
    def test_modeled_valuation_needs_linked_evidence(self):
        d=view_fixture();d['theses'][0]['valuation_status']='modeled'
        self.assertTrue(any('modeled valuation' in x for x in B.validate(d)[0]))
    def test_view_evidence_must_appear_on_page(self):
        d=view_fixture();d['slides'][1]['claim_ids']=['C02']
        self.assertTrue(any('evidence missing' in x for x in B.validate(d)[0]))
    def test_unknown_label_rejected(self):
        d=view_fixture();d['slides'][1]['takeaway_label']='<script>test</script>'
        self.assertTrue(any('invalid takeaway_label' in x for x in B.validate(d)[0]))
    def test_small_calendar_and_watchlist_can_share_a_page(self):
        d=W.fixture();d['outlook']['watchlist']=[{'item':'合成进度观察','window_text':'未确认','date_status':'unknown','focus':'只看合成证据','claim_ids':['CAL']}]
        d['slides'][0]['outlook_watchlist']=True
        self.assertFalse(B.validate(d)[0],B.validate(d));self.assertEqual(len(B.outlook.blocks(d,d['slides'][0])),2)
        self.assertIn('日期未定的研究观察项',B.render_html(d));self.assertIn('下周事件',B.render_md(d))
    def test_dense_combined_calendar_requires_split(self):
        d=W.fixture();d['calendar']=[dict(deepcopy(d['calendar'][0]),id='N'+str(i)) for i in range(4)]
        d['slides'][0].update(calendar_ids=[x['id'] for x in d['calendar']],outlook_watchlist=True)
        d['outlook']['watchlist']=[{'item':'合成观察'+str(i),'window_text':'未确认','date_status':'unknown','focus':'只看合成证据','claim_ids':['CAL']} for i in range(3)]
        self.assertTrue(any('combined page too dense' in x for x in B.validate(d)[0]))


if __name__=='__main__':unittest.main(verbosity=2)

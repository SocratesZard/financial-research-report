"""Synthetic calendar/private-source regression; no real events or IMA access."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
def module(name, filename):
    s=importlib.util.spec_from_file_location(name, ROOT/'scripts'/filename)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
B=module('outlook_builder_test','build_report.py')
A=module('outlook_audit_test','test_research_audit.py')


def fixture():
    d=deepcopy(json.loads((ROOT/'assets/example-report.json').read_text(encoding='utf-8')))
    d.update(report_id='SYNTHETIC-OUTLOOK-NOT-NEWS',title='合成验收样例：不是真实日程',mode='weekly',status='DRAFT')
    d['sources']=[{'id':'S','title':'合成排期来源（未真实访问）','kind':'primary','access':'opened','url':'https://example.com/synthetic',
      'published_at':'2026-10-15T00:00:00+08:00','accessed_at':'2026-10-18T12:00:00+08:00'}]
    d['claims']=[{'id':'CAL','kind':'calendar','verification':'supported','text':'仅用于校验的虚构排期，不是真实事件。',
      'source_refs':[{'source_id':'S','locator':'synthetic fixture','evidence':'Fictional test record only.'}]}]
    d['events']=[];d['theses']=[];d['limitations']=['全部事件、来源访问记录均为合成测试数据，不可用于投资研究。']
    d['outlook']={'anchor':'period_end','start':'2026-10-19','end':'2026-10-25','reviewed_at':'2026-10-20T09:00:00+08:00','status':'checked','watchlist':[]}
    d['calendar']=[{'id':'N','date':'2026-10-22T04:30:00+08:00','original_date':'2026-10-21T16:30:00-04:00','original_timezone':'America/New_York',
      'time_precision':'instant','item':'合成主体：虚构排期','focus':'仅测试日期、状态和证据同步','confirmation':'confirmed','schedule_basis':'official_schedule',
      'priority':1,'importance_reason':'测试用途','threshold_basis':'not_applicable','threshold_claim_ids':[],'claim_ids':['CAL']}]
    d['slides']=[{'type':'calendar','section':'06 节点与下周','title':'合成日历验收：日期转换与状态呈现','calendar_ids':['N'],'blocks':[],
      'claim_ids':['CAL'],'takeaway':'本页是合成验收样例，不是真实排期或研究结论。'}]
    return d


class Outlook(unittest.TestCase):
    def setUp(self):self.d=fixture()
    def rejected(self, phrase):self.assertTrue(any(phrase in x for x in B.validate(self.d)[0]), B.validate(self.d))
    def test_valid_cross_timezone(self):self.assertFalse(B.validate(self.d)[0], B.validate(self.d))
    def test_wrong_week(self):self.d['outlook']['start']='2026-10-26';self.rejected('window')
    def test_cutoff_week_anchor(self):
        self.d['cutoff_at']='2026-10-20T23:59:59+08:00';self.d['outlook'].update(anchor='cutoff_at',start='2026-10-26',end='2026-11-01',reviewed_at='2026-10-21T09:00:00+08:00')
        self.d['calendar'][0].update(date='2026-10-29T04:30:00+08:00',original_date='2026-10-28T16:30:00-04:00')
        self.assertFalse(B.validate(self.d)[0],B.validate(self.d))
    def test_wrong_conversion(self):self.d['calendar'][0]['date']='2026-10-22T05:30:00+08:00';self.rejected('instant')
    def test_secondary_cannot_confirm(self):self.d['sources'][0]['kind']='secondary';self.rejected('primary')
    def test_unknown_asof(self):self.d['sources'][0].update(published_at=None,accessed_at='2026-10-20T09:00:00+08:00');self.rejected('availability')
    def test_threshold_requires_assumptions(self):self.d['calendar'][0].update(threshold_basis='research_assumption',threshold_claim_ids=['CAL']);self.rejected('assumption')
    def test_missing_page(self):self.d['slides'][0]['calendar_ids']=[];self.rejected('must appear')
    def test_no_manual_duplicate(self):self.d['slides'][0]['blocks']=[{'type':'text','heading':'duplicate','items':[]}];self.rejected('manual')
    def test_instant_cannot_claim_date_precision(self):self.d['calendar'][0]['time_precision']='date';self.rejected('precision')
    def test_unknown_date_goes_to_watchlist(self):
        self.d['outlook']['watchlist']=[{'item':'合成验证项','window_text':'下周或更晚','date_status':'unknown','focus':'核对实际阶段','claim_ids':['CAL']}]
        self.d['slides'].append({'type':'calendar','section':'06 节点与下周','title':'合成观察项：日期尚未确认','outlook_watchlist':True,'blocks':[],'claim_ids':['CAL'],'takeaway':'未确认日期'})
        self.assertFalse(B.validate(self.d)[0],B.validate(self.d));self.assertIn('未确认',B.render_html(self.d))
    def test_render_reads_ledger(self):
        self.d['calendar'][0]['focus']='修改台账后同步到两种格式'
        self.assertIn('修改台账后同步到两种格式',B.render_html(self.d));self.assertIn('修改台账后同步到两种格式',B.render_md(self.d))
    def test_empty_calendar_requires_gap_reason(self):self.d['calendar']=[];self.d['slides'][0].pop('calendar_ids');self.rejected('gap reason')
    def test_private_evidence_with_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'evidence').mkdir();p=root/'evidence/sample.pdf';p.write_bytes(b'%PDF-synthetic')
            private={'provider':'ima','knowledge_base_name':'synthetic','knowledge_base_id':'fake-kb','media_id':'fake-media','retrieved_at':'2026-10-20T09:00:00+08:00',
                'url':None,'path':str(p),'snapshot':{'path':'evidence/sample.pdf','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'extent':'original','note':'Synthetic bytes only.'}}
            self.d['sources'][0].update(private)
            self.assertFalse(B.validate(self.d,root)[0], B.validate(self.d,root))
            p.write_bytes(b'tampered');self.assertTrue(any('checksum' in x for x in B.validate(self.d,root)[0]))
    def test_audit_private_source_compatibility(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'evidence').mkdir();p=root/'evidence/synthetic.pdf';p.write_bytes(b'%PDF-synthetic')
            d=A.fixture_v2();s=d['sources'][0]
            s.update(provider='ima',knowledge_base_name='synthetic',knowledge_base_id='fake-kb',media_id='fake-media',retrieved_at='2024-05-21T00:00:00+08:00',url=None,original_url=None,landing_url=None,
                snapshot={'path':'evidence/synthetic.pdf','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'extent':'original','note':'Synthetic bytes only.'},persistence_note='Reacquire with authorized IMA IDs')
            r=A.AUDIT.check(d,root);self.assertTrue(r['structural_ok'],r)
            s['snapshot']['sha256']='0'*64;r=A.AUDIT.check(d,root);self.assertFalse(r['structural_ok'])
    def test_ima_homepage_is_not_original_evidence(self):
        self.d['sources'][0].update(provider='ima',url='https://ima.qq.com/')
        self.rejected('snapshot')
    def test_build_copies_private_evidence_into_new_edition(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'evidence').mkdir();p=root/'evidence/synthetic.pdf';p.write_bytes(b'%PDF-synthetic')
            self.d['sources'][0].update(provider='ima',knowledge_base_name='synthetic',knowledge_base_id='fake-kb',media_id='fake-media',retrieved_at='2026-10-20T09:00:00+08:00',url=None,path=str(p),
                snapshot={'path':'evidence/synthetic.pdf','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'extent':'original','note':'Synthetic bytes only.'})
            inp=root/'input.json';inp.write_text(json.dumps(self.d,ensure_ascii=False),encoding='utf-8')
            subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'scripts/build_report.py'),str(inp),'--out',str(root/'edition')],check=True,capture_output=True)
            d=json.loads((root/'edition/report.json').read_text(encoding='utf-8'));saved=root/'edition/evidence/synthetic.pdf'
            self.assertEqual(saved.read_bytes(),p.read_bytes());self.assertEqual(d['sources'][0]['path'],str(saved))
            manifest=json.loads((root/'edition/manifest.json').read_text(encoding='utf-8'));self.assertIn('evidence/synthetic.pdf',manifest['files'])


if __name__=='__main__':unittest.main(verbosity=2)

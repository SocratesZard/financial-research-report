"""Synthetic offline regressions only: no news search, report rendering or baseline edits."""
from copy import deepcopy
import importlib.util
import json
import hashlib
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('audit_check', ROOT/'scripts/check_research_audit.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def instant(value='2024-05-15T12:00:00+08:00'):
    return {'raw': value, 'timezone': 'Asia/Shanghai', 'precision': 'instant',
            'lower': value, 'upper': value, 'beijing_lower': value,
            'beijing_upper': value, 'note': 'Synthetic offline timestamp, not a real publication.'}


def fixture():
    """Fictional materials-industry record, deliberately unrelated to the first news window."""
    source = {'id': 'S1', 'url': 'https://example.com/synthetic-disclosure',
              'title': 'SYNTHETIC OFFLINE FIXTURE', 'kind': 'primary', 'access': 'opened',
              'read_scope': 'full_text', 'accessed_at': '2024-05-21T12:00:00+08:00',
              'independence_group': 'original-release', 'publication': instant()}
    number = {'literal': '20', 'unit': 'units', 'currency': 'not applicable', 'period': 'forecast year',
              'denominator': 'not applicable', 'comparison': None, 'basis': 'company_forecast',
              'source_id': 'S1', 'locator': 'Synthetic paragraph 2',
              'limitation': 'Comparison and commercial delivery unestablished.'}
    claim = {'id': 'K1', 'candidate_id': 'C1', 'text': 'Fictional issuer discloses a capacity plan.',
             'kind': 'company_report', 'verification': 'supported', 'assumptions': None,
             'source_refs': [{'source_id': 'S1', 'locator': 'Synthetic paragraph 2',
                              'evidence': 'Fictional plan for 20 units, not actual output.', 'scope_limit': None}],
             'numbers': [number]}
    candidate = {'id': 'C1', 'event_key': 'fictional-materials/plant-A/capacity-plan',
                 'subsectors': ['materials'], 'info_types': ['supply'], 'stage': 'plan',
                 'summary': 'Synthetic proposed plant capacity.', 'new_fact': 'New disclosed capacity plan.',
                 'prior_baseline': 'No prior record in this fictional exercise.',
                 'increment': 'First disclosure in synthetic window.', 'first_disclosed': instant(),
                 'increment_time': instant(), 'window_status': 'in_window', 'source_ids': ['S1'],
                 'importance': 'high', 'assessment': {'impact': 'Potential capacity constraint.',
                    'novelty': 'New plan.', 'scale': '20 units, market denominator unknown.',
                    'realization': 'Plan, not operating plant.', 'evidence': 'Fictional disclosure only.'},
                 'decision': 'selected', 'reason': 'Retained for capacity monitoring, no delivery inference.',
                 'duplicate_of': None, 'claim_ids': ['K1'],
                 'analysis': {'status': 'insufficient', 'new_fact': 'Disclosed plan.', 'constraint': None,
                              'mechanism': None, 'evidence_limit': 'No commissioning/financing data.',
                              'next_check': 'Check binding funding and commissioning evidence.',
                              'unknown_reason': 'Cannot infer effective supply from planned units.'}}
    queries = []
    for i, kind in enumerate(AUDIT.INFO_TYPES):
        queries.append({'id': 'Q'+str(i), 'query': '合成材料 '+kind if i % 2 else 'synthetic materials '+kind,
                        'language': 'zh' if i % 2 else 'en', 'attempted_at': '2024-05-21T11:00:00+08:00',
                        'subsectors': ['materials'], 'info_types': [kind],
                        'source_families': list(AUDIT.FAMILIES), 'outcome': 'results',
                        'notes': 'Fabricated test record only; no query was executed.'})
    return {'audit_version': 1, 'report_id': 'SYNTHETIC-NOT-RESEARCH',
            'window': {'start': '2024-05-13T00:00:00+08:00', 'end': '2024-05-19T23:59:59+08:00',
                       'cutoff_at': '2024-05-19T23:59:59+08:00', 'timezone': 'Asia/Shanghai'},
            'scope': {'subsectors': ['materials'], 'info_types': list(AUDIT.INFO_TYPES),
                      'source_families': list(AUDIT.FAMILIES)}, 'queries': queries,
            'coverage': [{'subsector': 'materials', 'info_type': kind,
                          'status': 'searched_events' if kind == 'supply' else 'searched_no_qualifying',
                          'query_ids': ['Q'+str(i)], 'candidate_ids': ['C1'] if kind == 'supply' else [],
                          'note': 'Synthetic bookkeeping, not search evidence.'}
                         for i, kind in enumerate(AUDIT.INFO_TYPES)],
            'source_coverage': [{'family': f, 'status': 'searched', 'query_ids': ['Q0'],
                                 'note': 'Synthetic route, no actual source access.'} for f in AUDIT.FAMILIES],
            'coverage_review': {'before_selection': True, 'findings': ['Synthetic review recorded.'],
                                'follow_up_query_ids': [], 'remaining_gaps': []},
            'candidates': [candidate], 'sources': [source], 'claims': [claim],
            'limitations': ['All content is fictional test data; passing does not establish real research quality.']}


def fixture_v2():
    """Fictional capacity ratio, not a company financial statement or a news artifact."""
    d = fixture();d['audit_version'] = 2;d['scope']['regions'] = ['synthetic-region']
    d['discovery_review'] = {
        'summary': 'Synthetic scoped review; no real inventory/search was accessed.',
        'entity_checks': [{'entity': 'Fictional materials issuer', 'subsectors': ['materials'],
                           'region': 'synthetic-region', 'selection_basis': 'Fictional constraint supplier.',
                           'query_ids': ['Q0'], 'inventory_url': 'https://example.com/synthetic-inventory',
                           'outcome': 'checked', 'note': 'Synthetic, no real access.'}],
        'region_checks': [{'region': 'synthetic-region', 'subsectors': ['materials'], 'query_ids': ['Q0'],
                           'candidate_ids': ['C1'], 'status': 'searched', 'note': 'Synthetic scope.'}],
        'gap_actions': []}
    for cell in d['coverage']:
        cell.update(search_depth='directed', in_window_candidate_ids=list(cell['candidate_ids']))
    for s in d['sources']:
        s.update(original_url=s['url'], landing_url='https://example.com/synthetic-landing', snapshot=None,
                 persistence_note='No local snapshot needed for fictional test; never an actual source.')
    claim = d['claims'][0]
    claim['source_refs'][0].update(quote='Synthetic plan: 20 units out of 100.', quote_unavailable_reason=None)
    n = claim['numbers'][0];n.update(id='N1', normalized_value='20')
    n2 = deepcopy(n);n2.update(id='N2', literal='100', normalized_value='100', denominator='Fictional comparable total.')
    claim['numbers'].append(n2)
    d['calculations'] = [{'id': 'R1', 'candidate_id': 'C1', 'metric': 'Synthetic capacity share',
                          'operation': 'ratio_pct', 'input_ids': ['N1', 'N2'], 'formula': '20/100*100',
                          'result': '20.00', 'unit': '%', 'decimals': 2,
                          'scope': 'Fictional company plan, not actual delivered supply.',
                          'interpretation': 'Illustrative share only, no demand inference.',
                          'limitations': ['Synthetic forecast inputs remain forecasts.']}]
    d['material_access_failures'] = []
    candidate = d['candidates'][0]
    candidate['magnitude_review'] = {
        'checks': [{'basis': b, 'status': 'unavailable' if b != 'margin' else 'not_applicable',
                    'calculation_ids': [], 'reason': 'Synthetic missing prior data / not financial margin.'}
                   for b in ('yoy', 'qoq', 'historical', 'margin')]+
                  [{'basis': 'other', 'status': 'computed', 'calculation_ids': ['R1'],
                    'reason': 'Capacity ratio possible from fictional matched inputs.'}],
        'takeaway': 'Plan share is calculable while realized supply is unknown.',
        'priority_effect': 'Retain for tracking; ratio does not establish demand or realized scale.',
        'follow_up_query_ids': []}
    candidate['driver_review'] = {'status': 'unavailable', 'drivers': [], 'unknown': ['No funding or commissioning drivers.'],
                                 'follow_up_query_ids': ['Q0'], 'reason': 'Synthetic follow-up found no driver evidence.'}
    candidate['analysis']['state_checks'] = [{'distinction': 'planned vs commissioned', 'observed': 'Plan only.',
                                            'not_established': 'No commissioned capacity.', 'claim_ids': ['K1']}]
    return d


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture()

    def rejected(self, fragment):
        result = AUDIT.check(self.data)
        self.assertFalse(result['structural_ok'], result)
        self.assertTrue(any(fragment in s for s in result['errors']), result)

    def test_synthetic_valid_and_not_quality_certified(self):
        result = AUDIT.check(self.data)
        self.assertTrue(result['structural_ok'], result)
        self.assertTrue(result['coverage_complete'])
        self.assertFalse(result['research_quality_verified'])
        self.assertFalse(result['coverage_exhaustiveness_verified'])

    def test_full_research_has_no_digest_count_warning(self):
        result = AUDIT.check(self.data)
        self.assertTrue(result['structural_ok'], result)
        self.assertFalse(any('8–12' in item for item in result['warnings']), result)

    def test_attributed_institution_forecast_keeps_its_evidence_scope(self):
        self.data['sources'][0]['kind'] = 'secondary'
        claim = self.data['claims'][0]
        claim.update(kind='fact', text='A fictional institute forecasts 20 units; the fact is its attributed forecast.')
        claim['numbers'][0]['basis'] = 'third_party_estimate'
        claim['source_refs'][0]['evidence'] = 'The fictional institute forecasts 20 units, not actual output.'
        result = AUDIT.check(self.data)
        self.assertTrue(result['structural_ok'], result)
        self.assertEqual(claim['numbers'][0]['basis'], 'third_party_estimate')

    def test_missing_credit_cell_detected(self):
        self.data['coverage'] = [r for r in self.data['coverage'] if r['info_type'] != 'credit']
        self.rejected('full matrix')

    def test_fake_searched_cell_without_query_detected(self):
        self.data['coverage'][0]['query_ids'] = []
        self.rejected('effective query')

    def test_conference_only_cannot_hide_ir_route(self):
        self.data['source_coverage'] = [r for r in self.data['source_coverage'] if r['family'] != 'ir_filing']
        self.rejected('all six routes')

    def test_honest_unsearched_is_valid_but_incomplete(self):
        self.data['coverage'][0].update(status='not_searched', query_ids=[], note='Budget exhausted.')
        self.data['coverage_review']['remaining_gaps'] = ['Financial information not searched.']
        result = AUDIT.check(self.data)
        self.assertTrue(result['structural_ok'], result)
        self.assertFalse(result['coverage_complete'])

    def test_failure_not_equated_to_no_event(self):
        self.data['queries'][0].update(outcome='access_failed', notes='Synthetic access denied.')
        self.rejected('effective query')

    def test_one_language_remains_a_recorded_gap(self):
        for q in self.data['queries']:
            q['language'] = 'en'
        self.data['coverage_review']['remaining_gaps'] = ['Chinese search not performed.']
        result = AUDIT.check(self.data)
        self.assertTrue(result['structural_ok'], result)
        self.assertFalse(result['coverage_complete'])

    def test_no_preselection_review_detected(self):
        self.data['coverage_review']['before_selection'] = False
        self.rejected('preselection')

    def test_high_importance_excluded_needs_reason(self):
        self.data['candidates'][0].update(decision='excluded', reason='')
        self.rejected('reason required')

    def test_analysis_can_be_unknown_without_fabrication(self):
        result = AUDIT.check(self.data)
        self.assertTrue(result['structural_ok'], result)

    def test_claimed_mechanism_requires_variable(self):
        self.data['candidates'][0]['analysis']['status'] = 'reasoned'
        self.rejected('variable/mechanism')

    def test_headline_not_supported_fact(self):
        self.data['sources'][0].update(access='excerpt_only', read_scope='headline')
        self.rejected('headline/unread')

    def test_excerpt_cannot_claim_full_text(self):
        self.data['sources'][0]['access'] = 'excerpt_only'
        self.rejected('full_text contradicts')

    def test_excerpt_support_needs_limited_scope(self):
        self.data['sources'][0].update(access='excerpt_only', read_scope='excerpt')
        self.rejected('scope_limit')

    def test_reprints_not_independent_verification(self):
        other = deepcopy(self.data['sources'][0]);other['id'] = 'S2';other['url'] += '/reprint'
        self.data['sources'].append(other)
        c = self.data['claims'][0];c['verification'] = 'corroborated'
        c['source_refs'].append({**c['source_refs'][0], 'source_id': 'S2'})
        self.data['candidates'][0]['source_ids'].append('S2')
        self.rejected('independent upstreams')

    def test_number_requires_original_locator(self):
        self.data['claims'][0]['numbers'][0].pop('locator')
        self.rejected('locator')

    def test_unknown_denominator_needs_limit(self):
        self.data['claims'][0]['numbers'][0]['limitation'] = ''
        self.rejected('numeric context')

    def test_company_forecast_keeps_attribution(self):
        self.data['claims'][0]['kind'] = 'fact'
        self.rejected('must stay attributed')

    def test_unknown_precision_cannot_be_precise(self):
        t = self.data['candidates'][0]['increment_time'];t.update(lower=None, upper=None)
        self.rejected('unsupported precise instant')

    def test_date_only_source_cannot_gain_invented_clock_time(self):
        self.data['candidates'][0]['increment_time']['raw'] = '2024-05-15'
        self.rejected('raw source lacks time precision')

    def test_date_range_can_remain_uncertain_without_instant(self):
        t = {'raw': '2024-05-15, local zone uncertain', 'timezone': None, 'precision': 'range',
             'lower': '2024-05-15T00:00:00+08:00', 'upper': '2024-05-16T23:59:59+08:00',
             'beijing_lower': '2024-05-15T00:00:00+08:00', 'beijing_upper': '2024-05-16T23:59:59+08:00',
             'note': 'Synthetic conservative possible interval; boundaries are not event times.'}
        self.data['candidates'][0]['increment_time'] = t
        self.assertTrue(AUDIT.check(self.data)['structural_ok'])

    def test_boundary_overlap_is_not_falsely_marked_in_window(self):
        t = self.data['candidates'][0]['increment_time']
        t.update(precision='range', lower='2024-05-12T20:00:00+08:00', upper='2024-05-13T04:00:00+08:00',
                 beijing_lower='2024-05-12T20:00:00+08:00', beijing_upper='2024-05-13T04:00:00+08:00')
        self.rejected('contradicts interval')

    def test_time_conversion_must_represent_same_instant(self):
        self.data['candidates'][0]['increment_time']['beijing_lower'] = '2024-05-15T13:00:00+08:00'
        self.rejected('Beijing conversion')

    def test_wrong_requested_zone_offset(self):
        self.data['window']['start'] = '2024-05-13T00:00:00+00:00'
        self.rejected('offset mismatches')

    def test_old_reprint_is_not_in_window_increment(self):
        self.data['candidates'][0]['increment_time'] = instant('2024-05-10T12:00:00+08:00')
        self.rejected('contradicts interval')

    def test_post_cutoff_source_does_not_support_asof_claim(self):
        self.data['sources'][0]['publication'] = instant('2024-05-21T12:00:00+08:00')
        self.rejected('post-cutoff')

    def test_duplicate_selected_economic_event_rejected(self):
        c = deepcopy(self.data['candidates'][0]);c['id'] = 'C2';c['claim_ids'] = ['K2']
        self.data['candidates'].append(c)
        claim = deepcopy(self.data['claims'][0]);claim.update(id='K2', candidate_id='C2')
        self.data['claims'].append(claim)
        self.data['coverage'][5]['candidate_ids'].append('C2')
        self.rejected('duplicate selected economic event')

    def test_template_is_not_misreported_as_completed_search(self):
        template = json.loads((ROOT/'assets/research-audit.template.json').read_text(encoding='utf-8'))
        self.assertFalse(AUDIT.check(template)['structural_ok'])


class Revision2Tests(unittest.TestCase):
    def setUp(self):
        self.data = fixture_v2()

    def rejected(self, fragment):
        result = AUDIT.check(self.data)
        self.assertFalse(result['structural_ok'], result)
        self.assertTrue(any(fragment in e for e in result['errors']), result)

    def test_new_records_and_arithmetic_valid_not_research_quality(self):
        r = AUDIT.check(self.data)
        self.assertTrue(r['structural_ok'], r)
        self.assertTrue(r['quality_recording_complete'])
        self.assertFalse(r['research_quality_verified'])

    def test_legacy_v1_not_auto_upgraded(self):
        r = AUDIT.check(fixture())
        self.assertTrue(r['structural_ok'])
        self.assertFalse(r['quality_recording_complete'])
        self.assertTrue(any('NOT_ASSESSED' in w for w in r['warnings']))

    def test_missing_entity_followup_detected(self):
        self.data['discovery_review']['entity_checks'] = []
        self.rejected('entity inventory')

    def test_requested_region_missing_detected(self):
        self.data['scope']['regions'].append('another-synthetic-region')
        self.rejected('requested region review')

    def test_broad_only_is_not_deep_coverage(self):
        for c in self.data['coverage']:c['search_depth'] = 'broad'
        r = AUDIT.check(self.data)
        self.assertTrue(r['structural_ok'], r)
        self.assertFalse(r['quality_recording_complete'])

    def test_outside_window_not_used_as_active_discovery(self):
        c = self.data['candidates'][0]
        c.update(decision='excluded', window_status='outside_window', increment_time=instant('2024-05-10T12:00:00+08:00'))
        self.rejected('out-of-window')

    def test_financial_missing_applicability_detected(self):
        c = self.data['candidates'][0];c['info_types'].append('financial')
        c['magnitude_review']['checks'] = [c['magnitude_review']['checks'][-1]]
        self.rejected('four applicability')

    def test_wrong_ratio_arithmetic_detected(self):
        self.data['calculations'][0]['result'] = '55.00'
        self.rejected('arithmetic')

    def test_verified_group_ratio_does_not_require_invented_segment(self):
        c = self.data['candidates'][0];c['info_types'].append('financial')
        r = AUDIT.check(self.data)
        self.assertTrue(r['structural_ok'], r)
        self.assertEqual(c['driver_review']['drivers'], [])

    def test_growth_calculation(self):
        c = self.data['calculations'][0]
        c.update(operation='change_pct', formula='(20/100-1)*100', result='-80.00')
        self.assertTrue(AUDIT.check(self.data)['structural_ok'])

    def test_zero_denominator_rejected(self):
        self.data['claims'][0]['numbers'][1]['normalized_value'] = '0'
        self.rejected('zero denominator')

    def test_negative_growth_base_rejected(self):
        self.data['claims'][0]['numbers'][1]['normalized_value'] = '-100'
        self.data['calculations'][0].update(operation='change_pct', result='-120.00')
        self.rejected('nonpositive growth baseline')

    def test_decimal_rounding_checked(self):
        self.data['claims'][0]['numbers'][1]['normalized_value'] = '60'
        self.data['calculations'][0]['result'] = '33.33'
        self.assertTrue(AUDIT.check(self.data)['structural_ok'])

    def test_unverified_input_cannot_be_calculated_as_supported(self):
        self.data['claims'][0]['verification'] = 'unverified'
        # Add separate supported nonnumeric disclosure so base selection validation still passes.
        k = deepcopy(self.data['claims'][0]);k.update(id='K2', verification='supported', numbers=[])
        self.data['claims'].append(k);self.data['candidates'][0]['claim_ids'].append('K2')
        self.rejected('only supported')

    def test_unit_mismatch_detected(self):
        self.data['claims'][0]['numbers'][1]['unit'] = 'different scale'
        self.rejected('normalize units')

    def test_ratio_period_mismatch_detected(self):
        self.data['claims'][0]['numbers'][1]['period'] = 'different quarter'
        self.rejected('matched periods')

    def test_percentage_unit_cannot_be_monetary(self):
        self.data['calculations'][0]['unit'] = 'KRW'
        self.rejected('result unit')

    def test_difference_calculation(self):
        c = self.data['calculations'][0]
        c.update(operation='difference', formula='20-100', result='-80.00', unit='units')
        self.assertTrue(AUDIT.check(self.data)['structural_ok'])

    def test_nonfinite_numeric_input_rejected(self):
        self.data['claims'][0]['numbers'][0]['normalized_value'] = 'NaN'
        self.rejected('finite decimal')

    def test_claimed_driver_check_cannot_be_empty(self):
        self.data['candidates'][0]['driver_review']['status'] = 'checked'
        self.rejected('checked driver status')

    def test_missing_quote_not_hidden_as_paraphrase(self):
        r = self.data['claims'][0]['source_refs'][0];r['quote'] = None
        self.rejected('original quote')

    def test_quote_unavailable_is_explicit_gap(self):
        r = self.data['claims'][0]['source_refs'][0]
        r.update(quote=None, quote_unavailable_reason='Synthetic extraction failure.')
        result = AUDIT.check(self.data)
        self.assertTrue(result['structural_ok'], result)
        self.assertFalse(result['quality_recording_complete'])

    def test_temp_only_snapshot_rejected(self):
        self.data['sources'][0]['snapshot'] = {'path': 'C:/Users/test/Temp/e.pdf', 'sha256': '0'*64,
                                             'extent': 'p1', 'note': 'Wrong location.'}
        self.rejected('edition evidence')

    def test_snapshot_traversal_rejected(self):
        self.data['sources'][0]['snapshot'] = {'path': 'evidence/../../secret', 'sha256': '0'*64,
                                             'extent': 'p1', 'note': 'Wrong location.'}
        self.rejected('edition evidence')

    def test_snapshot_read_only_hash_check(self):
        with tempfile.TemporaryDirectory(prefix='synthetic-evidence-') as td:
            root = Path(td);(root/'evidence').mkdir();p = root/'evidence/excerpt.txt';p.write_text('synthetic', encoding='utf-8')
            snap = {'path': 'evidence/excerpt.txt', 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                    'extent': 'Synthetic one-line excerpt.', 'note': 'Test file only.'}
            self.data['sources'][0]['snapshot'] = snap
            result = AUDIT.check(self.data, root)
            self.assertTrue(result['structural_ok'], result)
            snap['sha256'] = '0'*64
            self.assertFalse(AUDIT.check(self.data, root)['structural_ok'])
            self.assertEqual(p.read_text(), 'synthetic')

    def test_failed_access_needs_alternative_record(self):
        self.data['material_access_failures'] = [{'url': 'https://example.com/original',
                'attempted_at': '2024-05-21T10:00:00+08:00', 'error': 'Synthetic blocked',
                'alternative_source_ids': ['MISSING'], 'limitation': 'No original obtained.'}]
        self.rejected('failure alternatives')

    def test_disclosed_driver_cannot_be_inferred_claim(self):
        k = deepcopy(self.data['claims'][0]);k.update(id='K2', kind='inference', assumptions='Synthetic mechanism only.', numbers=[])
        self.data['claims'].append(k);self.data['candidates'][0]['claim_ids'].append('K2')
        self.data['candidates'][0]['driver_review'].update(status='checked', drivers=[
            {'driver': 'Synthetic possible driver.', 'attribution': 'disclosed', 'claim_ids': ['K2']}])
        self.rejected('disclosed driver')

    def test_no_driver_search_stays_incomplete(self):
        self.data['candidates'][0]['driver_review']['follow_up_query_ids'] = []
        r = AUDIT.check(self.data)
        self.assertTrue(r['structural_ok'], r)
        self.assertFalse(r['quality_recording_complete'])

    def test_financing_or_contract_requires_state_boundary(self):
        self.data['candidates'][0]['info_types'].append('credit')
        self.data['candidates'][0]['analysis']['state_checks'] = []
        self.rejected('economic event needs state distinction')


if __name__ == '__main__':
    unittest.main(verbosity=2)

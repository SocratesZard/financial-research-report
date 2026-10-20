"""Offline consistency checks; never searches, reads URLs or certifies research quality."""
import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
import importlib.util
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_ima_spec = importlib.util.spec_from_file_location('audit_ima_record', Path(__file__).with_name('ima_source_record.py'))
ima_record = importlib.util.module_from_spec(_ima_spec)
_ima_spec.loader.exec_module(ima_record)

INFO_TYPES = ('financial', 'technology', 'orders', 'capex', 'credit', 'supply', 'infrastructure', 'regulation')
FAMILIES = ('ir_filing', 'official', 'media', 'industry_research', 'conference', 'contract_counterparty')
CELL_STATES = ('searched_events', 'searched_no_qualifying', 'leads_insufficient', 'not_searched', 'access_failed', 'not_applicable')


def check(data, base_dir=None):
    errors, warnings, gaps, quality_gaps = [], [], [], []

    def need(ok, message):
        if not ok:
            errors.append(message)

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def stamp(value, label):
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                raise ValueError('timezone offset required')
            return dt
        except (ValueError, TypeError, AttributeError):
            errors.append(f'{label}: invalid ISO time with offset')
            return None

    def fields(obj, names, label):
        for name in names:
            need(name in obj, f'{label}: missing {name}')

    def refs(values, mapping, label):
        if not isinstance(values, list):
            errors.append(f'{label}: expected ID list')
            return []
        for value in values:
            need(isinstance(value, str) and value in mapping, f'{label}: unknown ID {value!r}')
        return [mapping[v] for v in values if isinstance(v, str) and v in mapping]

    def index(items, label):
        result = {}
        if not isinstance(items, list):
            errors.append(f'{label}: expected list')
            return result
        for item in items:
            if not isinstance(item, dict) or not text(item.get('id')):
                errors.append(f'{label}: object with id required')
                continue
            need(item['id'] not in result, f'{label}: duplicate ID {item["id"]}')
            result[item['id']] = item
        return result

    def time_range(obj, label):
        if not isinstance(obj, dict):
            errors.append(f'{label}: time object required')
            return None, None
        fields(obj, ('raw', 'timezone', 'precision', 'lower', 'upper', 'beijing_lower', 'beijing_upper', 'note'), label)
        precision = obj.get('precision')
        need(precision in ('instant', 'date', 'range', 'unknown'), f'{label}: invalid precision')
        low, high = obj.get('lower'), obj.get('upper')
        need((low is None) == (high is None), f'{label}: paired range bounds required')
        a = stamp(low, label+'.lower') if low is not None else None
        b = stamp(high, label+'.upper') if high is not None else None
        if a and b:
            need(a <= b, f'{label}: reversed range')
        if precision == 'instant':
            need(bool(a and b and a == b and text(obj.get('raw')) and text(obj.get('timezone'))), f'{label}: unsupported precise instant')
            need(not re.fullmatch(r'\s*\d{4}[-/]\d{1,2}[-/]\d{1,2}\s*', str(obj.get('raw', ''))), f'{label}: raw source lacks time precision')
        else:
            need(text(obj.get('note')), f'{label}: date/uncertainty needs note')
        converted = (obj.get('beijing_lower'), obj.get('beijing_upper'))
        need((converted[0] is None) == (converted[1] is None), f'{label}: paired Beijing bounds required')
        for original, value in zip((a, b), converted):
            if value is not None:
                dt = stamp(value, label+'.beijing')
                need(bool(original and dt and dt == original and dt.utcoffset().total_seconds() == 28800), f'{label}: inconsistent Beijing conversion')
        if a and b and all(v is None for v in converted):
            need(text(obj.get('note')), f'{label}: missing Beijing conversion needs explanation')
        return a, b

    def result():
        return {'structural_ok': not errors, 'coverage_complete': not errors and not gaps,
                'quality_recording_complete': data.get('audit_version') == 2 and not errors and not quality_gaps if isinstance(data, dict) else False,
                'quality_recording_gaps': quality_gaps,
                'research_quality_verified': False, 'coverage_exhaustiveness_verified': False,
                'errors': errors, 'warnings': warnings, 'recorded_coverage_gaps': gaps}

    if not isinstance(data, dict):
        need(False, 'Audit must be an object')
        return result()
    fields(data, ('audit_version', 'report_id', 'window', 'scope', 'queries', 'coverage', 'source_coverage', 'coverage_review', 'candidates', 'sources', 'claims', 'limitations'), 'audit')
    if errors:
        return result()
    need(data['audit_version'] in (1, 2), 'Unsupported audit_version')
    if data['audit_version'] == 1:
        warnings.append('Legacy v1: discovery depth, magnitude, driver and durable-evidence checks NOT_ASSESSED.')
    need(text(data['report_id']), 'report_id required')
    for name in ('window', 'scope', 'coverage_review'):
        need(isinstance(data[name], dict), f'{name}: object required')
    for name in ('coverage', 'source_coverage', 'limitations'):
        need(isinstance(data[name], list), f'{name}: list required')
    queries, candidates, sources, claims = [index(data[name], name) for name in ('queries', 'candidates', 'sources', 'claims')]
    if errors:
        return result()
    window, scope = data['window'], data['scope']
    start, end, cutoff = [stamp(window.get(k), 'window.'+k) for k in ('start', 'end', 'cutoff_at')]
    if start and end and cutoff:
        need(start <= end <= cutoff, 'window: start/end/cutoff ordering')
    try:
        zone = ZoneInfo(window.get('timezone', ''))
        for dt in (start, end):
            if dt:
                need(dt.utcoffset() == dt.astimezone(zone).utcoffset(), 'window: offset mismatches requested timezone')
    except (ZoneInfoNotFoundError, TypeError, ValueError):
        need(False, 'window: IANA timezone unavailable/invalid (Windows may need tzdata)')
    sectors = scope.get('subsectors')
    need(isinstance(sectors, list) and bool(sectors) and all(text(s) for s in sectors), 'scope: subsectors required')
    if errors:
        return result()
    need(len(sectors) == len(set(sectors)), 'scope: duplicate subsectors')
    for name, expected in (('info_types', INFO_TYPES), ('source_families', FAMILIES)):
        values = scope.get(name)
        need(isinstance(values, list) and len(values) == len(expected) and set(values) == set(expected), f'scope: complete unique {name} required')
    for qid, q in queries.items():
        fields(q, ('query', 'language', 'attempted_at', 'subsectors', 'info_types', 'source_families', 'outcome', 'notes'), qid)
        need(text(q.get('query')) and text(q.get('language')), f'{qid}: query/language required')
        stamp(q.get('attempted_at'), qid+'.attempted_at')
        for name, allowed in (('subsectors', sectors), ('info_types', INFO_TYPES), ('source_families', FAMILIES)):
            values = q.get(name, [])
            need(isinstance(values, list) and bool(values) and all(v in allowed for v in values), f'{qid}: invalid {name}')
        need(q.get('outcome') in ('results', 'no_results', 'access_failed'), f'{qid}: invalid outcome')
        if q.get('outcome') == 'access_failed':
            need(text(q.get('notes')), f'{qid}: failed attempt needs explanation')
    languages = {q.get('language') for q in queries.values()}
    if not {'zh', 'en'} <= languages:
        gaps.append('Bilingual search not recorded in both zh and en; explain limitation.')

    seen_cells = set()
    for cell in data['coverage']:
        if not isinstance(cell, dict):
            need(False, 'coverage: object required')
            continue
        key = (cell.get('subsector'), cell.get('info_type'))
        label = '/'.join(str(v) for v in key)
        need(key[0] in sectors and key[1] in INFO_TYPES, f'{label}: unknown matrix cell')
        need(key not in seen_cells, f'{label}: duplicate coverage cell')
        seen_cells.add(key)
        state = cell.get('status')
        need(state in CELL_STATES, f'{label}: invalid coverage state')
        qs = refs(cell.get('query_ids'), queries, label+'.queries')
        cs = refs(cell.get('candidate_ids'), candidates, label+'.candidates')
        for q in qs:
            need(key[0] in q.get('subsectors', []) and key[1] in q.get('info_types', []), f'{label}: query does not target cell')
        for c in cs:
            need(key[0] in c.get('subsectors', []) and key[1] in c.get('info_types', []), f'{label}: candidate does not belong to cell')
        if state in ('searched_events', 'searched_no_qualifying', 'leads_insufficient'):
            need(any(q.get('outcome') != 'access_failed' for q in qs), f'{label}: searched state needs effective query')
        if state in ('searched_events', 'leads_insufficient'):
            need(bool(cs), f'{label}: candidate IDs required')
        if state == 'searched_no_qualifying':
            need(not any(c.get('decision') in ('selected', 'pending') for c in cs), f'{label}: no-qualifying contradicts active candidates')
        if state in ('not_searched', 'access_failed', 'not_applicable', 'leads_insufficient'):
            need(text(cell.get('note')), f'{label}: limitation/reason required')
        if state == 'not_searched':
            need(not qs, f'{label}: not_searched contradicts query records')
        if state == 'access_failed':
            need(bool(qs) and all(q.get('outcome') == 'access_failed' for q in qs), f'{label}: failed route needs failed attempts')
        if state in ('not_searched', 'access_failed', 'leads_insufficient'):
            gaps.append(f'{label}: {state}')
    need(seen_cells == {(s, t) for s in sectors for t in INFO_TYPES}, 'coverage: full matrix required, including unsearched cells')
    seen_routes = set()
    for route in data['source_coverage']:
        if not isinstance(route, dict):
            need(False, 'source_coverage: object required')
            continue
        family, state = route.get('family'), route.get('status')
        need(family in FAMILIES and family not in seen_routes, 'source_coverage: invalid/duplicate family')
        seen_routes.add(family)
        need(state in ('searched', 'not_searched', 'access_failed', 'not_applicable'), f'{family}: invalid route state')
        qs = refs(route.get('query_ids'), queries, str(family)+'.queries')
        need(all(family in q.get('source_families', []) for q in qs), f'{family}: query not in route')
        if state == 'searched':
            need(any(q.get('outcome') != 'access_failed' for q in qs), f'{family}: searched route needs effective query')
        else:
            need(text(route.get('note')), f'{family}: reason required')
        if state == 'access_failed':
            need(bool(qs) and all(q.get('outcome') == 'access_failed' for q in qs), f'{family}: failed attempts required')
        if state == 'not_searched':
            need(not qs, f'{family}: not_searched contradicts attempts')
        if state in ('not_searched', 'access_failed'):
            gaps.append(f'source route {family}: {state}')
    need(seen_routes == set(FAMILIES), 'source_coverage: all six routes required')
    review = data['coverage_review']
    need(review.get('before_selection') is True, 'coverage_review: preselection review required')
    need(bool(review.get('findings')), 'coverage_review: findings required')
    refs(review.get('follow_up_query_ids'), queries, 'coverage_review.follow_up')
    need(isinstance(review.get('remaining_gaps'), list), 'coverage_review.remaining_gaps required')
    if gaps:
        need(bool(review.get('remaining_gaps')) and bool(data['limitations']), 'Recorded gaps must appear in review and limitations')

    for sid, s in sources.items():
        fields(s, ('url', 'title', 'kind', 'access', 'read_scope', 'accessed_at', 'independence_group', 'publication'), sid)
        if s.get('provider') == 'ima':
            errors += ima_record.errors(s, base_dir)
        else:
            need(text(s.get('url')) and s['url'].startswith(('https://', 'http://')), f'{sid}: source HTTP(S) URL required')
        need(text(s.get('title')) and text(s.get('independence_group')), f'{sid}: title/upstream group required')
        need(s.get('kind') in ('primary', 'secondary', 'channel', 'reference'), f'{sid}: invalid kind')
        need(s.get('access') in ('opened', 'excerpt_only', 'inaccessible', 'not_accessed'), f'{sid}: invalid access')
        need(s.get('read_scope') in ('full_text', 'excerpt', 'headline', 'not_read'), f'{sid}: invalid read_scope')
        if s.get('read_scope') == 'full_text':
            need(s.get('access') == 'opened', f'{sid}: full_text contradicts access')
        if s.get('access') in ('inaccessible', 'not_accessed'):
            need(s.get('read_scope') == 'not_read', f'{sid}: inaccessible/unaccessed cannot claim reading')
        if s.get('read_scope') != 'not_read':
            stamp(s.get('accessed_at'), sid+'.accessed_at')
        time_range(s.get('publication'), sid+'.publication')

    selected_keys = set()
    for cid, c in candidates.items():
        fields(c, ('event_key', 'subsectors', 'info_types', 'stage', 'summary', 'new_fact', 'prior_baseline', 'increment', 'first_disclosed', 'increment_time', 'window_status', 'source_ids', 'importance', 'assessment', 'decision', 'reason', 'duplicate_of', 'claim_ids', 'analysis'), cid)
        for name in ('event_key', 'stage', 'summary', 'reason'):
            need(text(c.get(name)), f'{cid}: {name} required')
        for name, allowed in (('subsectors', sectors), ('info_types', INFO_TYPES)):
            values = c.get(name, [])
            need(isinstance(values, list) and bool(values) and all(v in allowed for v in values), f'{cid}: invalid {name}')
        need(c.get('importance') in ('high', 'medium', 'low'), f'{cid}: importance required')
        assessment = c.get('assessment', {})
        need(isinstance(assessment, dict) and all(text(assessment.get(k)) for k in ('impact', 'novelty', 'scale', 'realization', 'evidence')), f'{cid}: five assessment reasons required')
        decision = c.get('decision')
        need(decision in ('selected', 'pending', 'excluded', 'duplicate'), f'{cid}: decision required')
        ss = refs(c.get('source_ids'), sources, cid+'.sources')
        linked_claims = refs(c.get('claim_ids'), claims, cid+'.claims')
        need(all(x.get('candidate_id') == cid for x in linked_claims), f'{cid}: claim candidate mismatch')
        for linked_claim in linked_claims:
            need(all(r.get('source_id') in c.get('source_ids', []) for r in linked_claim.get('source_refs', [])), f'{cid}: claim source missing from candidate')
        time_range(c.get('first_disclosed'), cid+'.first_disclosed')
        a, b = time_range(c.get('increment_time'), cid+'.increment_time')
        window_state = c.get('window_status')
        need(window_state in ('in_window', 'overlaps_window', 'outside_window', 'unknown'), f'{cid}: invalid window_status')
        if start and end and a and b:
            calculated = 'outside_window' if b < start or a > end else 'in_window' if start <= a <= b <= end else 'overlaps_window'
            need(window_state == calculated, f'{cid}: window_status contradicts interval')
        elif window_state != 'unknown':
            need(False, f'{cid}: known window status needs interval bounds')
        if decision == 'duplicate':
            need(c.get('duplicate_of') in candidates and c.get('duplicate_of') != cid, f'{cid}: valid duplicate target required')
        else:
            need(c.get('duplicate_of') is None, f'{cid}: nonduplicate has duplicate target')
        if decision == 'selected':
            need(c.get('event_key') not in selected_keys, f'{cid}: duplicate selected economic event')
            selected_keys.add(c.get('event_key'))
            need(bool(ss) and bool(linked_claims), f'{cid}: selected needs sources/claims')
            need(any(x.get('verification') in ('supported', 'corroborated') and x.get('kind') in ('fact', 'company_report') for x in linked_claims), f'{cid}: selected needs supported factual disclosure; otherwise retain pending')
            need(text(c.get('new_fact')) and text(c.get('increment')), f'{cid}: selected needs factual increment')
            need(window_state in ('in_window', 'overlaps_window'), f'{cid}: cannot select unknown/outside-window item')
            analysis = c.get('analysis', {})
            need(isinstance(analysis, dict), f'{cid}: analysis object required')
            if isinstance(analysis, dict):
                need(analysis.get('status') in ('reasoned', 'insufficient'), f'{cid}: analysis status required')
                for name in ('new_fact', 'evidence_limit', 'next_check'):
                    need(text(analysis.get(name)), f'{cid}: analysis {name} required')
                if analysis.get('status') == 'reasoned':
                    need(text(analysis.get('constraint')) and text(analysis.get('mechanism')), f'{cid}: reasoned analysis needs variable/mechanism')
                else:
                    need(text(analysis.get('unknown_reason')), f'{cid}: insufficient analysis needs reason')
            if window_state == 'overlaps_window':
                warnings.append(f'{cid}: boundary uncertainty must be visible in main text')
    for kid, claim in claims.items():
        fields(claim, ('candidate_id', 'text', 'kind', 'verification', 'assumptions', 'source_refs', 'numbers'), kid)
        need(claim.get('candidate_id') in candidates and text(claim.get('text')), f'{kid}: candidate/text required')
        parent = candidates.get(claim.get('candidate_id'), {})
        need(kid in parent.get('claim_ids', []), f'{kid}: claim absent from candidate record')
        need(claim.get('kind') in ('fact', 'company_report', 'inference', 'scenario', 'calendar'), f'{kid}: invalid claim kind')
        level = claim.get('verification')
        need(level in ('supported', 'corroborated', 'reference_only', 'unverified'), f'{kid}: invalid verification')
        if claim.get('kind') in ('inference', 'scenario'):
            need(text(claim.get('assumptions')), f'{kid}: inference/scenario needs assumptions')
        evidence = claim.get('source_refs')
        if not isinstance(evidence, list) or not evidence:
            need(False, f'{kid}: evidence references required')
            continue
        usable = set()
        for ref in evidence:
            sid = ref.get('source_id')
            need(sid in sources and text(ref.get('locator')) and text(ref.get('evidence')), f'{kid}: source/locator/evidence required')
            s = sources.get(sid, {})
            if level in ('supported', 'corroborated'):
                need(s.get('read_scope') in ('full_text', 'excerpt') and s.get('kind') != 'reference', f'{kid}: headline/unread/reference cannot establish support')
                if s.get('read_scope') == 'excerpt':
                    need(text(ref.get('scope_limit')), f'{kid}: excerpt support needs scope_limit')
                publication = s.get('publication', {})
                raw_lower = publication.get('lower')
                if raw_lower and cutoff:
                    lo = stamp(raw_lower, kid+'.source_publication')
                    if lo:
                        need(lo <= cutoff, f'{kid}: post-cutoff support')
                    raw_upper = publication.get('upper')
                    hi = stamp(raw_upper, kid+'.source_publication_upper') if raw_upper else None
                    if hi and hi > cutoff:
                        warnings.append(f'{kid}: source publication range crosses cutoff; disclose uncertainty')
                else:
                    warnings.append(f'{kid}: unknown source publication; availability at cutoff needs review')
                usable.add(s.get('independence_group'))
        if level == 'corroborated':
            need(len(usable) >= 2, f'{kid}: independent upstreams required, not different URLs')
        numbers = claim.get('numbers')
        need(isinstance(numbers, list), f'{kid}: numbers list required')
        for n in numbers if isinstance(numbers, list) else []:
            fields(n, ('literal', 'unit', 'currency', 'period', 'denominator', 'comparison', 'basis', 'source_id', 'locator', 'limitation'), kid+'.number')
            need(text(n.get('literal')) and text(n.get('locator')), f'{kid}: numeric literal/locator required')
            need(n.get('source_id') in sources and any(r.get('source_id') == n.get('source_id') for r in evidence), f'{kid}: number must link claim evidence')
            need(n.get('basis') in ('realized', 'company_forecast', 'company_spec', 'media_report', 'third_party_estimate', 'researcher_calculation'), f'{kid}: invalid number basis')
            if any(n.get(k) is None for k in ('unit', 'currency', 'period', 'denominator', 'comparison')):
                need(text(n.get('limitation')), f'{kid}: unknown numeric context needs limitation')
            if n.get('basis') in ('company_forecast', 'company_spec'):
                need(claim.get('kind') != 'fact', f'{kid}: company forecast/spec must stay attributed')
    covered_candidates = {cid for cell in data['coverage'] for cid in cell.get('candidate_ids', [])}
    need(set(candidates) <= covered_candidates, 'Candidate missing from coverage ledger')
    if data['audit_version'] == 2 and not errors:
        check_v2(data, queries, candidates, sources, claims, errors, warnings, quality_gaps, base_dir)
    return result()


def check_v2(data, queries, candidates, sources, claims, errors, warnings, quality_gaps, base_dir):
    """Check records and arithmetic only; do not pretend to evaluate real discovery or causality."""
    def need(ok, msg):
        if not ok:
            errors.append(msg)

    def nonempty(v):
        return isinstance(v, str) and bool(v.strip())

    def links(ids, pool, label):
        ok = isinstance(ids, list) and all(isinstance(i, str) and i in pool for i in ids)
        need(ok, f'{label}: invalid linked IDs')
        return [pool[i] for i in ids] if ok else []

    def decimal(v, label):
        try:
            if not isinstance(v, str):
                raise ValueError('use explicit decimal string')
            d = Decimal(v)
            if not d.is_finite():
                raise ValueError('nonfinite')
            return d
        except (InvalidOperation, ValueError):
            need(False, f'{label}: finite decimal string required')
            return None

    def http(v):
        return isinstance(v, str) and v.startswith(('https://', 'http://'))

    review = data.get('discovery_review', {})
    need(isinstance(review, dict) and nonempty(review.get('summary')), 'v2: discovery review summary required')
    if not isinstance(review, dict):
        return
    entities = review.get('entity_checks')
    regions = review.get('region_checks')
    actions = review.get('gap_actions')
    need(isinstance(entities, list) and bool(entities), 'v2: scoped entity inventory checks required')
    need(isinstance(regions, list) and bool(regions), 'v2: region coverage checks required')
    need(isinstance(actions, list), 'v2: gap_actions list required')
    sectors = data['scope']['subsectors']
    requested_regions = data['scope'].get('regions', [])
    need(isinstance(requested_regions, list) and bool(requested_regions) and all(nonempty(x) for x in requested_regions), 'v2: explicit scope regions required')
    checked_regions = set()
    for ent in entities if isinstance(entities, list) else []:
        need(nonempty(ent.get('entity')) and nonempty(ent.get('selection_basis')) and nonempty(ent.get('note')), 'v2: entity scope/basis/evidence note required')
        need(bool(ent.get('subsectors')) and all(s in sectors for s in ent['subsectors']), 'v2: entity subsectors required')
        qs = links(ent.get('query_ids'), queries, 'entity checks')
        need(ent.get('outcome') in ('checked', 'not_checked', 'access_failed'), 'v2: invalid entity check outcome')
        if ent.get('outcome') == 'checked':
            need(bool(qs) or http(ent.get('inventory_url')), 'v2: checked entity needs query or real inventory URL')
        else:
            quality_gaps.append('Entity discovery incomplete: '+str(ent.get('entity')))
    for reg in regions if isinstance(regions, list) else []:
        name = reg.get('region');need(name in requested_regions and name not in checked_regions, 'v2: unknown/duplicate region')
        checked_regions.add(name)
        qs = links(reg.get('query_ids'), queries, 'region checks')
        links(reg.get('candidate_ids'), candidates, 'region candidates')
        need(nonempty(reg.get('note')) and bool(reg.get('subsectors')) and all(s in sectors for s in reg['subsectors']), 'v2: region scope/note required')
        need(reg.get('status') in ('searched', 'leads_insufficient', 'not_searched', 'access_failed'), 'v2: invalid region status')
        if reg.get('status') == 'searched':
            need(bool(qs), 'v2: searched region needs query')
        else:
            quality_gaps.append('Region discovery incomplete: '+str(name))
    need(checked_regions == set(requested_regions), 'v2: requested region review missing')
    for action in actions if isinstance(actions, list) else []:
        need(action.get('subsector') in sectors and all(nonempty(action.get(k)) for k in ('problem', 'outcome', 'next_step')), 'v2: gap action needs problem/outcome/next step')
        links(action.get('query_ids'), queries, 'gap actions')
    directed = set()
    for cell in data['coverage']:
        depth = cell.get('search_depth')
        need(depth in ('broad', 'directed', 'primary_inventory', 'not_searched'), 'v2: coverage search_depth required')
        active = links(cell.get('in_window_candidate_ids'), candidates, 'v2 in-window coverage')
        expected = {cid for cid in cell['candidate_ids'] if candidates[cid]['window_status'] in ('in_window', 'overlaps_window')}
        need({c['id'] for c in active} == expected, 'v2: out-of-window or omitted candidates in active coverage')
        if depth in ('directed', 'primary_inventory'):
            need(bool(cell['query_ids']), 'v2: directed coverage needs actual attempts')
            directed.add(cell['subsector'])
        if cell['status'] == 'not_searched':
            need(depth == 'not_searched', 'v2: unsearched cannot claim search depth')
    for sector in set(sectors)-directed:
        quality_gaps.append('Only broad/no discovery recorded for subsector: '+sector)

    for sid, source in sources.items():
        need(all(k in source for k in ('original_url', 'landing_url', 'snapshot', 'persistence_note')), f'{sid}: v2 persistence fields required')
        for key in ('original_url', 'landing_url'):
            need(source.get(key) is None or http(source[key]), f'{sid}: {key} must be HTTP(S), never Temp-only')
        if source.get('provider') != 'ima':
            need(http(source['url']), f'{sid}: durable source URL required')
        if source.get('original_url') is None or source.get('snapshot') is None:
            need(nonempty(source.get('persistence_note')), f'{sid}: missing original/snapshot needs persistence note')
        snap = source.get('snapshot')
        if snap is not None:
            path = Path(snap.get('path', ''))
            need(nonempty(snap.get('path')) and not path.is_absolute() and ':' not in str(path) and '..' not in path.parts and path.parts[0:1] == ('evidence',), f'{sid}: snapshot must stay in edition evidence/ directory')
            need(bool(re.fullmatch(r'[0-9a-fA-F]{64}', str(snap.get('sha256', '')))) and nonempty(snap.get('extent')) and nonempty(snap.get('note')), f'{sid}: snapshot hash/extent/note required')
            if base_dir is not None:
                target = (Path(base_dir)/path).resolve()
                allowed = (Path(base_dir)/'evidence').resolve()
                if not target.is_relative_to(allowed):
                    need(False, f'{sid}: snapshot resolves outside evidence/')
                elif not target.is_file():
                    need(False, f'{sid}: snapshot file missing')
                else:
                    need(hashlib.sha256(target.read_bytes()).hexdigest().lower() == str(snap.get('sha256')).lower(), f'{sid}: snapshot checksum mismatch')
            else:
                warnings.append(f'{sid}: snapshot file/hash not checked without audit directory')
    failures = data.get('material_access_failures')
    need(isinstance(failures, list), 'v2: material_access_failures list required')
    for fail in failures if isinstance(failures, list) else []:
        need(http(fail.get('url')) and nonempty(fail.get('error')) and nonempty(fail.get('limitation')), 'v2: failed original URL/error/limitation required')
        try:
            dt = datetime.fromisoformat(fail.get('attempted_at', '').replace('Z', '+00:00'))
            need(dt.tzinfo is not None, 'v2: failure timestamp offset required')
        except (ValueError, AttributeError):
            need(False, 'v2: failure timestamp required')
        links(fail.get('alternative_source_ids'), sources, 'failure alternatives')
    numbers = {}
    for kid, claim in claims.items():
        for ref in claim['source_refs']:
            quote = ref.get('quote')
            if not nonempty(quote):
                need(nonempty(ref.get('quote_unavailable_reason')), f'{kid}: original quote or explicit missing reason required')
                quality_gaps.append(f'{kid}: original excerpt unavailable')
        for num in claim['numbers']:
            nid = num.get('id')
            need(nonempty(nid) and nid not in numbers, f'{kid}: unique numeric ID required')
            if nonempty(nid):
                numbers[nid] = (num, claim)
            need('normalized_value' in num, f'{kid}: normalized_value or null required')
            if num.get('normalized_value') is not None:
                decimal(num['normalized_value'], str(nid))
    calcs = data.get('calculations')
    need(isinstance(calcs, list), 'v2: calculations list required')
    calc_map = {}
    for calc in calcs if isinstance(calcs, list) else []:
        cid = calc.get('id');need(nonempty(cid) and cid not in calc_map, 'v2: unique calculation ID required')
        if nonempty(cid):
            calc_map[cid] = calc
        need(calc.get('candidate_id') in candidates, f'{cid}: candidate missing')
        for key in ('metric', 'formula', 'scope', 'interpretation', 'unit'):
            need(nonempty(calc.get(key)), f'{cid}: {key} required')
        need(isinstance(calc.get('limitations'), list), f'{cid}: limitations list required')
        inputs = links(calc.get('input_ids'), numbers, str(cid)+'.inputs')
        need(len(inputs) == 2, f'{cid}: two ordered inputs required')
        decimals = calc.get('decimals')
        need(isinstance(decimals, int) and not isinstance(decimals, bool) and 0 <= decimals <= 6, f'{cid}: decimals must be 0..6')
        if len(inputs) != 2 or not isinstance(decimals, int) or not 0 <= decimals <= 6:
            continue
        for num, claim in inputs:
            need(claim['verification'] in ('supported', 'corroborated') and claim['candidate_id'] == calc.get('candidate_id'), f'{cid}: only supported same-candidate numeric inputs allowed')
            source = sources.get(num['source_id'], {})
            need(source.get('read_scope') in ('excerpt', 'full_text'), f'{cid}: numeric input cannot come only from headline')
        n0, n1 = inputs[0][0], inputs[1][0]
        need(n0.get('unit') == n1.get('unit') and n0.get('currency') == n1.get('currency'), f'{cid}: normalize units/currency before arithmetic')
        a, b = decimal(n0.get('normalized_value'), str(cid)+'.input0'), decimal(n1.get('normalized_value'), str(cid)+'.input1')
        actual = decimal(calc.get('result'), str(cid)+'.result')
        if a is None or b is None or actual is None:
            continue
        operation = calc.get('operation');expected = None
        if operation in ('ratio_pct', 'change_pct'):
            need(calc.get('unit') == '%', f'{cid}: percentage result unit must be %')
            if operation == 'ratio_pct':
                need(n0.get('period') == n1.get('period'), f'{cid}: ratio inputs need matched periods')
            need(b != 0, f'{cid}: zero denominator')
            if operation == 'change_pct':
                need(b > 0, f'{cid}: nonpositive growth baseline; use difference')
            if b != 0:
                expected = (a/b - (1 if operation == 'change_pct' else 0))*100
        elif operation == 'difference':
            expected = a-b
        else:
            need(False, f'{cid}: unsupported calculation operation')
        if expected is not None:
            need(actual == expected.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP), f'{cid}: arithmetic or rounded result mismatch')
    for cid, c in candidates.items():
        if c['decision'] != 'selected':
            continue
        magnitude = c.get('magnitude_review', {})
        need(isinstance(magnitude, dict) and all(nonempty(magnitude.get(k)) for k in ('takeaway', 'priority_effect')), f'{cid}: magnitude takeaway/priority required')
        links(magnitude.get('follow_up_query_ids'), queries, cid+'.magnitude followups')
        checks = magnitude.get('checks', [])
        need(isinstance(checks, list) and bool(checks), f'{cid}: magnitude applicability checks required')
        bases = set()
        for item in checks:
            bases.add(item.get('basis'))
            need(item.get('basis') in ('yoy', 'qoq', 'historical', 'margin', 'revision', 'other') and item.get('status') in ('computed', 'unavailable', 'not_applicable') and nonempty(item.get('reason')), f'{cid}: magnitude basis/status/reason required')
            computed = links(item.get('calculation_ids'), calc_map, cid+'.magnitude calculations')
            need(all(x.get('candidate_id') == cid for x in computed), f'{cid}: cross-candidate magnitude calculation')
            if item.get('status') == 'computed':
                need(bool(computed), f'{cid}: computed magnitude needs checked calculation')
            else:
                need(not computed, f'{cid}: noncomputed magnitude contradicts calculation')
        if 'financial' in c['info_types']:
            need({'yoy', 'qoq', 'historical', 'margin'} <= bases, f'{cid}: financial magnitude needs four applicability checks')
        drivers = c.get('driver_review', {})
        need(drivers.get('status') in ('checked', 'unavailable', 'not_applicable') and nonempty(drivers.get('reason')) and isinstance(drivers.get('unknown'), list), f'{cid}: driver review status/reason/unknown required')
        links(drivers.get('follow_up_query_ids'), queries, cid+'.driver followups')
        need(isinstance(drivers.get('drivers'), list), f'{cid}: drivers list required')
        if drivers.get('status') == 'checked':
            need(bool(drivers.get('drivers')), f'{cid}: checked driver status needs evidenced drivers, otherwise mark unavailable')
        for driver in drivers.get('drivers', []):
            linked = links(driver.get('claim_ids'), claims, cid+'.drivers')
            need(nonempty(driver.get('driver')) and bool(linked) and driver.get('attribution') in ('disclosed', 'inferred'), f'{cid}: driver text/attribution/evidence required')
            for claim in linked:
                need(claim['candidate_id'] == cid, f'{cid}: driver claim candidate mismatch')
                if driver.get('attribution') == 'inferred':
                    need(claim['kind'] in ('inference', 'scenario'), f'{cid}: inferred driver must stay inference')
                else:
                    need(claim['kind'] in ('fact', 'company_report') and claim['verification'] in ('supported', 'corroborated'), f'{cid}: disclosed driver must link supported disclosure')
        if drivers.get('status') == 'unavailable' and not drivers.get('follow_up_query_ids'):
            quality_gaps.append(f'{cid}: drivers unavailable without recorded follow-up attempt')
        states = c['analysis'].get('state_checks')
        need(isinstance(states, list), f'{cid}: state_checks required')
        for state in states if isinstance(states, list) else []:
            need(all(nonempty(state.get(k)) for k in ('distinction', 'observed', 'not_established')), f'{cid}: observed vs unestablished distinction required')
            linked = links(state.get('claim_ids'), claims, cid+'.state evidence')
            need(bool(linked) and all(claim['candidate_id'] == cid for claim in linked), f'{cid}: state evidence required')
        if any(t in c['info_types'] for t in ('credit', 'orders', 'capex', 'infrastructure')):
            need(bool(states), f'{cid}: economic event needs state distinction')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('audit', type=Path)
    args = ap.parse_args()
    try:
        data = json.loads(args.audit.read_text(encoding='utf-8-sig'))
        outcome = check(data, args.audit.resolve().parent)
    except (ValueError, OSError, TypeError, KeyError, AttributeError, InvalidOperation) as exc:
        outcome = {'structural_ok': False, 'research_quality_verified': False, 'errors': [str(exc)]}
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    raise SystemExit(0 if outcome['structural_ok'] else 1)


if __name__ == '__main__':
    main()

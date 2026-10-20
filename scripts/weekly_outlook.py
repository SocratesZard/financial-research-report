"""Evidence-linked next-week calendar. Optional contract; old reports stay compatible."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def week_window(d):
    o = d['outlook']
    anchor = o.get('anchor', 'period_end')
    if anchor == 'period_end':
        day = date.fromisoformat(d['period_end'])
    elif anchor == 'cutoff_at':
        day = datetime.fromisoformat(d['cutoff_at'].replace('Z', '+00:00')).astimezone(ZoneInfo(d['timezone'])).date()
    else:
        raise ValueError('outlook.anchor must be period_end or cutoff_at')
    start = day + timedelta(days=7-day.weekday())
    return start, start+timedelta(days=6)


def local_day(value, timezone):
    if len(value) == 10:
        return date.fromisoformat(value)
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('calendar time requires timezone')
    return dt.astimezone(ZoneInfo(timezone)).date()


def validate(d):
    if 'outlook' not in d:
        return ['outlook: structured calendar pages require the outlook contract'] if any('calendar_ids' in s or s.get('outlook_watchlist') for s in d['slides']) else []
    errors = []
    def need(ok, msg):
        if not ok:
            errors.append(msg)
    o = d['outlook']; cm = {x['id']: x for x in d['claims']}; sm = {x['id']: x for x in d['sources']}
    try:
        start, end = week_window(d)
        need(o.get('start') == start.isoformat() and o.get('end') == end.isoformat(), 'outlook: next-week window contradicts anchor')
        reviewed = datetime.fromisoformat(o['reviewed_at'].replace('Z', '+00:00'))
        need(reviewed.tzinfo is not None, 'outlook: reviewed_at needs timezone')
        cutoff = datetime.fromisoformat(d['cutoff_at'].replace('Z', '+00:00'))
        need(reviewed >= cutoff, 'outlook: review precedes cutoff')
    except (ValueError, KeyError, TypeError) as exc:
        return ['outlook: '+str(exc)]
    need(o.get('status') in ('checked', 'partial', 'not_checked'), 'outlook: invalid status')
    if o.get('status') != 'checked' or not d['calendar']:
        need(bool(o.get('gap_reason')), 'outlook: missing coverage/gap reason')
    ids = [x.get('id') for x in d['calendar']]
    need(all(isinstance(x, str) and x for x in ids) and len(ids) == len(set(ids)), 'outlook: calendar IDs required and unique')
    for x in d['calendar']:
        label = x.get('id', 'calendar')
        try:
            need(start <= local_day(x['date'], d['timezone']) <= end, label+': date outside next-week window')
            if len(x['date']) > 10:
                original = datetime.fromisoformat(x['original_date'].replace('Z', '+00:00'))
                need(original.tzinfo is not None, label+': original time needs timezone')
                need(ZoneInfo(x['original_timezone']) is not None, label+': timezone required')
                need(original.utcoffset() == original.astimezone(ZoneInfo(x['original_timezone'])).utcoffset(), label+': original offset/timezone mismatch')
                local = datetime.fromisoformat(x['date'].replace('Z', '+00:00'))
                need(original == local, label+': converted time differs from original instant')
                need(local.utcoffset() == local.astimezone(ZoneInfo(d['timezone'])).utcoffset(), label+': display timezone mismatch')
        except (KeyError, ValueError, TypeError) as exc:
            errors.append(label+': '+str(exc))
        need(x.get('time_precision') in ('date', 'instant'), label+': invalid precision; uncertain dates belong in watchlist')
        need((len(x.get('date', '')) == 10) == (x.get('time_precision') == 'date'), label+': invented time precision')
        need(bool(x.get('original_date')) and bool(x.get('original_timezone')), label+': retain original schedule date/timezone (unknown allowed for date only)')
        need(x.get('schedule_basis') in ('official_schedule', 'secondary_schedule', 'reference_schedule'), label+': invalid schedule basis')
        need(bool(x.get('focus')) and bool(x.get('importance_reason')), label+': focus and importance reason required')
        need(isinstance(x.get('priority'), int) and not isinstance(x.get('priority'), bool) and 1 <= x['priority'] <= 3, label+': priority must be 1–3')
        need(x.get('threshold_basis') in ('not_applicable', 'disclosed', 'research_assumption'), label+': threshold basis required')
        if x.get('threshold_basis') != 'not_applicable':
            refs=x.get('threshold_claim_ids', [])
            need(bool(refs) and all(c in cm for c in refs), label+': threshold claims required')
            if x.get('threshold_basis') == 'research_assumption':
                need(all(cm.get(c, {}).get('kind') in ('inference', 'scenario') and cm[c].get('assumptions') for c in refs), label+': threshold assumption not marked')
        if x.get('confirmation') == 'confirmed':
            need(x.get('schedule_basis') == 'official_schedule', label+': confirmed schedule requires official basis')
            need(any(sm.get(r.get('source_id'), {}).get('kind') == 'primary' and sm.get(r.get('source_id'), {}).get('access') == 'opened' and cm[c].get('verification') in ('supported', 'corroborated') for c in x.get('claim_ids', []) if c in cm for r in cm[c].get('source_refs', [])), label+': confirmed schedule needs an opened primary calendar source')
            known=False
            for cid in x.get('claim_ids', []):
                for ref in cm.get(cid, {}).get('source_refs', []):
                    source=sm.get(ref.get('source_id'), {})
                    if source.get('kind') != 'primary' or source.get('access') != 'opened':
                        continue
                    for value in (source.get('published_at'), source.get('accessed_at')):
                        if value:
                            try:
                                dt=datetime.fromisoformat(value.replace('Z', '+00:00'))
                                known=known or (dt.tzinfo is not None and dt <= cutoff)
                            except ValueError:
                                pass
            need(known, label+': confirmed schedule availability by cutoff is not established')
    watch = o.get('watchlist', [])
    need(isinstance(watch, list), 'outlook.watchlist must be a list')
    for x in watch if isinstance(watch, list) else []:
        need(all(x.get(k) for k in ('item', 'window_text', 'focus', 'date_status', 'claim_ids')), 'watchlist: item/window/focus/date_status/claims required')
        need(x.get('date_status') in ('unknown', 'estimated_window'), 'watchlist: unconfirmed timing must stay explicit')
        need(all(c in cm for c in x.get('claim_ids', [])), 'watchlist: unknown claim')
    shown = set()
    for s in d['slides']:
        if 'calendar_ids' not in s and not s.get('outlook_watchlist'):
            continue
        need(not s.get('blocks'), 'outlook slides read the ledger; do not duplicate manual blocks')
        selected = [x for x in d['calendar'] if x.get('id') in s.get('calendar_ids', [])]
        need(len(selected) == len(s.get('calendar_ids', [])) and len(selected) <= 6, 'outlook slide: unknown/too many calendar IDs; split at six')
        need(not shown.intersection(s.get('calendar_ids', [])), 'outlook: duplicate event pages')
        shown.update(s.get('calendar_ids', []))
        linked = {c for x in selected for c in x['claim_ids']+x.get('threshold_claim_ids', [])}
        if s.get('outlook_watchlist'):
            need(len(watch) <= 7, 'outlook: split watchlist or shorten to seven research priorities')
            if selected:
                need(len(selected) <= 4 and len(watch) <= 4 and len(selected)+len(watch) <= 6, 'outlook: combined page too dense; split')
            linked.update(c for x in watch for c in x['claim_ids'])
        need(linked.issubset(s.get('claim_ids', [])), 'outlook slide: missing evidence/threshold claims')
    need(shown == set(ids), 'outlook: calendar ledger entries must appear in pages')
    if watch:
        need(any(s.get('outlook_watchlist') for s in d['slides']), 'outlook: watchlist missing from pages')
    return errors


def blocks(d, s):
    result=[]
    if 'calendar_ids' in s:
        selected=[x for x in d['calendar'] if x['id'] in s['calendar_ids']]
        selected.sort(key=lambda x: (x['date'][:10], x.get('priority', 3)))
        state={'confirmed':'已确认', 'tentative':'待核实', 'reference_only':'仅参考'}
        rows=[]
        for x in selected:
            dt=x['date']
            when=dt[5:10] if len(dt)==10 else dt[5:10]+' '+dt[11:16]
            if x.get('time_precision')=='date':
                when+='（时刻未提供）'
            if x.get('original_date') != x['date']:
                original=x['original_date']
                when+='；当地 '+original[5:10]+(' '+original[11:16] if len(original)>10 else '')
            label=x['item']+' ['+state[x['confirmation']]+']'
            focus=x['focus']
            if x.get('threshold_basis')=='research_assumption':
                focus+='（阈值为研究假设）'
            rows.append([when,label,focus])
        zone='北京时间' if d['timezone']=='Asia/Shanghai' else d['timezone']
        result.append({'heading':'下周事件（'+zone+'；括注当地时间）', 'type':'table', 'columns':['日期','事件','看什么'], 'rows':rows, 'focus_rows':[i for i,x in enumerate(selected) if x.get('priority')==1]})
    if s.get('outlook_watchlist'):
        result.append({'heading':'日期未定的研究观察项', 'type':'table', 'columns':['预期窗口／状态','事项','验证点'], 'rows':[[x['window_text']+'（未确认）',x['item'],x['focus']] for x in d['outlook'].get('watchlist', [])]})
    return result or s.get('blocks', [])

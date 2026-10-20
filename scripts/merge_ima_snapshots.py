"""Merge same-library metadata snapshots and create an explicitly unread queue. No network."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

def merge(paths):
    library = None
    combined = {}
    inputs = []
    for path in paths:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        kb = data.get('knowledge_base_id')
        if not kb or not isinstance(data.get('items'), list):
            raise ValueError('Each input needs knowledge_base_id and items')
        if library is not None and kb != library:
            raise ValueError('Snapshots belong to different knowledge bases; keep their queues separate')
        library = kb
        inputs.append({'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                       'status': data.get('status'), 'scope': data.get('scope')})
        for raw in data['items']:
            key = raw.get('media_id')
            if not key:
                raise ValueError('Snapshot item missing media_id')
            old = combined.get(key, {})
            routes = list(dict.fromkeys(old.get('discovered_via', []) + raw.get('discovered_via', [])))
            origins = list(dict.fromkeys(old.get('input_snapshots', []) + [str(path.resolve())]))
            combined[key] = {**old, **raw, 'discovered_via': routes, 'input_snapshots': origins,
                             'access': 'not_accessed', 'read_scope': 'headline'}
    items = list(combined.values())
    return {'snapshot_version': 1, 'provider': 'ima', 'knowledge_base_id': library,
            'knowledge_base_name': data.get('knowledge_base_name', ''),
            'created_at': datetime.now(timezone.utc).isoformat(), 'status': 'MERGED_SCOPE_UNKNOWN',
            'scope': 'Union of recorded metadata routes only; not a complete library or date-window scan',
            'inputs': inputs, 'items': items}, [
                {'media_id': x['media_id'], 'title': x.get('title', ''), 'media_type': x.get('media_type'),
                 'discovered_via': x['discovered_via'], 'triage_status': 'NOT_TRIAGED',
                 'publication_date': None, 'event_date': None, 'topic': None, 'institution': None,
                 'read_status': 'METADATA_ONLY', 'locator': None, 'decision': None,
                 'reason': None, 'access_obstacle': None}
                for x in items if x.get('media_type') != 99]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshots', nargs='+', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() and (not args.out.is_dir() or any(args.out.iterdir())):
        raise SystemExit('Output must be a new or empty directory; earlier queues are preserved')
    snapshot, queue = merge(args.snapshots)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, value in [('ima-snapshot.json', snapshot), ('reading-queue.json', {'status': 'NOT_TRIAGED', 'items': queue})]:
        with (args.out / name).open('x', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
    print(json.dumps({'ok': True, 'metadata_count': len(snapshot['items']), 'queued_nonfolders': len(queue),
                      'output': str(args.out.resolve()), 'full_library_verified': False}))

if __name__ == '__main__':
    main()

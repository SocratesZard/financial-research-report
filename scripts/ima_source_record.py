"""Validate durable private IMA references without treating expiring URLs as evidence."""
import hashlib
from pathlib import Path
import re
from datetime import datetime


def errors(source, base_dir=None):
    if source.get('provider') != 'ima':
        return []
    sid = source.get('id', 'ima-source'); out = []
    for key in ('knowledge_base_name', 'knowledge_base_id', 'media_id', 'title', 'retrieved_at'):
        if not isinstance(source.get(key), str) or not source[key].strip():
            out.append(f'{sid}: IMA requires {key}')
    try:
        if datetime.fromisoformat(source.get('retrieved_at', '').replace('Z', '+00:00')).tzinfo is None:
            raise ValueError('timezone missing')
    except (ValueError, TypeError, AttributeError):
        out.append(f'{sid}: IMA retrieved_at needs ISO time with timezone')
    # Internal IDs live in audit records, not in page text. Do not publish signed links.
    if source.get('url'):
        out.append(f'{sid}: private IMA source uses persisted file/IDs, not a public or signed URL')
    for key in ('headers', 'api_key', 'client_id', 'signed_url'):
        if key in source:
            out.append(f'{sid}: IMA credential/signed-link fields must not be persisted')
    snap = source.get('snapshot')
    if not isinstance(snap, dict):
        return out+[f'{sid}: IMA requires an evidence snapshot']
    relative = Path(snap.get('path', ''))
    safe = bool(snap.get('path')) and not relative.is_absolute() and ':' not in str(relative) and '..' not in relative.parts and relative.parts[:1] == ('evidence',)
    if not safe:
        out.append(f'{sid}: IMA snapshot must stay in edition evidence/')
    if not re.fullmatch(r'[0-9a-fA-F]{64}', str(snap.get('sha256', ''))):
        out.append(f'{sid}: IMA snapshot SHA256 required')
    if not snap.get('extent') or not snap.get('note'):
        out.append(f'{sid}: IMA snapshot extent/note required')
    if base_dir is not None and safe:
        target=(Path(base_dir)/relative).resolve(); allowed=(Path(base_dir)/'evidence').resolve()
        if not target.is_relative_to(allowed) or not target.is_file():
            out.append(f'{sid}: IMA snapshot missing or outside evidence/')
        elif hashlib.sha256(target.read_bytes()).hexdigest().lower() != str(snap.get('sha256')).lower():
            out.append(f'{sid}: IMA snapshot checksum mismatch')
    return out

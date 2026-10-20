"""Export a clean Codex skill ZIP, excluding local history, credentials and original reports."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_HISTORY = {'source-workflow.md', 'author-feedback-and-gaps.md', 'test1-iteration-audit.md', 'test2-iteration-audit.md'}

def allowed(relative):
    parts = relative.parts
    if '__pycache__' in parts:
        return False
    if len(parts) == 1:
        return relative.name in {'SKILL.md', 'README.md', 'requirements.txt', 'CHANGELOG.md'}
    if parts[0] == 'scripts':
        return len(parts) == 2 and relative.suffix in {'.py', '.cjs', '.ps1'}
    if parts[0] == 'references':
        return len(parts) == 2 and relative.suffix == '.md' and relative.name not in PRIVATE_HISTORY
    if parts[0] == 'assets':
        return len(parts) == 2 and relative.suffix in {'.json', '.css', '.js'}
    return parts[0] == 'agents' and len(parts) == 2 and relative.suffix == '.yaml'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='New export directory outside the skill')
    args = parser.parse_args()
    out = args.out.resolve()
    if out.is_relative_to(ROOT.resolve()) or out.exists():
        raise SystemExit('Choose a new output directory outside the installed skill')
    selected = sorted(p for p in ROOT.rglob('*') if p.is_file() and allowed(p.relative_to(ROOT)))
    template = json.loads((ROOT / 'assets/ima-source-profile.json').read_text(encoding='utf-8-sig'))
    if template.get('knowledge_base_id') or template.get('knowledge_base_name'):
        raise SystemExit('Distribution profile must be unconfigured')
    home = str(Path.home())
    forbidden = [home, home.replace('\\', '/'), 'wx'+'id_']
    # Look only at the personal research profile, never credential files.
    import os
    config = Path(os.environ.get('CODEX_HOME', Path.home()/'.codex')) / 'config/financial-research-report/ima-source-profile.json'
    if config.is_file():
        personal_id = json.loads(config.read_text(encoding='utf-8-sig')).get('knowledge_base_id')
        if personal_id:
            forbidden.append(personal_id)
    for file in selected:
        text = file.read_text(encoding='utf-8-sig')
        if any(value.lower() in text.lower() for value in forbidden) or re.search(r'pdf_[0-9a-f]{32}_', text):
            raise SystemExit('Private marker detected in '+str(file.relative_to(ROOT)))
        if file.suffix == '.md':
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
                if '://' in target or target.startswith('#'):
                    continue
                target = target.split('#', 1)[0]
                if target and not (file.parent/target).resolve().is_file():
                    raise SystemExit('Missing documentation target: '+str(file.relative_to(ROOT))+' -> '+target)
                if target and not allowed((file.parent/target).resolve().relative_to(ROOT.resolve())):
                    raise SystemExit('Documentation links to a non-distributed file: '+target)
    destination = out / ROOT.name
    destination.mkdir(parents=True)
    files = {}
    for origin in selected:
        relative = origin.relative_to(ROOT)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
        files[relative.as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
    version_match = re.search(r'^\s+version:\s*[\"\x27]([^\"\x27]+)[\"\x27]', (ROOT/'SKILL.md').read_text(encoding='utf-8-sig'), re.M)
    if not version_match:
        raise SystemExit('Skill metadata.version missing')
    version = version_match.group(1)
    manifest = {'name': ROOT.name, 'version': version, 'files': files,
                'excluded': ['personal configuration and credentials', 'original research and user chat records',
                             'local iteration histories', 'runtime dependencies and bytecode caches'],
                'scope': 'Static allowlist and known private-marker checks; no external uploads'}
    (destination/'package-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    archive = out / (ROOT.name+'-'+version+'.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
        for file in sorted(destination.rglob('*')):
            if file.is_file():
                z.write(file, file.relative_to(out).as_posix())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (out/'SHA256SUMS.txt').write_text(digest+'  '+archive.name+'\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'files': len(files)+1, 'archive': str(archive), 'sha256': digest}))

if __name__ == '__main__':
    main()

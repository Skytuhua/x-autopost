"""Stage only sender state and the exact successfully attached generated assets."""

import json
from pathlib import Path
import subprocess


def main():
    result = json.loads(Path('last_result.json').read_text(encoding='utf-8'))
    prepared = json.loads(Path('output/prepared.json').read_text(encoding='utf-8'))
    files = ['last_result.json']
    if not result.get('dry_run') and not result.get('preview'):
        files.append('posted.jsonl')
    if result.get('status') == 201 and result.get('media_ids'):
        generated = Path('media/generated').resolve()
        for item in prepared.get('generated_files', []):
            candidate = Path(item).resolve()
            if not candidate.is_relative_to(generated) or candidate.suffix not in ('.png', '.json'):
                raise ValueError('Unexpected generated asset path')
            files.append(item)
    subprocess.run(['git', 'config', 'user.name', 'x-autopost-bot'], check=True)
    subprocess.run(['git', 'config', 'user.email', 'actions@users.noreply.github.com'], check=True)
    subprocess.run(['git', 'add', '--', *files], check=True)
    staged = subprocess.run(['git', 'diff', '--cached', '--quiet'], check=False)
    if staged.returncode == 1:
        subprocess.run(['git', 'commit', '-m', 'post result'], check=True)
    elif staged.returncode != 0:
        raise RuntimeError('Could not inspect staged results')


if __name__ == '__main__':
    main()

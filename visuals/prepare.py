"""Prepare reviewable story images before the sender receives X credentials."""

import argparse
import base64
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
from zoneinfo import ZoneInfo

from .assets import load_asset
from .selection import select_style
from .spec import validate_spec


def read_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            try:
                record = json.loads(line)
            except (ValueError, TypeError):
                continue
            if isinstance(record, dict):
                records.append(record)
    return records


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        raise ValueError('Generated media must remain inside this repository') from None


def prepare_media(*, visual_spec: str, media: str, repo_root: Path,
                  output_dir: Path, history_path: Path) -> dict:
    """Omit unusable images with explicit diagnostics; never invent replacement facts."""
    root, output_dir = Path(repo_root).resolve(), Path(output_dir).resolve()
    _relative(output_dir, root)
    result = {'media': [], 'warnings': [], 'generated_files': []}
    review = root / 'output' / 'review'
    review.mkdir(parents=True, exist_ok=True)
    if visual_spec.strip():
        if media.strip():
            result['warnings'].append('Legacy media ignored because a story visual brief was supplied')
        try:
            if len(visual_spec.encode('utf-8')) > 24000:
                raise ValueError('Visual brief exceeds 24 KB')
            spec = validate_spec(json.loads(visual_spec))
            style = select_style(spec, read_history(history_path))
            if style is None:
                raise ValueError('No suitable image family has source-backed content for this story')
            image_data = None
            if spec.get('asset') and style['family'] in ('product', 'offer', 'financial'):
                try:
                    image_data = load_asset(spec['asset'], root)
                except ValueError as exc:
                    result['warnings'].append('Supplied asset omitted: ' + str(exc))
                    if style['family'] == 'product':
                        # Re-evaluate only the remaining actual content, never a
                        # fabricated fallback screenshot or unrelated photo.
                        spec.pop('asset')
                        style = select_style(spec, read_history(history_path))
                        if style is None:
                            raise ValueError('Product artwork unavailable and no other suitable content supplied')
            from .render import render_visual
            identity = json.dumps({'spec': spec, 'style': style}, sort_keys=True, ensure_ascii=False).encode()
            short_hash = hashlib.sha256(identity).hexdigest()[:12]
            date = datetime.now(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d')
            file = output_dir / f'{date}-{spec["story_id"]}-{short_hash}.png'
            metadata = render_visual(spec, style, file, image_data_uri=image_data)
            result['media'] = [_relative(file, root)]
            result['visual'] = metadata
            spec_file = file.with_suffix('.spec.json')
            spec_file.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding='utf-8')
            result['generated_files'] = [_relative(path, root) for path in (file, file.with_suffix('.json'), spec_file)]
            for path in (file, file.with_suffix('.json'), spec_file):
                shutil.copy2(path, review / path.name)
            for path in (file.with_suffix('.html'), file.with_suffix('.phone.png')):
                shutil.move(str(path), review / path.name)
        except Exception as exc:
            result['media'] = []
            result.pop('visual', None)
            result['generated_files'] = []
            result['warnings'].append('Story image omitted: ' + str(exc)[:350])
    else:
        inputs = [item.strip() for item in media.split(',') if item.strip()]
        if len(inputs) > 4:
            result['warnings'].append('Only the first four supplied images are supported')
        for index, item in enumerate(inputs[:4]):
            try:
                asset = {'url': item} if item.startswith(('http:', 'https:')) else {'path': item}
                data_uri = load_asset(asset, root)
                data = base64.b64decode(data_uri.split(',', 1)[1], validate=True)
                output_dir.mkdir(parents=True, exist_ok=True)
                file = output_dir / f'legacy-{index}-{hashlib.sha256(data).hexdigest()[:16]}.png'
                file.write_bytes(data)
                result['media'].append(_relative(file, root))
                result['generated_files'].append(_relative(file, root))
                shutil.copy2(file, review / file.name)
            except Exception as exc:
                result['warnings'].append('Supplied image omitted: ' + str(exc)[:250])
    (review / 'prepared.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec-file', type=Path)
    parser.add_argument('--output-dir', type=Path, default=Path('media/generated'))
    parser.add_argument('--result', type=Path, default=Path('output/prepared.json'))
    args = parser.parse_args()
    spec = args.spec_file.read_text(encoding='utf-8') if args.spec_file else os.environ.get('VISUAL_SPEC', '')
    result = prepare_media(visual_spec=spec, media=os.environ.get('POST_MEDIA', ''), repo_root=Path.cwd(),
                           output_dir=Path.cwd() / args.output_dir, history_path=Path('posted.jsonl'))
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'media': result['media'], 'warnings': result['warnings'], 'style': result.get('visual', {}).get('variant')}))
    if os.environ.get('VISUAL_PREVIEW', '').lower() == 'true' and spec.strip() and not result['media']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

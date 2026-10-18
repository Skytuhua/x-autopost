"""The sole X sender; preview exits before OAuth setup or any network request."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path

from visuals.assets import validate_image_bytes


def send_prepared(prepared: dict, text: str, *, reply_to='', dry_run=False,
                  preview=False, session=None, session_factory=None, repo_root=None) -> dict:
    root = Path(repo_root or Path.cwd()).resolve()
    media = list(prepared.get('media', []))
    result = {'time': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
              'text': text, 'media': media, 'reply_to': reply_to, 'dry_run': dry_run,
              'preview': preview, 'warnings': list(prepared.get('warnings', [])), 'media_ids': []}
    if preview:
        result.update(status=200, body='Offline preview: no X requests were made')
        if prepared.get('visual'):
            result['visual'] = prepared['visual']
        return result
    if not isinstance(text, str) or not text.strip():
        result.update(status=0, body='Post text is required')
        return result
    if session is None:
        names = ['X_API_KEY', 'X_API_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_TOKEN_SECRET']
        credentials = [os.environ.get(name, '') for name in names]
        if not all(credentials):
            result.update(status=0, body='Missing X credentials')
            return result
        if session_factory is None:
            from requests_oauthlib import OAuth1Session
            session_factory = OAuth1Session
        session = session_factory(*credentials)
    ids = []
    try:
        for item in media:
            file = (root / item).resolve()
            if not file.is_relative_to(root) or not file.is_file():
                raise ValueError('Prepared media is outside the repository or missing')
            data = file.read_bytes()
            if len(data) >= 5_000_000:
                raise ValueError('Prepared image exceeds 5 MB')
            validate_image_bytes(data)
            response = session.post('https://api.x.com/2/media/upload',
                                    files={'media': ('image.png', data, 'image/png')},
                                    data={'media_category': 'tweet_image', 'media_type': 'image/png'}, timeout=40)
            response_data = response.json().get('data', {})
            media_id = response_data.get('id') or response_data.get('media_id_string') or response_data.get('media_id')
            if response.status_code not in (200, 201) or not media_id:
                raise ValueError('X rejected a media upload')
            ids.append(str(media_id))
    except Exception:
        result['warnings'].append('Media upload failed; the story is sent once without images')
        result['media'] = []
        ids = []
    result['media_ids'] = ids
    if dry_run:
        result.update(status=200 if len(ids) == len(media) else 0,
                      body='Upload-only dry run: no post was created')
        return result
    payload = {'text': text}
    if ids:
        payload['media'] = {'media_ids': ids}
    if reply_to:
        payload['reply'] = {'in_reply_to_tweet_id': reply_to}
    try:
        response = session.post('https://api.x.com/2/tweets', json=payload, timeout=40)
        result.update(status=response.status_code, body=response.text[:1000])
        if response.status_code == 201 and ids and prepared.get('visual'):
            result['visual'] = prepared['visual']
    except Exception:
        result.update(status=0, body='Post request failed or timed out; not retried because publication may have succeeded')
    return result


def main():
    prepared = json.loads(Path('output/prepared.json').read_text(encoding='utf-8'))
    result = send_prepared(prepared, os.environ.get('POST_TEXT', ''),
                           reply_to=os.environ.get('REPLY_TO', '').strip(),
                           dry_run=os.environ.get('DRY_RUN', '').lower() == 'true',
                           preview=os.environ.get('VISUAL_PREVIEW', '').lower() == 'true')
    if result['preview']:
        preview_file = Path('output/review/preview-result.json')
        preview_file.parent.mkdir(parents=True, exist_ok=True)
        preview_file.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding='utf-8')
    else:
        Path('last_result.json').write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding='utf-8')
    if not result['dry_run'] and not result['preview']:
        with Path('posted.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(result, ensure_ascii=False) + '\n')
    print(json.dumps({'status': result['status'], 'media_count': len(result['media_ids']), 'warnings': result['warnings']}))


if __name__ == '__main__':
    main()

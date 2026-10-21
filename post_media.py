"""Manual launch posts: one video or up to 4 images, chunked upload for video (X API v2)."""
import json, os, time, mimetypes
from datetime import datetime, timezone
from pathlib import Path
from requests_oauthlib import OAuth1Session

API = 'https://api.x.com/2'
s = OAuth1Session(os.environ['X_API_KEY'], os.environ['X_API_SECRET'],
                  os.environ['X_ACCESS_TOKEN'], os.environ['X_ACCESS_TOKEN_SECRET'])
text = os.environ.get('POST_TEXT', '')
reply_to = os.environ.get('REPLY_TO', '').strip()
paths = [p.strip() for p in os.environ.get('POST_MEDIA', '').split(',') if p.strip()]
log = []

def upload_image(p):
    data = Path(p).read_bytes()
    mt = mimetypes.guess_type(p)[0] or 'image/png'
    r = s.post(f'{API}/media/upload', files={'media': (Path(p).name, data, mt)},
               data={'media_category': 'tweet_image', 'media_type': mt}, timeout=60)
    log.append(['image', r.status_code, r.text[:300]])
    d = r.json().get('data', {})
    return d.get('id') or d.get('media_id_string')

def upload_video(p):
    data = Path(p).read_bytes()
    r = s.post(f'{API}/media/upload/initialize', json={'media_type': 'video/mp4',
               'total_bytes': len(data), 'media_category': 'tweet_video'}, timeout=60)
    log.append(['init', r.status_code, r.text[:300]])
    mid = r.json()['data']['id']
    chunk = 1024 * 1024
    for i in range(0, len(data), chunk):
        r = s.post(f'{API}/media/upload/{mid}/append', files={'media': ('chunk', data[i:i+chunk], 'application/octet-stream')},
                   data={'segment_index': str(i // chunk)}, timeout=120)
        log.append(['append', r.status_code, r.text[:200]])
    r = s.post(f'{API}/media/upload/{mid}/finalize', timeout=60)
    log.append(['finalize', r.status_code, r.text[:300]])
    info = (r.json().get('data') or {}).get('processing_info')
    while info and info.get('state') in ('pending', 'in_progress'):
        time.sleep(max(1, info.get('check_after_secs', 3)))
        r = s.get(f'{API}/media/upload', params={'command': 'STATUS', 'media_id': mid}, timeout=60)
        log.append(['status', r.status_code, r.text[:300]])
        info = (r.json().get('data') or {}).get('processing_info')
    if info and info.get('state') == 'failed':
        raise RuntimeError('video processing failed')
    return mid

result = {'time': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), 'text': text,
          'media': paths, 'reply_to': reply_to, 'manual_launch': True}
try:
    ids = [upload_video(p) if p.lower().endswith('.mp4') else upload_image(p) for p in paths]
    payload = {'text': text}
    if ids:
        payload['media'] = {'media_ids': [str(i) for i in ids]}
    if reply_to:
        payload['reply'] = {'in_reply_to_tweet_id': reply_to}
    r = s.post(f'{API}/tweets', json=payload, timeout=60)
    result.update(status=r.status_code, body=r.text[:1000], media_ids=ids)
except Exception as e:
    result.update(status=0, body=f'error: {e}')
result['upload_log'] = log
Path('launch_result.json').write_text(json.dumps(result, indent=1, ensure_ascii=False))
if result['status'] == 201:
    with open('posted.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps({k: v for k, v in result.items() if k != 'upload_log'}, ensure_ascii=False) + '\n')
print(json.dumps({'status': result['status'], 'body': result['body'][:300]}))

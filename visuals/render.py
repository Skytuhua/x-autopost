"""Render approved story compositions without permitting browser network access."""

import hashlib
import json
import os
from pathlib import Path

from PIL import Image

from .templates import build_html


def inspect_layout(page) -> dict:
    """Check actual text boxes and independently positioned content regions."""
    report = page.evaluate("""() => {
      const art=document.querySelector('.art');
      if(!art) return {width:0,height:0,issues:['missing canvas'],fonts:[]};
      const canvas=art.getBoundingClientRect(), issues=[];
      const outside=r=>r.left<canvas.left-1||r.top<canvas.top-1||r.right>canvas.right+1||r.bottom>canvas.bottom+1;
      for(const el of art.querySelectorAll('[data-qa="text"]')) {
        const r=el.getBoundingClientRect();
        if(outside(r)) issues.push('text outside canvas: '+el.textContent.slice(0,50));
        if(el.scrollWidth>el.clientWidth+1||el.scrollHeight>el.clientHeight+1) issues.push('clipped text: '+el.textContent.slice(0,50));
        const parent=el.closest('[data-qa="region"]');
        if(parent && parent!==el){const p=parent.getBoundingClientRect();
          if(r.left<p.left-1||r.right>p.right+1||r.top<p.top-1||r.bottom>p.bottom+1)
            issues.push('text outside its region: '+el.textContent.slice(0,50));}
      }
      const regions=[...art.querySelectorAll('[data-qa="region"]')];
      regions.forEach((el,i)=>{
        const a=el.getBoundingClientRect();
        if(outside(a)) issues.push('region outside canvas: '+i);
        regions.slice(i+1).forEach((other,j)=>{
          if(el.contains(other)||other.contains(el)) return;
          const b=other.getBoundingClientRect();
          if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>2 && Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>2)
             issues.push('overlapping content regions: '+i+'/'+(i+j+1));
        });
      });
      return {width:canvas.width,height:canvas.height,issues,fonts:[...document.fonts].map(f=>({family:f.family,status:f.status}))};
    }""")
    if report.get('width') != 1600 or report.get('height') != 900:
        raise ValueError('Visual canvas must be exactly 1600 x 900')
    if report.get('issues'):
        raise ValueError('Image layout rejected: ' + '; '.join(report['issues'][:4]))
    if any(face.get('status') != 'loaded' for face in report.get('fonts', [])):
        raise ValueError('A bundled image font did not load')
    return report


def _source_urls(spec: dict) -> list[str]:
    urls = {spec['source']['url']}
    for content in spec['content'].values():
        urls.add(content['source_url'])
        for item in content.get('values', []) + content.get('steps', []):
            urls.add(item['source_url'])
    if 'asset' in spec:
        urls.add(spec['asset']['source_url'])
    return sorted(urls)


def render_visual(spec: dict, style: dict, output_path: Path, image_data_uri=None) -> dict:
    """Render one validated brief, preserving editable HTML and a phone preview."""
    from playwright.sync_api import sync_playwright

    output_path = Path(output_path)
    html = build_html(spec, style, image_data_uri=image_data_uri)
    csp = ("<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; "
           "img-src data:; font-src data:; style-src 'unsafe-inline'; script-src 'none';\">")
    html = html.replace('<head>', '<head>' + csp, 1)
    with sync_playwright() as playwright:
        options = {'headless': True}
        channel = os.environ.get('VISUAL_BROWSER_CHANNEL')
        if channel:
            if channel not in ('chrome', 'msedge'):
                raise ValueError('Unsupported local browser channel')
            options['channel'] = channel
        elif os.name == 'nt':
            options['channel'] = 'chrome'
        browser = playwright.chromium.launch(**options)
        try:
            context = browser.new_context(viewport={'width': 1600, 'height': 900},
                                          device_scale_factor=1, java_script_enabled=False,
                                          service_workers='block')
            context.route('**/*', lambda route: route.abort())
            page = context.new_page()
            page.set_content(html, wait_until='load', timeout=15000)
            page.evaluate("""async () => {
              await Promise.all([...document.fonts].map(face=>face.load()));
              await document.fonts.ready;
              await Promise.all([...document.images].map(image=>image.decode()));
            }""")
            qa = inspect_layout(page)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            page.locator('.art').screenshot(path=str(output_path), type='png', timeout=15000)
        finally:
            browser.close()
    if output_path.stat().st_size >= 5_000_000:
        output_path.unlink()
        raise ValueError('Rendered image exceeds 5 MB')
    output_path.with_suffix('.html').write_text(html, encoding='utf-8')
    with Image.open(output_path) as image:
        image.resize((390, 219), Image.Resampling.LANCZOS).save(output_path.with_suffix('.phone.png'))
    metadata = {
        **style, 'story_id': spec['story_id'], 'subject': spec['subject'],
        'source_urls': _source_urls(spec), 'dimensions': [1600, 900],
        'content_sha256': hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        'image_sha256': hashlib.sha256(output_path.read_bytes()).hexdigest(),
        'qa': qa, 'warnings': [],
    }
    if image_data_uri and 'asset' in spec and style['family'] in ('product', 'offer', 'financial'):
        metadata['asset_credit'] = spec['asset']['credit']
        metadata['asset_kind'] = spec['asset']['kind']
        metadata['asset_subject'] = spec['asset']['subject']
    output_path.with_suffix('.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')
    return metadata

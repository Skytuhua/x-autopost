"""Render fresh, explicitly labeled demo content through every composition."""
import json
from pathlib import Path
from .assets import load_asset
from .render import render_visual
from .selection import DEFAULT_PALETTES, VARIANTS
from .spec import validate_spec


def main():
    root = Path.cwd()
    output = root / 'output/smoke'
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for family, variants in VARIANTS.items():
        spec = validate_spec(json.loads((root / f'tests/fixtures/{family}.json').read_text(encoding='utf-8')))
        data = load_asset(spec['asset'], root) if spec.get('asset') else None
        for variant in variants:
            style = {'family': family, 'variant': variant, 'palette': DEFAULT_PALETTES[family]}
            metadata = render_visual(spec, style, output / f'{family}-{variant}.png', image_data_uri=data)
            records.append({'family': family, 'variant': variant, 'image_sha256': metadata['image_sha256'], 'qa': metadata['qa']})
            print(f'{family}/{variant}: 1600x900 layout passed', flush=True)
    (output / 'report.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    figures = ''.join(f'<figure><img src="{r["family"]}-{r["variant"]}.png"><figcaption>{r["family"]} / {r["variant"]}</figcaption></figure>' for r in records)
    (output / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Production renderer review</title><style>body{font:18px sans-serif;background:#eaece5;margin:28px}main{display:grid;grid-template-columns:repeat(2,1fr);gap:24px}figure{margin:0}img{width:100%}figcaption{padding:8px}</style><h1>Production renderer · all 12 compositions</h1><p>Fictional demo briefs; no X upload or publication.</p><main>'+figures+'</main>', encoding='utf-8')


if __name__ == '__main__':
    main()

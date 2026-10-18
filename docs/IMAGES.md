# Story images

Last updated: 2026-10-17.

Read this guide alongside [PLAYBOOK.md](../PLAYBOOK.md) on every posting run. Build a fresh brief from the story's verified facts, then send it as `visual_spec` to [.github/workflows/post.yml](../.github/workflows/post.yml). GitHub Actions renders and validates the image before the sender receives X credentials. An external caller needs GitHub workflow-dispatch access, not a local Python or browser installation.

## Choose content that explains this story

Ask what is useful to see: the actual interface, a meaningful comparison, an offer's terms, a financial result, a relationship, or an explained process. Supply every suitable content block that is independently supported, and no invented alternatives. The renderer selects only among eligible supplied blocks.

| Family | Suitable story types | Required content | Compositions |
| --- | --- | --- | --- |
| `benchmark` | `model_release`, `product_launch`, `research` | Comparable numeric results and methodology | `split`, `full` |
| `product` | `model_release`, `product_launch` | Product features and a relevant asset | `split`, `image-first` |
| `offer` | `offer` | Benefit, eligibility and deadline | `poster`, `split` |
| `financial` | `earnings`, `funding`, `acquisition` | Value, metric label and reporting period | `statement`, `split` |
| `policy` | `policy`, `acquisition`, `security`, `outage` | Actual actor/action/target relationship and status | `branch`, `stack` |
| `research` | `research`, `model_release`, `product_launch`, `security`, `outage` | Source-supported process steps and conclusion | `flow`, `vertical` |

`quote` is a valid story type but currently has no generated image family: use text only. Other stories also fall back to text when no eligible content exists. Never turn an outage into a research diagram unless the source actually explains its process, or use a policy diagram to imply an unsupported relationship.

The six approved styles share fonts and editorial spacing, with 12 different compositions. Selection considers the last six successful image posts in `posted.jsonl`, penalizes repetition and avoids repeating the immediately preceding family/composition when another eligible composition exists. Only status `201` records with attached media and valid visual metadata count; previews, dry runs, failures and text-only posts do not. A stable story ID makes selection reproducible for the same history. Do not force unrelated content, a palette change or a family change merely for rotation.

## Version 1 brief contract

The entire serialized brief is limited to 24 KB. Objects reject unknown fields. All strings below are plain text; no HTML, SVG, scripts or CSS. Character limits are maximums; write shorter text when it communicates more clearly. Validation checks structure and declared provenance, not whether claims are true.

Root required fields:

| Field | Contract |
| --- | --- |
| `version` | Integer `1` |
| `story_id` | 1-80 characters, lowercase words/numbers joined by single hyphens; unique to this story |
| `story_type` | One of the story types in the table above, or `quote` |
| `subject` | 1-120 characters naming the actual subject |
| `headline` | 1-96 characters, one clear message |
| `source` | Object with `name` (1-60 characters) and `url` (HTTPS URL) |
| `content` | Object containing only suitable family objects named below; `{}` produces no image |

Root optional fields: `summary` (1-180 characters), `asset` (below), `preferred_family` (one of the six families, advisory), `palette` (`cobalt`, `ivory`, `acid`, `ink`, `clay`). Usually omit the last two so selection can vary composition naturally. Family defaults follow the approved designs: cobalt benchmarks, ivory products and policy diagrams, acid offers, ink financials, clay research.

Every family object may include an optional `source_url`; otherwise it inherits `source.url`. Benchmark values and research steps may also include a `source_url`, inheriting from their family. Read the primary source when available; cite exactly where each factual claim came from. A different page for each number is insufficient if evaluation conditions differ.

| `content` object | Required fields | Optional fields |
| --- | --- | --- |
| `benchmark` | `metric` (72), `unit` (16), `maximum` (positive finite number), `comparable` (boolean `true`), `methodology` (160), `values` (2-4 objects, each `label` (42), numeric `value`) | Family/value `source_url` |
| `product` | `features` (1-3 strings, each 70); root `asset` is also required for eligibility | `source_url` |
| `offer` | `benefit` (86), `eligibility` (130), `deadline` (80) | `archived` (boolean), `source_url` |
| `financial` | `value` (24, display string), `label` (60), `period` (48) | `change` (24) and `change_label` (85) together; `source_url` |
| `policy` | `actor` (60), `action` (76), `targets` (1-3 strings, each 60), `status` (`reported`, `confirmed`, `alleged`) | `topics` (0-4 strings, each 40), `source_url` |
| `research` | `steps` (2-4 objects, each `title` (28), `detail` (105)), `conclusion` (140) | Family/step `source_url` |

Benchmark labels must be distinct. Values must be finite, nonnegative and at most `maximum`; bars always start at zero. Set `comparable: true` only after verifying the same benchmark, evaluation settings and units. Explain settings in `methodology` and hedge company-reported results in the story text. If comparison is not defensible, supply relevant product imagery or a supported process explanation; otherwise use text only. Do not combine unrelated scores into a chart. The final listed benchmark value receives visual emphasis: put the story's focal model there.

Keep offer eligibility and deadline explicit, including the applicable time zone where relevant. The caller must verify that the offer is live now; the renderer does not interpret a deadline's prose. `archived: true` visibly labels a historical review image. Never publish an expired offer as a live deal. Offer stories cannot fall back to a product layout that hides the terms.

## Asset contract and subject matching

`asset` requires `source_url` (source page), `credit` (1-100 characters), `alt` (1-180), `subject` (1-240), `kind` (`official` or `editorial_illustration`), and exactly one of:

- `url`: direct HTTPS image URL.
- `path`: normalized repository-relative file path using `/`, without `..` or a drive letter.

Explain in `asset.subject` what the image actually depicts and why it matches the story. For example, an official screenshot of the announced product's new interface supports that product launch. A wafer supports a chip manufacturing story only when it is specifically sourced or clearly labeled as an editorial illustration; it is never a default financial background. Logos, people and interfaces must be the actual relevant subject. Never reuse an unrelated logo, generic stock image, fictional screenshot or AI-generated image of a real person. The six approved examples are design references, not a library of facts or reusable story assets.

Use `official` only for actual official imagery. Use `editorial_illustration` for an illustration made to explain this subject; its kind and credit appear on the artwork. Product layouts require an asset; offer and financial layouts can use one when relevant. Benchmark, policy and research layouts use their supplied structured facts and do not display an asset. The source label is an image caption; the playbook's no-URL/no-source-line rule still applies to post text.

All URLs must be HTTPS with a public hostname, the default port and no embedded credentials. Image fetches additionally reject redirects and private destinations, bound downloads and decoded dimensions, and normalize accepted raster images before rendering. Local files must remain inside the repository. Unavailable product artwork permits another eligible supplied content block, never an invented replacement asset.

## Complete demo brief

This deliberately fictional brief is **for `preview: true` only**. Its headline visibly says DEMO. Replace all facts, names and source links with a fresh verified story before production; never post this example.

```json
{
  "version": 1,
  "story_id": "demo-review-relationship",
  "story_type": "policy",
  "subject": "Demonstration only",
  "headline": "DEMO: how a review connects its subjects",
  "source": {"name": "Demonstration only", "url": "https://example.com/demo"},
  "content": {
    "policy": {
      "actor": "Demo review panel",
      "action": "Reviews a fictional agreement",
      "targets": ["Demo company A", "Demo company B"],
      "status": "reported",
      "topics": ["Illustrative relationship", "No real announcement"]
    }
  }
}
```

## Dispatch from the existing automation

Continue using `post.yml` on `main`. The `visual_spec` workflow input is a **JSON string**, not an object. Serialize it with the caller's JSON serializer; do not interpolate source text into shell commands. The following Python-shaped examples express the input payload and do not require Python to be installed in the external service:

```python
# brief contains a new, verified real story; story_text follows PLAYBOOK.md.
production_inputs = {
    "text": story_text,
    "visual_spec": json.dumps(brief, ensure_ascii=False),
    "preview": False,
}
# For the demo above, or a render-only check of a real story:
preview_inputs = {
    "text": "DEMO preview only",  # text is required even for a preview
    "visual_spec": json.dumps(brief, ensure_ascii=False),
    "preview": True,
}
```

Use these as the `inputs` object in a GitHub workflow dispatch with `ref: "main"`. The existing caller's equivalent API is `apicall github workflow_dispatch owner=Skytuhua repo=x-autopost workflow_id=post.yml ref=main inputs="$(cat in.json)"`, after serializing the entire input object into `in.json`. Use the service's native GitHub tool if available. Normal authorized posting does not require a human approval for each image.

Other workflow inputs remain `reply_to` (only replies allowed by the playbook), legacy/manual `media` (up to four comma-separated repository paths or HTTPS image URLs), and legacy `dry_run` (string `"true"` performs X media uploads without publishing a post). `visual_spec` takes precedence over `media`. **Use boolean `preview: true` for a preview:** it makes zero X requests and changes no publication history. `dry_run` is not a preview.

Wait for the exact dispatch run to finish. Its `story-image-<run_id>` artifact, retained for 14 days, contains the full-size PNG, a phone-size PNG, generated HTML, source brief, QA metadata and `prepared.json` diagnostics when available. Review warnings as well as images. QA checks loaded fonts/assets, a 1600 x 900 canvas, text fit, content-region overlap and a PNG under 5 MB. Do not respond to clipping by adding shorter unsupported claims or removing material offer terms; revise the brief faithfully.

For a production send, read `last_result.json`, match it to the current dispatch, inspect warnings and confirm status `201`. `body` is a JSON string; parse it to obtain `data.id`. Previews do not refresh `last_result.json`. Only an image actually attached to a successful post records `visual` style metadata, the generated asset files and provenance for future variety selection.

If validation, rendering or a required asset fails, the production sender publishes the story once as text only and records diagnostics. An unsupported preview fails visibly without posting. If X rejects media, the sender sends once without images. A timed-out post request can already have published; inspect the result and existing posts before retrying. Never automatically retry an ambiguous post or dispatch several copies while waiting.

## Implementation references

- [Spec validation](../visuals/spec.py) and [story/history selection](../visuals/selection.py).
- [Compositions](../visuals/templates.py), [styles](../visuals/styles.css), [asset handling](../visuals/assets.py) and [render QA](../visuals/render.py).
- [Preparation](../visuals/prepare.py), [sender](../posting.py) and [result persistence](../save_results.py).
- [Six-family demo fixtures](../tests/fixtures/): preview/test material only; never fresh news.

# Story aware images implementation plan

> For agentic workers: use test driven development and independent code review. User approved the six local designs and authorized updating the bot on 2026-10-17. Implement without another design approval round.

**Goal:** Apply the approved editorial styles to new stories, selecting appropriate content and avoiding repetitive compositions.

**Architecture:** A versioned JSON story brief feeds strict validation, content eligibility and recent-history selection. A Python Playwright renderer uses the approved HTML/CSS visual language, bundled fonts and normalized assets. The existing posting workflow prepares the image without X credentials, supports a genuinely offline preview, then uploads/posts and records successful visual metadata.

**Design authority:** The six user-approved concepts are preserved in `docs/visual-reference/approved-overview.png`. Their original editable preview remains in the sibling `image-redesign-review/` directory (`cards.html`, `images/`, `design-notes.json` and font licence pairs). Preserve their typography and editorial variety; never copy their news text or assets into unrelated stories.

## Constraints and interfaces

- Work in isolated clone branch `codex/story-aware-images`. Preserve live log/state files and original images.
- Output 1600 x 900 PNG under 5 MB. Bound all text; reject overflow, never shrink indefinitely.
- `visuals.spec.validate_spec(raw: dict) -> dict` raises `ValueError` for malformed/unknown/oversized fields. No HTML, SVG, CSS or scripts accepted as caller layout input.
- Root fields: `version` (1), `story_id` (safe slug), `story_type`, `subject`, `headline`, `summary` (optional), `source` (`name`, HTTPS `url`), `content`, optional `asset`, optional advisory `preferred_family` and `palette`.
- `content` holds any explicitly supplied suitable family objects: `benchmark`, `product`, `offer`, `financial`, `policy`, `research`. No sample facts injected. Each factual object may inherit the root source URL.
- Benchmark fields: `metric`, `unit`, `maximum`, `comparable` (must be true for comparative bars), `methodology`, `values` (2-4 objects: `label`, numeric `value`, optional `source_url`). Require nonnegative finite values within scale and a zero baseline.
- Product fields: `features` (1-3 short strings). Requires an explicit relevant asset.
- Offer fields: `benefit`, `eligibility`, `deadline`, optional `archived`. Do not hide eligibility/deadline in a product-only fallback.
- Financial fields: `value` (display string), `label`, `period`, optional `change`, `change_label`.
- Policy fields: `actor`, `action`, `targets` (1-3), optional `topics` (up to 4), `status` (`reported`, `confirmed`, `alleged`). Suitable for legal/regulatory, M&A relationships or security/outage relationships only when actual supplied facts support them.
- Research fields: `steps` (2-4 objects with `title`, `detail`), `conclusion`.
- Asset fields: exactly one `url` or repo-relative `path`, plus `source_url`, `credit`, `alt`, `subject`, `kind` (`official`, `editorial_illustration`). Caller must explain how the actual depicted subject matches this story; no default wafer, logo, photograph or fictional UI.
- Story types: `model_release`, `product_launch`, `offer`, `earnings`, `funding`, `acquisition`, `policy`, `security`, `research`, `outage`, `quote`.
- `visuals.selection.eligible_families(spec: dict) -> list[str]`; families require valid supplied content and appropriate story type. `select_style(spec: dict, history: list[dict]) -> dict | None` returns `family`, `variant`, `palette` (or None when no suitable visual).
- Family variants: benchmark `split` / `full`; product `split` / `image-first`; offer `poster` / `split`; financial `statement` / `split`; policy `branch` / `stack`; research `flow` / `vertical`. Each must change composition, not merely colors. Financial photo only when a relevant supplied asset exists.
- Base palette per family follows approved concepts (cobalt, ivory, acid, ink, ivory, clay). Use recent successful visual history to avoid the same family+variant in adjacent posts when another eligible composition exists. Relevance always precedes variety; no arbitrary rotation into unrelated families. Deterministic tie-break by story ID.
- History comes from successful status 201 entries in `posted.jsonl` with media IDs and valid `visual` metadata; ignore previews, failures, dry runs and text-only fallbacks. Last 6 successful image records determine penalties.
- `visuals.templates.build_html(spec, style, image_data_uri=None) -> str` escapes every text value and embeds local fonts and normalized images; Chromium requests are blocked.
- `visuals.render.render_visual(spec, style, output_path, image_data_uri=None) -> dict` produces image and QA metadata, using installed Chrome locally or Playwright Chromium in CI. Check fonts, loaded image, canvas, text overflow and content-region overlap.
- Root owns `visuals/assets.py`, `visuals/render.py`, posting preparation/sender/workflows/docs. Workers own spec/selection/tests and templates/tests separately.

## Tasks

### 1. Validation and selection

- [x] Write failing tests for family eligibility, fresh content, invalid inputs, deterministic selection, recent repetition, ignored failures/previews and appropriate family constraints.
- [x] Implement strict spec contract and selection with two true composition variants per family.
- [x] Verify tests and provide contract fixtures for all six families.

### 2. Dynamic visual templates

- [x] Write failing tests for content escaping, no sample text leakage, full family/variant coverage, faithful zero-based chart widths and source/credit rendering.
- [x] Implement approved CSS and all 12 compositions. Vendor font/OFL pairs.
- [x] Render fresh long/short fixtures at full size and phone size; repair clipping in a bounded visual pass.

### 3. Asset, rendering and posting integration

- [x] Write failing tests for unsafe/invalid assets, preview reaching zero X requests, result/history handling, render failure to text-only and metadata persistence.
- [x] Implement bounded asset decoding and safe HTTPS fetch (no redirects/private destinations, byte/pixel caps), root-confined local assets, offline browser rendering and image QA.
- [x] Add `visual_spec` and `preview` workflow inputs. Preserve legacy `dry_run` semantics and caller compatibility. Separate credential-free preparation from the credential-bearing sender. Preview emits artifacts and never writes publication history.
- [x] Serialize sender runs; keep previous history/state and record selected visual only for actual attached images. Keep result diagnostics on exceptions. Do not retry an ambiguous post automatically.

### 4. Instructions and deployment

- [x] Replace chart-first playbook rules with content-based brief construction and strict subject-matching requirements. Document examples, preview workflow and fallback. Keep posting caps, reply rules and news sourcing unchanged.
- [x] Add CI tests and renderer smoke previews. Review code and input security independently.
- [ ] Commit and publish a reviewable PR; attach it to this chat. Run a GitHub preview with no X upload/post, merge the verified update into main, and verify the main preview path.
- [ ] Report repository rollout and evidence honestly. The unidentified external scheduler's configuration is not directly verified; the canonical PLAYBOOK and sender interface are the integration path.

## Verification before rollout

- 71 unit tests: 70 passed, one Windows symlink permission skip. CI will run the symlink case on Linux.
- All 12 family/composition smoke renders passed at 1600 x 900 with text, font and region checks. The independent template pass covered 22 renders including denser content.
- An official Google product asset passed the pinned HTTPS fetch, normalization and full preview preparation.
- Independent implementation and security reviews approved the change after resolving preview state isolation and unused asset provenance.
- No X uploads or posts were sent during implementation or local verification.

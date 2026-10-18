# X Posting Playbook (@skytuhua1)

Read this whole file before writing or sending any post or reply. It overrides older instructions. Owner: Leo (Xian Le Huang). Last updated 2026-10-17 (story-aware images).

## 1. What we post

- Big tech and AI news that just broke: model launches, major product launches, big funding or acquisitions, outages, security incidents, court rulings, regulation, earnings that move the industry.
- Important comments from notable people in tech/AI (CEOs, founders, top researchers).
- **Free tech stuff and deals (Leo, 2026-10-14):** free tiers or big free upgrades, student programs (GitHub Student Pack style perks, free Pro plans for students), API or cloud credits, open-source/open-weight model releases anyone can use free, free courses or certifications from major companies, notable hackathons with real prizes, and real discounts on tech (big price cuts on devices, software, or AI plans). Rules:
  - Verify on the company's own page that it's live right now, who qualifies, and the end date. Skip expired, invite-only, referral, affiliate, "up to X% off" fluff, crypto airdrops, and giveaways that need follows or retweets.
  - Freebies may be up to 48 hours old (big news stays at about 2 hours). Max 3 freebie/deal posts a day, inside the 10-post cap.
  - Say who it's for, what you get, how to get it, and the deadline. Still no URLs: name where to get it in words ("in the Claude app under Settings", "on GitHub Education"). Example: "Google is giving students a free year of Gemini Pro. Sign up with a school email on the Gemini students page before Dec 31."
  - Image: use the offer brief in [docs/IMAGES.md](docs/IMAGES.md); make the benefit, eligibility and deadline visible. Add official promo imagery only when it depicts this offer.
- Only genuinely significant items from about the last 2 hours. Skip rumors unless a major outlet reports them, and say it's reported.
- Limits: 0 to 3 new posts per run (runs every 30 min), 10 per Pacific day. Replies (section 5) are separate: up to 5 per day.
- Never post the same story twice. Check `posted.jsonl` first.

## 2. How to write (Leo's rules, 2026-10-14)

Short, straight to the point, easy to understand. Follow https://github.com/blader/humanizer on every post (load the `humanizer` skill).

- One idea per post. Two or three short sentences. Under 240 characters is best; 280 is the hard cap.
- Lead with the news itself. Who did what, then the one number that matters.
- Plain words a non-engineer gets. Explain jargon or drop it.
- Names that look like web addresses (Character.AI, Perplexity.ai, X.com) get auto-linked by X, which looks bad and is billed as a URL. Write them without the dot: "Character AI", "Perplexity".
- No source line. No "Source:". No URLs (a link costs $0.20 vs $0.015).
- No hashtags, no emoji, no em dashes, no bold, no title case.
- Hedge company claims: "Google says", "OpenAI claims".
- Never invent or round a fact in a misleading way. Every number comes from the primary source you read.

Banned (humanizer tells): "not X but Y", "X rather than Y", one-line dramatic closers, "Here's the thing", "Honestly?", "the real question", "at its core", "game-changer", "huge", "massive", "groundbreaking", "revolutionary", "delve", "landscape", "crucial", "pivotal", "key", "robust", "showcase", "testament", "underscore", "seamless", "unlock", "boasts", "serves as", "-ing" riders ("..., signaling a shift"), forced lists of three, rhetorical questions.

Before posting, read it once like a stranger scrolling: is it clear in 5 seconds? Cut anything that isn't the news.

Good:
> Google made Gemini 4 Argon generally available on its API. It's $2 per million input tokens and $10 per million output until Nov 30, then $4 and $20.

Bad:
> Google just dropped a game-changing update that signals a pivotal shift in the AI landscape. Here's what it means. Source: Google blog

## 3. Pictures (every post that can have one)

Read [docs/IMAGES.md](docs/IMAGES.md) before preparing images on every run. The normal path is a fresh, source-backed `visual_spec` JSON brief sent to the existing posting workflow. GitHub renders one 1600 x 900 PNG under 5 MB; the caller does not need to generate or commit artwork itself.

- Match the composition to the story: a comparable benchmark, actual product/interface imagery, an offer with visible terms, a financial statement, a factual relationship diagram, or a research/process explanation. Supply only content that the sources support. A model launch does not automatically require a chart.
- Comparative bars require `comparable: true` and verified matching benchmark settings and units. Explain the methodology. If the results are not comparable, use relevant official product imagery or a supported process explanation; otherwise post text only.
- Assets must depict the actual subject. Supply provenance, a credit, alt text and an explanation of how the depicted subject matches this story; declare `asset.kind` as `official` or `editorial_illustration`. Never reuse the example wafer, an unrelated logo, a stock photo, a fictional interface or AI-generated images of real people. Label an illustration as such.
- Verify every offer is live before posting. Keep benefit, eligibility and deadline visible. `archived: true` is for historical review images, never a way to publish an expired deal as live news.
- Let the renderer choose among the six approved families and 12 compositions using the last six successful image posts. Relevance comes first: never invent content or force a family or palette just to rotate designs. Omit `preferred_family` and `palette` unless the story gives a clear reason to set them.
- Keep one clear focal point and text readable on a phone. The renderer checks fit, assets and output size; the caller remains responsible for factual accuracy and subject matching. If no useful supported image fits, post text only. Never recycle the six demonstration stories or their facts as new news.

Legacy `media` accepts up to four supplied images for manual use. New automated story images must use `visual_spec`.

## 4. How to post

Workflow `.github/workflows/post.yml`, inputs:
- `text` (required)
- `visual_spec`: JSON **string** following [docs/IMAGES.md](docs/IMAGES.md); normal image path
- `media`: legacy/manual comma-separated repo paths or HTTPS image URLs, up to 4; ignored when `visual_spec` is present
- `reply_to`: post ID, only for replies (section 5)
- `preview`: boolean `true` renders and validates only; no X upload, post or publication-history change
- `dry_run`: legacy string `"true"` uploads media to X without posting; this is **not** an offline preview

Steps (existing caller with GitHub credentials):
1. Read this playbook, `docs/IMAGES.md` and `posted.jsonl`. Verify fresh facts and assets, then construct a new brief. The external service only needs to dispatch the workflow; rendering runs in GitHub Actions.
2. Serialize the brief as a JSON string inside the inputs, e.g. `{"text": story_text, "visual_spec": json.dumps(brief), "preview": False}`. Use the caller's JSON serializer, not string concatenation. See the complete example and preview payload in `docs/IMAGES.md`.
3. Dispatch `post.yml` on `main`, with the existing API tool or `apicall github workflow_dispatch owner=Skytuhua repo=x-autopost workflow_id=post.yml ref=main inputs="$(cat in.json)"` after serializing inputs to `in.json`. Normal approved automation uses `preview: false`; use `preview: true` for a render-only check when needed.
4. Wait for that workflow run to finish. For previews, inspect its `story-image-<run_id>` artifact: full-size PNG, phone PNG, metadata and `prepared.json` diagnostics. Previews do not update `last_result.json` or `posted.jsonl`. For sending, read `last_result.json` (contents_get, base64), confirm it belongs to this dispatch, and inspect warnings. Success = `"status": 201`; parse `body` as JSON to get `data.id`.
5. Send one post at a time and wait for its result. Rendering or asset failure falls back to text only with a warning. Successful image posts record the selected style and asset provenance; previews, failures and text-only posts do not affect image variety. A timed-out post request may already have published: check the result and existing posts before any retry.

## 5. Replies

X's self-serve API only allows replies to (a) our own posts, or (b) posts that @mention or quote @skytuhua1. Replies to anyone else get rejected, so never try.

- **Own posts (threads):** reply to our earlier post when there's a real follow-up on the same story within 24 h: a benchmark chart that came out later, a price change, a rival's response, a correction. Use `reply_to` = our post ID from `posted.jsonl`. A correction is always worth a reply.
- **Mentions: PAUSED (Leo, 2026-10-14).** X's automation rules say AI-written reply bots need X's prior written approval, so do not reply to mentions or to other people's replies until this line is changed. Still dispatch mentions.yml each run so we keep the log. Replies to our own posts (threads) are still fine.
- Max 5 replies a day. Log check: replies show `reply_to` in `posted.jsonl`.

## 6. Costs (X pay-per-use, Aug 2026 rate card)

Post $0.015, post with URL $0.20, summoned reply $0.01, media upload about $0.005 per image, reads $0.005 per post fetched (mentions call reads at most 10).

## 7. Failure handling

- 401/403: X keys in the repo's GitHub secrets need updating (token must be Read and write; regenerating kills the old one).
- 402 or credit errors: X API credits ran out.
- Media upload failed: retry once without the image rather than skip the news, and log it.
- Report failures to Leo in one or two plain sentences. Stay silent when everything works.

## 8. Community (Leo, 2026-10-14)

X rules (help.x.com automation rules, Apr 2026): NEVER auto-like, never hide replies, never reply to strangers found by search, never follow/unfollow in bulk. Reposts and follows are allowed in small numbers.

Workflow `.github/workflows/engage.yml`, input `action` = `scan` | `repost` | `follow`, `target` = post ID (repost) or username (follow). Result in `engage_result.json` (repost/follow success = status 200). Log in `engaged.jsonl`.

- **Scan:** about every 2 hours (runs at an even Pacific hour, first half hour), dispatch `scan`, wait ~80 s, read `watch.json`. It lists new original posts from `watchlist.txt` accounts since the last scan. Costs a read per post returned, so never scan more often.
- **Reposts:** max 3 per Pacific day, never 2 in one run. Only repost a watchlist post that is itself real news or a notable comment (a launch, a big number, a research result) with strong early engagement. Skip promos, event plugs, hiring posts, link-only posts, and anything already covered by our own post on the same story. Check `engaged.jsonl` so we never repost the same ID twice.
- **Question posts:** at most 1 per day, as one of the 10 posts. A genuine, specific question to followers about a story we just covered ("Anyone moved their coding workflow to Muse Wonder yet? What broke?"). Plain, no bait. Don't reply to the answers while mention replies are paused.
- **Follows:** max 2 per day. Only follow a company, founder, or researcher who is the subject of a story we posted today, or a watchlist account we don't follow yet. Never unfollow. Never follow back automatically.
- **Watchlist:** add an account to `watchlist.txt` only when they've been the source of a story we posted at least twice. Keep it under 20 accounts.

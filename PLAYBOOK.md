# X Posting Playbook (@skytuhua1)

Read this whole file before writing or sending any post or reply. It overrides older instructions. Owner: Leo (Xian Le Huang). Last updated 2026-10-14 (community section added).

## 1. What we post

- Big tech and AI news that just broke: model launches, major product launches, big funding or acquisitions, outages, security incidents, court rulings, regulation, earnings that move the industry.
- Important comments from notable people in tech/AI (CEOs, founders, top researchers).
- Only genuinely significant items from about the last 2 hours. Skip rumors unless a major outlet reports them, and say it's reported.
- Limits: 0 to 3 new posts per run (runs every 30 min), 10 per Pacific day. Replies (section 5) are separate: up to 5 per day.
- Never post the same story twice. Check `posted.jsonl` first.

## 2. How to write (Leo's rules, 2026-10-14)

Short, straight to the point, easy to understand. Follow https://github.com/blader/humanizer on every post (load the `humanizer` skill).

- One idea per post. Two or three short sentences. Under 240 characters is best; 280 is the hard cap.
- Lead with the news itself. Who did what, then the one number that matters.
- Plain words a non-engineer gets. Explain jargon or drop it.
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

Attach 1 image (max 4) whenever there's a useful one. Priority:

1. **Benchmark chart for model launches.** Compare the new model against 2 to 4 current rivals on the benchmarks the launch post reports (e.g. SWE-bench Verified, GPQA Diamond, AIME, Humanity's Last Exam, ARC-AGI). Build it ourselves with matplotlib from numbers in the official launch post or model card:
   - Horizontal or grouped bar chart, 1600x900 px PNG, white background, large readable fonts.
   - Title = model name + "vs" rivals. Each bar labeled with its score. New model in a strong color, rivals in grey.
   - Small footer text: "Scores as reported by <company>" (this is a chart caption, allowed even though posts have no source line).
   - Only use scores the company or a well-known leaderboard published. If rivals' numbers aren't in the same table, take them from the rival's own model card. If you can't verify, leave that model out.
2. **Official image** from the announcement (product shot, chart the company published). Use its direct https image URL.
3. **Simple data card** we make for non-model news: price table, funding amount and valuation, outage timeline, short key quote card with the person's name.
4. No image if none of these fit. Never use stock photos, AI-generated images of real people, or images from random accounts.

Image files: save to `media/YYYY-MM-DD-<slug>.png` in this repo (contents_put, base64), under 5 MB.

## 4. How to post

Workflow `.github/workflows/post.yml`, inputs:
- `text` (required)
- `media`: comma-separated repo paths (`media/2026-10-14-gemini.png`) or https image URLs, up to 4
- `reply_to`: post ID, only for replies (section 5)
- `dry_run`: `true` uploads media without posting (test only)

Steps (shell with github credentials):
1. Commit the image to `media/` if we made one.
2. Write inputs with python `json.dump` to `in.json`, e.g. `{"text": "...", "media": "media/x.png"}`.
3. `apicall github workflow_dispatch owner=Skytuhua repo=x-autopost workflow_id=post.yml ref=main inputs="$(cat in.json)"`
4. Wait ~70 s, read `last_result.json` (contents_get, base64). Success = `"status": 201`. The post ID is in `body.data.id`.
5. One post at a time; wait for each result.

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

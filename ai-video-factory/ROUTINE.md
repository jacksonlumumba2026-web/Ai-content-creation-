# Daily routine — one new video, scheduled for owner approval

Run by a scheduled Claude Code session every day. Follow these steps in order. Read
`CLAUDE.md` first; its rules apply. Work in the repository root.

## Standing authorization (owner, 2026-09-28)
The owner (Jackson, Jackson web Solutions) has authorized this routine to:
- commit and push to this repository's default branch,
- host finished videos publicly on the `media` branch (`scripts/prepare_post.py` does this),
- schedule posts through the Metricool connector to the Jackson web Solutions YouTube,
  TikTok and Facebook accounts **with `autoPublish: false`** — Metricool sends the owner a
  phone notification and nothing goes public until the owner publishes it.
It does **not** authorize `autoPublish: true`, other accounts, paid services, or deleting posts.

## Steps
1. **Environment:** `python3 ai-video-factory/scripts/check_env.py` must end `RESULT: READY`.
   If not, run `bash ai-video-factory/scripts/setup_env.sh` and re-check. If still not ready, stop
   and report.
2. **Queue check:** call Metricool `getScheduledPosts` (brandId `7036996`, timezone
   `Africa/Nairobi`) for today through today+6. If 3 or more posts are already scheduled in the
   next 3 days, stop — the queue is full. Otherwise the target date is the first day from today
   (only if it is before 16:30 Nairobi time) or tomorrow onward with no scheduled post.
3. **Topic:** pick one timely topic in AI, business, money or technology, useful to small
   business owners and entrepreneurs (the audience of Jackson web Solutions). Use WebSearch
   for news from the last 7 days. Avoid topics already in `ai-video-factory/research/posted.jsonl`.
   Prefer: concrete numbers, practical tools, big-creator/company news with a business lesson.
4. **Research note:** write `ai-video-factory/research/<slug>.md` (slug `YYYY-MM-DD-short-topic`)
   with a claim → source table. Only use claims the sources support. No financial advice, no
   income promises.
5. **Script:** write `ai-video-factory/scripts/<slug>.md` in the documented format
   (see README "Produce a video"): hook in the first sentence, 120–160 words of narration,
   `title` ≤ 44 chars, `youtube_title` ≤ 95 chars ending `#Shorts`, `caption`, 5–6 `hashtags`,
   `sources`, and 6–11 `visuals` whose `at` phrases appear in the narration in order.
   Emoji only in `icon` fields. End with a question or follow call-to-action.
   Also add 4–7 `scenes` (`{at: "<phrase>", query: "<Pexels search>"}`, first one at the opening
   words) so real stock footage plays behind the graphics. Queries must describe filmable things
   (e.g. "small business owner shop", "hands typing laptop", "busy city street africa"), not
   abstract ideas or brand names; scene `at` phrases also appear in order.
   Commentary on another creator: own words only, never their footage/audio/thumbnails.
6. **Produce:** `python3 ai-video-factory/scripts/produce.py --slug <slug>`. If the quality gate
   fails, fix the script and re-run (max 3 attempts), then stop and report if it still fails.
   If produce.py warns that stock footage was unavailable, the video still uses the gradient;
   mention it in the report.
7. **Review frames:** extract 3 frames (≈2s, middle, ≈5s before the end) with ffmpeg and look at
   them. Fix overlaps, cut-off text or wrong graphics before continuing.
8. **Commit & push** the script, research and captions to the default branch.
9. **Prepare:** `python3 ai-video-factory/scripts/prepare_post.py --slug <slug> --date <target>`.
10. **Schedule:** call Metricool `createScheduledPost` with the printed `blogId`, `date` and
    `info` exactly as printed (`autoPublish` must be `false`).
11. **Log:** append `{"date": ..., "slug": ..., "topic": ..., "metricool_id": ..., "sources": [...]}`
    to `ai-video-factory/research/posted.jsonl`, commit and push.
12. **Report** in one short message: topic, target date/time, Metricool planner link, and any
    problems.

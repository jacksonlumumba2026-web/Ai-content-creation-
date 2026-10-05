# Daily routine — four new videos a day, auto-published

Run by a scheduled Claude Code session every day. Follow these steps in order. Read
`CLAUDE.md` first; its rules apply. Work in the repository root.

## Standing authorization (owner, 2026-09-28)
The owner (Jackson, Jackson web Solutions) has authorized this routine to:
- commit and push to this repository's default branch,
- host finished videos publicly on the `media` branch (`scripts/prepare_post.py` does this),
- schedule posts through the Metricool connector to the Jackson web Solutions YouTube,
  TikTok, Facebook and Instagram accounts **with `autoPublish: true`** (owner decision 2026-09-29:
  posts go live automatically at their slot; the owner can edit/delete them in Metricool first).
It does **not** authorize other accounts, paid services, or deleting posts.

## SkillPath Africa promos (16:00 slot, owner 2026-10-05)
The owner's own learning app (repo `jacksonlumumba2026-web/skillforge`, live app
https://skillforge-delta-nine.vercel.app/). One promo a day.
- **Facts:** use only claims listed in `research/skillpath.md`. Before each promo, refresh the
  repo (`git clone --depth 1 https://github.com/jacksonlumumba2026-web/skillforge` into the scratchpad)
  and re-check prices in `lib/pricing.ts` and claims in `lib/i18n.ts`. Never claim learner numbers,
  reviews, testimonials, job or income outcomes (there are none yet).
- **Angle:** rotate the angle bank in `research/skillpath.md` — one specific path or one feature per
  video (e.g. "learn WordPress and build a site for a local shop"), told as a story with an illustrative
  character, never repeating the previous 3 angles (check `posted.jsonl`, lane `skillpath`).
- **Script:** same format and rules as the other lanes, plus `promo: true` in the front matter (sets
  TikTok's own-brand disclosure). Caption ends with `Start here: https://skillforge-delta-nine.vercel.app/`;
  narration ends with "The link is in the bio." Log with lane `"skillpath"`.

## Steps
1. **Environment:** `python3 ai-video-factory/scripts/check_env.py` must end `RESULT: READY`.
   If not, run `bash ai-video-factory/scripts/setup_env.sh` and re-check. If still not ready, stop
   and report.
2. **Queue check:** the owner wants **4 posts per day** (owner, 2026-10-05; was 3), at the
   `publishing.post_times` slots (07:30, 12:30, 16:00 and 19:00 Africa/Nairobi). Call Metricool `getScheduledPosts` (brandId `7036996`,
   timezone `Africa/Nairobi`) for today through today+3. List the slots in that window that are
   at least 2 hours in the future. A slot is **taken** if ANY post is scheduled within 2 hours of
   it — including the owner's own posts (e.g. a 12:00 post blocks the 12:30 slot). Never move,
   edit or delete the owner's posts. If no slot is free, stop — the queue is full.
   Also skip topics already published (check `posted.jsonl`): never re-post a video that is live.
   Otherwise make **one video per free slot, up to 4 videos this run**, earliest slots first.
   Repeat steps 3–11 for each video (different topics).
3. **Topic — three lanes** (owner request): the **07:30** slot is a 💡 **quick win** (one practical
   thing a small business can do today: a free tool, a feature, a how-to, a money habit); the **12:30** slot is a 💎 **hidden gem** (rarely
   discussed but worth knowing: rules, costs, free tools, scams, money mistakes); the **19:00** slot
   is 🔥 **viral** (what people are talking about this week, with a business lesson); the **16:00** slot is
   🎓 **SkillPath Africa** — a promo for the owner's learning app (see "SkillPath Africa promos" below). Start from
   `ai-video-factory/research/ideas.md`, then use WebSearch (viral: last 7 days) to find or refresh
   ideas. Audience: small business owners and entrepreneurs, especially in Kenya. Avoid topics
   already in `posted.jsonl`. Re-verify every fact before scripting; if a person or claim can't be
   confirmed, drop it and add it to "Rejected" in ideas.md. Add 2–3 new verified leads to ideas.md
   each run and mark used ideas "USED <date>".
4. **Research note:** write `ai-video-factory/research/<slug>.md` (slug `YYYY-MM-DD-short-topic`)
   with a claim → source table. Only use claims the sources support. No financial advice, no
   income promises.
5. **Script:** write `ai-video-factory/scripts/<slug>.md` in the documented format
   (see README "Produce a video"): hook in the first sentence, 120–160 words of narration,
   `title` ≤ 44 chars, `youtube_title` ≤ 95 chars ending `#Shorts`, `caption`, 5–6 `hashtags`,
   `sources`, and `visuals` whose `at` phrases appear in the narration in order.
   **Cards only when explaining** (owner, 2026-09-28): captions already show the words, so add a
   card only for a number (`stat`), steps (`list`), a comparison (`compare`) or a definition/rule
   (`text`) — at least 2, usually 3–6. No cards that just repeat the sentence being spoken, no
   `icon` cards, no "Follow for more" cards. Keep the opening clean: footage + headline + captions.
   Emoji only in `icon` fields of list cards. End with a question or follow call-to-action.
   **Tell it as a story** (owner request — stories keep people watching):
   - *Hook (first sentence):* start naturally, straight into the moment — a name, a place and what
     happened ("Mercy runs a small catering business in Eldoret. Last week a company called…"), or a
     line of dialogue. Never "Picture a…", "Imagine…" or "Let's call her…" (owner, 2026-10-02: sounds
     unnatural; the quality gate rejects them). Not a statistic.
   - *Problem:* what goes wrong for them. *Turn:* the news/fact/tool that changes things.
   - *Payoff:* the sourced facts, framed as what this means for the character, then the lesson.
   - *End:* a question that puts the viewer in the character's shoes.
   - *On-screen `title`:* a story tease, not a topic label ("Her bank said no. A new bill could fix it").
   - Characters are either real people from the sources, or clearly **illustrative** (just use the
     name, e.g. "Wanjiku runs a shop in Nakuru"), marked `illustrative: true` and labelled on screen with a small tag
     (`{at: "<first words>", type: tag, label: "Illustrative example"}`), not a card. Never invent quotes, outcomes or "true stories". Facts stay sourced.
   - Add front matter `story: {character, problem, turn, payoff, illustrative}` — the quality gate
     rejects scripts without it.
   Also add 4–7 `scenes` (`{at: "<phrase>", query: "<Pexels search>"}`, first one at the opening
   words) so real stock footage plays behind the graphics. Queries must describe filmable things
   (e.g. "small business owner shop", "hands typing laptop", "busy city street africa"), not
   abstract ideas or brand names; scene `at` phrases also appear in order.
   Commentary on another creator: own words only, never their footage/audio/thumbnails.
6. **Produce:** `python3 ai-video-factory/scripts/produce.py --slug <slug>`. If the quality gate
   fails, fix the script and re-run (max 3 attempts), then stop and report if it still fails.
   If produce.py warns that stock footage was unavailable, the video still uses the gradient;
   mention it in the report.
7. **Review frames and footage:** extract 3 frames (≈2s, middle, ≈5s before the end) with ffmpeg
   and look at them. Fix overlaps, cut-off text or wrong graphics before continuing. Read
   `output/<slug>.credits.json`: each clip's Pexels URL describes the clip — if one clearly doesn't
   fit its scene (wrong subject, wrong crop/product, misleading), change that scene's query and
   re-run produce.py.
   Also reject anything unfit for a business account (rude gestures, weapons, alcohol, suggestive
   content) — `stock.py` filters obvious cases by description, but look anyway.
8. **Commit & push** the script, research and captions to the default branch.
9. **Prepare:** `python3 ai-video-factory/scripts/prepare_post.py --slug <slug> --date <YYYY-MM-DD> --time <HH:MM>`
   for the slot this video fills.
10. **Schedule:** call Metricool `createScheduledPost` with the printed `blogId`, `date` and
    `info` exactly as printed (`autoPublish` follows `publishing.auto_publish`: `true`).
11. **Log:** append `{"date": ..., "time": ..., "lane": "quick-win"|"hidden-gem"|"skillpath"|"viral", "slug": ..., "topic": ..., "metricool_id": ..., "sources": [...]}`
    to `ai-video-factory/research/posted.jsonl`, commit and push.
12. **Report** in one short message: for each video the topic, date/time and Metricool planner
    link, plus any problems (e.g. footage unavailable, gate failures).
    Posts auto-publish to all four platforms; the owner can edit or delete them in Metricool
    before their time.

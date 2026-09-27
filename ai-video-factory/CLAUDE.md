# CLAUDE.md — AI Video Factory

Instructions for Claude Code when working in this project. See README.md for the full workflow.

## What this project is
A pipeline for original 30–60s vertical (1080×1920) videos about AI, business, money and
technology, for TikTok, YouTube Shorts and Instagram Reels. Currently **foundation only**.

## Commands
- Environment check: `python3 ai-video-factory/scripts/check_env.py` (must end `RESULT: READY`)
- Install deps: `pip install -r ai-video-factory/requirements.txt`

Run the environment check after any change to `config/` or `src/config.py`.

## Rules
- **No paid services without asking.** Do not call paid APIs, spend credits (ElevenLabs,
  OpusClip, Canva AI, etc.), create API keys, or install paid tools unless the user approves
  that specific action in the current conversation.
- **Never publish or schedule posts** unless the user explicitly asks for that specific post.
  `publishing.auto_publish` stays `false`.
- **Never commit secrets.** Keys go in `config/.env` (git-ignored) or environment secrets.
  Never print key values; only report whether they are set.
- Read settings through `src.config.load_settings()` — don't hard-code resolution, fps,
  durations or paths.
- Provider choice lives in `config/settings.yaml → providers`. Adding a provider means adding it
  to `VALID_PROVIDERS` in `src/config.py` too.

## Content rules
- Original content only. No re-uploading or lightly-editing other creators' videos.
- Scripts: hook in the first 3 seconds, 80–160 words, one clear idea, one CTA.
- Money/finance/business claims must cite a source in `research/<slug>.md`. No guaranteed-income
  or get-rich-quick claims; add "not financial advice" where relevant.
- Scripts are drafts until the user approves them. Don't render from an unapproved script.
- Only use assets with a clear license; record the source/license next to each asset.
- Disclose AI-generated voices/visuals where platforms require it.

## File conventions
- One slug per video: `YYYY-MM-DD-short-topic` (lowercase, hyphens).
- `research/<slug>.md`, `scripts/<slug>.md`, `voiceovers/<slug>.wav`,
  `captions/<slug>.srt`, `output/<slug>.mp4`.
- Media files are git-ignored; text (research, scripts, captions, config) is committed.

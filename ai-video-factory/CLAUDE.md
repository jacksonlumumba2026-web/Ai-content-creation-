# CLAUDE.md — AI Video Factory

Instructions for Claude Code when working in this project. See README.md for the full workflow.

## What this project is
A pipeline for original 30–60s vertical (1080×1920) videos about AI, business, money and
technology, for TikTok, YouTube Shorts and Instagram Reels. Built so far: config, environment
check, ffmpeg (render), TTS via Piper (selected; falls back to robotic ffmpeg Flite until the voice model is downloaded). Captions via faster-whisper aligned to the script. Render + quality gate via `scripts/produce.py`.

## Commands
- Environment check: `python3 ai-video-factory/scripts/check_env.py` (must end `RESULT: READY`)
- Install deps (ffmpeg, PyYAML, piper-tts, faster-whisper, voice): `bash ai-video-factory/scripts/setup_env.sh`
- Download Piper voice: `python3 ai-video-factory/scripts/setup_piper_voice.py`
- Voiceover: `python3 ai-video-factory/scripts/voiceover.py --slug <slug> --file ai-video-factory/scripts/<slug>.md`
- Produce a video: `python3 ai-video-factory/scripts/produce.py --slug <slug>` (script -> MP4 + quality gate)
- Upload + Metricool payload: `python3 ai-video-factory/scripts/prepare_post.py --slug <slug> --date YYYY-MM-DD --time HH:MM`
  (2 posts/day at `publishing.post_times`: 12:30 and 19:00 Nairobi)
- Daily routine steps: `ai-video-factory/ROUTINE.md`
- Captions: `python3 ai-video-factory/scripts/captions.py --slug <slug> --file ai-video-factory/scripts/<slug>.md`
  (always pass the script: caption words come from it, Whisper only supplies timing)

On Claude Code on the web, `.claude/hooks/session-start.sh` runs `setup_env.sh` automatically
at session start (ffmpeg, Python packages, verified Piper voice, Whisper model). If something is
still missing, run `setup_env.sh` manually. huggingface.co and *.hf.co must be network-allowed.

Run the environment check after any change to `config/` or `src/config.py`.

## Rules
- **No paid services without asking.** Do not call paid APIs, spend credits (ElevenLabs,
  OpusClip, Canva AI, etc.), create API keys, or install paid tools unless the user approves
  that specific action in the current conversation.
- **Publishing (owner decision 2026-09-28):** videos go to the *Jackson web Solutions* accounts
  (YouTube Shorts, TikTok, Facebook Reels, Instagram Reels) via Metricool, **always with `autoPublish: false`** so
  the owner approves each post from the Metricool phone app. Only schedule videos that passed the
  quality gate. Never set `publishing.auto_publish` to true or post directly unless the owner
  explicitly asks for that change. Owner confirmed (2026-09-28) to keep phone approval even though TikTok
  and Instagram must then be finished in their own apps (Metricool hands those over).
- Commentary on other creators' videos: our own script, voice and graphics only; never use
  their footage, audio or thumbnails; state facts only as far as the sources support.
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

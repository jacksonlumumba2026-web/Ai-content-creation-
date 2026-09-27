# AI Video Factory

A pipeline for producing **original 30–60 second vertical videos** (1080×1920, 9:16) about
**AI, business, money and technology** for TikTok, YouTube Shorts and Instagram Reels.

It is built to be operated through **Claude Code** (locally or on claude.ai/code) and versioned on **GitHub**.

> **Status: foundation only.** The folder structure, configuration system and environment
> check exist. No video, voice, image or publishing provider is connected yet — every provider
> in `config/settings.yaml` is set to `none`.

---

## Quick start

```bash
pip install -r ai-video-factory/requirements.txt     # just PyYAML for now
python3 ai-video-factory/scripts/check_env.py         # should end with: RESULT: READY
```

`check_env.py` exits `0` when the foundation works. Missing optional tools (ffmpeg, etc.)
and missing API keys show as `WARN`, not failures.

---

## Intended workflow

Each video is a **job** identified by a slug, e.g. `2026-09-27-ai-agents-replace-saas`.
Every stage writes its output into the matching folder using that slug, so any stage can be
re-run on its own and every step is reviewable in a Git diff.

| # | Stage | Output | Folder | Who / what |
|---|-------|--------|--------|------------|
| 1 | **Research** — pick a topic, collect facts + sources | `<slug>.md` | `research/` | Claude Code (web search) |
| 2 | **Script** — hook (≤3s), body, CTA; 80–160 words | `<slug>.md` | `scripts/` | Claude Code → **human review** |
| 3 | **Voiceover** — narrate the approved script | `<slug>.wav` | `voiceovers/` | TTS provider *(not connected)* |
| 4 | **Captions** — word-timed subtitles from the voiceover | `<slug>.srt` | `captions/` | transcription *(not connected)* |
| 5 | **Visuals** — b-roll, images, on-screen text | `<slug>/…` | `assets/images`, `assets/video` | stock / image provider *(not connected)* |
| 6 | **Music** — royalty-free bed, ducked under voice | `…` | `music/` | local licensed library |
| 7 | **Render** — assemble 1080×1920 MP4 | `<slug>.mp4` | `output/` | ffmpeg *(not installed)* |
| 8 | **Review & publish** — human check, then schedule | — | — | manual → Metricool / OpusClip later |

Guardrails baked into the config:

- `script.require_sources: true` — factual claims (especially money/finance) need a source in `research/`.
- `script.require_human_review: true` — nothing is rendered from an unapproved script.
- `publishing.auto_publish: false` — nothing is posted automatically.
- `publishing.ai_disclosure: true` — label synthetic media where platforms require it.
- Only use music, footage and images you have the rights to. Keep a license note next to each asset.

---

## Project layout

```
ai-video-factory/
├── CLAUDE.md            # instructions for Claude Code working in this project
├── README.md
├── requirements.txt
├── config/
│   ├── settings.yaml        # committed defaults (no secrets)
│   ├── settings.local.yaml  # optional personal overrides (git-ignored)
│   ├── .env.example         # template for API keys
│   └── .env                 # your keys (git-ignored)
├── src/
│   └── config.py        # loads + validates configuration
├── scripts/
│   └── check_env.py     # environment check
├── research/            # topic research + sources (committed)
├── assets/{images,video,audio}/   # visual/audio source material (media git-ignored)
├── voiceovers/          # narration audio (git-ignored)
├── captions/            # .srt/.vtt (committed — small, reviewable)
├── music/               # licensed music (git-ignored)
└── output/              # rendered videos (git-ignored)
```

Note: `scripts/` holds **both** the tooling scripts (`*.py`) and the video scripts (`*.md`).

---

## Configuration

Settings are resolved in this order (later wins):

1. `config/settings.yaml` — committed defaults
2. `config/settings.local.yaml` — your personal overrides (same shape, git-ignored)
3. `config/.env` — secrets and overrides (git-ignored)
4. Process environment — e.g. secrets configured in Claude Code on the web or GitHub Actions

Override any setting with `AVF__SECTION__KEY`, e.g. `AVF__VIDEO__FPS=60` or `AVF__PROVIDERS__TTS=piper`.

```python
from src.config import load_settings
s = load_settings()
s["video"]["width"]          # 1080
s.path("output")             # absolute Path to output/
s.has_secret("PEXELS_API_KEY")
```

Invalid settings (e.g. a horizontal resolution or an unknown provider name) fail fast with a clear error.

---

## Large files

Rendered video and audio are git-ignored to keep the repo small. If you want to keep finished
videos in GitHub, attach them to a GitHub Release or enable Git LFS rather than committing them directly.

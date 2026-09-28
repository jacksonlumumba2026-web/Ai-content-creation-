# AI Video Factory

A pipeline for producing **original 30–60 second vertical videos** (1080×1920, 9:16) about
**AI, business, money and technology** for TikTok, YouTube Shorts and Instagram Reels.

It is built to be operated through **Claude Code** (locally or on claude.ai/code) and versioned on **GitHub**.

> **Status: foundation + local tooling.** Folder structure, configuration, environment check,
> **ffmpeg** (rendering) and **Piper** (free local text-to-speech) are set up. Image, stock,
> caption and publishing providers are still `none`. No video has been generated yet.

---

## Quick start

```bash
bash ai-video-factory/scripts/setup_env.sh            # ffmpeg, PyYAML, piper-tts, faster-whisper, Piper voice
python3 ai-video-factory/scripts/check_env.py         # should end with: RESULT: READY
```

`check_env.py` also encodes a 1-second 1080×1920 test clip with ffmpeg and, once a voice is
installed, synthesizes a short test phrase with Piper.

### Voiceovers (free & local)

Two engines, chosen by `providers.tts` in `config/settings.yaml`:

- `piper` (selected): natural-sounding male voice `en_US-ryan-high`; needs a one-time voice
  model download (below).
- `ffmpeg_flite`: built into ffmpeg, no downloads, sounds robotic. Male voice `rms` by default
  (`tts.ffmpeg_flite.voice`: `rms`, `awb`, `kal`, or female `slt`).

Until the Piper voice is installed, voiceovers automatically use `tts.fallback` (`ffmpeg_flite`)
and print a warning. Set `tts.fallback: none` to fail instead.

```bash
python3 ai-video-factory/scripts/setup_piper_voice.py                 # voice from settings.yaml
python3 ai-video-factory/scripts/voiceover.py --slug 2026-09-27-demo --text "Your narration."
python3 ai-video-factory/scripts/voiceover.py --slug 2026-09-27-demo --file ai-video-factory/scripts/2026-09-27-demo.md
```

- Voice, speed and pauses live under `tts.piper` in `config/settings.yaml`. Preview voices at
  <https://rhasspy.github.io/piper-samples/>.
- Voice files (~60–110 MB) download from **huggingface.co** into `models/piper/` (git-ignored).
  In Claude Code on the web, huggingface.co must be allowed in the environment's network settings.
- From a script markdown file, only the `## Narration` section is read (falls back to the whole file).
- Check each voice's `MODEL_CARD` for its license before commercial use.

### Captions (faster-whisper, free & local)

```bash
python3 ai-video-factory/scripts/captions.py --slug 2026-09-28-demo --file ai-video-factory/scripts/2026-09-28-demo.md
```

- Reads `voiceovers/<slug>.wav`; writes `captions/<slug>.srt` and `captions/<slug>.words.json`
  (per-word timings for animated captions in the render stage).
- **Whisper is used only for timing.** Caption words come from the script, so mishearings
  ("thirty" → "30") and hallucinated extra text never appear on screen. Without a script
  (and no `scripts/<slug>.md`), Whisper's own transcription is used and a warning is printed.
- Cue style lives under `captions` in `config/settings.yaml` (words per cue, line length, pause breaks).
- The Whisper model (`base.en`, ~140 MB) downloads from huggingface.co into `models/whisper/` on first use.

### Claude Code on the web

Containers are fresh each session, so installed tools don't persist. Paste the contents of
`scripts/setup_env.sh` into the environment's **Setup script** so every new session starts with
ffmpeg, Piper and the voice ready.

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
| 3 | **Voiceover** — narrate the approved script | `<slug>.wav` | `voiceovers/` | Piper (falls back to ffmpeg Flite until its voice is installed) — `scripts/voiceover.py` |
| 4 | **Captions** — word-timed subtitles from the voiceover | `<slug>.srt`, `<slug>.words.json` | `captions/` | faster-whisper (local, free) — `scripts/captions.py` |
| 5 | **Visuals** — b-roll, images, on-screen text | `<slug>/…` | `assets/images`, `assets/video` | stock / image provider *(not connected)* |
| 6 | **Music** — royalty-free bed, ducked under voice | `…` | `music/` | local licensed library |
| 7 | **Render** — assemble 1080×1920 MP4 | `<slug>.mp4` | `output/` | ffmpeg *(installed; render stage not built yet)* |
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
│   ├── config.py        # loads + validates configuration
│   ├── tts.py           # text-to-speech (Piper, ffmpeg Flite)
│   ├── captions.py      # word timing + script alignment + SRT/VTT
│   └── scriptfile.py    # reads narration from script markdown
├── scripts/
│   ├── check_env.py         # environment check
│   ├── setup_env.sh         # installs ffmpeg, Python deps, Piper voice
│   ├── setup_piper_voice.py # downloads the configured Piper voice
│   ├── voiceover.py         # text/script -> voiceovers/<slug>.wav
│   └── captions.py          # voiceover -> captions/<slug>.srt + words.json
├── models/              # downloaded model files, e.g. Piper voices (git-ignored)
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

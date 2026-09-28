#!/usr/bin/env python3
"""Make word-timed captions for a voiceover (free, local faster-whisper).

    python3 ai-video-factory/scripts/captions.py --slug 2026-09-28-demo
    python3 ai-video-factory/scripts/captions.py --slug 2026-09-28-demo --file ai-video-factory/scripts/2026-09-28-demo.md
    python3 ai-video-factory/scripts/captions.py --slug 2026-09-28-demo --text "Exact narration..."

Reads voiceovers/<slug>.wav and writes captions/<slug>.srt plus
captions/<slug>.words.json. If no script is given, scripts/<slug>.md is used
when it exists; otherwise captions use Whisper's own (less reliable) words.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.captions import align_to_script, group_cues, transcribe_words, write_captions  # noqa: E402
from src.config import load_settings  # noqa: E402
from src.scriptfile import narration_from_markdown  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", required=True)
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--text", help="exact narration text")
    src.add_argument("--file", type=Path, help="script markdown file")
    args = parser.parse_args()

    settings = load_settings()
    audio = settings.path("voiceovers") / f"{args.slug}.wav"
    if not audio.exists():
        print(f"ERROR: {audio.relative_to(ROOT)} not found — run scripts/voiceover.py first", file=sys.stderr)
        return 1

    script = args.text
    default_script = settings.path("scripts") / f"{args.slug}.md"
    if args.file:
        script = narration_from_markdown(args.file.read_text())
    elif script is None and default_script.exists():
        script = narration_from_markdown(default_script.read_text())

    try:
        heard = transcribe_words(audio, settings, prompt=script)
        if script:
            words = align_to_script(script, heard)
        else:
            print("WARNING: no script given; captions use Whisper's transcription as-is", file=sys.stderr)
            words = heard
        cues = group_cues(words, settings)
        files = write_captions(args.slug, words, cues, settings)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for f in files:
        print(f"Wrote {f.relative_to(ROOT)}")
    print(f"{len(cues)} caption cues, {len(words)} words, ends at {words[-1].end:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

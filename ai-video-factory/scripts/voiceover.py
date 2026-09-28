#!/usr/bin/env python3
"""Generate a voiceover WAV with the configured TTS provider (Piper, local + free).

    python3 ai-video-factory/scripts/voiceover.py --slug 2026-09-27-demo --text "Hello world."
    python3 ai-video-factory/scripts/voiceover.py --slug 2026-09-27-demo --file scripts/2026-09-27-demo.md

Output: voiceovers/<slug>.wav. Warns if the result falls outside the
configured 30–60s window.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_settings  # noqa: E402
from src.tts import effective_provider, synthesize  # noqa: E402

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def narration_from_markdown(text: str) -> str:
    """Use the '## Narration' section if present, otherwise the whole file minus headings."""
    match = re.search(r"^##\s*Narration\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    body = match.group(1) if match else text
    lines = [ln for ln in body.splitlines() if not ln.lstrip().startswith(("#", "<!--"))]
    return " ".join(" ".join(lines).split())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", required=True, help="video slug, e.g. 2026-09-27-ai-agents")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="narration text")
    src.add_argument("--file", type=Path, help="script markdown file")
    args = parser.parse_args()

    if not SLUG_RE.match(args.slug):
        parser.error("slug must be lowercase letters, digits and hyphens")

    settings = load_settings()
    text = args.text if args.text else narration_from_markdown(args.file.read_text())
    out = settings.path("voiceovers") / f"{args.slug}.wav"
    engine = effective_provider(settings)
    if engine != settings["providers"]["tts"]:
        print(f"WARNING: {settings['providers']['tts']} voice not installed; using fallback {engine}. "
              "Run scripts/setup_piper_voice.py for the natural voice.", file=sys.stderr)
    try:
        duration = synthesize(text, out, settings)
    except Exception as exc:  # engine errors (bad model file, ffmpeg failure) -> clean message
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    v = settings["video"]
    print(f"Wrote {out.relative_to(ROOT)} ({duration:.1f}s, {len(text.split())} words, {engine})")
    if not v["min_duration_sec"] <= duration <= v["max_duration_sec"]:
        print(f"WARNING: duration is outside {v['min_duration_sec']}-{v['max_duration_sec']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Produce a finished video from a script, in one command.

    python3 ai-video-factory/scripts/produce.py --slug 2026-09-28-ai-tools

Reads scripts/<slug>.md (front matter + '## Narration'), then:
  1. voiceover   -> voiceovers/<slug>.wav
  2. captions    -> captions/<slug>.srt + .words.json
  3. render      -> output/<slug>.mp4
  4. quality gate (duration, resolution, required metadata, sources, banned claims)
  5. report      -> output/<slug>.report.json

Exit code 0 only if the video passed the quality gate. Nothing is published here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.captions import align_to_script, group_cues, transcribe_words, write_captions  # noqa: E402
from src.config import load_settings  # noqa: E402
from src.publish import quality_gate  # noqa: E402
from src.render import TAIL_SEC, audio_duration, probe, render_video  # noqa: E402
from src.stock import fetch_scenes  # noqa: E402
from src.scriptfile import load_script  # noqa: E402
from src.tts import effective_provider, synthesize  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", required=True)
    args = parser.parse_args()

    settings = load_settings()
    script_path = settings.path("scripts") / f"{args.slug}.md"
    if not script_path.exists():
        print(f"ERROR: {script_path.relative_to(ROOT)} not found", file=sys.stderr)
        return 1
    script = load_script(script_path)

    engine = effective_provider(settings)
    if engine != "piper":
        print(f"WARNING: using {engine} voice — Piper voice not installed", file=sys.stderr)

    print("1/4 voiceover ...", flush=True)
    audio = settings.path("voiceovers") / f"{args.slug}.wav"
    secs = synthesize(script.narration, audio, settings)
    print(f"    {secs:.1f}s, {len(script.narration.split())} words ({engine})")

    print("2/4 captions ...", flush=True)
    words = align_to_script(script.narration, transcribe_words(audio, settings, prompt=script.narration))
    cues = group_cues(words, settings)
    write_captions(args.slug, words, cues, settings)
    print(f"    {len(cues)} cues")

    print("3/4 render ...", flush=True)
    scenes = None
    if script.meta.get("scenes") and settings["providers"]["stock_video"] == "pexels":
        try:
            duration = audio_duration(audio) + TAIL_SEC
            scenes = fetch_scenes(script.meta["scenes"], words, duration, settings, args.slug)
            print(f"    footage: {len(scenes)} Pexels clips")
        except Exception as exc:  # no key, network blocked, no matching clips
            if settings["stock"]["required"]:
                print(f"ERROR: stock footage: {exc}", file=sys.stderr)
                return 1
            print(f"WARNING: stock footage unavailable ({exc}); using gradient background",
                  file=sys.stderr)
    try:
        video = render_video(args.slug, cues, script.title, settings,
                             visuals=script.meta.get("visuals"), words=words, scenes=scenes)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    info = probe(video)
    print(f"    {video.relative_to(ROOT)}: {info['width']}x{info['height']} {info['codec']}, "
          f"{info['duration']:.1f}s, {info['size_mb']:.1f} MB")

    print("4/4 quality gate ...", flush=True)
    problems = quality_gate(script, info, settings)
    report = {"slug": args.slug, "video": str(video.relative_to(ROOT)), "probe": info,
              "voice": engine, "footage": bool(scenes), "passed": not problems, "problems": problems}
    (settings.path("output") / f"{args.slug}.report.json").write_text(json.dumps(report, indent=1))
    if problems:
        print("    FAILED:\n      - " + "\n      - ".join(problems))
        return 1
    print("    PASSED — ready to publish")
    return 0


if __name__ == "__main__":
    sys.exit(main())

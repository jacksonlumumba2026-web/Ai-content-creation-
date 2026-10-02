#!/usr/bin/env python3
"""Re-render an already-produced video with the current look, keeping its voiceover and clips.

    python3 ai-video-factory/scripts/rerender.py --slug <slug> [--slug <slug> ...]

Use after a renderer/style change: the voiceover (voiceovers/<slug>.wav) and the reviewed Pexels
clips (output/<slug>.credits.json) are reused, so nothing new needs reviewing except the look.
Captions are re-timed from the existing audio. Runs the quality gate and rewrites the report.
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
from src.render import probe, render_video  # noqa: E402
from src.scriptfile import load_script  # noqa: E402
from src.stock import Scene  # noqa: E402


def rerender(slug: str, settings) -> bool:
    script = load_script(settings.path("scripts") / f"{slug}.md")
    audio = settings.path("voiceovers") / f"{slug}.wav"
    words = align_to_script(script.narration, transcribe_words(audio, settings, prompt=script.narration))
    cues = group_cues(words, settings)
    write_captions(slug, words, cues, settings)

    scenes = None
    credits_path = settings.path("output") / f"{slug}.credits.json"
    if credits_path.exists():
        cache = settings.path("video") / "pexels"
        scenes = []
        for c in json.loads(credits_path.read_text()):
            clips = sorted(cache.glob(f"{c['pexels_id']}_*.mp4"))
            if not clips:
                raise FileNotFoundError(f"{slug}: cached clip for Pexels {c['pexels_id']} is missing")
            credit = {k: c[k] for k in ("pexels_id", "url", "author", "query") if k in c}
            scenes.append(Scene(clips[0], c["start"], c["end"], credit))

    video = render_video(slug, cues, script.title, settings,
                         visuals=script.meta.get("visuals"), words=words, scenes=scenes)
    info = probe(video)
    problems = quality_gate(script, info, settings)
    report = {"slug": slug, "video": str(video.relative_to(ROOT)), "probe": info,
              "footage": bool(scenes), "passed": not problems, "problems": problems, "rerender": True}
    (settings.path("output") / f"{slug}.report.json").write_text(json.dumps(report, indent=1))
    print(f"{slug}: {info['duration']:.1f}s {'PASSED' if not problems else 'FAILED: ' + '; '.join(problems)}",
          flush=True)
    return not problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", action="append", required=True)
    args = parser.parse_args()
    settings = load_settings()
    ok = all([rerender(slug, settings) for slug in args.slug])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

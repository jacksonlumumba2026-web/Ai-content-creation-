#!/usr/bin/env python3
"""Render a quiz/challenge video from scripts/<slug>.quiz.yaml.

    python3 ai-video-factory/scripts/quiz.py --slug 2026-09-29-5-question-challenge

Checks the spec (3 options, valid answer index, 50-60 s target), renders output/<slug>.mp4
and writes output/<slug>.credits.json + output/<slug>.report.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_settings  # noqa: E402
from src.quiz import render_quiz  # noqa: E402
from src.render import probe  # noqa: E402


def validate(spec: dict) -> list[str]:
    problems = []
    for i, q in enumerate(spec.get("questions", []), start=1):
        if len(q.get("options", [])) != 3:
            problems.append(f"question {i}: needs exactly 3 options")
        if not isinstance(q.get("answer"), int) or not 0 <= q["answer"] < len(q.get("options", [])):
            problems.append(f"question {i}: answer index out of range")
        if str(q["options"][q["answer"]]).split()[0].lower() not in q.get("reveal", "").lower().replace("zero", "0"):
            problems.append(f"question {i}: reveal narration doesn't name the correct option")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--pace", type=float, default=0.88, help="Piper length_scale (<1 = faster, more energetic)")
    args = ap.parse_args()

    settings = load_settings()
    spec = yaml.safe_load((settings.path("scripts") / f"{args.slug}.quiz.yaml").read_text())
    problems = validate(spec)
    if problems:
        print("ERROR:\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 1
    settings["tts"]["piper"]["length_scale"] = args.pace

    video, credits = render_quiz(args.slug, spec, settings)
    info = probe(video)
    out = settings.path("output")
    (out / f"{args.slug}.credits.json").write_text(json.dumps(credits, indent=1))
    v = settings["video"]
    issues = []
    if not v["min_duration_sec"] <= info["duration"] <= v["max_duration_sec"] + 1:
        issues.append(f"duration {info['duration']:.1f}s outside {v['min_duration_sec']}-{v['max_duration_sec']}s")
    if (info["width"], info["height"]) != (v["width"], v["height"]):
        issues.append("wrong resolution")
    (out / f"{args.slug}.report.json").write_text(json.dumps(
        {"slug": args.slug, "format": "quiz", "probe": info, "passed": not issues, "problems": issues}, indent=1))
    print(f"{video.relative_to(ROOT)}: {info['width']}x{info['height']}, {info['duration']:.1f}s, "
          f"{info['size_mb']:.1f} MB -> {'PASSED' if not issues else 'FAILED: ' + '; '.join(issues)}")
    for c in credits:
        print(f"  {c['start']:5.1f}-{c['end']:5.1f}  {c['query']:<32} | {c['url'].split('/video/')[1][:60]}")
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())

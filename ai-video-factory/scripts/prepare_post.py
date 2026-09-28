#!/usr/bin/env python3
"""Upload a finished, gate-passed video and print its Metricool post payload.

    python3 ai-video-factory/scripts/prepare_post.py --slug <slug> --date 2026-10-01

Requires output/<slug>.report.json with passed=true (from produce.py).
Uploads output/<slug>.mp4 to the public media branch, writes
output/<slug>.metricool.json and prints JSON with `blogId`, `date` and `info`
ready for the Metricool createScheduledPost tool. autoPublish follows
publishing.auto_publish (false = the owner approves in the Metricool app).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date as Date
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_settings  # noqa: E402
from src.publish import metricool_info, upload_media  # noqa: E402
from src.scriptfile import load_script  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--date", required=True, help="publication date, YYYY-MM-DD (brand timezone)")
    args = parser.parse_args()

    settings = load_settings()
    pub = settings["publishing"]
    out = settings.path("output")
    report_file = out / f"{args.slug}.report.json"
    if not report_file.exists() or not json.loads(report_file.read_text()).get("passed"):
        print(f"ERROR: {args.slug} has not passed the quality gate (run produce.py)", file=sys.stderr)
        return 1

    day = Date.fromisoformat(args.date)
    local = datetime.fromisoformat(f"{day}T{pub['post_time']}:00").replace(tzinfo=ZoneInfo(pub["timezone"]))

    url = upload_media(out / f"{args.slug}.mp4", settings)
    credits_file = out / f"{args.slug}.credits.json"
    credits = json.loads(credits_file.read_text()) if credits_file.exists() else None
    info = metricool_info(load_script(settings.path("scripts") / f"{args.slug}.md"), url, settings, credits)
    info["publicationDate"] = {"dateTime": local.strftime("%Y-%m-%dT%H:%M:%S"), "timezone": pub["timezone"]}
    (out / f"{args.slug}.metricool.json").write_text(json.dumps(info, ensure_ascii=False))

    print(json.dumps({"blogId": pub["metricool_blog_id"], "date": local.isoformat(), "info": info},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Free stock footage from Pexels (https://www.pexels.com/api/).

Scripts list scenes in front matter; each scene's footage plays from the moment its
`at` phrase is spoken until the next scene starts (the first scene starts at 0s):

    scenes:
      - {at: "Almost half", query: "small business owner shop"}
      - {at: "Number one", query: "person typing laptop marketing"}

Clips are searched in portrait orientation, downloaded once into assets/video/pexels/
(git-ignored) and credited in output/<slug>.credits.json. The Pexels license allows free
commercial use; the API guidelines ask for a visible link to Pexels and photographer credit,
which publish.post_text adds to the post caption.

Needs PEXELS_API_KEY and network access to api.pexels.com + videos.pexels.com.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from src.captions import Word
from src.config import ConfigError, Settings
from src.visuals import find_phrase

API = "https://api.pexels.com/v1/videos/search"  # /videos/ is deprecated per Pexels docs


@dataclass
class Scene:
    clip: Path
    start: float
    end: float
    credit: dict


def _request_json(url: str, key: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": "ai-video-factory"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def pick_file(video: dict, min_height: int = 1280) -> dict | None:
    """Best portrait MP4 rendition: the smallest one that is at least min_height tall."""
    files = [f for f in video.get("video_files", [])
             if f.get("file_type") == "video/mp4" and f.get("height") and f.get("width")
             and f["height"] > f["width"]]
    tall = sorted((f for f in files if f["height"] >= min_height), key=lambda f: f["height"])
    if tall:
        return tall[0]
    return max(files, key=lambda f: f["height"], default=None)


def search(query: str, key: str, per_page: int = 15) -> list[dict]:
    params = urllib.parse.urlencode({"query": query, "orientation": "portrait",
                                     "size": "medium", "per_page": per_page})
    return _request_json(f"{API}?{params}", key).get("videos", [])


def download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    part = dest.with_suffix(".part")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ai-video-factory"})
            with urllib.request.urlopen(req, timeout=120) as resp, part.open("wb") as fh:
                expected = int(resp.headers.get("Content-Length", 0))
                while block := resp.read(1 << 20):
                    fh.write(block)
            if not expected or part.stat().st_size == expected:
                part.replace(dest)
                return dest
        except OSError:
            pass
        time.sleep(2 * (attempt + 1))
    part.unlink(missing_ok=True)
    raise RuntimeError(f"could not download {url}")


def fetch_scenes(specs: list, words: list[Word], duration: float, settings: Settings,
                 slug: str) -> list[Scene]:
    """Resolve scene specs to downloaded clips with start/end times."""
    key = settings.secrets.get("PEXELS_API_KEY")
    if not key:
        raise ConfigError("PEXELS_API_KEY is not set")
    cache = settings.path("video") / "pexels"
    cache.mkdir(parents=True, exist_ok=True)
    min_dur = settings["stock"]["min_clip_sec"]

    timed: list[tuple[float, dict]] = []
    cursor = 0
    for n, spec in enumerate(specs or [], start=1):
        if not spec.get("query"):
            raise ValueError(f"scene {n}: missing 'query'")
        idx = find_phrase(words, str(spec.get("at", "")), cursor) if spec.get("at") else None
        if idx is None and n > 1:
            raise ValueError(f"scene {n}: phrase {spec.get('at')!r} not found in narration (in order)")
        start = 0.0 if n == 1 else words[idx].start
        cursor = (idx + 1) if idx is not None else cursor
        timed.append((start, spec))

    used: set[int] = set()
    scenes: list[Scene] = []
    for i, (start, spec) in enumerate(timed):
        end = timed[i + 1][0] if i + 1 < len(timed) else duration
        candidates = [v for v in search(spec["query"], key)
                      if v["id"] not in used and v.get("duration", 0) >= min_dur and pick_file(v)]
        if not candidates:
            raise ValueError(f"scene {i + 1}: no portrait clips found for {spec['query']!r}")
        # Prefer clips long enough to cover the segment without looping.
        video = next((v for v in candidates if v["duration"] >= end - start), candidates[0])
        used.add(video["id"])
        rendition = pick_file(video)
        clip = download(rendition["link"], cache / f"{video['id']}_{rendition['height']}.mp4")
        credit = {"pexels_id": video["id"], "url": video.get("url"),
                  "author": video.get("user", {}).get("name"), "query": spec["query"]}
        scenes.append(Scene(clip, round(start, 2), round(end, 2), credit))

    (settings.path("output") / f"{slug}.credits.json").write_text(
        json.dumps([s.credit | {"start": s.start, "end": s.end} for s in scenes], indent=1))
    return scenes

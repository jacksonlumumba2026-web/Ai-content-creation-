"""Publishing helpers: quality gates, public media hosting, Metricool post payload.

Media hosting: the repository is public, so finished MP4s are pushed to an
orphan `media` branch and served from raw.githubusercontent.com. Metricool
fetches the file from that URL when the post is scheduled.

Posting itself goes through the Metricool connector in Claude Code (MCP), so
this module only builds the exact payload; the daily routine passes it on.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
from datetime import date
from pathlib import Path

from src.config import ROOT, Settings
from src.scriptfile import Script

BANNED_PHRASES = [
    "guaranteed", "get rich quick", "risk-free", "risk free", "100% profit",
    "double your money", "can't lose", "cannot lose", "financial freedom overnight",
]


def quality_gate(script: Script, probe_info: dict, settings: Settings) -> list[str]:
    """Return a list of problems; an empty list means the video may be published."""
    problems: list[str] = []
    v, meta = settings["video"], script.meta
    words = len(script.narration.split())

    if not (v["min_duration_sec"] <= probe_info["duration"] <= v["max_duration_sec"] + 1):
        problems.append(f"duration {probe_info['duration']:.1f}s outside "
                        f"{v['min_duration_sec']}-{v['max_duration_sec']}s ({words} words)")
    if (probe_info["width"], probe_info["height"]) != (v["width"], v["height"]):
        problems.append(f"resolution {probe_info['width']}x{probe_info['height']}")
    if probe_info["size_mb"] > 95:
        problems.append(f"file too large ({probe_info['size_mb']:.0f} MB)")

    for key in ("title", "youtube_title", "caption"):
        if not str(meta.get(key, "")).strip():
            problems.append(f"front matter missing '{key}'")
    if len(str(meta.get("youtube_title", ""))) > 100:
        problems.append("youtube_title longer than 100 characters")
    if len(meta.get("visuals") or []) < settings["script"]["min_visuals"]:
        problems.append(f"fewer than {settings['script']['min_visuals']} visuals — "
                        "videos need on-screen graphics, not just captions")
    if settings["script"]["require_sources"] and not meta.get("sources"):
        problems.append("no sources listed in front matter")

    text = (script.narration + " " + " ".join(str(meta.get(k, "")) for k in meta)).lower()
    for phrase in BANNED_PHRASES:
        if phrase in text:
            problems.append(f"banned phrase: {phrase!r}")
    return problems


def post_text(script: Script) -> str:
    tags = " ".join("#" + re.sub(r"[^A-Za-z0-9]", "", str(t)) for t in script.meta.get("hashtags", []))
    return f"{script.meta['caption'].strip()}\n\n{tags}".strip()


def metricool_info(script: Script, media_url: str, settings: Settings) -> dict:
    """The `info` object for Metricool createScheduledPost (without date/blogId)."""
    pub = settings["publishing"]
    networks = [n for n, cfg in pub["platforms"].items() if cfg.get("enabled")]
    provider_names = {"youtube_shorts": "youtube", "tiktok": "tiktok", "facebook_reels": "facebook",
                      "instagram_reels": "instagram"}
    providers = [{"network": provider_names[n]} for n in networks]
    title = script.meta["youtube_title"].strip()
    ai = pub["ai_disclosure"]
    info = {
        # False = Metricool pushes a notification and the owner publishes from the app.
        "autoPublish": bool(pub["auto_publish"]),
        "draft": False,
        "text": post_text(script),
        "media": [media_url],
        "providers": providers,
        "shortener": False,
        "descendants": [],
        "firstCommentText": "",
        "mediaAltText": [],
        "smartLinkData": {"ids": []},
        "hasNotReadNotes": False,
    }
    if "youtube_shorts" in networks:
        info["youtubeData"] = {
            "title": title, "type": "short", "privacy": "public", "madeForKids": False,
            "category": "SCIENCE_TECHNOLOGY", "isAiGeneratedContent": ai,
            "tags": [str(t) for t in script.meta.get("hashtags", [])][:10],
        }
    if "tiktok" in networks:
        info["tiktokData"] = {
            "privacyOption": "PUBLIC_TO_EVERYONE", "disableComment": False, "disableDuet": False,
            "disableStitch": False, "commercialContentThirdParty": False,
            "commercialContentOwnBrand": False, "autoAddMusic": False, "isAigc": ai,
        }
    if "facebook_reels" in networks:
        info["facebookData"] = {"type": "REEL", "title": title}
    if "instagram_reels" in networks:
        info["instagramData"] = {"type": "REEL", "showReelOnFeed": True, "isAiGenerated": ai}
    return info


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def upload_media(video: Path, settings: Settings) -> str:
    """Push the MP4 to the orphan `media` branch; return its public raw URL."""
    repo_root = ROOT.parent
    remote = _git("remote", "get-url", "origin", cwd=repo_root).strip()
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?$", remote)
    if not m:
        raise RuntimeError(f"cannot parse GitHub repo from remote {remote!r}")
    owner, repo = m.groups()
    branch = settings["publishing"]["media_branch"]
    rel = f"{date.today():%Y/%m}/{video.name}"

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "media"
        exists = subprocess.run(["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
                                cwd=repo_root, capture_output=True).returncode == 0
        if exists:
            _git("clone", "--quiet", "--depth", "1", "--branch", branch, remote, str(work), cwd=repo_root)
        else:
            work.mkdir()
            _git("init", "--quiet", "-b", branch, cwd=work)
            _git("remote", "add", "origin", remote, cwd=work)
            (work / "README.md").write_text(
                "Rendered videos served publicly for scheduled social posts. Managed by ai-video-factory.\n")
        dest = work / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(video, dest)
        _git("add", "-A", cwd=work)
        _git("-c", "user.name=ai-video-factory", "-c", "user.email=ai-video-factory@users.noreply.github.com",
             "commit", "--quiet", "-m", f"Add {video.name}", cwd=work)
        for attempt in range(4):
            push = subprocess.run(["git", "push", "--quiet", "origin", f"HEAD:{branch}"],
                                  cwd=work, capture_output=True, text=True)
            if push.returncode == 0:
                break
            time.sleep(2 ** (attempt + 1))
        else:
            raise RuntimeError(f"git push to {branch} failed: {push.stderr.strip()}")

    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{rel}"
    wait_until_public(url, video.stat().st_size)
    return url


def wait_until_public(url: str, expected_size: int, timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while True:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=30) as resp:
                if int(resp.headers.get("Content-Length", 0)) == expected_size:
                    return
        except OSError:
            pass
        if time.time() > deadline:
            raise RuntimeError(f"{url} not publicly available with the right size after {timeout}s")
        time.sleep(5)


def log_post(entry: dict, settings: Settings) -> None:
    log = settings.path("research") / "posted.jsonl"
    with log.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")

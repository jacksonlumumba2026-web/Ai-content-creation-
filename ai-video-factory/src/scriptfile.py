"""Reading video scripts: YAML front matter (metadata) + '## Narration' body.

Example scripts/<slug>.md:

    ---
    title: "3 free AI tools that save hours"      # on-screen headline (<= 60 chars)
    youtube_title: "3 Free AI Tools That Save Small Businesses Hours #Shorts"
    caption: "Which one are you trying first?"      # post text for TikTok/Facebook
    hashtags: [ai, smallbusiness, productivity]
    sources:
      - https://example.com/article
    ---

    ## Narration
    AI is quietly changing how small businesses make money...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


@dataclass
class Script:
    narration: str
    meta: dict = field(default_factory=dict)

    @property
    def title(self) -> str:
        return str(self.meta.get("title", "")).strip()


def narration_from_markdown(text: str) -> str:
    """Use the '## Narration' section if present, otherwise the whole file minus headings."""
    text = FRONT_MATTER.sub("", text, count=1)
    match = re.search(r"^##\s*Narration\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    body = match.group(1) if match else text
    lines = [ln for ln in body.splitlines() if not ln.lstrip().startswith(("#", "<!--"))]
    return " ".join(" ".join(lines).split())


def load_script(path: Path) -> Script:
    text = path.read_text()
    match = FRONT_MATTER.match(text)
    meta = yaml.safe_load(match.group(1)) if match else {}
    if not isinstance(meta, dict):
        raise ValueError(f"{path}: front matter must be a YAML mapping")
    return Script(narration=narration_from_markdown(text), meta=meta)

"""Reading narration text out of script markdown files."""

from __future__ import annotations

import re


def narration_from_markdown(text: str) -> str:
    """Use the '## Narration' section if present, otherwise the whole file minus headings."""
    match = re.search(r"^##\s*Narration\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    body = match.group(1) if match else text
    lines = [ln for ln in body.splitlines() if not ln.lstrip().startswith(("#", "<!--"))]
    return " ".join(" ".join(lines).split())

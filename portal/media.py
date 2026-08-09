from __future__ import annotations

import re


DRIVE_PREVIEW_PATTERN = re.compile(r"^https://drive\.google\.com/file/d/([^/]+)/preview$")


def playable_video_url(value: str) -> str:
    match = DRIVE_PREVIEW_PATTERN.match(value)
    if not match:
        return value
    return f"https://drive.google.com/uc?export=download&id={match.group(1)}"


def srt_to_vtt(value: str) -> str:
    blocks = re.split(r"\n\s*\n", value.strip())
    converted = []
    for block in blocks:
        lines = block.splitlines()
        if lines and lines[0].strip().isdigit():
            lines = lines[1:]
        if not lines or " --> " not in lines[0]:
            continue
        lines[0] = lines[0].replace(",", ".")
        converted.append("\n".join(lines))
    return "WEBVTT\n\n" + "\n\n".join(converted) + "\n"

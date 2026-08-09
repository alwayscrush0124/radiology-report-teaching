from __future__ import annotations

import re
from urllib.request import Request, urlopen


DRIVE_PREVIEW_PATTERN = re.compile(r"^https://drive\.google\.com/file/d/([^/]+)/preview$")
MAX_VIDEO_BYTES = 100 * 1024 * 1024


class DriveVideoError(RuntimeError):
    pass


def playable_video_url(value: str) -> str:
    match = DRIVE_PREVIEW_PATTERN.match(value)
    if not match:
        return value
    return f"https://drive.google.com/uc?export=download&id={match.group(1)}"


def download_drive_video(value: str) -> bytes:
    download_url = playable_video_url(value)
    if download_url == value:
        raise DriveVideoError("不是支援的 Google Drive preview 網址")
    request = Request(download_url, headers={"User-Agent": "Radiology-Teaching-Atlas/1.0"})
    try:
        with urlopen(request, timeout=60) as response:
            content_type = response.headers.get_content_type()
            length = int(response.headers.get("Content-Length", "0") or 0)
            if length > MAX_VIDEO_BYTES:
                raise DriveVideoError("影片超過 100 MB，無法由 Portal 代理播放")
            payload = response.read(MAX_VIDEO_BYTES + 1)
    except DriveVideoError:
        raise
    except OSError as exc:
        raise DriveVideoError(f"無法從 Google Drive 讀取影片：{exc}") from exc
    if content_type != "video/mp4":
        raise DriveVideoError(f"Google Drive 回傳的不是 MP4：{content_type}")
    if len(payload) > MAX_VIDEO_BYTES:
        raise DriveVideoError("影片超過 100 MB，無法由 Portal 代理播放")
    return payload


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

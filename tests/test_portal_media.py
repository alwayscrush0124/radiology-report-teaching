from email.message import Message

import portal.media as media
from portal.media import download_drive_video, playable_video_url, srt_to_vtt


def test_drive_preview_becomes_direct_playable_video() -> None:
    preview = "https://drive.google.com/file/d/abc_123-X/preview"
    assert playable_video_url(preview) == "https://drive.google.com/uc?export=download&id=abc_123-X"


def test_non_drive_video_url_is_unchanged() -> None:
    url = "https://cdn.example.com/video.mp4"
    assert playable_video_url(url) == url


def test_srt_is_converted_to_streamlit_compatible_vtt() -> None:
    srt = "1\n00:00:00,000 --> 00:00:02,500\n第一句\n\n2\n00:00:03,000 --> 00:00:04,000\n第二句\n"
    assert srt_to_vtt(srt) == (
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:02.500\n第一句\n\n"
        "00:00:03.000 --> 00:00:04.000\n第二句\n"
    )


def test_drive_video_is_downloaded_as_mp4(monkeypatch) -> None:
    headers = Message()
    headers["Content-Type"] = "video/mp4"
    headers["Content-Length"] = "5"

    class Response:
        def __init__(self):
            self.headers = headers

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _limit):
            return b"video"

    monkeypatch.setattr(media, "urlopen", lambda *_args, **_kwargs: Response())
    assert download_drive_video("https://drive.google.com/file/d/abc/preview") == b"video"

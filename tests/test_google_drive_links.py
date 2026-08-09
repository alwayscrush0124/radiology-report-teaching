import pytest

from scripts.link_google_drive_videos import preview_url


def test_preview_url_builds_embeddable_drive_url() -> None:
    assert preview_url("abc_123-X") == "https://drive.google.com/file/d/abc_123-X/preview"


def test_preview_url_rejects_full_urls() -> None:
    with pytest.raises(ValueError):
        preview_url("https://drive.google.com/file/d/abc/preview")


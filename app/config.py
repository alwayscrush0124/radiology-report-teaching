"""Project configuration and path helpers."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
VIDEOS_DIR = DATA_DIR / "videos"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
CLIPS_DIR = DATA_DIR / "clips"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
CARDS_DIR = DATA_DIR / "cards"
INDEX_DIR = DATA_DIR / "index"
LLM_JOBS_DIR = DATA_DIR / "llm_jobs"

DEFAULT_BUFFER_SECONDS = 12
HUMAN_COMPLETION = "needs human completion"
NOT_MENTIONED = "not mentioned"


def ensure_data_dirs() -> None:
    """Create output directories used by the MVP pipeline."""
    for path in [
        VIDEOS_DIR,
        TRANSCRIPTS_DIR,
        CLIPS_DIR,
        SCREENSHOTS_DIR,
        CARDS_DIR,
        INDEX_DIR,
        LLM_JOBS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)

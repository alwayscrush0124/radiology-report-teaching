"""Index writers for generated teaching cards."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .teaching_card import TeachingCard


INDEX_FIELDS = [
    "card_id",
    "case_id",
    "source_video",
    "timestamp_range",
    "teaching_moment_type",
    "topic",
    "image_dependency",
    "report_issue_type",
    "key_screenshot",
    "scroll_clip",
    "human_review_status",
]


def write_indexes(cards: list[TeachingCard], output_dir: str | Path) -> tuple[Path, Path]:
    """Write CSV and JSON indexes for cards."""
    index_dir = Path(output_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    rows = [_card_to_row(card) for card in cards]

    csv_path = index_dir / "cards_index.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=INDEX_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    json_path = index_dir / "cards_index.json"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path


def _card_to_row(card: TeachingCard) -> dict[str, str]:
    return {
        "card_id": card.card_id,
        "case_id": card.case_id,
        "source_video": card.source_video,
        "timestamp_range": card.timestamp_range,
        "teaching_moment_type": card.teaching_moment_type,
        "topic": card.topic,
        "image_dependency": card.image_dependency,
        "report_issue_type": ";".join(card.report_issue_type),
        "key_screenshot": card.optional_image_evidence.key_screenshot,
        "scroll_clip": card.optional_image_evidence.scroll_clip,
        "human_review_status": card.human_review.status,
    }

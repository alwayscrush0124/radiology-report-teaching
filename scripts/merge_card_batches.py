"""Merge reviewed chunk card batches into one chronologically ordered atlas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.index_writer import write_indexes
from app.teaching_card import HumanReview, OptionalImageEvidence, TeachingCard
from app.transcript_parser import time_to_seconds


def load_card(path: Path) -> TeachingCard:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["optional_image_evidence"] = OptionalImageEvidence(
        **payload["optional_image_evidence"]
    )
    payload["human_review"] = HumanReview(**payload["human_review"])
    return TeachingCard(**payload)


def merge_batches(
    input_root: Path,
    output_cards: Path,
    output_index: Path,
    case_id: str,
    source_transcript: str,
    exclusions: set[str],
    overrides: dict[str, dict[str, object]],
) -> tuple[list[TeachingCard], Path]:
    candidates: list[tuple[str, TeachingCard]] = []
    excluded: list[str] = []
    for path in sorted(input_root.glob("CHUNK*/CARD*.json")):
        relative_id = f"{path.parent.name}/{path.stem}"
        if relative_id in exclusions:
            excluded.append(relative_id)
            continue
        candidates.append((relative_id, load_card(path)))

    candidates.sort(key=lambda item: (_card_start_seconds(item[1]), item[0]))
    merged: list[TeachingCard] = []
    provenance: list[dict[str, str]] = []
    for index, (relative_id, card) in enumerate(candidates, start=1):
        old_card_id = card.card_id
        override = overrides.get(relative_id, {})
        if "timestamp_range" in override:
            card.timestamp_range = str(override["timestamp_range"])
        merged_sources = [relative_id] + [
            str(value) for value in override.get("additional_source_chunk_cards", [])
        ]
        card.card_id = f"CARD{index:03d}"
        card.case_id = case_id
        card.source_transcript = source_transcript
        card.optional_image_evidence.notes = (
            f"{card.optional_image_evidence.notes} Source chunk cards: {', '.join(merged_sources)}."
        ).strip()
        merged.append(card)
        provenance.append(
            {
                "card_id": card.card_id,
                "source_chunk_card": relative_id,
                "merged_source_chunk_cards": merged_sources,
                "source_card_id": old_card_id,
                "timestamp_range": card.timestamp_range,
                "topic": card.topic,
            }
        )

    output_cards.mkdir(parents=True, exist_ok=True)
    for card in merged:
        card.write_markdown(output_cards)
        card.write_json(output_cards)
    write_indexes(merged, output_index)
    summary_path = _write_summary(merged, output_index, source_transcript)

    merge_manifest = output_index / "merge_manifest.json"
    merge_manifest.write_text(
        json.dumps(
            {
                "input_root": str(input_root),
                "case_id": case_id,
                "source_transcript": source_transcript,
                "included_cards": provenance,
                "excluded_chunk_cards": excluded,
                "summary_path": str(summary_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return merged, merge_manifest


def _card_start_seconds(card: TeachingCard) -> float:
    start = card.timestamp_range.split("-", 1)[0]
    return time_to_seconds(start) or 0


def _write_summary(cards: list[TeachingCard], output_index: Path, source_transcript: str) -> Path:
    summary_path = output_index / "cards_summary.md"
    lines = [
        "# Full Video Teaching Card Summary",
        "",
        f"- Source transcript: {source_transcript}",
        f"- Teaching cards: {len(cards)}",
        "- Review status: all cards require teacher review",
        "",
        "| Card | Timestamp | Type | Topic |",
        "|---|---|---|---|",
    ]
    for card in cards:
        topic = card.topic.replace("|", "\\|")
        lines.append(
            f"| {card.card_id} | {card.timestamp_range} | "
            f"{card.teaching_moment_type} | {topic} |"
        )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--output-cards", required=True, type=Path)
    parser.add_argument("--output-index", required=True, type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--source-transcript", required=True)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--overrides", type=Path)
    args = parser.parse_args()

    overrides: dict[str, dict[str, object]] = {}
    if args.overrides:
        overrides = json.loads(args.overrides.read_text(encoding="utf-8"))

    cards, manifest = merge_batches(
        input_root=args.input_root,
        output_cards=args.output_cards,
        output_index=args.output_index,
        case_id=args.case_id,
        source_transcript=args.source_transcript,
        exclusions=set(args.exclude),
        overrides=overrides,
    )
    print(f"Merged cards: {len(cards)}")
    print(f"Wrote cards: {args.output_cards}")
    print(f"Wrote indexes: {args.output_index}")
    print(f"Wrote merge manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

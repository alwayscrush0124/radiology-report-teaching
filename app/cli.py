"""Command line interface for the Radiology Report Teaching Atlas MVP."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import CARDS_DIR, CLIPS_DIR, INDEX_DIR, LLM_JOBS_DIR, SCREENSHOTS_DIR, ensure_data_dirs
from .index_writer import write_indexes
from .llm_segmenter import LLMResponseValidationError, load_llm_analysis, write_manual_job
from .media_extractor import FFmpegUnavailableError, extract_clip, extract_screenshot
from .segment_detector import TeachingSegment, detect_teaching_segments
from .teaching_card import TeachingCard, card_from_segment
from .transcript_chunker import write_chunked_llm_jobs
from .transcript_parser import parse_transcript


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create teaching cards from local radiology report feedback transcripts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    process = subparsers.add_parser("process", help="Process a transcript and optional video into teaching cards.")
    process.add_argument("--transcript", required=True, help="Path to .srt, .vtt, or .txt transcript.")
    process.add_argument("--video", default="", help="Optional path to .mp4 video.")
    process.add_argument("--case-id", required=True, help="Case identifier, for example CASE001.")
    process.add_argument("--cards-dir", default=str(CARDS_DIR), help="Output directory for card markdown/json files.")
    process.add_argument("--index-dir", default=str(INDEX_DIR), help="Output directory for index files.")
    process.add_argument("--screenshots-dir", default=str(SCREENSHOTS_DIR), help="Output directory for screenshots.")
    process.add_argument("--clips-dir", default=str(CLIPS_DIR), help="Output directory for clips.")

    prepare_llm = subparsers.add_parser(
        "prepare-llm",
        help="Create a manual LLM request from a timestamped transcript; no API required.",
    )
    prepare_llm.add_argument("--transcript", required=True, help="Path to .srt, .vtt, or .txt transcript.")
    prepare_llm.add_argument(
        "--output-dir",
        default="",
        help="Job output directory. Defaults to data/llm_jobs/<transcript-name>.",
    )

    process_llm_parser = subparsers.add_parser(
        "process-llm",
        help="Validate a manual LLM JSON response and create teaching cards.",
    )
    process_llm_parser.add_argument("--transcript", required=True, help="Path to the source transcript.")
    process_llm_parser.add_argument("--response", required=True, help="Path to the LLM JSON response.")
    process_llm_parser.add_argument("--video", default="", help="Optional path to .mp4 video.")
    process_llm_parser.add_argument("--case-id", required=True, help="Case identifier, for example CASE001.")
    process_llm_parser.add_argument("--cards-dir", default=str(CARDS_DIR), help="Output directory for cards.")
    process_llm_parser.add_argument("--index-dir", default=str(INDEX_DIR), help="Output directory for indexes.")
    process_llm_parser.add_argument(
        "--screenshots-dir", default=str(SCREENSHOTS_DIR), help="Output directory for screenshots."
    )
    process_llm_parser.add_argument("--clips-dir", default=str(CLIPS_DIR), help="Output directory for clips.")

    prepare_chunks = subparsers.add_parser(
        "prepare-llm-chunks",
        help="Split a long transcript into overlapping manual LLM jobs.",
    )
    prepare_chunks.add_argument("--transcript", required=True, help="Path to a timestamped transcript.")
    prepare_chunks.add_argument("--output-dir", required=True, help="Output directory for chunk jobs.")
    prepare_chunks.add_argument(
        "--chunk-minutes", type=int, default=10, help="Length of each chunk in minutes."
    )
    prepare_chunks.add_argument(
        "--overlap-seconds", type=int, default=45, help="Overlap between adjacent chunks."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "process":
        process(args)
        return 0
    if args.command == "prepare-llm":
        prepare_llm_job(args)
        return 0
    if args.command == "process-llm":
        try:
            process_llm(args)
        except LLMResponseValidationError as exc:
            print(f"LLM response validation failed: {exc}")
            return 1
        return 0
    if args.command == "prepare-llm-chunks":
        prepare_llm_chunks(args)
        return 0
    parser.error(f"Unknown command: {args.command}")
    return 2


def process(args: argparse.Namespace) -> list[TeachingCard]:
    ensure_data_dirs()
    transcript_path = Path(args.transcript)
    video_path = Path(args.video) if args.video else None

    entries = parse_transcript(transcript_path)
    segments = detect_teaching_segments(entries)
    cards = [
        card_from_segment(
            segment=segment,
            card_id=f"CARD{index + 1:03d}",
            case_id=args.case_id,
            source_transcript=transcript_path.name,
            source_video=video_path.name if video_path else "",
        )
        for index, segment in enumerate(segments)
    ]

    if video_path:
        _attach_media_assets(
            cards=cards,
            segments=segments,
            video_path=video_path,
            screenshots_dir=Path(args.screenshots_dir),
            clips_dir=Path(args.clips_dir),
        )

    cards_dir = Path(args.cards_dir)
    for card in cards:
        card.write_markdown(cards_dir)
        card.write_json(cards_dir)

    csv_path, json_path = write_indexes(cards, args.index_dir)
    print(f"Parsed transcript entries: {len(entries)}")
    print(f"Detected teaching moments: {len(segments)}")
    print(f"Wrote cards to: {cards_dir}")
    print(f"Wrote indexes: {csv_path}, {json_path}")
    return cards


def prepare_llm_job(args: argparse.Namespace) -> tuple[Path, Path]:
    """Create files for a manual copy/paste LLM segmentation round trip."""
    ensure_data_dirs()
    transcript_path = Path(args.transcript)
    entries = parse_transcript(transcript_path)
    output_dir = Path(args.output_dir) if args.output_dir else LLM_JOBS_DIR / transcript_path.stem
    request_path, response_template_path = write_manual_job(
        entries=entries,
        transcript_name=transcript_path.name,
        output_dir=output_dir,
    )
    print(f"Prepared transcript entries: {len(entries)}")
    print(f"Wrote manual LLM request: {request_path}")
    print(f"Wrote response template: {response_template_path}")
    return request_path, response_template_path


def process_llm(args: argparse.Namespace) -> list[TeachingCard]:
    """Create cards from an LLM response grounded to transcript line IDs."""
    ensure_data_dirs()
    transcript_path = Path(args.transcript)
    response_path = Path(args.response)
    video_path = Path(args.video) if args.video else None

    entries = parse_transcript(transcript_path)
    analysis = load_llm_analysis(response_path, entries)
    segments = analysis.to_segments(entries)
    cards = [
        card_from_segment(
            segment=segment,
            card_id=f"CARD{index + 1:03d}",
            case_id=args.case_id,
            source_transcript=transcript_path.name,
            source_video=video_path.name if video_path else "",
            topic=moment.topic,
            conversation_summary=moment.summary,
            resident_report_problem=moment.resident_report_problem,
            teacher_feedback=moment.teacher_feedback,
            key_teaching_point=moment.key_teaching_point,
            improved_report_phrase=moment.improved_report_phrase,
            common_pitfall=moment.common_pitfall,
            discussion_question=moment.discussion_question,
            checklist_item_for_next_report=moment.checklist_item_for_next_report,
            generation_method="llm",
        )
        for index, (segment, moment) in enumerate(zip(segments, analysis.teaching_moments))
    ]

    if video_path:
        _attach_media_assets(
            cards=cards,
            segments=segments,
            video_path=video_path,
            screenshots_dir=Path(args.screenshots_dir),
            clips_dir=Path(args.clips_dir),
        )

    cards_dir = Path(args.cards_dir)
    for card in cards:
        card.write_markdown(cards_dir)
        card.write_json(cards_dir)

    csv_path, json_path = write_indexes(cards, args.index_dir)
    print(f"Parsed transcript entries: {len(entries)}")
    print(f"LLM teaching moments: {len(segments)}")
    print(f"Wrote cards to: {cards_dir}")
    print(f"Wrote indexes: {csv_path}, {json_path}")
    return cards


def prepare_llm_chunks(args: argparse.Namespace) -> tuple[list[object], Path]:
    """Split a long transcript and prepare one manual LLM job per chunk."""
    ensure_data_dirs()
    transcript_path = Path(args.transcript)
    entries = parse_transcript(transcript_path)
    manifest_entries, manifest_path = write_chunked_llm_jobs(
        entries=entries,
        source_transcript=transcript_path.name,
        output_dir=args.output_dir,
        chunk_seconds=args.chunk_minutes * 60,
        overlap_seconds=args.overlap_seconds,
    )
    print(f"Parsed transcript entries: {len(entries)}")
    print(f"Prepared LLM chunks: {len(manifest_entries)}")
    for entry in manifest_entries:
        print(
            f"{entry.chunk_id}: {entry.start_time}-{entry.end_time} "
            f"({entry.transcript_entries} entries)"
        )
    print(f"Wrote chunk manifest: {manifest_path}")
    return manifest_entries, manifest_path


def _attach_media_assets(
    cards: list[TeachingCard],
    segments: list[TeachingSegment],
    video_path: Path,
    screenshots_dir: Path,
    clips_dir: Path,
) -> None:
    for card, segment in zip(cards, segments):
        if not segment.start_time or not segment.end_time:
            card.optional_image_evidence.notes += " No timestamp available for media extraction."
            continue

        try:
            if card.image_dependency == "high" or card.suggested_asset in {"key_screenshot", "both"}:
                timestamp = card.optional_image_evidence.best_pause_time or segment.start_time
                screenshot_path = screenshots_dir / f"{card.card_id}.jpg"
                extract_screenshot(video_path, timestamp, screenshot_path)
                card.optional_image_evidence.key_screenshot = str(screenshot_path)

            if card.suggested_asset in {"scroll_clip", "both"}:
                clip_path = clips_dir / f"{card.card_id}.mp4"
                extract_clip(video_path, segment.start_time, segment.end_time, clip_path)
                card.optional_image_evidence.scroll_clip = str(clip_path)
        except FFmpegUnavailableError as exc:
            card.optional_image_evidence.notes += f" Media extraction skipped: {exc}"
        except RuntimeError as exc:
            card.optional_image_evidence.notes += f" Media extraction failed: {exc}"


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Generate reviewable H.264 clips around teaching-card pause times."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path


def timestamp_seconds(value: str) -> float:
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def ffmpeg_timestamp(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{seconds:06.3f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--project", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--duration", default=12.0, type=float)
    parser.add_argument("--lead", default=4.0, type=float)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project = args.project.resolve()
    cards_dir = project / "data/cards/full_video_final"
    clips_dir = project / "data/clips/full_video_final"
    index_json = project / "data/index/full_video_final/cards_index.json"
    index_csv = project / "data/index/full_video_final/cards_index.csv"
    clips_dir.mkdir(parents=True, exist_ok=True)

    generated: dict[str, str] = {}
    for card_path in sorted(cards_dir.glob("CARD*.json")):
        card = json.loads(card_path.read_text(encoding="utf-8"))
        if card.get("image_dependency") != "high":
            continue
        evidence = card.setdefault("optional_image_evidence", {})
        existing = evidence.get("scroll_clip", "")
        if existing and not args.overwrite:
            generated[card["card_id"]] = existing
            continue
        pause_time = evidence.get("best_pause_time")
        if not pause_time:
            continue

        relative_clip = f"data/clips/full_video_final/{card['card_id']}_scroll.mp4"
        output = project / relative_clip
        start = ffmpeg_timestamp(timestamp_seconds(pause_time) - args.lead)
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", start, "-i", str(args.video), "-t", str(args.duration),
                "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
            ],
            check=True,
        )
        evidence["scroll_clip"] = relative_clip
        evidence["notes"] = (
            f"Auto-extracted {args.duration:g}-second silent H.264 candidate clip around "
            f"{pause_time}; teacher review required. " + evidence.get("notes", "")
        ).strip()
        card_path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        md_path = card_path.with_suffix(".md")
        if md_path.exists():
            md = md_path.read_text(encoding="utf-8")
            lines = [
                f"- Scroll clip: {relative_clip}" if line.startswith("- Scroll clip:") else line
                for line in md.splitlines()
            ]
            md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        generated[card["card_id"]] = relative_clip

    rows = json.loads(index_json.read_text(encoding="utf-8"))
    for row in rows:
        if row["card_id"] in generated:
            row["scroll_clip"] = generated[row["card_id"]]
    index_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with index_csv.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        csv_rows = list(reader)
    for row in csv_rows:
        if row["card_id"] in generated:
            row["scroll_clip"] = generated[row["card_id"]]
    with index_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"Clips indexed: {len(generated)}")


if __name__ == "__main__":
    main()

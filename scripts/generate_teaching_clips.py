#!/usr/bin/env python3
"""Generate audible teaching clips from final semantic card boundaries."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def seconds(value: str) -> float:
    hours, minutes, secs = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(secs)


def stamp(value: float) -> str:
    hours, remainder = divmod(max(0, value), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{secs:06.3f}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--cards-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    video = args.video.expanduser().resolve()
    cards_dir = args.cards_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    for card_path in sorted(cards_dir.glob("CARD*.json")):
        card = json.loads(card_path.read_text(encoding="utf-8"))
        start_text, end_text = card["timestamp_range"].split("-")
        start, end = seconds(start_text), seconds(end_text)
        duration = end - start
        if duration <= 0:
            raise ValueError(f"Invalid range for {card['card_id']}: {card['timestamp_range']}")

        output = output_dir / f"{card['card_id']}_teaching.mp4"
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", stamp(start), "-i", str(video), "-t", f"{duration:.3f}",
                "-map", "0:v:0", "-map", "0:a:0?",
                "-c:v", "libx264", "-preset", "medium", "-crf", "22",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
                "-movflags", "+faststart", str(output),
            ],
            check=True,
        )
        manifest.append(
            {
                "card_id": card["card_id"],
                "topic": card["topic"],
                "teaching_clip_range": card["timestamp_range"],
                "duration_seconds": duration,
                "boundary_source": "llm-semantic-boundary",
                "teaching_clip": str(output.relative_to(PROJECT)),
                "teacher_review_status": "needs_review",
            }
        )

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {len(manifest)} complete teaching clips")
    print(f"Total duration: {sum(item['duration_seconds'] for item in manifest):.1f} seconds")


if __name__ == "__main__":
    main()

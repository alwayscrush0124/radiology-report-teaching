"""Collapse obvious consecutive duplicate cues while preserving timestamps."""

from __future__ import annotations

import argparse
from pathlib import Path

from merge_srt import RawCue, parse_srt_raw, write_srt_raw


def clean_repeated_cues(cues: list[RawCue], minimum_run: int = 3) -> tuple[list[RawCue], int]:
    cleaned: list[RawCue] = []
    collapsed_runs = 0
    index = 0
    while index < len(cues):
        end_index = index + 1
        while end_index < len(cues) and cues[end_index].text == cues[index].text:
            end_index += 1
        run = cues[index:end_index]
        if len(run) >= minimum_run:
            cleaned.append(RawCue(start=run[0].start, end=run[-1].end, text=run[0].text))
            collapsed_runs += 1
        else:
            cleaned.extend(run)
        index = end_index
    return cleaned, collapsed_runs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--minimum-run", type=int, default=3)
    args = parser.parse_args()
    if args.minimum_run < 2:
        parser.error("--minimum-run must be at least 2")

    cues = parse_srt_raw(args.input)
    cleaned, collapsed_runs = clean_repeated_cues(cues, args.minimum_run)
    write_srt_raw(cleaned, args.output)
    print(f"Input cues: {len(cues)}")
    print(f"Collapsed repeated runs: {collapsed_runs}")
    print(f"Output cues: {len(cleaned)}")
    print(f"Wrote cleaned SRT: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

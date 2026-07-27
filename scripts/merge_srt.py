"""Merge a corrected SRT tail into an earlier transcript at a timestamp."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


TIME_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})"
)


@dataclass(frozen=True)
class RawCue:
    start: str
    end: str
    text: str

    @property
    def start_ms(self) -> int:
        return _timestamp_to_ms(self.start)

    @property
    def end_ms(self) -> int:
        return _timestamp_to_ms(self.end)


def parse_srt_raw(path: Path) -> list[RawCue]:
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip())
    cues: list[RawCue] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        time_index = next((index for index, line in enumerate(lines) if "-->" in line), None)
        if time_index is None:
            continue
        match = TIME_RE.search(lines[time_index])
        if not match:
            continue
        text = "\n".join(lines[time_index + 1 :]).strip()
        if text:
            cues.append(RawCue(match.group("start"), match.group("end"), text))
    return cues


def merge_srt(base: Path, replacement: Path, replace_from: str, output: Path) -> Path:
    cutoff_ms = _timestamp_to_ms(_normalize_cutoff(replace_from))
    base_cues = [cue for cue in parse_srt_raw(base) if cue.end_ms <= cutoff_ms]
    replacement_cues = [
        cue for cue in parse_srt_raw(replacement) if cue.start_ms >= cutoff_ms
    ]
    merged = sorted(base_cues + replacement_cues, key=lambda cue: (cue.start_ms, cue.end_ms))
    if not merged:
        raise ValueError("No transcript cues remained after merge.")

    return write_srt_raw(merged, output)


def write_srt_raw(cues: list[RawCue], output: Path) -> Path:
    """Write raw cues without discarding millisecond timestamps."""
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered_blocks = [
        f"{index}\n{cue.start.replace('.', ',')} --> {cue.end.replace('.', ',')}\n{cue.text}"
        for index, cue in enumerate(cues, start=1)
    ]
    output.write_text("\n\n".join(rendered_blocks) + "\n", encoding="utf-8")
    return output


def _normalize_cutoff(value: str) -> str:
    clean = value.strip().replace(",", ".")
    if re.fullmatch(r"\d{2}:\d{2}:\d{2}", clean):
        return clean + ".000"
    if re.fullmatch(r"\d{2}:\d{2}:\d{2}\.\d{3}", clean):
        return clean
    raise ValueError("replace-from must use HH:MM:SS or HH:MM:SS.mmm")


def _timestamp_to_ms(value: str) -> int:
    hours, minutes, seconds_part = value.replace(",", ".").split(":")
    seconds, milliseconds = seconds_part.split(".")
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(seconds) * 1_000
        + int(milliseconds)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--replacement", required=True, type=Path)
    parser.add_argument("--replace-from", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = merge_srt(args.base, args.replacement, args.replace_from, args.output)
    print(f"Wrote merged SRT: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Transcript parsing for SRT, VTT, and plain text files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


TIME_ARROW_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?(?:[,.]\d{1,3})?)\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?(?:[,.]\d{1,3})?)"
)
TEXT_TIMESTAMP_RE = re.compile(
    r"^\s*(?:\[)?(?P<start>\d{1,2}:\d{2}(?::\d{2})?)(?:\])?\s*[-:]\s*(?P<text>.+)$"
)


@dataclass(frozen=True)
class TranscriptEntry:
    """One transcript cue or text chunk."""

    index: int
    start_time: str | None
    end_time: str | None
    text: str

    @property
    def start_seconds(self) -> float | None:
        return time_to_seconds(self.start_time) if self.start_time else None

    @property
    def end_seconds(self) -> float | None:
        return time_to_seconds(self.end_time) if self.end_time else None


def time_to_seconds(value: str | None) -> float | None:
    """Convert HH:MM:SS(.mmm) or MM:SS(.mmm) into seconds."""
    if not value:
        return None
    clean = value.strip().replace(",", ".")
    parts = clean.split(":")
    if len(parts) == 2:
        hours = 0
        minutes = int(parts[0])
        seconds = float(parts[1])
    elif len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
    else:
        raise ValueError(f"Unsupported timestamp: {value}")
    return hours * 3600 + minutes * 60 + seconds


def seconds_to_time(seconds: float | int | None) -> str | None:
    """Convert seconds into HH:MM:SS."""
    if seconds is None:
        return None
    rounded = max(0, int(round(float(seconds))))
    hours = rounded // 3600
    minutes = (rounded % 3600) // 60
    secs = rounded % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def parse_transcript(path: str | Path) -> list[TranscriptEntry]:
    """Parse a transcript file by extension."""
    transcript_path = Path(path)
    suffix = transcript_path.suffix.lower()
    if suffix == ".srt":
        return parse_srt(transcript_path)
    if suffix == ".vtt":
        return parse_vtt(transcript_path)
    if suffix == ".txt":
        return parse_txt(transcript_path)
    raise ValueError(f"Unsupported transcript format: {suffix}")


def parse_srt(path: str | Path) -> list[TranscriptEntry]:
    """Parse SubRip subtitles."""
    text = Path(path).read_text(encoding="utf-8-sig")
    return _parse_timed_blocks(text)


def parse_vtt(path: str | Path) -> list[TranscriptEntry]:
    """Parse WebVTT subtitles."""
    text = Path(path).read_text(encoding="utf-8-sig")
    lines = [
        line
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith(("WEBVTT", "NOTE", "STYLE"))
    ]
    return _parse_timed_blocks("\n".join(lines))


def parse_txt(path: str | Path) -> list[TranscriptEntry]:
    """Parse text transcripts, with optional simple line timestamps."""
    raw_text = Path(path).read_text(encoding="utf-8-sig").strip()
    if not raw_text:
        return []

    entries: list[TranscriptEntry] = []
    untimed_lines: list[str] = []
    for line in raw_text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        match = TEXT_TIMESTAMP_RE.match(clean)
        if match:
            entries.append(
                TranscriptEntry(
                    index=len(entries) + 1,
                    start_time=seconds_to_time(time_to_seconds(match.group("start"))),
                    end_time=None,
                    text=match.group("text").strip(),
                )
            )
        else:
            untimed_lines.append(clean)

    if entries and not untimed_lines:
        return entries

    if entries:
        entries.append(
            TranscriptEntry(
                index=len(entries) + 1,
                start_time=None,
                end_time=None,
                text=" ".join(untimed_lines),
            )
        )
        return entries

    return [TranscriptEntry(index=1, start_time=None, end_time=None, text=raw_text)]


def _parse_timed_blocks(text: str) -> list[TranscriptEntry]:
    blocks = re.split(r"\n\s*\n", text.strip())
    entries: list[TranscriptEntry] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        arrow_line_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if arrow_line_index is None:
            continue

        match = TIME_ARROW_RE.search(lines[arrow_line_index])
        if not match:
            continue

        cue_text = " ".join(lines[arrow_line_index + 1 :]).strip()
        if not cue_text:
            continue

        entries.append(
            TranscriptEntry(
                index=len(entries) + 1,
                start_time=seconds_to_time(time_to_seconds(match.group("start"))),
                end_time=seconds_to_time(time_to_seconds(match.group("end"))),
                text=cue_text,
            )
        )
    return entries

"""Split a long timed transcript into overlapping LLM work units."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .llm_segmenter import write_manual_job
from .transcript_parser import TranscriptEntry, seconds_to_time


@dataclass(frozen=True)
class TranscriptChunk:
    chunk_id: str
    start_seconds: int
    end_seconds: int
    entries: list[TranscriptEntry]

    @property
    def start_time(self) -> str:
        return seconds_to_time(self.start_seconds) or "00:00:00"

    @property
    def end_time(self) -> str:
        return seconds_to_time(self.end_seconds) or "00:00:00"


@dataclass(frozen=True)
class ChunkManifestEntry:
    chunk_id: str
    start_time: str
    end_time: str
    transcript_entries: int
    transcript_path: str
    request_path: str
    response_template_path: str
    expected_response_path: str


def chunk_transcript(
    entries: list[TranscriptEntry], chunk_seconds: int = 600, overlap_seconds: int = 45
) -> list[TranscriptChunk]:
    """Create overlapping chunks while retaining absolute transcript timestamps."""
    if chunk_seconds <= 0:
        raise ValueError("chunk_seconds must be positive.")
    if overlap_seconds < 0 or overlap_seconds >= chunk_seconds:
        raise ValueError("overlap_seconds must be non-negative and shorter than chunk_seconds.")

    timed_entries = [
        entry
        for entry in entries
        if entry.start_seconds is not None and (entry.end_seconds or entry.start_seconds) is not None
    ]
    if not timed_entries:
        raise ValueError("Chunked LLM processing requires a timestamped transcript.")

    duration_seconds = int(
        max((entry.end_seconds or entry.start_seconds or 0) for entry in timed_entries) + 0.999
    )
    stride = chunk_seconds - overlap_seconds
    chunks: list[TranscriptChunk] = []
    start = 0
    while start < duration_seconds:
        end = min(duration_seconds, start + chunk_seconds)
        selected = [
            entry
            for entry in timed_entries
            if (entry.end_seconds or entry.start_seconds or 0) > start
            and (entry.start_seconds or 0) < end
        ]
        if selected:
            reindexed = [
                TranscriptEntry(
                    index=index,
                    start_time=entry.start_time,
                    end_time=entry.end_time,
                    text=entry.text,
                )
                for index, entry in enumerate(selected, start=1)
            ]
            chunks.append(
                TranscriptChunk(
                    chunk_id=f"CHUNK{len(chunks) + 1:03d}",
                    start_seconds=start,
                    end_seconds=end,
                    entries=reindexed,
                )
            )
        start += stride
    return chunks


def write_chunked_llm_jobs(
    entries: list[TranscriptEntry],
    source_transcript: str,
    output_dir: str | Path,
    chunk_seconds: int = 600,
    overlap_seconds: int = 45,
) -> tuple[list[ChunkManifestEntry], Path]:
    """Write chunk SRT files, manual prompts, and a machine-readable manifest."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    chunks = chunk_transcript(entries, chunk_seconds, overlap_seconds)
    manifest_entries: list[ChunkManifestEntry] = []

    for chunk in chunks:
        label = f"{chunk.chunk_id}_{_compact_time(chunk.start_time)}_{_compact_time(chunk.end_time)}"
        chunk_dir = root / label
        transcript_path = chunk_dir / "transcript.srt"
        _write_srt(chunk.entries, transcript_path)
        request_path, response_template_path = write_manual_job(
            entries=chunk.entries,
            transcript_name=f"{source_transcript} [{chunk.start_time}-{chunk.end_time}]",
            output_dir=chunk_dir,
        )
        manifest_entries.append(
            ChunkManifestEntry(
                chunk_id=chunk.chunk_id,
                start_time=chunk.start_time,
                end_time=chunk.end_time,
                transcript_entries=len(chunk.entries),
                transcript_path=str(transcript_path),
                request_path=str(request_path),
                response_template_path=str(response_template_path),
                expected_response_path=str(chunk_dir / "llm_response.json"),
            )
        )

    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source_transcript": source_transcript,
                "chunk_seconds": chunk_seconds,
                "overlap_seconds": overlap_seconds,
                "chunks": [asdict(entry) for entry in manifest_entries],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_entries, manifest_path


def _write_srt(entries: list[TranscriptEntry], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blocks = [
        f"{index}\n{_srt_time(entry.start_time)} --> {_srt_time(entry.end_time)}\n{entry.text}"
        for index, entry in enumerate(entries, start=1)
    ]
    output_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def _srt_time(value: str | None) -> str:
    if not value:
        raise ValueError("Chunked SRT output requires start and end timestamps.")
    clean = value.replace(".", ",")
    return clean if "," in clean else clean + ",000"


def _compact_time(value: str) -> str:
    return value.replace(":", "")

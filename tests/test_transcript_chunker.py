from pathlib import Path

from app.transcript_chunker import chunk_transcript, write_chunked_llm_jobs
from app.transcript_parser import TranscriptEntry


def _entry(index: int, start: str, end: str, text: str) -> TranscriptEntry:
    return TranscriptEntry(index=index, start_time=start, end_time=end, text=text)


def test_chunks_overlap_and_keep_absolute_timestamps() -> None:
    entries = [
        _entry(1, "00:00:10", "00:00:20", "first"),
        _entry(2, "00:09:20", "00:09:30", "overlap"),
        _entry(3, "00:10:10", "00:10:20", "second"),
    ]

    chunks = chunk_transcript(entries, chunk_seconds=600, overlap_seconds=60)

    assert len(chunks) == 2
    assert [entry.text for entry in chunks[0].entries] == ["first", "overlap"]
    assert [entry.text for entry in chunks[1].entries] == ["overlap", "second"]
    assert chunks[1].entries[0].start_time == "00:09:20"


def test_writes_manifest_and_manual_jobs(tmp_path: Path) -> None:
    entries = [
        _entry(1, "00:00:10", "00:00:20", "first"),
        _entry(2, "00:10:10", "00:10:20", "second"),
    ]

    manifest_entries, manifest_path = write_chunked_llm_jobs(
        entries,
        source_transcript="full.srt",
        output_dir=tmp_path,
        chunk_seconds=600,
        overlap_seconds=60,
    )

    assert len(manifest_entries) == 2
    assert manifest_path.exists()
    assert Path(manifest_entries[0].request_path).exists()
    assert "[L001]" in Path(manifest_entries[0].request_path).read_text(encoding="utf-8")

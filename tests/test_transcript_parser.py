from pathlib import Path

from app.transcript_parser import parse_srt, parse_transcript


def test_srt_parser_reads_timestamps_and_text() -> None:
    entries = parse_srt(Path("examples/sample_transcript.srt"))

    assert entries[0].start_time == "00:00:05"
    assert entries[0].end_time == "00:00:11"
    assert "impression" in entries[0].text


def test_txt_without_timestamp_is_supported(tmp_path: Path) -> None:
    transcript = tmp_path / "untimed.txt"
    transcript.write_text("Teacher: 這個要寫在 impression 裡。", encoding="utf-8")

    entries = parse_transcript(transcript)

    assert entries[0].start_time is None
    assert "impression" in entries[0].text

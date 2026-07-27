from pathlib import Path

from app.segment_detector import detect_teaching_segments
from app.transcript_parser import parse_srt


def test_detector_finds_teaching_moments_from_sample() -> None:
    entries = parse_srt(Path("examples/sample_transcript.srt"))

    segments = detect_teaching_segments(entries)

    assert segments
    assert any(segment.teaching_moment_type == "impression_refinement" for segment in segments)
    assert any(segment.image_dependency == "high" for segment in segments)

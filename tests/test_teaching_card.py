from app.segment_detector import TeachingSegment
from app.teaching_card import card_from_segment


def test_teaching_card_outputs_json_and_markdown() -> None:
    segment = TeachingSegment(
        segment_id="SEG001",
        start_time="00:00:01",
        end_time="00:00:20",
        teaching_moment_type="impression_refinement",
        evidence_text="Teacher: impression should include the answer to the clinical question.",
        confidence=0.79,
        image_dependency="low",
        suggested_asset="none",
    )

    card = card_from_segment(segment, "CARD001", "CASE001", "session_001.srt")

    assert '"card_id": "CARD001"' in card.to_json()
    assert "# Report Teaching Card: CARD001" in card.to_markdown()
    assert "clinical question" in card.key_teaching_point

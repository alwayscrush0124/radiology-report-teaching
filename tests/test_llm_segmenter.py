import json
from pathlib import Path

import pytest

from app.llm_segmenter import (
    LLMResponseValidationError,
    build_manual_prompt,
    parse_llm_analysis,
)
from app.transcript_parser import parse_srt


def _valid_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "lecture_summary": "老師示範如何回答 clinical question。",
        "teaching_moments": [
            {
                "start_line": "L001",
                "end_line": "L002",
                "topic": "Impression 回答臨床問題",
                "teaching_moment_type": "clinical_question_alignment",
                "summary": "老師指出 impression 不能只重複 findings。",
                "resident_report_problem": "Impression 沒有回答 clinical question。",
                "teacher_feedback": "整合 findings 並回答 clinical question。",
                "key_teaching_point": "Impression 應直接回答臨床問題。",
                "improved_report_phrase": "needs human completion",
                "common_pitfall": "直接複製 findings。",
                "discussion_question": "這份 impression 是否回答臨床問題？",
                "checklist_item_for_next_report": "送出前確認 impression 已回答臨床問題。",
                "image_dependency": "low",
                "suggested_asset": "none",
                "confidence": 0.9,
            }
        ],
    }


def test_prompt_uses_stable_line_ids() -> None:
    entries = parse_srt(Path("examples/sample_transcript.srt"))

    prompt = build_manual_prompt(entries, "sample_transcript.srt")

    assert "[L001][00:00:05 --> 00:00:11]" in prompt
    assert "[L004][00:00:48 --> 00:00:55]" in prompt
    assert "只輸出 JSON" in prompt


def test_llm_analysis_maps_lines_to_transcript_timestamps() -> None:
    entries = parse_srt(Path("examples/sample_transcript.srt"))

    analysis = parse_llm_analysis(_valid_payload(), entries)
    segment = analysis.to_segments(entries)[0]

    assert segment.start_time == "00:00:05"
    assert segment.end_time == "00:00:29"
    assert segment.teaching_moment_type == "clinical_question_alignment"
    assert "比較保守" in segment.evidence_text


def test_llm_analysis_rejects_unknown_line_id() -> None:
    entries = parse_srt(Path("examples/sample_transcript.srt"))
    payload = json.loads(json.dumps(_valid_payload()))
    payload["teaching_moments"][0]["end_line"] = "L999"

    with pytest.raises(LLMResponseValidationError, match="only 4 lines"):
        parse_llm_analysis(payload, entries)

import json
from pathlib import Path

from app.cli import main


def test_cli_process_without_video_completes(tmp_path: Path) -> None:
    cards_dir = tmp_path / "cards"
    index_dir = tmp_path / "index"

    exit_code = main(
        [
            "process",
            "--transcript",
            "examples/sample_transcript.srt",
            "--case-id",
            "CASE001",
            "--cards-dir",
            str(cards_dir),
            "--index-dir",
            str(index_dir),
        ]
    )

    assert exit_code == 0
    assert (cards_dir / "CARD001.md").exists()
    assert (index_dir / "cards_index.csv").exists()


def test_cli_prepares_manual_llm_job(tmp_path: Path) -> None:
    output_dir = tmp_path / "llm_job"

    exit_code = main(
        [
            "prepare-llm",
            "--transcript",
            "examples/sample_transcript.srt",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert "[L001]" in (output_dir / "llm_request.md").read_text(encoding="utf-8")
    assert (output_dir / "llm_response.template.json").exists()


def test_cli_processes_manual_llm_response(tmp_path: Path) -> None:
    response_path = tmp_path / "response.json"
    response_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "lecture_summary": "Impression 教學。",
                "teaching_moments": [
                    {
                        "start_line": "L001",
                        "end_line": "L002",
                        "topic": "Impression 回答臨床問題",
                        "teaching_moment_type": "clinical_question_alignment",
                        "summary": "老師指出 impression 沒有回答 clinical question。",
                        "resident_report_problem": "只放 findings。",
                        "teacher_feedback": "要回答 clinical question。",
                        "key_teaching_point": "Impression 應回答 clinical question。",
                        "improved_report_phrase": "needs human completion",
                        "common_pitfall": "複製 findings。",
                        "discussion_question": "臨床問題是否已被回答？",
                        "checklist_item_for_next_report": "確認 impression 回答臨床問題。",
                        "image_dependency": "low",
                        "suggested_asset": "none",
                        "confidence": 0.9,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cards_dir = tmp_path / "cards"
    index_dir = tmp_path / "index"

    exit_code = main(
        [
            "process-llm",
            "--transcript",
            "examples/sample_transcript.srt",
            "--response",
            str(response_path),
            "--case-id",
            "CASE_LLM",
            "--cards-dir",
            str(cards_dir),
            "--index-dir",
            str(index_dir),
        ]
    )

    assert exit_code == 0
    card = json.loads((cards_dir / "CARD001.json").read_text(encoding="utf-8"))
    assert card["timestamp_range"] == "00:00:05-00:00:29"
    assert card["topic"] == "Impression 回答臨床問題"
    assert card["key_teaching_point"] == "Impression 應回答 clinical question。"
    assert "LLM-assisted" in card["optional_image_evidence"]["notes"]

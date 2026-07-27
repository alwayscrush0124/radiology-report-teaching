import json
from pathlib import Path

from portal.library import TeachingLibrary


def make_library(tmp_path: Path) -> TeachingLibrary:
    root = tmp_path / "data/teaching_library"
    case_dir = root / "cases/CARD001"
    case_dir.mkdir(parents=True)
    (root / "taxonomy.json").write_text(json.dumps({"V": "Vascular", "N": "Neoplasm"}), encoding="utf-8")
    (tmp_path / "subtitle.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nTest\n", encoding="utf-8")
    (tmp_path / "transcript.txt").write_text("Test\n", encoding="utf-8")
    source_card = tmp_path / "card.json"
    source_card.write_text(json.dumps({
        "topic": "Stroke", "key_teaching_point": "Point", "common_pitfall": "Pitfall",
        "improved_report_phrase": "Phrase", "checklist_item_for_next_report": "Checklist",
        "discussion_question": "Question",
    }), encoding="utf-8")
    (case_dir / "metadata.json").write_text(json.dumps({
        "clip_id": "CLIP0001", "card_id": "CARD001", "title": "Stroke",
        "vitamin_cd": [{"code": "V", "label": "Vascular"}], "anatomy": ["brain"],
        "modality": ["CT"], "sequences": [], "teaching_type": "diagnostic_reasoning_discussion",
        "duration_seconds": 30, "assets": {"teaching_clip": "video.mp4", "subtitle": "subtitle.srt", "transcript": "transcript.txt"},
        "teaching_point": "Point", "common_pitfall": "Pitfall", "suggested_report_phrase": "Phrase",
        "checklist_item_for_next_report": "Checklist", "discussion_question": "Question",
        "review_status": "needs_review", "assets": {"teaching_clip": "video.mp4", "subtitle": "subtitle.srt", "transcript": "transcript.txt", "teaching_card": "card.json"},
    }), encoding="utf-8")
    return TeachingLibrary(tmp_path)


def test_dashboard_counts_multilabel_cases(tmp_path: Path) -> None:
    repo = make_library(tmp_path)
    stats = repo.dashboard()
    assert stats["case_count"] == 1
    assert stats["vitamin"] == {"Vascular": 1}
    assert stats["review"] == {"needs_review": 1}


def test_save_case_rebuilds_indexes_and_views(tmp_path: Path) -> None:
    repo = make_library(tmp_path)
    case = repo.get_case("CARD001")
    case["vitamin_cd"].append({"code": "N", "label": "Neoplasm"})
    case["review_status"] = "approved"
    repo.save_case(case)
    saved = repo.get_case("CARD001")
    assert saved["review_status"] == "approved"
    assert (repo.library_root / "cases_index.csv").exists()
    view = json.loads((repo.library_root / "views/N_neoplasm.json").read_text())
    assert view["case_count"] == 1


def test_asset_paths_cannot_escape_data_root(tmp_path: Path) -> None:
    repo = make_library(tmp_path)
    try:
        repo.resolve_asset("../outside.mp4")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected path traversal to be rejected")


def test_validate_srt_rejects_bad_order_and_accepts_valid_srt() -> None:
    valid = "1\n00:00:00,000 --> 00:00:01,000\nFirst\n\n2\n00:00:01,000 --> 00:00:02,000\nSecond\n"
    invalid = "1\n00:00:02,000 --> 00:00:01,000\nBroken\n"
    assert TeachingLibrary.validate_srt(valid) == []
    assert "結束時間" in TeachingLibrary.validate_srt(invalid)[0]


def test_save_case_text_updates_subtitle_and_transcript(tmp_path: Path) -> None:
    repo = make_library(tmp_path)
    subtitle = "1\n00:00:00,000 --> 00:00:02,000\nUpdated\n"
    repo.save_case_text("CARD001", subtitle, "Updated transcript")
    assert repo.read_case_text("CARD001", "subtitle") == subtitle
    assert repo.read_case_text("CARD001", "transcript") == "Updated transcript\n"


def test_save_card_content_updates_metadata_and_source_card(tmp_path: Path) -> None:
    repo = make_library(tmp_path)
    repo.save_card_content("CARD001", {
        "title": "Updated title",
        "teaching_point": "Updated point",
        "common_pitfall": "Updated pitfall",
        "suggested_report_phrase": "Updated phrase",
        "checklist_item_for_next_report": "Updated checklist",
        "discussion_question": "Updated question",
    })
    case = repo.get_case("CARD001")
    source = json.loads((tmp_path / "card.json").read_text())
    assert case["title"] == "Updated title"
    assert source["topic"] == "Updated title"
    assert source["key_teaching_point"] == "Updated point"

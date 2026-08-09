from portal.supabase_library import SupabaseTeachingLibrary, make_record_id


class FakeSupabaseLibrary(SupabaseTeachingLibrary):
    def __init__(self) -> None:
        super().__init__("https://example.supabase.co", "publishable-test-key")
        self.rows = {
            "20260707_CARD001": {
                "record_id": "20260707_CARD001",
                "card_id": "CARD001",
                "lecture_date": "2026-07-07",
                "source_video": "lecture.mp4",
                "storage_path": "2026-07-07/CARD001.mp4",
                "metadata": {
                    "record_id": "20260707_CARD001",
                    "card_id": "CARD001",
                    "lecture_date": "2026-07-07",
                    "title": "Stroke",
                    "teaching_point": "Point",
                    "common_pitfall": "Pitfall",
                    "suggested_report_phrase": "Phrase",
                    "checklist_item_for_next_report": "Checklist",
                    "discussion_question": "Question",
                    "vitamin_cd": [{"code": "V", "label": "Vascular"}],
                    "duration_seconds": 30,
                    "review_status": "needs_review",
                },
                "subtitle": "1\n00:00:00,000 --> 00:00:01,000\nTest\n",
                "transcript": "Test\n",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        }

    def _request(self, table, *, method="GET", query=None, payload=None, prefer=None):
        assert table in {"atlas_cases", "atlas_teaching_sets"}
        if table == "atlas_teaching_sets":
            return [payload]
        record_filter = (query or {}).get("record_id", "")
        record_id = record_filter.removeprefix("eq.") if record_filter else None
        if method == "PATCH":
            self.rows[record_id].update(payload)
            return [self.rows[record_id]]
        if method == "POST":
            self.rows[payload["record_id"]] = dict(payload, updated_at="2026-01-01T00:00:00Z")
            return [self.rows[payload["record_id"]]]
        rows = [self.rows[record_id]] if record_id else list(self.rows.values())
        select = (query or {}).get("select")
        if select in {"subtitle", "transcript"}:
            return [{select: row[select]} for row in rows]
        return rows


def test_cloud_library_loads_cases_and_dashboard() -> None:
    repo = FakeSupabaseLibrary()
    assert repo.get_case("20260707_CARD001")["title"] == "Stroke"
    assert repo.get_case("20260707_CARD001")["card_id"] == "CARD001"
    assert repo.dashboard()["case_count"] == 1
    assert repo.taxonomy()["V"] == "Vascular"


def test_cloud_library_updates_transcript_and_card_content() -> None:
    repo = FakeSupabaseLibrary()
    subtitle = "1\n00:00:00,000 --> 00:00:02,000\nUpdated\n"
    repo.save_case_text("20260707_CARD001", subtitle, "Updated transcript")
    repo.save_card_content("20260707_CARD001", {
        "title": "Updated title",
        "teaching_point": "Updated point",
        "common_pitfall": "Updated pitfall",
        "suggested_report_phrase": "Updated phrase",
        "checklist_item_for_next_report": "Updated checklist",
        "discussion_question": "Updated question",
    })
    assert repo.read_case_text("20260707_CARD001", "subtitle") == subtitle
    assert repo.get_case("20260707_CARD001")["title"] == "Updated title"


def test_record_ids_keep_same_local_card_id_separate_by_date() -> None:
    assert make_record_id("2026-07-07", "CARD001") == "20260707_CARD001"
    assert make_record_id("2026-07-21", "CARD001") == "20260721_CARD001"


def test_upsert_stores_date_and_storage_path() -> None:
    repo = FakeSupabaseLibrary()
    case = dict(repo.get_case("20260707_CARD001"))
    case.pop("record_id")
    repo.upsert_case(
        case,
        "subtitle",
        "transcript",
        lecture_date="2026-07-21",
        source_video="2026-07-21.mp4",
        storage_path="2026-07-21/CARD001.mp4",
    )
    newer = repo.get_case("20260721_CARD001")
    assert newer["card_id"] == "CARD001"
    assert newer["storage_path"] == "2026-07-21/CARD001.mp4"

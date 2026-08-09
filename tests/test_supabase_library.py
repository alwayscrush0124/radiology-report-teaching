from portal.supabase_library import SupabaseTeachingLibrary


class FakeSupabaseLibrary(SupabaseTeachingLibrary):
    def __init__(self) -> None:
        super().__init__("https://example.supabase.co", "publishable-test-key")
        self.rows = {
            "CARD001": {
                "card_id": "CARD001",
                "metadata": {
                    "card_id": "CARD001",
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
        card_filter = (query or {}).get("card_id", "")
        card_id = card_filter.removeprefix("eq.") if card_filter else None
        if method == "PATCH":
            self.rows[card_id].update(payload)
            return [self.rows[card_id]]
        rows = [self.rows[card_id]] if card_id else list(self.rows.values())
        select = (query or {}).get("select")
        if select in {"subtitle", "transcript"}:
            return [{select: row[select]} for row in rows]
        return rows


def test_cloud_library_loads_cases_and_dashboard() -> None:
    repo = FakeSupabaseLibrary()
    assert repo.get_case("CARD001")["title"] == "Stroke"
    assert repo.dashboard()["case_count"] == 1
    assert repo.taxonomy()["V"] == "Vascular"


def test_cloud_library_updates_transcript_and_card_content() -> None:
    repo = FakeSupabaseLibrary()
    subtitle = "1\n00:00:00,000 --> 00:00:02,000\nUpdated\n"
    repo.save_case_text("CARD001", subtitle, "Updated transcript")
    repo.save_card_content("CARD001", {
        "title": "Updated title",
        "teaching_point": "Updated point",
        "common_pitfall": "Updated pitfall",
        "suggested_report_phrase": "Updated phrase",
        "checklist_item_for_next_report": "Updated checklist",
        "discussion_question": "Updated question",
    })
    assert repo.read_case_text("CARD001", "subtitle") == subtitle
    assert repo.get_case("CARD001")["title"] == "Updated title"


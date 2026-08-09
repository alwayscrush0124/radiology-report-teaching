#!/usr/bin/env python3
"""Sync teaching text fields from dated card packages without touching media."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import toml

from portal.supabase_library import SupabaseTeachingLibrary


DATE_CODES = {
    "2026-07-07": "0707",
    "2026-07-14": "0714",
    "2026-07-21": "0721",
    "2026-07-28": "0728",
    "2026-08-04": "0804",
}


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    secrets_path = project / ".streamlit/secrets.toml"
    secrets = toml.loads(secrets_path.read_text(encoding="utf-8")) if secrets_path.exists() else {}
    parser = argparse.ArgumentParser(description="同步教學重點、陷阱、報告句與下次報告注意事項。")
    parser.add_argument("--url", default=os.environ.get("SUPABASE_URL") or secrets.get("SUPABASE_URL"))
    parser.add_argument("--key", default=os.environ.get("SUPABASE_KEY") or secrets.get("SUPABASE_KEY"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.url or not args.key:
        parser.error("請提供 SUPABASE_URL 與 SUPABASE_KEY")

    repo = SupabaseTeachingLibrary(args.url, args.key)
    cases = repo.load_cases()
    updated = 0
    for case in cases:
        date = case.get("lecture_date", "")
        code = DATE_CODES.get(date)
        if not code:
            continue
        card_path = project / f"data/{code}/cards/json/{case['card_id']}.json"
        if not card_path.exists():
            raise SystemExit(f"找不到來源卡片：{card_path}")
        card = json.loads(card_path.read_text(encoding="utf-8"))
        case.update({
            "teaching_point": card.get("key_teaching_point", ""),
            "common_pitfall": card.get("common_pitfall", ""),
            "suggested_report_phrase": card.get("improved_report_phrase", ""),
            "checklist_item_for_next_report": card.get("checklist_item_for_next_report", ""),
        })
        if args.apply:
            repo.save_case(case)
        updated += 1
        print(f"{case['record_id']} · {case['card_id']}")
    print(f"{'Updated' if args.apply else 'Validated'} {updated} cases.")


if __name__ == "__main__":
    main()

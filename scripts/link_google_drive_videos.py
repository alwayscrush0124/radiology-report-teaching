#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import toml

from portal.supabase_library import SupabaseTeachingLibrary


def preview_url(file_id: str) -> str:
    value = file_id.strip()
    if not value or "/" in value:
        raise ValueError("Google Drive file ID 格式錯誤")
    return f"https://drive.google.com/file/d/{value}/preview"


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    secrets_path = project / ".streamlit/secrets.toml"
    secrets = toml.loads(secrets_path.read_text(encoding="utf-8")) if secrets_path.exists() else {}
    parser = argparse.ArgumentParser(description="Link Google Drive teaching videos to Supabase cases.")
    parser.add_argument("--lecture-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--mapping", type=Path, required=True, help="JSON object: filename -> Drive file ID")
    parser.add_argument("--url", default=os.environ.get("SUPABASE_URL") or secrets.get("SUPABASE_URL"))
    parser.add_argument("--key", default=os.environ.get("SUPABASE_KEY") or secrets.get("SUPABASE_KEY"))
    parser.add_argument("--apply", action="store_true", help="Write changes to Supabase")
    args = parser.parse_args()
    if not args.url or not args.key:
        parser.error("請提供 SUPABASE_URL 與 SUPABASE_KEY")

    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    if not isinstance(mapping, dict):
        parser.error("mapping 必須是 filename -> Drive file ID 的 JSON object")

    repo = SupabaseTeachingLibrary(args.url, args.key)
    cases = [case for case in repo.load_cases() if case.get("lecture_date") == args.lecture_date]
    expected = {f"{case['card_id']}_teaching.mp4": case for case in cases}
    missing = sorted(set(expected) - set(mapping))
    extra = sorted(set(mapping) - set(expected))
    if missing:
        raise SystemExit(f"缺少 {len(missing)} 個影片：{', '.join(missing)}")
    if extra:
        raise SystemExit(f"mapping 有未對應檔案：{', '.join(extra)}")

    for filename, case in expected.items():
        file_id = str(mapping[filename]).strip()
        case.setdefault("assets", {})["teaching_clip"] = preview_url(file_id)
        case["drive_file_id"] = file_id
        case["storage_path"] = f"{args.lecture_date}/videos/{filename}"
        if args.apply:
            repo.save_case(case)
        print(f"{case['record_id']} -> {filename}")
    action = "Updated" if args.apply else "Validated"
    print(f"{action} {len(cases)} Google Drive video links.")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

import toml

from portal.library import TeachingLibrary
from portal.supabase_library import SupabaseTeachingLibrary


def main() -> None:
    secrets_path = Path(__file__).resolve().parents[1] / ".streamlit/secrets.toml"
    secrets = toml.loads(secrets_path.read_text(encoding="utf-8")) if secrets_path.exists() else {}
    parser = argparse.ArgumentParser(description="Import the local teaching library into Supabase.")
    parser.add_argument("--url", default=os.environ.get("SUPABASE_URL") or secrets.get("SUPABASE_URL"))
    parser.add_argument("--key", default=os.environ.get("SUPABASE_KEY") or secrets.get("SUPABASE_KEY"))
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    if not args.url or not args.key:
        parser.error("請提供 SUPABASE_URL 與 SUPABASE_KEY")

    local = TeachingLibrary(args.data_root)
    cloud = SupabaseTeachingLibrary(args.url, args.key, local.data_root)
    cases = local.load_cases()
    for position, case in enumerate(cases, 1):
        subtitle = local.read_case_text(case["card_id"], "subtitle")
        transcript = local.read_case_text(case["card_id"], "transcript")
        cloud.upsert_case(case, subtitle, transcript)
        print(f"[{position}/{len(cases)}] {case['card_id']} {case['title']}")
    print(f"Imported {len(cases)} cases to Supabase.")


if __name__ == "__main__":
    main()

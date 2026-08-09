from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from portal.library import TeachingLibrary, configured_data_root


TAXONOMY = {
    "V": "Vascular",
    "I": "Infection",
    "T": "Trauma",
    "A": "Autoimmune / Inflammation",
    "M": "Metabolic / Toxic",
    "I2": "Iatrogenic / Idiopathic",
    "N": "Neoplasm",
    "C": "Congenital",
    "D": "Degenerative",
}


class SupabaseError(RuntimeError):
    pass


class SupabaseTeachingLibrary:
    def __init__(self, url: str, key: str, data_root: Path | None = None) -> None:
        self.url = url.rstrip("/")
        self.key = key
        self.data_root = (data_root or configured_data_root()).resolve()

    @property
    def location_label(self) -> str:
        return "Supabase 雲端資料庫"

    def taxonomy(self) -> dict[str, str]:
        return dict(TAXONOMY)

    def _request(
        self,
        table: str,
        *,
        method: str = "GET",
        query: dict[str, str] | None = None,
        payload: object | None = None,
        prefer: str | None = None,
    ) -> list[dict]:
        endpoint = f"{self.url}/rest/v1/{table}"
        if query:
            endpoint += "?" + urlencode(query, safe="(),.*")
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        try:
            with urlopen(Request(endpoint, data=body, headers=headers, method=method), timeout=20) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SupabaseError(f"Supabase {exc.code}: {detail}") from exc
        except OSError as exc:
            raise SupabaseError(f"無法連線 Supabase：{exc}") from exc
        return json.loads(raw) if raw else []

    def load_cases(self) -> list[dict]:
        rows = self._request(
            "atlas_cases",
            query={"select": "card_id,metadata,updated_at", "order": "card_id.asc"},
        )
        return [self._case_from_row(row) for row in rows]

    def get_case(self, card_id: str) -> dict:
        rows = self._request(
            "atlas_cases",
            query={"select": "card_id,metadata,updated_at", "card_id": f"eq.{card_id}", "limit": "1"},
        )
        if not rows:
            raise FileNotFoundError(f"Supabase 找不到 Case：{card_id}")
        return self._case_from_row(rows[0])

    @staticmethod
    def _case_from_row(row: dict) -> dict:
        case = dict(row.get("metadata") or {})
        case.setdefault("card_id", row["card_id"])
        case["_cloud_updated_at"] = row.get("updated_at", "")
        return case

    def save_case(self, case: dict) -> None:
        clean = {key: value for key, value in case.items() if not key.startswith("_")}
        clean["updated_at"] = datetime.now(timezone.utc).isoformat()
        card_id = clean["card_id"]
        self._request(
            "atlas_cases",
            method="PATCH",
            query={"card_id": f"eq.{card_id}"},
            payload={"metadata": clean},
            prefer="return=representation",
        )

    def resolve_asset(self, relative_path: str) -> Path | str | None:
        if not relative_path:
            return None
        if relative_path.startswith(("https://", "http://")):
            return relative_path
        target = (self.data_root / relative_path).resolve()
        try:
            target.relative_to(self.data_root)
        except ValueError as exc:
            raise ValueError("素材路徑不可超出 ATLAS_DATA_ROOT") from exc
        return target if target.exists() else None

    def read_case_text(self, card_id: str, asset_name: str) -> str:
        if asset_name not in {"subtitle", "transcript"}:
            raise ValueError("只允許讀取 subtitle 或 transcript")
        rows = self._request(
            "atlas_cases",
            query={"select": asset_name, "card_id": f"eq.{card_id}", "limit": "1"},
        )
        if not rows:
            raise FileNotFoundError(f"Supabase 找不到 Case：{card_id}")
        return rows[0].get(asset_name, "")

    def save_case_text(self, card_id: str, subtitle: str, transcript: str) -> None:
        errors = TeachingLibrary.validate_srt(subtitle)
        if errors:
            raise ValueError("；".join(errors))
        self._request(
            "atlas_cases",
            method="PATCH",
            query={"card_id": f"eq.{card_id}"},
            payload={"subtitle": subtitle.strip() + "\n", "transcript": transcript.strip() + "\n"},
            prefer="return=representation",
        )
        case = self.get_case(card_id)
        case["subtitle_updated_at"] = datetime.now(timezone.utc).isoformat()
        self.save_case(case)

    def save_card_content(self, card_id: str, updates: dict[str, str]) -> None:
        allowed = {
            "title", "teaching_point", "common_pitfall",
            "suggested_report_phrase", "checklist_item_for_next_report",
            "discussion_question",
        }
        unexpected = set(updates) - allowed
        if unexpected:
            raise ValueError(f"不允許更新欄位：{', '.join(sorted(unexpected))}")
        if any(not str(value).strip() for value in updates.values()):
            raise ValueError("卡片欄位不可留白")
        case = self.get_case(card_id)
        case.update({key: str(value).strip() for key, value in updates.items()})
        case["card_content_updated_at"] = datetime.now(timezone.utc).isoformat()
        self.save_case(case)

    def dashboard(self) -> dict:
        cases = self.load_cases()
        vitamin, review = Counter(), Counter()
        total_seconds = 0.0
        for case in cases:
            total_seconds += float(case.get("duration_seconds", 0))
            review[case.get("review_status", "needs_review")] += 1
            for tag in case.get("vitamin_cd", []):
                vitamin[tag["label"]] += 1
        return {"case_count": len(cases), "total_seconds": total_seconds, "vitamin": dict(vitamin), "review": dict(review)}

    def create_teaching_set(self, name: str, card_ids: Iterable[str], description: str = "") -> Path:
        ids = list(card_ids)
        rows = self._request(
            "atlas_teaching_sets",
            method="POST",
            payload={"name": name, "description": description, "card_ids": ids},
            prefer="return=representation",
        )
        payload = rows[0] if rows else {"name": name, "description": description, "card_ids": ids}
        slug = "_".join(name.strip().split()) or "teaching_set"
        path = Path(tempfile.gettempdir()) / f"{slug}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def upsert_case(self, case: dict, subtitle: str, transcript: str) -> None:
        clean = {key: value for key, value in case.items() if not key.startswith("_")}
        self._request(
            "atlas_cases",
            method="POST",
            payload={
                "card_id": clean["card_id"],
                "metadata": clean,
                "subtitle": subtitle,
                "transcript": transcript,
            },
            prefer="resolution=merge-duplicates,return=representation",
        )


def configured_supabase_library() -> SupabaseTeachingLibrary | None:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_KEY", "").strip()
    if not url or not key:
        return None
    return SupabaseTeachingLibrary(url, key)

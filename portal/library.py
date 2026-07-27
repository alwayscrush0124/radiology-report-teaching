from __future__ import annotations

import csv
import json
import os
import tempfile
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def configured_data_root() -> Path:
    """Return the synced project root containing data/teaching_library."""
    return Path(os.environ.get("ATLAS_DATA_ROOT", PROJECT_ROOT)).expanduser().resolve()


class TeachingLibrary:
    def __init__(self, data_root: Path | None = None) -> None:
        self.data_root = (data_root or configured_data_root()).resolve()
        self.library_root = self.data_root / "data/teaching_library"
        self.cases_root = self.library_root / "cases"
        self.sets_root = self.library_root / "teaching_sets"
        if not self.cases_root.exists():
            raise FileNotFoundError(f"找不到教學資料庫：{self.cases_root}")

    def load_cases(self) -> list[dict]:
        cases = []
        for path in sorted(self.cases_root.glob("CARD*/metadata.json")):
            case = json.loads(path.read_text(encoding="utf-8"))
            case["_metadata_path"] = str(path)
            cases.append(case)
        return cases

    def get_case(self, card_id: str) -> dict:
        path = self.cases_root / card_id / "metadata.json"
        case = json.loads(path.read_text(encoding="utf-8"))
        case["_metadata_path"] = str(path)
        return case

    def resolve_asset(self, relative_path: str) -> Path | None:
        if not relative_path:
            return None
        target = (self.data_root / relative_path).resolve()
        try:
            target.relative_to(self.data_root)
        except ValueError as exc:
            raise ValueError("素材路徑不可超出 ATLAS_DATA_ROOT") from exc
        return target if target.exists() else None

    def save_case(self, case: dict) -> None:
        clean = {key: value for key, value in case.items() if not key.startswith("_")}
        clean["updated_at"] = datetime.now(timezone.utc).isoformat()
        path = self.cases_root / clean["card_id"] / "metadata.json"
        self._atomic_json(path, clean)
        self.rebuild_indexes()

    def read_case_text(self, card_id: str, asset_name: str) -> str:
        if asset_name not in {"subtitle", "transcript"}:
            raise ValueError("只允許讀取 subtitle 或 transcript")
        case = self.get_case(card_id)
        path = self.resolve_asset(case["assets"].get(asset_name, ""))
        if not path:
            raise FileNotFoundError(f"找不到 {asset_name} 檔案")
        return path.read_text(encoding="utf-8")

    def save_case_text(self, card_id: str, subtitle: str, transcript: str) -> None:
        case = self.get_case(card_id)
        subtitle_path = self.resolve_asset(case["assets"].get("subtitle", ""))
        transcript_path = self.resolve_asset(case["assets"].get("transcript", ""))
        if not subtitle_path or not transcript_path:
            raise FileNotFoundError("找不到字幕或逐字稿檔案")
        errors = self.validate_srt(subtitle)
        if errors:
            raise ValueError("；".join(errors))
        self._atomic_text(subtitle_path, subtitle.strip() + "\n")
        self._atomic_text(transcript_path, transcript.strip() + "\n")
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
        for key, value in updates.items():
            case[key] = str(value).strip()
        case["card_content_updated_at"] = datetime.now(timezone.utc).isoformat()

        card_path = self.resolve_asset(case["assets"].get("teaching_card", ""))
        if not card_path:
            raise FileNotFoundError("找不到原始 Teaching Card JSON")
        card = json.loads(card_path.read_text(encoding="utf-8"))
        field_map = {
            "title": "topic",
            "teaching_point": "key_teaching_point",
            "common_pitfall": "common_pitfall",
            "suggested_report_phrase": "improved_report_phrase",
            "checklist_item_for_next_report": "checklist_item_for_next_report",
            "discussion_question": "discussion_question",
        }
        for metadata_key, card_key in field_map.items():
            if metadata_key in updates:
                card[card_key] = str(updates[metadata_key]).strip()

        self._atomic_json(card_path, card)
        self.save_case(case)

    @staticmethod
    def validate_srt(value: str) -> list[str]:
        blocks = re.split(r"\n\s*\n", value.strip()) if value.strip() else []
        if not blocks:
            return ["字幕不可為空"]
        errors = []
        time_pattern = re.compile(r"^(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})$")

        def milliseconds(timestamp: str) -> int:
            hours, minutes, rest = timestamp.split(":")
            seconds, millis = rest.split(",")
            return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + int(millis)

        previous_end = -1
        for position, block in enumerate(blocks, 1):
            lines = [line.rstrip() for line in block.splitlines()]
            if len(lines) < 3:
                errors.append(f"第 {position} 段缺少編號、時間或文字")
                continue
            if lines[0].strip() != str(position):
                errors.append(f"第 {position} 段編號應為 {position}")
            match = time_pattern.match(lines[1].strip())
            if not match:
                errors.append(f"第 {position} 段時間格式錯誤")
                continue
            start, end = milliseconds(match.group(1)), milliseconds(match.group(2))
            if end <= start:
                errors.append(f"第 {position} 段結束時間必須晚於開始時間")
            if start < previous_end:
                errors.append(f"第 {position} 段與前一段時間重疊")
            previous_end = end
        return errors

    def rebuild_indexes(self) -> None:
        cases = self.load_cases()
        clean_cases = [{key: value for key, value in case.items() if not key.startswith("_")} for case in cases]
        self._atomic_json(self.library_root / "cases_index.json", clean_cases)

        fields = ["clip_id", "card_id", "title", "vitamin_cd", "anatomy", "modality", "sequences", "teaching_type", "duration_seconds", "teaching_clip", "subtitle", "review_status"]
        csv_path = self.library_root / "cases_index.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8-sig", dir=csv_path.parent, delete=False) as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for item in clean_cases:
                writer.writerow({
                    "clip_id": item["clip_id"], "card_id": item["card_id"], "title": item["title"],
                    "vitamin_cd": "|".join(tag["code"] for tag in item["vitamin_cd"]),
                    "anatomy": "|".join(item["anatomy"]), "modality": "|".join(item["modality"]),
                    "sequences": "|".join(item["sequences"]), "teaching_type": item["teaching_type"],
                    "duration_seconds": item["duration_seconds"], "teaching_clip": item["assets"]["teaching_clip"],
                    "subtitle": item["assets"]["subtitle"], "review_status": item["review_status"],
                })
            temp_name = handle.name
        Path(temp_name).replace(csv_path)
        self._rebuild_views(clean_cases)

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
        selected = [self.get_case(card_id) for card_id in card_ids]
        payload = {
            "schema_version": "1.0", "name": name, "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cases": [{"card_id": case["card_id"], "title": case["title"], "metadata": f"data/teaching_library/cases/{case['card_id']}/metadata.json"} for case in selected],
        }
        self.sets_root.mkdir(parents=True, exist_ok=True)
        slug = "_".join(name.strip().split()) or "teaching_set"
        path = self.sets_root / f"{slug}.json"
        self._atomic_json(path, payload)
        return path

    def _rebuild_views(self, cases: list[dict]) -> None:
        taxonomy = json.loads((self.library_root / "taxonomy.json").read_text(encoding="utf-8"))
        views_root = self.library_root / "views"
        views_root.mkdir(exist_ok=True)
        for code, label in taxonomy.items():
            members = [{"card_id": case["card_id"], "clip_id": case["clip_id"], "title": case["title"], "metadata": f"data/teaching_library/cases/{case['card_id']}/metadata.json"} for case in cases if code in {tag["code"] for tag in case["vitamin_cd"]}]
            safe_label = "_".join(label.lower().replace("/", " ").split())
            self._atomic_json(views_root / f"{code}_{safe_label}.json", {"code": code, "label": label, "case_count": len(members), "cases": members})

    @staticmethod
    def _atomic_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temp_name = handle.name
        Path(temp_name).replace(path)

    @staticmethod
    def _atomic_text(path: Path, value: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            handle.write(value)
            temp_name = handle.name
        Path(temp_name).replace(path)

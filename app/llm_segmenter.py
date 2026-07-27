"""Manual-first LLM segmentation with transcript-grounded boundaries."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import HUMAN_COMPLETION
from .segment_detector import KEYWORDS_BY_TYPE, TeachingSegment
from .transcript_parser import TranscriptEntry


SCHEMA_VERSION = "1.0"
VALID_MOMENT_TYPES = set(KEYWORDS_BY_TYPE)
VALID_IMAGE_DEPENDENCIES = {"low", "moderate", "high"}
VALID_SUGGESTED_ASSETS = {"none", "key_screenshot", "scroll_clip", "both"}
LINE_ID_RE = re.compile(r"^L(?P<number>\d+)$", flags=re.IGNORECASE)


class LLMResponseValidationError(ValueError):
    """Raised when an LLM response cannot be safely mapped to a transcript."""


@dataclass(frozen=True)
class LLMTeachingMoment:
    start_line: int
    end_line: int
    topic: str
    teaching_moment_type: str
    summary: str
    resident_report_problem: str
    teacher_feedback: str
    key_teaching_point: str
    improved_report_phrase: str
    common_pitfall: str
    discussion_question: str
    checklist_item_for_next_report: str
    image_dependency: str
    suggested_asset: str
    confidence: float

    def to_segment(self, entries: list[TranscriptEntry], segment_id: str) -> TeachingSegment:
        selected = entries[self.start_line - 1 : self.end_line]
        first = selected[0]
        last = selected[-1]
        evidence_text = " ".join(entry.text.strip() for entry in selected if entry.text.strip())
        return TeachingSegment(
            segment_id=segment_id,
            start_time=first.start_time,
            end_time=last.end_time or last.start_time,
            teaching_moment_type=self.teaching_moment_type,
            evidence_text=evidence_text,
            confidence=self.confidence,
            image_dependency=self.image_dependency,
            suggested_asset=self.suggested_asset,
        )


@dataclass(frozen=True)
class LLMAnalysis:
    lecture_summary: str
    teaching_moments: list[LLMTeachingMoment]
    schema_version: str = SCHEMA_VERSION

    def to_segments(self, entries: list[TranscriptEntry]) -> list[TeachingSegment]:
        return [
            moment.to_segment(entries, segment_id=f"SEG{index + 1:03d}")
            for index, moment in enumerate(self.teaching_moments)
        ]


def format_transcript_for_llm(entries: list[TranscriptEntry]) -> str:
    """Format transcript cues with stable line IDs that the LLM must cite."""
    lines: list[str] = []
    for index, entry in enumerate(entries, start=1):
        start = entry.start_time or "not mentioned"
        end = entry.end_time or "not mentioned"
        lines.append(f"[L{index:03d}][{start} --> {end}] {entry.text.strip()}")
    return "\n".join(lines)


def build_manual_prompt(entries: list[TranscriptEntry], transcript_name: str) -> str:
    """Build a two-pass analysis prompt for use in a web-based LLM chat."""
    moment_types = ", ".join(sorted(VALID_MOMENT_TYPES))
    transcript = format_transcript_for_llm(entries)
    return f"""# Radiology Report Teaching Atlas: LLM segmentation job

你是一位放射科醫學教育內容整理助理。請閱讀完整逐字稿，先理解內容，再決定教學事件的切點。

## 任務

請在內部依序完成兩個階段：

1. 理解整段對話的病例脈絡、老師糾正的報告問題，以及可重複使用的教學原則。
2. 將屬於同一主題的連續討論合併成一個完整教學事件，輸出開始與結束行號。

不要因為單獨出現一個醫學名詞就建立卡片。排除閒聊、軟體操作、沒有教學結論的重複語句，以及逐字稿辨識錯誤。若同一個教學觀念跨越數行，切點應涵蓋問題、推理與結論。

## 邊界規則

- `start_line` 與 `end_line` 必須引用下方既有行號，例如 `L003`，不得自行創造時間。
- `start_line` 應涵蓋理解教學問題所需的前文。
- `end_line` 應包含老師的結論、建議報告句或最後一項判讀依據。
- 重疊或高度相關的事件應合併，避免為同一觀念產生多張卡。
- 每個重要欄位都必須以逐字稿內容為依據；資訊不足時填 `needs human completion`。
- 不得新增逐字稿沒有提到的診斷或病人資訊。

## 可用分類

`teaching_moment_type` 只能是：{moment_types}

`image_dependency` 只能是：`low`, `moderate`, `high`

`suggested_asset` 只能是：`none`, `key_screenshot`, `scroll_clip`, `both`

## 輸出格式

只輸出 JSON，不要加 Markdown code fence 或額外說明：

{{
  "schema_version": "{SCHEMA_VERSION}",
  "lecture_summary": "整段內容的簡短摘要",
  "teaching_moments": [
    {{
      "start_line": "L001",
      "end_line": "L008",
      "topic": "教學事件標題",
      "teaching_moment_type": "diagnostic_reasoning_discussion",
      "summary": "這段對話發生了什麼",
      "resident_report_problem": "原報告或判讀的問題",
      "teacher_feedback": "老師提供的回饋",
      "key_teaching_point": "可重複使用的教學原則",
      "improved_report_phrase": "逐字稿足以支持時提供建議報告句，否則填 needs human completion",
      "common_pitfall": "常見陷阱",
      "discussion_question": "可用於教學討論的問題",
      "checklist_item_for_next_report": "下次報告前可執行的檢查項目",
      "image_dependency": "high",
      "suggested_asset": "scroll_clip",
      "confidence": 0.85
    }}
  ]
}}

## 來源

Transcript: {transcript_name}

## 有行號的逐字稿

{transcript}
"""


def write_manual_job(
    entries: list[TranscriptEntry], transcript_name: str, output_dir: str | Path
) -> tuple[Path, Path]:
    """Write a manual LLM request and an empty response template."""
    job_dir = Path(output_dir)
    job_dir.mkdir(parents=True, exist_ok=True)
    request_path = job_dir / "llm_request.md"
    response_path = job_dir / "llm_response.template.json"
    request_path.write_text(build_manual_prompt(entries, transcript_name), encoding="utf-8")
    response_path.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "lecture_summary": "",
                "teaching_moments": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return request_path, response_path


def load_llm_analysis(path: str | Path, entries: list[TranscriptEntry]) -> LLMAnalysis:
    """Load and validate an LLM response against the source transcript."""
    response_path = Path(path)
    raw_text = response_path.read_text(encoding="utf-8-sig").strip()
    payload = _parse_json_payload(raw_text)
    return parse_llm_analysis(payload, entries)


def parse_llm_analysis(payload: dict[str, Any], entries: list[TranscriptEntry]) -> LLMAnalysis:
    """Validate a decoded LLM response and map its line references."""
    if not entries:
        raise LLMResponseValidationError("The source transcript is empty.")
    if not isinstance(payload, dict):
        raise LLMResponseValidationError("LLM response must be a JSON object.")

    version = str(payload.get("schema_version", ""))
    if version != SCHEMA_VERSION:
        raise LLMResponseValidationError(
            f"Unsupported schema_version {version!r}; expected {SCHEMA_VERSION!r}."
        )

    raw_moments = payload.get("teaching_moments")
    if not isinstance(raw_moments, list):
        raise LLMResponseValidationError("teaching_moments must be a JSON array.")

    moments = [
        _parse_moment(raw_moment, entries, index)
        for index, raw_moment in enumerate(raw_moments, start=1)
    ]
    moments.sort(key=lambda moment: (moment.start_line, moment.end_line))
    return LLMAnalysis(
        schema_version=version,
        lecture_summary=_text(payload.get("lecture_summary"), HUMAN_COMPLETION),
        teaching_moments=moments,
    )


def _parse_json_payload(raw_text: str) -> dict[str, Any]:
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"\s*```$", "", raw_text)
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMResponseValidationError(f"Invalid JSON response: {exc}") from exc
    if not isinstance(payload, dict):
        raise LLMResponseValidationError("LLM response must be a JSON object.")
    return payload


def _parse_moment(
    raw_moment: Any, entries: list[TranscriptEntry], position: int
) -> LLMTeachingMoment:
    if not isinstance(raw_moment, dict):
        raise LLMResponseValidationError(f"Teaching moment {position} must be a JSON object.")

    start_line = _line_number(raw_moment.get("start_line"), "start_line", position)
    end_line = _line_number(raw_moment.get("end_line"), "end_line", position)
    if start_line > end_line:
        raise LLMResponseValidationError(
            f"Teaching moment {position} has start_line after end_line."
        )
    if end_line > len(entries):
        raise LLMResponseValidationError(
            f"Teaching moment {position} references L{end_line:03d}, but the transcript has "
            f"only {len(entries)} lines."
        )

    moment_type = _text(raw_moment.get("teaching_moment_type"), "")
    if moment_type not in VALID_MOMENT_TYPES:
        raise LLMResponseValidationError(
            f"Teaching moment {position} has invalid teaching_moment_type {moment_type!r}."
        )

    image_dependency = _text(raw_moment.get("image_dependency"), "moderate")
    if image_dependency not in VALID_IMAGE_DEPENDENCIES:
        raise LLMResponseValidationError(
            f"Teaching moment {position} has invalid image_dependency {image_dependency!r}."
        )

    suggested_asset = _text(raw_moment.get("suggested_asset"), "none")
    if suggested_asset not in VALID_SUGGESTED_ASSETS:
        raise LLMResponseValidationError(
            f"Teaching moment {position} has invalid suggested_asset {suggested_asset!r}."
        )

    confidence = raw_moment.get("confidence", 0.75)
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise LLMResponseValidationError(
            f"Teaching moment {position} confidence must be a number between 0 and 1."
        )
    confidence = float(confidence)
    if not 0 <= confidence <= 1:
        raise LLMResponseValidationError(
            f"Teaching moment {position} confidence must be between 0 and 1."
        )

    return LLMTeachingMoment(
        start_line=start_line,
        end_line=end_line,
        topic=_text(raw_moment.get("topic"), HUMAN_COMPLETION),
        teaching_moment_type=moment_type,
        summary=_text(raw_moment.get("summary"), HUMAN_COMPLETION),
        resident_report_problem=_text(raw_moment.get("resident_report_problem"), HUMAN_COMPLETION),
        teacher_feedback=_text(raw_moment.get("teacher_feedback"), HUMAN_COMPLETION),
        key_teaching_point=_text(raw_moment.get("key_teaching_point"), HUMAN_COMPLETION),
        improved_report_phrase=_text(raw_moment.get("improved_report_phrase"), HUMAN_COMPLETION),
        common_pitfall=_text(raw_moment.get("common_pitfall"), HUMAN_COMPLETION),
        discussion_question=_text(raw_moment.get("discussion_question"), HUMAN_COMPLETION),
        checklist_item_for_next_report=_text(
            raw_moment.get("checklist_item_for_next_report"), HUMAN_COMPLETION
        ),
        image_dependency=image_dependency,
        suggested_asset=suggested_asset,
        confidence=round(confidence, 2),
    )


def _line_number(value: Any, field_name: str, position: int) -> int:
    if isinstance(value, bool):
        value = None
    if isinstance(value, int):
        number = value
    elif isinstance(value, str):
        match = LINE_ID_RE.fullmatch(value.strip())
        number = int(match.group("number")) if match else -1
    else:
        number = -1
    if number < 1:
        raise LLMResponseValidationError(
            f"Teaching moment {position} {field_name} must look like L001."
        )
    return number


def _text(value: Any, default: str) -> str:
    if not isinstance(value, str):
        return default
    clean = value.strip()
    return clean or default

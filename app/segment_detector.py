"""Rule-based teaching moment detection."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .config import DEFAULT_BUFFER_SECONDS
from .transcript_parser import TranscriptEntry, seconds_to_time


KEYWORDS_BY_TYPE: dict[str, list[str]] = {
    "report_wording_correction": [
        "你這裡",
        "這個要寫",
        "這個不能只放",
        "這樣臨床會不知道",
        "title都要正確",
        "title",
        "template",
        "describe",
        "敘述",
        "should mention",
        "should include",
        "not enough",
        "too vague",
        "wording",
        "phrase",
    ],
    "diagnostic_reasoning_discussion": [
        "為什麼",
        "診斷",
        "鑑別",
        "enhancement",
        "inhancement",
        "density",
        "mass effect",
        "midnight shift",
        "midline shift",
        "herniation",
        "subduro",
        "subdural",
        "hematoma",
        "undercall",
        "overcall",
        "correlate with",
        "diagnosis",
        "differential",
        "reasoning",
    ],
    "impression_refinement": [
        "impression",
        "findings",
        "這個不能只放",
        "整合",
        "summary",
        "summarize",
    ],
    "clinical_question_alignment": [
        "clinical question",
        "臨床問題",
        "回答",
        "addressed",
        "這樣臨床會不知道",
    ],
    "confidence_calibration": [
        "語氣太弱",
        "太保守",
        "太肯定",
        "confidence",
        "too vague",
        "undercall",
        "overcall",
    ],
    "missed_comparison": [
        "要比較前片",
        "跟前片比",
        "前片",
        "上次比",
        "上一次比",
        "上上次",
        "跟它上次",
        "compare with prior",
        "prior",
        "comparison",
    ],
    "safety_or_critical_finding_communication": [
        "critical finding",
        "需要通知",
        "notify",
        "communication",
        "urgent",
    ],
    "image_evidence_discussion": [
        "你看這裡",
        "往上滾",
        "往下滾",
        "這張",
        "對照",
        "dwi",
        "adc",
        "ct",
        "mri",
        "brain ct",
        "bone window",
        "chrono view",
        "coronal",
        "look here",
        "scroll up",
        "scroll down",
        "axial",
        "coronal",
        "sagittal",
    ],
}

IMAGE_HIGH_KEYWORDS = [
    "你看這裡",
    "往上滾",
    "往下滾",
    "這張",
    "對照",
    "dwi",
    "adc",
    "look here",
    "scroll up",
    "scroll down",
    "axial",
    "coronal",
    "sagittal",
]
SCROLL_KEYWORDS = ["往上滾", "往下滾", "scroll up", "scroll down"]
SCREENSHOT_KEYWORDS = ["你看這裡", "這張", "對照", "look here", "dwi", "adc", "axial", "coronal", "sagittal"]
LOW_IMAGE_TYPES = {"report_wording_correction", "impression_refinement", "clinical_question_alignment"}
MODERATE_IMAGE_TYPES = {"diagnostic_reasoning_discussion", "confidence_calibration", "missed_comparison"}


@dataclass(frozen=True)
class TeachingSegment:
    segment_id: str
    start_time: str | None
    end_time: str | None
    teaching_moment_type: str
    evidence_text: str
    confidence: float
    image_dependency: str
    suggested_asset: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def detect_teaching_segments(
    entries: list[TranscriptEntry], buffer_seconds: int = DEFAULT_BUFFER_SECONDS
) -> list[TeachingSegment]:
    """Detect likely teaching moments using transparent keyword rules."""
    segments: list[TeachingSegment] = []
    last_timed_match_end: float | None = None

    for entry in entries:
        text = entry.text.strip()
        if not text:
            continue
        text_lower = text.lower()
        scores = _score_text(text_lower)
        if not scores:
            continue

        best_type, best_score = sorted(scores.items(), key=lambda item: item[1], reverse=True)[0]
        start_seconds = entry.start_seconds
        end_seconds = entry.end_seconds if entry.end_seconds is not None else entry.start_seconds

        if (
            start_seconds is not None
            and last_timed_match_end is not None
            and start_seconds <= last_timed_match_end + 3
            and segments
        ):
            previous = segments[-1]
            merged_end = seconds_to_time((end_seconds or start_seconds) + buffer_seconds)
            merged_text = f"{previous.evidence_text} {text}"
            segments[-1] = TeachingSegment(
                segment_id=previous.segment_id,
                start_time=previous.start_time,
                end_time=merged_end,
                teaching_moment_type=previous.teaching_moment_type,
                evidence_text=merged_text,
                confidence=max(previous.confidence, _confidence(best_score)),
                image_dependency=_stronger_image_dependency(
                    previous.image_dependency,
                    _image_dependency(text_lower, best_type),
                ),
                suggested_asset=_combine_assets(
                    previous.suggested_asset,
                    _suggested_asset(text_lower, _image_dependency(text_lower, best_type)),
                ),
            )
            last_timed_match_end = end_seconds
            continue

        start_time = seconds_to_time(start_seconds - buffer_seconds) if start_seconds is not None else None
        end_time = seconds_to_time((end_seconds or start_seconds) + buffer_seconds) if end_seconds is not None else None
        image_dependency = _image_dependency(text_lower, best_type)

        segments.append(
            TeachingSegment(
                segment_id=f"SEG{len(segments) + 1:03d}",
                start_time=start_time,
                end_time=end_time,
                teaching_moment_type=best_type,
                evidence_text=text,
                confidence=_confidence(best_score),
                image_dependency=image_dependency,
                suggested_asset=_suggested_asset(text_lower, image_dependency),
            )
        )
        if end_seconds is not None:
            last_timed_match_end = end_seconds

    return [_with_context_text(segment, entries) for segment in segments]


def _score_text(text_lower: str) -> dict[str, int]:
    scores: dict[str, int] = {}
    for moment_type, keywords in KEYWORDS_BY_TYPE.items():
        hits = sum(1 for keyword in keywords if keyword.lower() in text_lower)
        if hits:
            scores[moment_type] = hits
    return scores


def _confidence(score: int) -> float:
    return round(min(0.95, 0.55 + score * 0.12), 2)


def _image_dependency(text_lower: str, moment_type: str) -> str:
    if any(keyword in text_lower for keyword in IMAGE_HIGH_KEYWORDS):
        return "high"
    if moment_type in LOW_IMAGE_TYPES:
        return "low"
    if moment_type in MODERATE_IMAGE_TYPES:
        return "moderate"
    return "moderate"


def _suggested_asset(text_lower: str, image_dependency: str) -> str:
    wants_clip = any(keyword in text_lower for keyword in SCROLL_KEYWORDS)
    wants_screenshot = any(keyword in text_lower for keyword in SCREENSHOT_KEYWORDS)
    if wants_clip and wants_screenshot:
        return "both"
    if wants_clip:
        return "scroll_clip"
    if wants_screenshot or image_dependency == "high":
        return "key_screenshot"
    return "none"


def _stronger_image_dependency(left: str, right: str) -> str:
    rank = {"low": 0, "moderate": 1, "high": 2}
    return left if rank[left] >= rank[right] else right


def _combine_assets(left: str, right: str) -> str:
    if left == right:
        return left
    if "both" in {left, right}:
        return "both"
    if {left, right} == {"key_screenshot", "scroll_clip"}:
        return "both"
    return right if left == "none" else left


def _with_context_text(segment: TeachingSegment, entries: list[TranscriptEntry]) -> TeachingSegment:
    """Replace a one-line keyword hit with the full transcript context inside the buffered segment."""
    if not segment.start_time or not segment.end_time:
        return segment

    from .transcript_parser import time_to_seconds

    start_seconds = time_to_seconds(segment.start_time)
    end_seconds = time_to_seconds(segment.end_time)
    if start_seconds is None or end_seconds is None:
        return segment

    context_lines: list[str] = []
    for entry in entries:
        entry_start = entry.start_seconds
        entry_end = entry.end_seconds if entry.end_seconds is not None else entry.start_seconds
        if entry_start is None or entry_end is None:
            continue
        if entry_end < start_seconds or entry_start > end_seconds:
            continue
        context_lines.append(entry.text.strip())

    if not context_lines:
        return segment

    return TeachingSegment(
        segment_id=segment.segment_id,
        start_time=segment.start_time,
        end_time=segment.end_time,
        teaching_moment_type=segment.teaching_moment_type,
        evidence_text=" ".join(context_lines),
        confidence=segment.confidence,
        image_dependency=segment.image_dependency,
        suggested_asset=segment.suggested_asset,
    )

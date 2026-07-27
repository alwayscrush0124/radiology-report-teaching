"""Teaching card data model and renderers."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import HUMAN_COMPLETION, NOT_MENTIONED
from .segment_detector import TeachingSegment


REPORT_ISSUE_BY_MOMENT = {
    "report_wording_correction": ["report_wording_issue"],
    "diagnostic_reasoning_discussion": ["misinterpretation"],
    "impression_refinement": ["impression_mismatch"],
    "clinical_question_alignment": ["clinical_question_not_addressed"],
    "confidence_calibration": ["under_calling"],
    "missed_comparison": ["missing_comparison"],
    "safety_or_critical_finding_communication": ["critical_finding_communication"],
    "image_evidence_discussion": ["other"],
}


@dataclass
class OptionalImageEvidence:
    key_screenshot: str = ""
    scroll_clip: str = ""
    best_pause_time: str = ""
    series_or_image_number: str = NOT_MENTIONED
    notes: str = ""


@dataclass
class HumanReview:
    status: str = "needs_review"
    reviewer: str = ""
    review_notes: str = ""


@dataclass
class TeachingCard:
    card_id: str
    case_id: str
    source_video: str
    source_transcript: str
    timestamp_range: str
    teaching_moment_type: str
    image_dependency: str
    report_issue_type: list[str]
    what_happened_in_conversation: str
    topic: str = HUMAN_COMPLETION
    resident_report_problem: str = HUMAN_COMPLETION
    teacher_feedback: str = HUMAN_COMPLETION
    key_teaching_point: str = HUMAN_COMPLETION
    improved_report_phrase: str = HUMAN_COMPLETION
    common_pitfall: str = HUMAN_COMPLETION
    discussion_question: str = HUMAN_COMPLETION
    checklist_item_for_next_report: str = HUMAN_COMPLETION
    optional_image_evidence: OptionalImageEvidence = field(default_factory=OptionalImageEvidence)
    human_review: HumanReview = field(default_factory=HumanReview)
    suggested_asset: str = "none"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_markdown(self) -> str:
        issue_text = ", ".join(self.report_issue_type) if self.report_issue_type else "other"
        image = self.optional_image_evidence
        review = self.human_review
        return "\n".join(
            [
                f"# Report Teaching Card: {self.card_id}",
                "",
                "## Source",
                f"- Case ID: {self.case_id}",
                f"- Source video: {self.source_video}",
                f"- Source transcript: {self.source_transcript}",
                f"- Timestamp: {self.timestamp_range}",
                "",
                "## Teaching Moment",
                f"- Type: {self.teaching_moment_type}",
                f"- Image dependency: {self.image_dependency}",
                f"- Suggested asset: {self.suggested_asset}",
                "",
                "## Topic",
                self.topic,
                "",
                "## Conversation Summary",
                self.what_happened_in_conversation,
                "",
                "## Report Issue",
                issue_text,
                "",
                "## Resident Report Problem",
                self.resident_report_problem,
                "",
                "## Teaching Point",
                self.key_teaching_point,
                "",
                "## Teacher Feedback",
                self.teacher_feedback,
                "",
                "## Improved Report Phrase",
                self.improved_report_phrase,
                "",
                "## Common Pitfall",
                self.common_pitfall,
                "",
                "## Discussion Question",
                self.discussion_question,
                "",
                "## Checklist Item For Next Report",
                self.checklist_item_for_next_report,
                "",
                "## Optional Image Evidence",
                f"- Screenshot: {image.key_screenshot}",
                f"- Scroll clip: {image.scroll_clip}",
                f"- Best pause time: {image.best_pause_time}",
                f"- Series or image number: {image.series_or_image_number}",
                f"- Notes: {image.notes}",
                "",
                "## Human Review",
                f"- Status: {review.status}",
                f"- Reviewer: {review.reviewer}",
                f"- Notes: {review.review_notes}",
                "",
            ]
        )

    def write_markdown(self, output_dir: str | Path) -> Path:
        output_path = Path(output_dir) / f"{self.card_id}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.to_markdown(), encoding="utf-8")
        return output_path

    def write_json(self, output_dir: str | Path) -> Path:
        output_path = Path(output_dir) / f"{self.card_id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.to_json(), encoding="utf-8")
        return output_path


def card_from_segment(
    segment: TeachingSegment,
    card_id: str,
    case_id: str,
    source_transcript: str,
    source_video: str = "",
    *,
    topic: str | None = None,
    conversation_summary: str | None = None,
    resident_report_problem: str | None = None,
    teacher_feedback: str | None = None,
    key_teaching_point: str | None = None,
    improved_report_phrase: str | None = None,
    common_pitfall: str | None = None,
    discussion_question: str | None = None,
    checklist_item_for_next_report: str | None = None,
    generation_method: str = "rules",
) -> TeachingCard:
    """Create a human-reviewable teaching card from a detected segment."""
    timestamp_range = _timestamp_range(segment.start_time, segment.end_time)
    best_pause_time = _best_pause_time(segment.start_time, segment.end_time)
    rule_key_teaching_point = _extract_key_teaching_point(
        segment.evidence_text, segment.teaching_moment_type
    )
    rule_teacher_feedback = _extract_teacher_feedback(segment.evidence_text)
    rule_improved_report_phrase = _extract_improved_report_phrase(segment.evidence_text)
    rule_checklist_item = _build_checklist_item(segment.evidence_text, segment.teaching_moment_type)
    note_source = "LLM-assisted transcript analysis" if generation_method == "llm" else "rule-based conversation anchor"
    return TeachingCard(
        card_id=card_id,
        case_id=case_id,
        source_video=source_video,
        source_transcript=source_transcript,
        timestamp_range=timestamp_range,
        teaching_moment_type=segment.teaching_moment_type,
        image_dependency=segment.image_dependency,
        report_issue_type=REPORT_ISSUE_BY_MOMENT.get(segment.teaching_moment_type, ["other"]),
        what_happened_in_conversation=conversation_summary or segment.evidence_text,
        topic=topic or segment.teaching_moment_type,
        resident_report_problem=resident_report_problem or HUMAN_COMPLETION,
        teacher_feedback=teacher_feedback or rule_teacher_feedback,
        key_teaching_point=key_teaching_point or rule_key_teaching_point,
        improved_report_phrase=improved_report_phrase or rule_improved_report_phrase,
        common_pitfall=common_pitfall or HUMAN_COMPLETION,
        discussion_question=discussion_question or HUMAN_COMPLETION,
        checklist_item_for_next_report=checklist_item_for_next_report or rule_checklist_item,
        optional_image_evidence=OptionalImageEvidence(
            best_pause_time=best_pause_time or "",
            notes=f"Auto-created from {note_source}; teacher review required.",
        ),
        suggested_asset=segment.suggested_asset,
    )


def _timestamp_range(start_time: str | None, end_time: str | None) -> str:
    if start_time and end_time:
        return f"{start_time}-{end_time}"
    if start_time:
        return f"{start_time}-not mentioned"
    return "not mentioned"


def _best_pause_time(start_time: str | None, end_time: str | None) -> str | None:
    if not start_time or not end_time:
        return None
    from .transcript_parser import time_to_seconds, seconds_to_time

    start_seconds = time_to_seconds(start_time)
    end_seconds = time_to_seconds(end_time)
    if start_seconds is None or end_seconds is None:
        return None
    return seconds_to_time((start_seconds + end_seconds) / 2)


def _extract_key_teaching_point(text: str, moment_type: str) -> str:
    normalized = _normalize_text(text)
    lower = normalized.lower()
    if "hematoma" in lower and ("size" in lower or "量" in normalized):
        return "報告中應描述 hematoma 的新舊變化、位置與大小量測，並交代周邊 edema 或術後相關變化。"
    if ("enhancement" in lower or "inhancement" in lower) and ("pre-post" in lower or "打藥" in normalized):
        return "Brain CT pre/post 判讀時，要區分打藥前本來就高密度的鈣化或血管結構，額外 enhancement 才需要描述。"
    if "bone window" in lower or "meta stasis" in lower or "metastasis" in lower:
        return "Brain CT 若臨床問題包含 metastasis，除了軟組織窗，也要用 bone window 檢查骨轉移。"
    if "subduro" in lower or "subdural" in lower:
        return "Subdural collection 報告應與前次影像比較，描述 density、size/thickness 變化，並交代 midline shift 或 herniation。"
    if "title" in lower and ("pre-post" in lower or "post" in lower):
        return "報告 title/protocol 要符合實際檢查內容；預期 pre-post 但實際只有 post 時，標題不能照 template 誤寫。"
    if "residual" in lower or "residual tumor" in lower:
        return "術後影像若仍可見疑似 residual tumor，報告應明確描述殘餘位置與影像依據。"
    if "extracerebral" in lower or "epidural" in lower or "subduro" in lower:
        return "術後腦外血液若 epidural/subdural 不易區分，可用 extracerebral blood 描述並交代其術後脈絡。"
    if "clinical question" in lower or "臨床問題" in normalized:
        return "Impression 應整合 findings 並回答 clinical question，而不是只複製影像描述。"

    cues = [
        r"所以我們現在敘述(?P<point>.+?)(?:。|$)",
        r"所以你就敘述說(?P<point>.+?)(?:。|$)",
        r"變成說我們在報告裡面(?P<point>.+?)(?:。|$)",
        r"我們就敘述一下(?P<point>.+?)(?:。|$)",
        r"這個我們也要敘述(?P<point>.+?)(?:。|$)",
        r"這個要寫(?P<point>.+?)(?:。|$)",
        r"要比較前片(?P<point>.+?)(?:。|$)",
        r"should mention(?P<point>.+?)(?:\.|$)",
        r"should include(?P<point>.+?)(?:\.|$)",
    ]
    extracted = _first_regex_group(normalized, cues)
    if extracted:
        return _compact_sentence(extracted)

    if moment_type == "image_evidence_discussion":
        return "這段主要是影像證據定位與報告描述的連結，建議教師 review 時選定 key image 或 scroll clip。"
    if moment_type == "diagnostic_reasoning_discussion":
        return "這段包含診斷推理討論，建議教師 review 時補上判斷依據與常見陷阱。"
    return HUMAN_COMPLETION


def _extract_teacher_feedback(text: str) -> str:
    normalized = _normalize_text(text)
    feedback_cues = [
        r"(所以你就敘述說.+?)(?:。|$)",
        r"(我們就敘述一下.+?)(?:。|$)",
        r"(這個我們也要敘述.+?)(?:。|$)",
        r"(你就講它是.+?)(?:。|$)",
        r"(should mention.+?)(?:\.|$)",
        r"(should include.+?)(?:\.|$)",
    ]
    extracted = _first_regex_group(normalized, feedback_cues, group_index=1)
    return _compact_sentence(extracted) if extracted else HUMAN_COMPLETION


def _extract_improved_report_phrase(text: str) -> str:
    normalized = _normalize_text(text)
    phrase_cues = [
        r"你就敘述說(?P<phrase>.+?)(?:。|$)",
        r"你就講它是(?P<phrase>.+?)(?:。|$)",
        r"可以講(?P<phrase>.+?)(?:。|$)",
        r"寫(?P<phrase>.+?)(?:。|$)",
    ]
    extracted = _first_regex_group(normalized, phrase_cues)
    return _compact_sentence(extracted) if extracted else HUMAN_COMPLETION


def _build_checklist_item(text: str, moment_type: str) -> str:
    lower = text.lower()
    if "hematoma" in lower:
        return "遇到 hematoma 時，確認報告有交代新舊變化、位置、大小與周邊 edema/mass effect。"
    if "enhancement" in lower or "inhancement" in lower:
        return "Brain CT pre/post 報告前，確認 enhancement 是否為打藥後新增，而非原本鈣化或正常血管/腺體。"
    if "bone window" in lower or "meta stasis" in lower or "metastasis" in lower:
        return "有 metastasis 評估需求時，確認已查看 bone window 並記錄是否有骨轉移。"
    if "subduro" in lower or "subdural" in lower:
        return "Subdural collection 報告前，確認已比較前次影像，並描述 density、thickness、mass effect/midline shift。"
    if "title" in lower:
        return "送出報告前確認 title/protocol 與實際掃描內容一致。"
    if "residual" in lower or "tumor" in lower:
        return "術後腫瘤追蹤報告中，確認是否描述 residual tumor 的位置、範圍與比較基準。"
    if "prior" in lower or "前片" in text:
        return "完成報告前確認是否需要與前片比較，並在 impression 中交代變化。"
    if "critical" in lower or "通知" in text:
        return "遇到 critical finding 時，確認報告與臨床溝通紀錄都有清楚記載。"
    if moment_type == "image_evidence_discussion":
        return "選定支持報告描述的 key image 或 scroll clip，避免只有文字描述而缺少影像證據。"
    return HUMAN_COMPLETION


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _first_regex_group(pattern_text: str, patterns: list[str], group_index: int | None = None) -> str:
    for pattern in patterns:
        match = re.search(pattern, pattern_text, flags=re.IGNORECASE)
        if not match:
            continue
        if group_index is not None:
            return match.group(group_index).strip()
        groupdict = match.groupdict()
        if "point" in groupdict:
            return groupdict["point"].strip()
        if "phrase" in groupdict:
            return groupdict["phrase"].strip()
        return match.group(1).strip()
    return ""


def _compact_sentence(text: str, max_chars: int = 180) -> str:
    clean = _normalize_text(text).strip(" ，,。.")
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 1].rstrip() + "..."

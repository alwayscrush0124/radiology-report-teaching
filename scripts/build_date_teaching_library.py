#!/usr/bin/env python3
"""Build an importable teaching library for one dated lecture package."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.transcript_parser import parse_transcript, time_to_seconds


PROJECT = Path(__file__).resolve().parents[1]
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
VITAMIN_RULES = {
    "V": ["stroke", "infarct", "embol", "thromb", "moyamoya", "aneurysm", "avm", "hemorrhage", "hematoma", "ich", "microbleed", "small vessel", "vascular", "pres", "caa", "cadasil"],
    "I": ["infection", "fungal", "hiv", "pml", "tb ", "tuberculosis"],
    "T": ["trauma", "traumatic", "axonal injury", "fat embolism", "sdh", "subdural"],
    "A": ["autoimmune", "inflammation", "inflammatory", "iris", "adem", "mog", "clippers", "gfap", "encephalitis"],
    "M": ["metabolic", "toxic", "hypoglyc", "hyperglyc", "uremic", "cpm", "methotrexate"],
    "I2": ["postoperative", "post-op", "術後", "放療", "radiation", "treatment", "iatrogenic", "idiopathic", "nph", "fahr"],
    "N": ["tumor", "mass", "cancer", "carcinoma", "lymphoma", "metast", "glioma", "adenoma", "meningioma", "schwannoma", "hemangioblastoma", "dnet", "chordoma", "neoplasm", "npc", "腫瘤"],
    "C": ["congenital", "moyamoya", "dural ectasia", "meningocele", "perineural cyst", "fibrous dysplasia"],
    "D": ["dementia", "atrophy", "degenerative", "parkinson", "psp", "amyloid", "mta", "alzheimer"],
}
ANATOMY_RULES = {
    "brain": ["brain", "cerebral", "intracranial", "stroke", "dementia", "moyamoya", "sellar", "sella", "pituitary", "ventric", "temporal lobe", "basal ganglia", "white matter", "encephal"],
    "head_and_neck": ["neck", "tongue", "oral", "mandib", "npc", "nasopharyn", "sinus", "skull base", "clival", "clivus", "hypoglossal"],
    "spine": ["spine", "spinal", "sacral"],
    "skull": ["skull", "calvar", "clival", "sella", "sellar"],
}
MODALITY_RULES = {
    "CT": [" ct", "cta", "density", "calcif", "bone window"],
    "MRI": ["mri", " mr ", "flair", "adc", "dwi", "swi", "mrs", " t1", " t2", "mra", "asl"],
}
SEQUENCES = ["FLAIR", "DWI", "ADC", "SWI", "MRS", "T1", "T2", "CTA", "MRA", "ASL"]


def labels_for(text: str, rules: dict[str, list[str]]) -> list[str]:
    lowered = f" {text.lower()} "
    return [label for label, terms in rules.items() if any(term in lowered for term in terms)]


def srt_time(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def normalized_text(card: dict) -> str:
    keys = ("topic", "what_happened_in_conversation", "teacher_feedback", "key_teaching_point", "common_pitfall", "improved_report_phrase")
    return " ".join(str(card.get(key, "")) for key in keys)


def write_indexes(library: Path, cases: list[dict]) -> None:
    (library / "cases_index.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ["clip_id", "card_id", "title", "vitamin_cd", "anatomy", "modality", "sequences", "teaching_type", "duration_seconds", "teaching_clip", "subtitle", "review_status"]
    with (library / "cases_index.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in cases:
            writer.writerow({
                "clip_id": item["clip_id"], "card_id": item["card_id"], "title": item["title"],
                "vitamin_cd": "|".join(tag["code"] for tag in item["vitamin_cd"]),
                "anatomy": "|".join(item["anatomy"]), "modality": "|".join(item["modality"]),
                "sequences": "|".join(item["sequences"]), "teaching_type": item["teaching_type"],
                "duration_seconds": item["duration_seconds"], "teaching_clip": item["assets"]["teaching_clip"],
                "subtitle": item["assets"]["subtitle"], "review_status": item["review_status"],
            })


def main() -> None:
    parser = argparse.ArgumentParser(description="依日期資料夾建立可匯入 Portal 的教學資料庫。")
    parser.add_argument("--date-code", required=True, help="例如 0714")
    parser.add_argument("--output-root", type=Path, help="預設 data/library_exports/<date-code>")
    args = parser.parse_args()

    package = PROJECT / "data" / args.date_code
    cards_dir = package / "cards/json"
    manifest_path = package / "videos/manifest.json"
    transcripts = sorted((package / "transcripts").glob("*.srt"))
    if not cards_dir.is_dir() or not manifest_path.exists() or len(transcripts) != 1:
        parser.error(f"{package} 必須包含 cards/json、videos/manifest.json 與一份 transcripts/*.srt")

    output_root = (args.output_root or PROJECT / "data/library_exports" / args.date_code).resolve()
    library = output_root / "data/teaching_library"
    cases_dir = library / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    entries = parse_transcript(transcripts[0])
    manifest = {item["card_id"]: item for item in json.loads(manifest_path.read_text(encoding="utf-8"))}
    cases = []

    for card_path in sorted(cards_dir.glob("CARD*.json")):
        card = json.loads(card_path.read_text(encoding="utf-8"))
        card_id = card["card_id"]
        clip = manifest[card_id]
        start_text, end_text = clip["teaching_clip_range"].split("-")
        start, end = time_to_seconds(start_text), time_to_seconds(end_text)
        selected = [cue for cue in entries if cue.end_seconds >= start and cue.start_seconds <= end]
        blocks, lines, previous_end = [], [], 0.0
        for cue in selected:
            local_start = max(0, cue.start_seconds - start, previous_end)
            local_end = min(end - start, max(local_start + 0.5, cue.end_seconds - start))
            if local_end <= local_start:
                continue
            blocks.append(f"{len(blocks) + 1}\n{srt_time(local_start)} --> {srt_time(local_end)}\n{cue.text}")
            lines.append(cue.text)
            previous_end = local_end

        case_dir = cases_dir / card_id
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "subtitle.srt").write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
        (case_dir / "transcript.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        text = normalized_text(card)
        vitamin = labels_for(text, VITAMIN_RULES) or ["I2"]
        metadata = {
            "schema_version": "1.0", "clip_id": f"CLIP{int(card_id[-3:]):04d}",
            "case_id": card["case_id"], "card_id": card_id, "title": card["topic"],
            "vitamin_cd": [{"code": code, "label": TAXONOMY[code]} for code in vitamin],
            "anatomy": labels_for(text, ANATOMY_RULES) or ["other"],
            "modality": labels_for(text, MODALITY_RULES),
            "sequences": [name for name in SEQUENCES if name.lower() in text.lower()],
            "disease_keywords": sorted(set(re.findall(r"[A-Za-z][A-Za-z-]{3,}", card["topic"]))),
            "teaching_type": card["teaching_moment_type"], "report_issue_type": card["report_issue_type"],
            "image_dependency": card["image_dependency"], "teaching_point": card["key_teaching_point"],
            "common_pitfall": card["common_pitfall"], "suggested_report_phrase": card["improved_report_phrase"],
            "checklist_item_for_next_report": card.get("checklist_item_for_next_report", ""),
            "source_time_range": card["timestamp_range"], "teaching_clip_range": clip["teaching_clip_range"],
            "duration_seconds": clip["duration_seconds"],
            "assets": {
                "teaching_clip": str(package / "videos" / f"{card_id}_teaching.mp4"),
                "scroll_clip": card.get("optional_image_evidence", {}).get("scroll_clip", ""),
                "key_screenshot": card.get("optional_image_evidence", {}).get("key_screenshot", ""),
                "subtitle": f"data/teaching_library/cases/{card_id}/subtitle.srt",
                "transcript": f"data/teaching_library/cases/{card_id}/transcript.txt",
                "teaching_card": str(card_path),
            },
            "classification_method": "rule-assisted multi-label draft from LLM teaching card",
            "review_status": "needs_review", "reviewer": "", "review_notes": "",
        }
        (case_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        cases.append(metadata)

    (library / "taxonomy.json").write_text(json.dumps(TAXONOMY, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_indexes(library, cases)
    print(f"Built {len(cases)} cases at {library}")


if __name__ == "__main__":
    main()

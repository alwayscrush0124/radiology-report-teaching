from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from portal.library import TeachingLibrary
from portal.media import DriveVideoError, download_drive_video, playable_video_url, srt_to_vtt
from portal.supabase_library import SupabaseTeachingLibrary


st.set_page_config(page_title="Radiology Teaching Atlas", page_icon="🩻", layout="wide")


def repository() -> TeachingLibrary | SupabaseTeachingLibrary:
    try:
        secrets = st.secrets
        for name in ("SUPABASE_URL", "SUPABASE_KEY"):
            if name in secrets:
                os.environ[name] = secrets[name]
    except FileNotFoundError:
        pass
    from portal.supabase_library import configured_supabase_library
    cloud = configured_supabase_library()
    if cloud:
        return cloud
    return TeachingLibrary()


def tags(case: dict, field: str) -> set[str]:
    if field == "vitamin_cd":
        return {item["code"] for item in case.get(field, [])}
    return set(case.get(field, []))


def case_key(case: dict) -> str:
    return case.get("record_id") or case["card_id"]


def case_label(case: dict) -> str:
    date = case.get("lecture_date", "")
    prefix = f"{date} · " if date else ""
    return f"{prefix}{case['card_id']} · {case['title']}"


@st.cache_data(ttl=3600, max_entries=3, show_spinner=False)
def cached_drive_video(url: str) -> bytes:
    return download_drive_video(url)


def show_video(repo: TeachingLibrary, case: dict) -> None:
    video = repo.resolve_asset(case["assets"].get("teaching_clip", ""))
    subtitle = repo.resolve_asset(case["assets"].get("subtitle", ""))
    if not video:
        st.warning("找不到教學影片")
        return
    video_url = playable_video_url(str(video))
    if video_url != str(video):
        try:
            current_subtitle = repo.read_case_text(case_key(case), "subtitle")
        except (FileNotFoundError, ValueError):
            current_subtitle = ""
        try:
            with st.spinner("載入教學影片..."):
                video_bytes = cached_drive_video(str(video))
        except DriveVideoError as exc:
            st.error(f"影片載入失敗：{exc}")
            return
        st.video(video_bytes, format="video/mp4", subtitles=srt_to_vtt(current_subtitle) if current_subtitle else None)
        return
    try:
        st.video(str(video), subtitles=str(subtitle) if subtitle else None)
    except TypeError:
        st.video(str(video))


def dashboard_page(repo: TeachingLibrary) -> None:
    st.title("Radiology Teaching Atlas")
    stats = repo.dashboard()
    cols = st.columns(4)
    cols[0].metric("Cases", stats["case_count"])
    cols[1].metric("影片總時數", f"{stats['total_seconds'] / 60:.1f} 分")
    cols[2].metric("待審核", stats["review"].get("needs_review", 0))
    cols[3].metric("已核准", stats["review"].get("approved", 0))
    left, right = st.columns(2)
    with left:
        st.subheader("VITAMIN-CD 分布")
        st.bar_chart(stats["vitamin"], horizontal=True)
    with right:
        st.subheader("審核狀態")
        st.bar_chart(stats["review"], horizontal=True)


def library_page(repo: TeachingLibrary) -> None:
    st.title("Case Library")
    cases = repo.load_cases()
    vitamin_options = sorted({tag["code"] for case in cases for tag in case.get("vitamin_cd", [])})
    anatomy_options = sorted({value for case in cases for value in case.get("anatomy", [])})
    modality_options = sorted({value for case in cases for value in case.get("modality", [])})
    date_options = sorted({case.get("lecture_date", "") for case in cases if case.get("lecture_date")}, reverse=True)
    query = st.text_input("搜尋標題或教學重點")
    f1, f2, f3, f4 = st.columns(4)
    dates = f1.multiselect("上課日期", date_options)
    vitamin = f2.multiselect("VITAMIN-CD", vitamin_options)
    anatomy = f3.multiselect("解剖部位", anatomy_options)
    modality = f4.multiselect("Modality", modality_options)
    filtered = []
    for case in cases:
        haystack = f"{case['title']} {case.get('teaching_point', '')}".lower()
        if query and query.lower() not in haystack:
            continue
        if dates and case.get("lecture_date") not in dates:
            continue
        if vitamin and not set(vitamin).issubset(tags(case, "vitamin_cd")):
            continue
        if anatomy and not set(anatomy).intersection(tags(case, "anatomy")):
            continue
        if modality and not set(modality).intersection(tags(case, "modality")):
            continue
        filtered.append(case)
    st.caption(f"找到 {len(filtered)} 個 Cases")
    selected_id = st.selectbox("選擇 Case", [case_key(case) for case in filtered], format_func=lambda value: next(case_label(case) for case in filtered if case_key(case) == value)) if filtered else None
    if not selected_id:
        return
    case = next(case for case in filtered if case_key(case) == selected_id)
    media, content = st.columns([1.2, 1])
    with media:
        show_video(repo, case)
    with content:
        st.subheader(case["title"])
        if case.get("lecture_date"):
            st.write("**上課日期：**", case["lecture_date"])
        st.write("**VITAMIN-CD：**", "、".join(f"{tag['code']} {tag['label']}" for tag in case["vitamin_cd"]))
        st.write("**部位：**", "、".join(case["anatomy"]))
        st.write("**影像：**", "、".join(case["modality"] + case["sequences"]))
        st.write("**教學重點**")
        st.write(case["teaching_point"])
        st.write("**常見陷阱**")
        st.write(case["common_pitfall"])
        st.write("**下次報告注意**")
        st.write(case.get("checklist_item_for_next_report") or "尚未填寫")
        st.write("**建議報告句**")
        st.write(case.get("suggested_report_phrase") or "尚未填寫")


def review_page(repo: TeachingLibrary) -> None:
    st.title("Review Workspace")
    cases = repo.load_cases()
    card_id = st.selectbox("選擇待審 Case", [case_key(case) for case in cases], format_func=lambda value: next(case_label(case) for case in cases if case_key(case) == value))
    case = repo.get_case(card_id)
    video_col, form_col = st.columns([1.1, 1])
    with video_col:
        show_video(repo, case)
        st.caption(f"片段：{case['teaching_clip_range']} · {case['duration_seconds']:.0f} 秒")
    with form_col, st.form("review_form"):
        taxonomy = repo.taxonomy()
        selected_codes = st.multiselect("VITAMIN-CD", list(taxonomy), default=[tag["code"] for tag in case["vitamin_cd"]], format_func=lambda code: f"{code} · {taxonomy[code]}")
        anatomy = st.text_input("解剖部位（逗號分隔）", ", ".join(case["anatomy"]))
        modality = st.text_input("Modality（逗號分隔）", ", ".join(case["modality"]))
        sequences = st.text_input("Sequences（逗號分隔）", ", ".join(case["sequences"]))
        status = st.selectbox("審核狀態", ["needs_review", "approved", "adjust_start", "adjust_end", "wrong_visual", "reject"], index=["needs_review", "approved", "adjust_start", "adjust_end", "wrong_visual", "reject"].index(case.get("review_status", "needs_review")))
        notes = st.text_area("審核備註", case.get("review_notes", ""))
        if st.form_submit_button("儲存審核結果", type="primary"):
            case["vitamin_cd"] = [{"code": code, "label": taxonomy[code]} for code in selected_codes]
            case["anatomy"] = [item.strip() for item in anatomy.split(",") if item.strip()]
            case["modality"] = [item.strip() for item in modality.split(",") if item.strip()]
            case["sequences"] = [item.strip() for item in sequences.split(",") if item.strip()]
            case["review_status"] = status
            case["review_notes"] = notes
            repo.save_case(case)
            st.success("已儲存 metadata，並重建 CSV、JSON 與分類視圖。")


def transcript_page(repo: TeachingLibrary) -> None:
    st.title("Transcript Editor")
    cases = repo.load_cases()
    card_id = st.selectbox("選擇 Case", [case_key(case) for case in cases], format_func=lambda value: next(case_label(case) for case in cases if case_key(case) == value), key="transcript_case")
    case = repo.get_case(card_id)
    if st.session_state.pop("transcript_saved", None) == card_id:
        st.success("字幕與逐字稿已儲存，播放器已載入最新字幕。")
    video_col, editor_col = st.columns([1, 1.25])
    with video_col:
        show_video(repo, case)
        st.caption(f"影片範圍：{case['teaching_clip_range']} · {case['duration_seconds']:.0f} 秒")
        st.info("字幕時間以這段小影片的 00:00:00 為起點。")
    with editor_col:
        subtitle = repo.read_case_text(card_id, "subtitle")
        transcript = repo.read_case_text(card_id, "transcript")
        with st.form(f"transcript_form_{card_id}"):
            edited_subtitle = st.text_area("SRT 字幕", subtitle, height=360, help="格式：編號、開始時間 --> 結束時間、字幕文字")
            edited_transcript = st.text_area("純文字逐字稿", transcript, height=240)
            if st.form_submit_button("儲存字幕與逐字稿", type="primary"):
                try:
                    repo.save_case_text(card_id, edited_subtitle, edited_transcript)
                except ValueError as exc:
                    st.error(f"字幕格式檢查未通過：{exc}")
                else:
                    st.session_state["transcript_saved"] = card_id
                    st.rerun()


def card_editor_page(repo: TeachingLibrary) -> None:
    st.title("Card Editor")
    cases = repo.load_cases()
    card_id = st.selectbox("選擇 Case", [case_key(case) for case in cases], format_func=lambda value: next(case_label(case) for case in cases if case_key(case) == value), key="card_editor_case")
    case = repo.get_case(card_id)
    media_col, editor_col = st.columns([1, 1.15])
    with media_col:
        show_video(repo, case)
        st.write("**分類：**", "、".join(f"{tag['code']} {tag['label']}" for tag in case["vitamin_cd"]))
        st.write("**影像：**", "、".join(case["modality"] + case["sequences"]))
        st.caption("分類標籤請至 Review Workspace 修改。")
    with editor_col, st.form(f"card_editor_form_{card_id}"):
        title = st.text_input("卡片標題", case["title"])
        teaching_point = st.text_area("教學重點", case.get("teaching_point", ""), height=150)
        common_pitfall = st.text_area("常見陷阱", case.get("common_pitfall", ""), height=110)
        report_phrase = st.text_area("建議報告句", case.get("suggested_report_phrase", ""), height=130)
        checklist = st.text_area("下次報告檢查項目", case.get("checklist_item_for_next_report", ""), height=100)
        discussion = st.text_area("教學討論問題", case.get("discussion_question", ""), height=100)
        if st.form_submit_button("儲存卡片內容", type="primary"):
            try:
                repo.save_card_content(card_id, {
                    "title": title,
                    "teaching_point": teaching_point,
                    "common_pitfall": common_pitfall,
                    "suggested_report_phrase": report_phrase,
                    "checklist_item_for_next_report": checklist,
                    "discussion_question": discussion,
                })
            except (ValueError, FileNotFoundError) as exc:
                st.error(f"無法儲存：{exc}")
            else:
                st.success("卡片內容已同步更新至 metadata 與原始 Teaching Card。")


def builder_page(repo: TeachingLibrary) -> None:
    st.title("Teaching Set Builder")
    cases = repo.load_cases()
    selected = st.multiselect("選擇 Cases（順序即教案順序）", [case_key(case) for case in cases], format_func=lambda value: next(case_label(case) for case in cases if case_key(case) == value))
    name = st.text_input("教案名稱")
    description = st.text_area("教案說明")
    if selected:
        st.write("**內容順序**")
        for number, card_id in enumerate(selected, 1):
            case = next(case for case in cases if case_key(case) == card_id)
            st.write(f"{number}. {case_label(case)}")
    if st.button("建立教案索引", type="primary", disabled=not (name and selected)):
        path = repo.create_teaching_set(name, selected, description)
        st.success(f"已建立：{path}")
        st.download_button("下載教案 JSON", path.read_bytes(), file_name=path.name, mime="application/json")


repo = repository()
page = st.sidebar.radio("功能", ["Dashboard", "Case Library", "Review Workspace", "Transcript Editor", "Card Editor", "Teaching Set Builder"])
st.sidebar.caption(f"資料位置：{repo.location_label}")
if page == "Dashboard":
    dashboard_page(repo)
elif page == "Case Library":
    library_page(repo)
elif page == "Review Workspace":
    review_page(repo)
elif page == "Transcript Editor":
    transcript_page(repo)
elif page == "Card Editor":
    card_editor_page(repo)
else:
    builder_page(repo)

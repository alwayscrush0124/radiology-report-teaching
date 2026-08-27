from __future__ import annotations

import os
import sys
from html import escape
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from portal.library import TeachingLibrary
from portal.media import DriveVideoError, download_drive_video, playable_video_url, srt_to_vtt
from portal.supabase_library import SupabaseError, SupabaseTeachingLibrary


st.set_page_config(page_title="Radiology Teaching Atlas", page_icon="R", layout="wide", initial_sidebar_state="auto")


APP_CSS = """
<style>
:root {
  --atlas-ink: #374151;
  --atlas-heading: #1f2937;
  --atlas-muted: #6b7280;
  --atlas-line: #e5e7eb;
  --atlas-primary: #066fd1;
  --atlas-primary-soft: #edf6ff;
  --atlas-danger: #d63939;
  --atlas-warning: #f59f00;
  --atlas-paper: #ffffff;
  --atlas-canvas: #f9fafb;
}
.stApp { background: var(--atlas-canvas); color: var(--atlas-ink); font-size: 14px; }
[data-testid="stMainBlockContainer"] { max-width: 1500px; padding-top: 4.5rem; padding-bottom: 4rem; }
[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid var(--atlas-line); }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--atlas-muted); }
[data-testid="stSidebar"] [role="radiogroup"] label {
  padding: .52rem .7rem; border-radius: 6px; margin-bottom: .18rem;
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background: var(--atlas-primary-soft); color: var(--atlas-primary); font-weight: 650;
}
h1, h2, h3 { color: var(--atlas-heading); letter-spacing: 0; }
h1 { font-size: 2rem !important; line-height: 1.2 !important; }
h2 { font-size: 1.35rem !important; }
h3 { font-size: 1.08rem !important; }
.atlas-kicker { color: var(--atlas-muted); font-size: .74rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
.atlas-header { margin-bottom: 1.2rem; }
.atlas-header h1 { margin: .18rem 0 .2rem; }
.atlas-header p { color: var(--atlas-muted); margin: 0; max-width: 760px; }
.atlas-brand { padding: .45rem .15rem 1rem; border-bottom: 1px solid var(--atlas-line); margin-bottom: .8rem; }
.atlas-brand strong { display: block; color: var(--atlas-heading); font-size: 1.05rem; }
.atlas-brand span { color: var(--atlas-muted); font-size: .78rem; }
[data-testid="stMetric"] { background: var(--atlas-paper); border: 1px solid var(--atlas-line); border-radius: 7px; padding: .85rem 1rem; }
[data-testid="stMetricLabel"] { color: var(--atlas-muted); }
[data-testid="stMetricValue"] { color: var(--atlas-ink); }
[data-testid="stVerticalBlockBorderWrapper"] { background: var(--atlas-paper); border-color: var(--atlas-line) !important; border-radius: 7px !important; }
[data-baseweb="input"] > div, [data-baseweb="select"] > div, textarea {
  border-color: #d1d5db !important; border-radius: 6px !important; background: var(--atlas-paper) !important;
}
.stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button { border-radius: 6px; font-weight: 650; }
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] { background: var(--atlas-primary); border-color: var(--atlas-primary); }
.atlas-meta { display: flex; flex-wrap: wrap; gap: .42rem; margin: .5rem 0 1rem; }
.atlas-chip { display: inline-flex; align-items: center; border: 1px solid #dbe1e8; background: #f3f4f6; color: #4b5563; border-radius: 999px; padding: .2rem .55rem; font-size: .78rem; }
.atlas-guide { border-left: 4px solid var(--atlas-primary); background: var(--atlas-paper); border-top: 1px solid var(--atlas-line); border-right: 1px solid var(--atlas-line); border-bottom: 1px solid var(--atlas-line); border-radius: 6px; padding: .85rem 1rem; margin: 0 0 .72rem; }
.atlas-guide.pitfall { border-left-color: var(--atlas-danger); }
.atlas-guide.checklist { border-left-color: var(--atlas-warning); }
.atlas-guide.phrase { border-left-color: #4263eb; }
.atlas-guide .label { color: var(--atlas-muted); font-size: .76rem; font-weight: 750; letter-spacing: .05em; margin-bottom: .28rem; }
.atlas-guide .text { color: var(--atlas-ink); line-height: 1.65; }
.atlas-result { color: var(--atlas-muted); font-size: .86rem; margin: .3rem 0 .55rem; }
video { border-radius: 7px; background: #111827; border: 1px solid #d1d5db; }
hr { border-color: var(--atlas-line) !important; }
@media (max-width: 900px) {
  [data-testid="stMainBlockContainer"] { padding-left: 1rem; padding-right: 1rem; padding-top: 4rem; }
  h1 { font-size: 1.65rem !important; }
  .atlas-guide { padding: .75rem .8rem; }
}
</style>
"""


def page_header(title: str, description: str, kicker: str = "Teaching Atlas") -> None:
    st.markdown(
        f'<div class="atlas-header"><div class="atlas-kicker">{escape(kicker)}</div>'
        f'<h1>{escape(title)}</h1><p>{escape(description)}</p></div>',
        unsafe_allow_html=True,
    )


def guidance_block(label: str, text: str, kind: str = "") -> None:
    value = text.strip() if text else "尚未填寫"
    st.markdown(
        f'<div class="atlas-guide {escape(kind)}"><div class="label">{escape(label)}</div>'
        f'<div class="text">{escape(value)}</div></div>',
        unsafe_allow_html=True,
    )


def metadata_chips(case: dict) -> None:
    values = []
    if case.get("lecture_date"):
        values.append(case["lecture_date"])
    values.extend(f"{tag['code']} {tag['label']}" for tag in case.get("vitamin_cd", []))
    values.extend(case.get("anatomy", []))
    values.extend(case.get("modality", []) + case.get("sequences", []))
    chips = "".join(f'<span class="atlas-chip">{escape(str(value))}</span>' for value in values if value)
    st.markdown(f'<div class="atlas-meta">{chips}</div>', unsafe_allow_html=True)


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
    page_header("教學資料總覽", "快速掌握病例數、影片時數、疾病分類與目前審核進度。", "Radiology Report Teaching Atlas")
    stats = repo.dashboard()
    cols = st.columns(4)
    cols[0].metric("病例數", stats["case_count"])
    cols[1].metric("影片總時數", f"{stats['total_seconds'] / 60:.1f} 分")
    cols[2].metric("待審核", stats["review"].get("needs_review", 0))
    cols[3].metric("已核准", stats["review"].get("approved", 0))
    st.write("")
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("VITAMIN-CD 分布")
        st.bar_chart(stats["vitamin"], horizontal=True, color="#066fd1")
    with right:
        st.subheader("審核狀態")
        review_labels = {
            "needs_review": "待審核", "approved": "已核准", "adjust_start": "調整起點",
            "adjust_end": "調整終點", "wrong_visual": "畫面不符", "reject": "不採用",
        }
        review_data = {review_labels.get(key, key): value for key, value in stats["review"].items()}
        st.bar_chart(review_data, horizontal=True, color="#d63939")


def library_page(repo: TeachingLibrary) -> None:
    page_header("病例資料庫", "依日期、疾病分類與影像條件尋找教學片段，搭配字幕閱讀完整教學重點。", "Case Library")
    cases = repo.load_cases()
    vitamin_options = sorted({tag["code"] for case in cases for tag in case.get("vitamin_cd", [])})
    anatomy_options = sorted({value for case in cases for value in case.get("anatomy", [])})
    modality_options = sorted({value for case in cases for value in case.get("modality", [])})
    date_options = sorted({case.get("lecture_date", "") for case in cases if case.get("lecture_date")}, reverse=True)
    query = st.text_input("搜尋", placeholder="輸入疾病、影像表現或教學重點")
    f1, f2, f3, f4 = st.columns(4, gap="medium")
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
    st.markdown(f'<div class="atlas-result">找到 <strong>{len(filtered)}</strong> 個病例</div>', unsafe_allow_html=True)
    selected_id = st.selectbox("選擇病例", [case_key(case) for case in filtered], format_func=lambda value: next(case_label(case) for case in filtered if case_key(case) == value)) if filtered else None
    if not selected_id:
        return
    case = next(case for case in filtered if case_key(case) == selected_id)
    st.divider()
    media, content = st.columns([1.25, 1], gap="large")
    with media:
        show_video(repo, case)
        st.caption(f"影片片段：{case.get('teaching_clip_range', '')} · {case.get('duration_seconds', 0):.0f} 秒 · 播放器可開啟字幕")
    with content:
        st.subheader(case["title"])
        metadata_chips(case)
        guidance_block("教學重點", case.get("teaching_point", ""))
        guidance_block("常見陷阱", case.get("common_pitfall", ""), "pitfall")
        guidance_block("下次報告注意", case.get("checklist_item_for_next_report", ""), "checklist")
        guidance_block("建議報告句", case.get("suggested_report_phrase", ""), "phrase")


def review_page(repo: TeachingLibrary) -> None:
    page_header("病例審核", "檢查分類、影像標籤與片段品質，留下後續調整狀態。", "Review Workspace")
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
    page_header("逐字稿編輯", "一邊播放教學片段，一邊校正字幕時間與逐字稿內容。", "Transcript Editor")
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
    page_header("教學卡片編輯", "調整病例標題、教學重點、常見陷阱與建議報告句。", "Card Editor")
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
    page_header("教案組合", "挑選病例並排列順序，建立可重複使用的主題教案。", "Teaching Set Builder")
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


st.markdown(APP_CSS, unsafe_allow_html=True)
repo = repository()
st.sidebar.markdown('<div class="atlas-brand"><strong>Radiology Teaching Atlas</strong><span>放射診斷教學資料庫</span></div>', unsafe_allow_html=True)
pages = {
    "總覽": "Dashboard",
    "病例資料庫": "Case Library",
    "病例審核": "Review Workspace",
    "逐字稿編輯": "Transcript Editor",
    "教學卡片編輯": "Card Editor",
    "教案組合": "Teaching Set Builder",
}
page_label = st.sidebar.radio("功能", list(pages))
page = pages[page_label]
st.sidebar.divider()
st.sidebar.caption(f"資料來源：{repo.location_label}")
try:
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
except SupabaseError:
    st.error("資料庫暫時無法連線，病例資料目前沒有遺失。請稍後重新整理；若持續發生，請至 Supabase Dashboard 確認專案是否已暫停。")
    if st.button("重新嘗試", type="primary"):
        st.rerun()

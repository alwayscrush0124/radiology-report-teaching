# Radiology Teaching Atlas Portal

## 啟動

在專案根目錄執行：

```bash
./scripts/start_portal.sh
```

瀏覽器開啟 `http://127.0.0.1:8501`。

Portal 包含 Dashboard、Case Library、Review Workspace、Transcript Editor、Card Editor 與 Teaching Set Builder。Transcript Editor 可一邊播放 Case 影片，一邊編輯 SRT 字幕與純文字逐字稿；Card Editor 可修改教學重點、常見陷阱、建議報告句與討論問題，並同步更新 metadata 與原始 Teaching Card。

## Supabase 雲端模式

當 `.streamlit/secrets.toml` 或部署環境包含 `SUPABASE_URL` 與 `SUPABASE_KEY` 時，Portal 會自動使用 Supabase；未設定時則維持本機資料模式。

第一次把本機資料匯入雲端：

```bash
.venv/bin/python -m scripts.import_library_to_supabase \
  --lecture-date 2026-07-07 \
  --source-video "2026-07-07 14-12-27.mp4" \
  --storage-prefix "2026-07-07"
```

雲端模式會保存 metadata、字幕、逐字稿與教案集合。影片仍使用 metadata 內的素材路徑；部署到網路前，需要把這些路徑換成可存取的雲端影片網址。

多日期資料使用 `record_id` 作為唯一鍵，例如 `20260707_CARD001`；原始 `card_id` 仍保留為 `CARD001`。因此不同日期資料夾可使用相同影片檔名，不會互相覆蓋。

Google Drive 影片使用公開 `/preview` 網址，Portal 會自動切換為 Drive 內嵌播放器。批次連結工具接受 `filename -> Drive file ID` 的 JSON mapping：

```bash
.venv/bin/python -m scripts.link_google_drive_videos \
  --lecture-date 2026-07-07 \
  --mapping data/drive_maps/2026-07-07.json \
  --apply
```

Portal 會將 Drive preview 網址轉成可串流的 MP4 網址，再用 Streamlit 原生播放器載入 Supabase 中的最新版 SRT。Transcript Editor 儲存成功後會立即重新載入頁面，因此 Case Library 與各編輯分頁下一次播放時都會使用更新後的字幕。

## 放在雲端硬碟

整個 `radiology_report_teaching_atlas` 資料夾可以移到 iCloud Drive、Google Drive、Dropbox 或 OneDrive。Portal 使用相對路徑，不依賴原本的 `/Users/...` 位置。

每台電腦第一次使用時，在同步完成的專案資料夾執行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./scripts/start_portal.sh
```

若程式與資料分開存放，可設定：

```bash
export ATLAS_DATA_ROOT="/雲端硬碟中的/radiology_report_teaching_atlas"
./scripts/start_portal.sh
```

## 同步注意事項

- 使用 Portal 前，先等待雲端硬碟完成同步。
- 同一時間只在一台電腦編輯 metadata，避免同步衝突。
- 大型影片應設定為「保留在本機」或「離線可用」，否則播放時可能需要等待下載。
- Portal 僅在 `127.0.0.1` 提供服務，不會自動公開到網際網路。

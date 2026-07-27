# Radiology Teaching Atlas Portal

## 啟動

在專案根目錄執行：

```bash
./scripts/start_portal.sh
```

瀏覽器開啟 `http://127.0.0.1:8501`。

Portal 包含 Dashboard、Case Library、Review Workspace、Transcript Editor、Card Editor 與 Teaching Set Builder。Transcript Editor 可一邊播放 Case 影片，一邊編輯 SRT 字幕與純文字逐字稿；Card Editor 可修改教學重點、常見陷阱、建議報告句與討論問題，並同步更新 metadata 與原始 Teaching Card。

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

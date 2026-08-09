# 部署到 Streamlit Community Cloud

## 部署前確認

- GitHub 的 `main` 已包含 Supabase Portal 整合。
- Supabase 已有 `atlas_cases` 與 `atlas_teaching_sets`。
- `atlas_cases` 已匯入 34 張去識別化 Teaching Cards。
- `.streamlit/secrets.toml` 不可提交到 GitHub。

## 建立 App

1. 開啟 [Streamlit Community Cloud](https://share.streamlit.io/) 並使用 GitHub 登入。
2. 點選 **Create app**，再選 **Yup, I have an app**。
3. 填入：
   - Repository：`alwayscrush0124/radiology-report-teaching-atlas`
   - Branch：`main`
   - Main file path：`portal/app.py`
4. 開啟 **Advanced settings**。
5. Python version 選擇 `3.12`。
6. 在 Secrets 貼入：

```toml
SUPABASE_URL = "https://ufearyujukdjypyybksp.supabase.co"
SUPABASE_KEY = "你的 publishable key"
```

7. 儲存設定並點選 **Deploy**。

## 讓合作對象免登入

若 GitHub Repository 是 Private，Streamlit App 預設也可能是 Private。部署成功後進入 App settings，將 App visibility 改為 **Public**，再分享 `streamlit.app` 網址。

目前 Supabase 權限允許未登入使用者讀取、新增與修改，但不允許刪除。這只適合去識別化 MVP；正式收案或多人使用前，應加入登入與成員權限。

## 目前影片限制

文字、分類、字幕與逐字稿已存於 Supabase。影片仍是本機相對路徑，所以公開 Portal 暫時無法播放影片；下一階段需把片段上傳到雲端檔案空間，並將 metadata 的 `assets.teaching_clip` 改成可播放網址。


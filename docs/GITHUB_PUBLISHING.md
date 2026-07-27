# GitHub 公開版上架指南

## 公開版包含什麼

建議公開：

- `app/`：逐字稿解析、切點驗證、教學卡產生與索引程式
- `portal/`：本機教學資料管理介面
- `scripts/`：可重複使用且不含個案內容的通用工具
- `tests/`：自動測試
- `examples/`：完全人工撰寫的示範資料
- `README.md`、`pyproject.toml`、`requirements.txt`

預設不公開：

- `data/`：影片、逐字稿、截圖、Cards、LLM 工作包及索引
- `outputs/`：含影像或影片的 PowerPoint
- `.venv/`、模型快取與執行紀錄
- 依特定教學日期人工整理的 LLM response scripts
- `.env`、API key 或其他憑證

這些排除規則已寫入根目錄的 `.gitignore`。

## 上傳前檢查

每次公開前都應完成：

1. 確認 `git status --short` 沒有列出 `data/`、`outputs/`、影片、PPT 或 `.env`。
2. 搜尋姓名、病歷號、生日、檢查日期、院內代碼及本機帳號路徑。
3. 確認 `examples/` 只使用人工製作的假資料，不從真實逐字稿改寫。
4. 執行 `python3 -m pytest -q`。
5. 檢查即將提交的清單：`git diff --cached --name-only`。
6. 檢查即將提交的內容：`git diff --cached`。

## 建立 GitHub repository

先在 GitHub 建立一個空白 repository，建議名稱：

`radiology-report-teaching-atlas`

第一次可先設為 **Private**。確認檔案清單正確後，再依院方、IRB 或資料治理規範決定是否改為 Public。

本機指令：

```bash
git init -b main
git add .
git status --short
git commit -m "Initial public MVP"
git remote add origin https://github.com/YOUR_ACCOUNT/radiology-report-teaching-atlas.git
git push -u origin main
```

不要使用 `git add -f data/` 或 `git add -f outputs/` 繞過保護。

## 公開後發現誤傳資料

只刪除最新版本不代表資料已從 Git 歷史移除。若誤傳任何臨床或敏感資料：

1. 立即將 repository 改為 Private。
2. 撤銷或更換任何外洩憑證。
3. 依院方資料事件流程通報。
4. 使用 Git 歷史清理工具完整移除檔案，再重新檢查所有 commit。


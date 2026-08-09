# Radiology Report Teaching Atlas

Radiology Report Teaching Atlas 是一個本機執行的 MVP，用來把已去識別化的放射科報告回饋逐字稿整理成可搜尋、可分類、可再利用的教學卡。第一版特別適合處理「老師與住院醫師討論報告內容」這類 conversation-anchored teaching moments，不要求一定要有明確的 DICOM slice 或病灶座標。

## 專案目的

這個工具協助教師從教學影片或逐字稿中快速找出可能有教學價值的片段，例如：

- impression 是否整合 findings
- 報告文字是否清楚
- 是否回答 clinical question
- 是否需要比較前片
- confidence wording 是否過弱或過強
- critical finding 是否需要溝通與記錄
- 是否需要搭配影片截圖或 scroll clip

輸出的 teaching cards 仍然需要教師人工確認與補完。這個 MVP 的目標是減少整理素材的時間，而不是取代教師判斷。

## 為什麼第一版不是自動診斷工具

本工具不會自動判斷影像診斷是否正確，也不會替住院醫師評分。目前同時保留兩種切點方式：透明的規則式關鍵字偵測，以及由人工複製貼上完成的 LLM 輔助切點。LLM 模式必須引用逐字稿行號，程式再將行號映射回時間，避免模型自行編造時間戳。

本工具不做以下事情：

- 不判斷診斷正確與否
- 不辨識 CT/MRI 病灶
- 不推論病人資訊
- 不評分住院醫師
- 不自動產生最終教學結論

需要教師判斷的欄位會填入 `needs human completion`；資訊不足的欄位會填入 `not mentioned`。

## 安全與隱私原則

- 所有資料預設在本機處理。
- 規則模式不會把影片、逐字稿或病人資訊送到雲端。
- Manual LLM 模式只產生本機提示詞檔案；是否貼到雲端服務由使用者自行決定。
- 使用雲端 LLM 前，逐字稿必須先移除姓名、病歷號、生日及其他可識別資訊。
- 影像預設留在本機，不會包含在 LLM 提示詞中。
- 目前不整合 LLM API，也不需要 API key。
- 規則式偵測只負責整理 candidate teaching moments。
- 所有 teaching cards 預設狀態都是 `needs_review`。
- 最終教學內容必須由教師人工確認。

## 專案結構

```text
radiology_report_teaching_atlas/
├── app/
│   ├── config.py
│   ├── transcript_parser.py
│   ├── segment_detector.py
│   ├── llm_segmenter.py
│   ├── teaching_card.py
│   ├── media_extractor.py
│   ├── index_writer.py
│   └── cli.py
├── data/
│   ├── videos/
│   ├── transcripts/
│   ├── clips/
│   ├── screenshots/
│   ├── cards/
│   ├── llm_jobs/
│   └── index/
├── examples/
│   └── sample_transcript.srt
├── tests/
├── requirements.txt
├── README.md
└── pyproject.toml
```

## 安裝方式

```bash
cd radiology_report_teaching_atlas
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如果你的環境提供的是 `python` 而不是 `python3`，兩種指令都可以，請依照本機環境調整。

FFmpeg 是選用依賴。只有在需要從影片擷取 screenshot 或 clip 時才需要安裝 FFmpeg；若沒有影片或沒有 FFmpeg，仍然可以從逐字稿產生 teaching cards。

## 使用方式

只處理逐字稿，不提供影片：

```bash
python3 -m app.cli process \
  --transcript data/transcripts/session_001.srt \
  --case-id CASE001
```

處理逐字稿並搭配本機影片：

```bash
python3 -m app.cli process \
  --transcript data/transcripts/session_001.srt \
  --video data/videos/session_001.mp4 \
  --case-id CASE001
```

執行內建範例：

```bash
python3 -m app.cli process \
  --transcript examples/sample_transcript.srt \
  --case-id CASE001
```

## 先理解再切點：Manual LLM 模式

Manual LLM 模式不需要 API。第一步會替每句逐字稿加入固定行號，並產生一份要求模型先理解完整上下文、再決定教學事件邊界的提示詞。

建立 LLM 工作包：

```bash
python3 -m app.cli prepare-llm \
  --transcript data/transcripts/demo_first_5min_cleaned.srt \
  --output-dir data/llm_jobs/demo_first_5min
```

輸出檔案：

- `llm_request.md`：貼給 Codex、ChatGPT 或其他 LLM 的完整提示詞。
- `llm_response.template.json`：預期回傳格式的空白範本。

將模型回傳的純 JSON 存成 `llm_response.json` 後，執行：

```bash
python3 -m app.cli process-llm \
  --transcript data/transcripts/demo_first_5min_cleaned.srt \
  --response data/llm_jobs/demo_first_5min/llm_response.json \
  --video data/videos_test/demo_first_5min.mp4 \
  --case-id DEMO_FIRST_5MIN_LLM \
  --cards-dir data/cards/demo_first_5min_llm \
  --index-dir data/index/demo_first_5min_llm \
  --screenshots-dir data/screenshots/demo_first_5min_llm \
  --clips-dir data/clips/demo_first_5min_llm
```

程式會檢查 JSON schema、教學事件類型、影像依賴程度、信心值，以及所有 `L001` 格式的開始與結束行號。只有通過驗證的結果才會產生 Cards。未來接上 API 時，只需要自動產生同格式的 `llm_response.json`，後面的驗證、Card 與媒體流程不必改寫。

## 長影片分段

一小時以上的逐字稿不建議一次交給 LLM。可以切成 10 分鐘區塊，相鄰區塊重疊 45 秒：

```bash
python3 -m app.cli prepare-llm-chunks \
  --transcript data/transcripts/session_full_cleaned.srt \
  --output-dir data/llm_jobs/session_full_chunks \
  --chunk-minutes 10 \
  --overlap-seconds 45
```

每個 chunk 資料夾包含：

- `transcript.srt`：保留完整影片絕對時間的區段逐字稿。
- `llm_request.md`：該區段的 Manual LLM 提示詞。
- `llm_response.template.json`：回傳格式範本。
- `llm_response.json`：完成分析後放入的實際回覆。

根目錄的 `manifest.json` 記錄所有 chunk 的時間、檔案位置與預期 response 路徑。重疊區域用來避免教學事件剛好被切斷；整批完成後仍需合併相鄰 chunk 的重複事件。

## 支援的輸入格式

- `.srt`：可讀取時間戳與字幕文字。
- `.vtt`：可讀取時間戳與字幕文字。
- `.txt`：若沒有時間戳，仍可產生 teaching cards，但不能自動剪片或截圖。
- `.mp4`：選用影片來源，用於擷取 screenshot 或 clip。

Card 流程假設逐字稿已經存在；目前 Whisper 仍由獨立指令在本機執行，尚未整合進 CLI。

## 教學資料管理 Portal

Portal 提供 Dashboard、Case Library、Review Workspace 與 Teaching Set Builder。啟動方式：

```bash
./scripts/start_portal.sh
```

預設網址為 `http://127.0.0.1:8501`。專案可放在 iCloud Drive、Google Drive、Dropbox 或 OneDrive；詳細設定與多電腦同步注意事項請見 `portal/README.md`。

### Supabase 雲端資料庫

公開部署時，去識別化的卡片 metadata、字幕、逐字稿與教案集合可存入 Supabase；大型影片仍應放在獨立的雲端檔案空間。資料表與權限設定請見 [`docs/SUPABASE_SETUP.md`](docs/SUPABASE_SETUP.md)。

Streamlit Community Cloud 的部署欄位、Secrets 與公開權限設定請見 [`docs/STREAMLIT_DEPLOYMENT.md`](docs/STREAMLIT_DEPLOYMENT.md)。

## Teaching Moment 偵測類型

規則模式的 `app/segment_detector.py` 與 Manual LLM 模式共用以下分類：

- `report_wording_correction`
- `diagnostic_reasoning_discussion`
- `impression_refinement`
- `clinical_question_alignment`
- `confidence_calibration`
- `missed_comparison`
- `safety_or_critical_finding_communication`
- `image_evidence_discussion`

偵測規則刻意保持簡單透明，方便之後由教師或工程師直接修改關鍵字。

## 影像依賴程度

每個 segment 會被標成：

- `low`：多半是 report wording、findings/impression 整合、clinical question 等文字討論。
- `moderate`：診斷推理或 confidence calibration，但沒有明確影像定位。
- `high`：出現「你看這裡」、「往上滾」、「往下滾」、「這張」、「對照 DWI/ADC」、「coronal」、「sagittal」等需要影像輔助的語句。

若有影片與時間戳，CLI 會依照 `image_dependency` 與 `suggested_asset` 嘗試擷取 screenshot 或 scroll clip。

## GitHub 公開版

專案可以放上 GitHub，但公開內容應限於程式、文件、測試與完全人工製作的假資料。根目錄的 `.gitignore` 已排除 `data/`、`outputs/`、影片、PPT、虛擬環境、模型快取與 lecture-specific response scripts。

第一次公開建議先建立 **Private repository**，確認 Git 檔案清單沒有臨床素材後，再依院方、IRB 或資料治理規範決定是否改為 Public。完整步驟與誤傳處理方式請見 [`docs/GITHUB_PUBLISHING.md`](docs/GITHUB_PUBLISHING.md)。

### 教學影像選擇原則

影像應以教學正確性為優先，不以畫面完整或排版美觀取代診斷價值。選圖順序如下：

1. 能直接支持該 Card 的 teaching point。
2. 序列、切面、病灶層面與前後比較正確。
3. 病灶及必要解剖範圍可辨識。
4. 最後才考慮畫面完整度、留白與簡報版面。

若單張 screenshot 無法正確呈現多序列比較、捲動定位或動態變化，應優先使用 contact sheet 或 scroll clip，並保留教師人工確認狀態；不可只因影像較完整或較美觀就替換掉更具教學證據的畫面。

## 輸出資料夾說明

- `data/cards/`：每張 teaching card 的 Markdown 與 JSON。
- `data/index/cards_index.csv`：方便搜尋或匯入試算表的索引。
- `data/index/cards_index.json`：方便後續 dashboard 或程式讀取的索引。
- `data/screenshots/`：選用的 key screenshot 輸出位置。
- `data/clips/`：選用的 scroll clip 輸出位置。

## Teaching Card 內容

每張 card 會包含：

- case ID
- source transcript
- source video
- timestamp range
- teaching moment type
- image dependency
- 初步 report issue type
- conversation summary
- optional image evidence
- human review 狀態

需要教師補充的欄位會先填入 `needs human completion`，例如：

- resident report problem
- teacher feedback
- key teaching point
- improved report phrase
- common pitfall
- discussion question
- checklist item for next report

## 測試

```bash
pytest
```

目前測試涵蓋：

- SRT parser 可以讀取時間戳與文字。
- TXT 沒有時間戳時仍可解析。
- detector 可以從 sample transcript 找到 teaching moment。
- teaching card 可以輸出 JSON 與 Markdown。
- 沒有影片時 CLI 流程仍可完成。
- Manual LLM 提示詞包含穩定行號與時間。
- LLM 回傳行號可以正確映射回逐字稿時間。
- 無效或超出範圍的 LLM 行號會被拒絕。
- LLM 內容可以寫入 Teaching Card。

## 下一階段可擴充項目

- Whisper transcription
- 自動 LLM API provider
- 長影片分段、重疊與跨段事件合併
- Human review UI
- DICOM anchor support
- Searchable dashboard
- Teaching slide generation
- AMEE pilot evaluation metrics

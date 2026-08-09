# Supabase 雲端資料庫設定

這個設定會把去識別化的 Teaching Card metadata、字幕、逐字稿與教案集合放在 Supabase。大型影片不放進資料庫，只在 metadata 中保存雲端檔案連結。

## 1. 建立資料表

1. 開啟 Supabase 專案 `radiology-teaching-atlas`。
2. 左側選單進入 **SQL Editor**。
3. 點選 **New query**。
4. 貼上 `supabase/schema.sql` 的全部內容。
5. 點選 **Run**。

執行完成後，Table Editor 應出現：

- `atlas_cases`
- `atlas_teaching_sets`

## 2. 取得 Portal 連線資料

進入 **Project Settings > API Keys**，取得：

- Project URL：`https://ufearyujukdjypyybksp.supabase.co`
- Publishable key；若畫面仍是舊版金鑰，使用 `anon` key

不要使用或公開 `secret`／`service_role` key。它們可略過資料庫權限，不應放入 Portal 或 GitHub。

## 3. 權限說明

第一版尚未加入登入，因此 RLS 允許持有 publishable／anon key 的使用者讀取、新增及修改資料，但不允許刪除。公開網址仍可能被未授權者修改，因此只適合 MVP 討論，且資料必須完成去識別化。

正式使用前應加入 Supabase Auth，將寫入權限改成僅限登入成員。

## 4. 將既有資料升級成多日期結構

如果 `atlas_cases` 已經有 2026-07-07 的 34 張卡片，請在 SQL Editor 執行：

`supabase/migrations/20260809_multi_date_cases.sql`

執行後：

- `record_id`：跨日期唯一鍵，例如 `20260707_CARD001`
- `card_id`：課程內編號，例如 `CARD001`
- `lecture_date`：上課日期
- `source_video`：原始長影片檔名
- `storage_path`：雲端日期資料夾與影片檔名

不同日期可擁有相同的 `CARD001.mp4`，因為實際識別會同時使用日期與卡片編號。

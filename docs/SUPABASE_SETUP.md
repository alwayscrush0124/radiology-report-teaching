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


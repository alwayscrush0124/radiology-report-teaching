-- Upgrade an existing single-date atlas_cases table to multi-date records.
-- Existing 34 cases came from the 2026-07-07 lecture.

alter table public.atlas_cases
  add column if not exists record_id text,
  add column if not exists lecture_date date,
  add column if not exists source_video text not null default '',
  add column if not exists storage_path text not null default '';

update public.atlas_cases
set
  lecture_date = coalesce(lecture_date, date '2026-07-07'),
  source_video = case
    when source_video = '' then '2026-07-07 14-12-27.mp4'
    else source_video
  end;

update public.atlas_cases
set record_id = replace(lecture_date::text, '-', '') || '_' || card_id
where record_id is null or record_id = '';

update public.atlas_cases
set metadata = metadata || jsonb_build_object(
  'record_id', record_id,
  'card_id', card_id,
  'lecture_date', lecture_date::text,
  'source_video', source_video,
  'storage_path', storage_path
);

alter table public.atlas_cases drop constraint if exists atlas_cases_pkey;
alter table public.atlas_cases alter column record_id set not null;
alter table public.atlas_cases alter column lecture_date set not null;
alter table public.atlas_cases add constraint atlas_cases_pkey primary key (record_id);

create index if not exists atlas_cases_lecture_date_card_id
  on public.atlas_cases (lecture_date desc, card_id);

drop policy if exists "atlas cases can be inserted" on public.atlas_cases;
create policy "atlas cases can be inserted"
on public.atlas_cases for insert
to anon, authenticated
with check (record_id <> '' and card_id <> '' and jsonb_typeof(metadata) = 'object');

drop policy if exists "atlas cases can be updated" on public.atlas_cases;
create policy "atlas cases can be updated"
on public.atlas_cases for update
to anon, authenticated
using (true)
with check (record_id <> '' and card_id <> '' and jsonb_typeof(metadata) = 'object');


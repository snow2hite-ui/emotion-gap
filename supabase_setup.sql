-- Run once in Supabase > SQL Editor.
create table if not exists public.emotiongap_runs (
  run_id uuid primary key,
  participant_id text not null,
  run_number integer not null check(run_number >= 1),
  level integer not null check(level between 1 and 5),
  mode text not null check(mode in ('live', 'demo')),
  model text not null,
  answers jsonb not null,
  created_at timestamptz not null default now(),
  unique(participant_id, run_number)
);
create index if not exists emotiongap_runs_participant_idx on public.emotiongap_runs(participant_id);
alter table public.emotiongap_runs enable row level security;
-- No public SELECT/INSERT policies. Only the backend's secret service role accesses rows.
-- If you ran an older 3-level setup, widen the level constraint for levels 4-5.
alter table public.emotiongap_runs drop constraint if exists emotiongap_runs_level_check;
alter table public.emotiongap_runs add constraint emotiongap_runs_level_check check(level between 1 and 5);

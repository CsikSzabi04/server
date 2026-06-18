-- ─────────────────────────────────────────────────────────────────────────────
-- AuriGPT — BRAIN state (the /brain page: stage, stats, layout seed, autonomy,
-- and any learned structures the engine wants to persist). One JSON blob per user.
--
-- Separate migration on purpose: do NOT edit schema.sql (avoids clashing with the
-- existing team). Run in the Supabase dashboard:  SQL Editor → New query → Run.
-- Re-running is safe (idempotent). Row Level Security: each user only sees their
-- own brain_state row (auth.uid() = user_id).
-- ─────────────────────────────────────────────────────────────────────────────

create table if not exists public.brain_state (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  state      jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.brain_state enable row level security;

drop policy if exists "own brain_state" on public.brain_state;
create policy "own brain_state" on public.brain_state
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

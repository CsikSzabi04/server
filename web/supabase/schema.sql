-- ─────────────────────────────────────────────────────────────────────────────
-- AuriGPT — Supabase schema (chat persistence + BRAIN memory)
-- Run in the Supabase dashboard:  SQL Editor → New query → paste → Run.
-- Re-running is safe (idempotent: "if not exists" + "drop policy if exists").
-- Row Level Security ensures each signed-in user only sees their OWN data.
-- ─────────────────────────────────────────────────────────────────────────────

-- Conversations ---------------------------------------------------------------
create table if not exists public.conversations (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users (id) on delete cascade,
  title      text,
  summary    text,
  keywords   text[] default '{}',
  pinned     boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.conversations add column if not exists summary text;
alter table public.conversations add column if not exists keywords text[] default '{}';
alter table public.conversations add column if not exists pinned boolean not null default false;
alter table public.conversations enable row level security;
drop policy if exists "own conversations" on public.conversations;
create policy "own conversations" on public.conversations
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Messages --------------------------------------------------------------------
create table if not exists public.messages (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  user_id         uuid not null references auth.users (id) on delete cascade,
  role            text not null check (role in ('system', 'user', 'assistant')),
  content         text not null,
  created_at      timestamptz not null default now()
);
alter table public.messages enable row level security;
drop policy if exists "own messages" on public.messages;
create policy "own messages" on public.messages
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- User profile (one row per user) — the BRAIN's picture of the user -----------
create table if not exists public.profiles (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  name       text,
  nickname   text,
  language   text,
  tone       text,
  about      text,
  interests  text[] default '{}',
  prefs      jsonb default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
alter table public.profiles enable row level security;
drop policy if exists "own profile" on public.profiles;
create policy "own profile" on public.profiles
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Memories (facts / keywords / document snippets / summaries) ------------------
create table if not exists public.memories (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users (id) on delete cascade,
  kind       text not null default 'fact' check (kind in ('fact', 'keyword', 'doc', 'summary')),
  content    text not null,
  weight     int  not null default 1,
  pinned     boolean not null default false,
  source     text,
  created_at timestamptz not null default now()
);
alter table public.memories enable row level security;
drop policy if exists "own memories" on public.memories;
create policy "own memories" on public.memories
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Indexes ---------------------------------------------------------------------
create index if not exists messages_conversation_idx on public.messages (conversation_id, created_at);
create index if not exists conversations_user_idx on public.conversations (user_id, updated_at desc);
create index if not exists memories_user_idx on public.memories (user_id, created_at desc);

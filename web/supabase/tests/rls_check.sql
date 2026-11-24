-- ─────────────────────────────────────────────────────────────────────────────
-- AuriGPT — Row Level Security self-test (SECURITY.md §4.7, H-16)
--
-- Proves on the REAL database that one user can never read or change another
-- user's data, and that a logged-out (anon) caller sees nothing.
--
-- SAFE TO RUN: everything happens inside ONE transaction that is ROLLED BACK at the
-- end — the two throwaway users and their rows never persist.
-- How: Supabase dashboard → SQL Editor → New query → paste → Run.
--   Success: the last message is  NOTICE: RLS OK — …
--   Failure: an ERROR starting with "RLS FAIL" names the table and the problem.
-- Run it after every schema / policy change (SECURITY.md §28.2).
-- ─────────────────────────────────────────────────────────────────────────────
begin;

-- 0) Every table in `public` must have RLS switched on.
do $$
declare t text;
begin
  for t in select tablename from pg_tables where schemaname = 'public' and not rowsecurity loop
    raise exception 'RLS FAIL: table public.% has Row Level Security DISABLED', t;
  end loop;
end $$;

-- 1) Two throwaway users (rolled back at the end) and user A's data.
insert into auth.users (id, email) values
  ('00000000-0000-4000-a000-0000000000a1', 'rls-test-a@example.invalid'),
  ('00000000-0000-4000-a000-0000000000b2', 'rls-test-b@example.invalid');

insert into public.profiles (user_id, name) values ('00000000-0000-4000-a000-0000000000a1', 'User A');
insert into public.memories (user_id, kind, content) values ('00000000-0000-4000-a000-0000000000a1', 'fact', 'A private fact');
insert into public.conversations (id, user_id, title)
  values ('00000000-0000-4000-c000-0000000000c1', '00000000-0000-4000-a000-0000000000a1', 'A private chat');
insert into public.messages (conversation_id, user_id, role, content)
  values ('00000000-0000-4000-c000-0000000000c1', '00000000-0000-4000-a000-0000000000a1', 'user', 'hello from A');
-- brain_state is optional (separate migration)
do $$ begin
  if to_regclass('public.brain_state') is not null then
    insert into public.brain_state (user_id, state) values ('00000000-0000-4000-a000-0000000000a1', '{"vocab":{}}');
  end if;
end $$;

-- 2) Act as USER B (a real signed-in user, but not the owner).
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-4000-a000-0000000000b2","role":"authenticated"}', true);

do $$
declare
  n int;
  t text;
  a constant uuid := '00000000-0000-4000-a000-0000000000a1';
begin
  -- B must not SEE anything of A
  foreach t in array array['profiles', 'memories', 'conversations', 'messages', 'brain_state'] loop
    if to_regclass('public.' || t) is null then continue; end if;
    execute format('select count(*) from public.%I where user_id = $1', t) into n using a;
    if n <> 0 then raise exception 'RLS FAIL: user B can read % row(s) of user A in public.%', n, t; end if;
  end loop;

  -- B must not CHANGE or DELETE anything of A (RLS filters the rows → 0 affected)
  update public.memories set content = 'tampered' where user_id = a;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'RLS FAIL: user B updated % memory row(s) of user A', n; end if;
  delete from public.messages where user_id = a;
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'RLS FAIL: user B deleted % message row(s) of user A', n; end if;

  -- B must not WRITE rows in A's name (with check → error 42501)
  begin
    insert into public.memories (user_id, kind, content) values (a, 'fact', 'forged by B');
    raise exception 'RLS FAIL: user B inserted a memory as user A';
  exception when insufficient_privilege then null; -- expected
  end;
  begin
    insert into public.messages (conversation_id, user_id, role, content)
      values ('00000000-0000-4000-c000-0000000000c1', a, 'user', 'forged by B');
    raise exception 'RLS FAIL: user B inserted a message as user A';
  exception when insufficient_privilege then null; -- expected
  end;
end $$;

-- 3) Act as a LOGGED-OUT visitor (anon key, no user).
reset role;
set local role anon;
select set_config('request.jwt.claims', '{"role":"anon"}', true);

do $$
declare n int; t text;
begin
  foreach t in array array['profiles', 'memories', 'conversations', 'messages', 'brain_state'] loop
    if to_regclass('public.' || t) is null then continue; end if;
    begin
      execute format('select count(*) from public.%I', t) into n;
    exception when insufficient_privilege then n := 0; -- no grant at all = also fine
    end;
    if n <> 0 then raise exception 'RLS FAIL: a logged-out visitor can read % row(s) in public.%', n, t; end if;
  end loop;
  -- anon must not be able to call the account deletion function
  begin
    perform public.delete_my_account();
    raise exception 'RLS FAIL: anon could call delete_my_account()';
  exception
    when insufficient_privilege then null; -- expected (no EXECUTE grant / not signed in)
    when undefined_function then null;    -- delete_account.sql not installed yet
  end;
end $$;

-- 4) Act as USER A (the owner): A must see A's own data.
reset role;
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-4000-a000-0000000000a1","role":"authenticated"}', true);

do $$
declare n int;
begin
  select count(*) into n from public.memories;
  if n <> 1 then raise exception 'RLS FAIL: the owner sees % of their 1 memory row', n; end if;
  select count(*) into n from public.messages;
  if n <> 1 then raise exception 'RLS FAIL: the owner sees % of their 1 message row', n; end if;
  raise notice 'RLS OK — other users and logged-out visitors cannot read or change anyone''s data; owners see their own.';
end $$;

reset role;
rollback; -- nothing of this test is kept

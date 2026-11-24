-- ─────────────────────────────────────────────────────────────────────────────
-- AuriGPT — "delete my account" (GDPR art. 17, SECURITY.md §16.1, H-6).
--
-- Run ONCE in the Supabase dashboard:  SQL Editor → New query → paste → Run.
-- Re-running is safe (create or replace).
--
-- What it does: a signed-in user calls  supabase.rpc('delete_my_account')  and their
-- auth.users row is deleted. Every AuriGPT table references auth.users with
-- ON DELETE CASCADE (conversations, messages, profiles, memories, brain_state), so
-- ALL of the user's data goes with it, in one transaction.
--
-- Why it is safe:
--   • It takes NO parameters — the id comes from auth.uid() (the caller's own verified
--     JWT), so nobody can delete anyone else's account.
--   • SECURITY DEFINER is needed to delete from auth.users; search_path is pinned to ''
--     and every name is schema-qualified, so it can't be hijacked.
--   • Only the `authenticated` role may execute it (not anon, not public).
-- ─────────────────────────────────────────────────────────────────────────────

create or replace function public.delete_my_account()
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  uid uuid := auth.uid();
begin
  if uid is null then
    raise exception 'not signed in' using errcode = '42501';
  end if;
  delete from auth.users where id = uid;
end;
$$;

revoke all on function public.delete_my_account() from public;
revoke all on function public.delete_my_account() from anon;
grant execute on function public.delete_my_account() to authenticated;

comment on function public.delete_my_account() is
  'Deletes the CALLER''s own account (auth.uid()) and, via ON DELETE CASCADE, all of their AuriGPT data.';

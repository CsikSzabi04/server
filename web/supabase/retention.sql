-- ─────────────────────────────────────────────────────────────────────────────
-- AuriGPT — retention for INACTIVE accounts (GDPR art. 5(1)(e) storage limitation,
-- SECURITY.md §15.6, H-7). OPTIONAL — installing it changes nothing by itself.
--
-- Run once in the Supabase SQL Editor to install. Then:
--   select * from public.inactive_accounts(24);              -- who WOULD be deleted (read-only)
--   select public.purge_inactive_accounts(24, true);          -- dry run: count only
--   select public.purge_inactive_accounts(24, false);         -- really delete (cascade)
--
-- "Inactive" = no sign-in AND no chat message for `months` months (default 24).
-- Deleting the auth.users row removes ALL of the user's AuriGPT data (ON DELETE CASCADE).
--
-- Only the database owner / service role can run these (not anon, not signed-in users).
-- Before turning on a schedule: announce the rule in /adatvedelem.html, and ideally
-- e-mail affected users ~30 days in advance (Supabase cannot e-mail from SQL; do it
-- from a small server job using the list from inactive_accounts()).
-- ─────────────────────────────────────────────────────────────────────────────

create or replace function public.inactive_accounts(months int default 24)
returns table (user_id uuid, email text, last_sign_in_at timestamptz, last_message_at timestamptz)
language sql
stable
security definer
set search_path = ''
as $$
  select u.id, u.email::text, u.last_sign_in_at, m.last_message_at
  from auth.users u
  left join lateral (
    select max(msg.created_at) as last_message_at from public.messages msg where msg.user_id = u.id
  ) m on true
  where coalesce(greatest(u.last_sign_in_at, m.last_message_at), u.created_at)
        < now() - make_interval(months => greatest(months, 6))   -- never shorter than 6 months
$$;

create or replace function public.purge_inactive_accounts(months int default 24, dry_run boolean default true)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  n integer;
begin
  select count(*) into n from public.inactive_accounts(months);
  if not dry_run then
    delete from auth.users where id in (select ia.user_id from public.inactive_accounts(months) ia);
  end if;
  return n;
end;
$$;

-- Not callable through the public API (anon / authenticated): owner & service role only.
revoke all on function public.inactive_accounts(int) from public, anon, authenticated;
revoke all on function public.purge_inactive_accounts(int, boolean) from public, anon, authenticated;

-- Optional schedule (needs the pg_cron extension: Database → Extensions → pg_cron):
-- select cron.schedule('auri-purge-inactive', '0 3 1 * *',
--   $$select public.purge_inactive_accounts(24, false)$$);

-- Install or repair the registration RPC used by POST /api/registrations.
-- Run in the Supabase SQL Editor. No authentication is introduced.
create or replace function public.create_event_registration(
    p_user_id uuid,
    p_event_id uuid
)
returns public.registrations
language plpgsql
security definer
set search_path = ''
as $$
declare
    selected_event public.events%rowtype;
    new_registration public.registrations%rowtype;
begin
    select * into selected_event
      from public.events
     where id = p_event_id
     for update;

    if not found then
        raise exception 'event_not_found' using errcode = 'P0001';
    end if;

    if not exists (select 1 from public.users where id = p_user_id) then
        raise exception 'user_not_found' using errcode = 'P0001';
    end if;

    if exists (
        select 1 from public.registrations
         where user_id = p_user_id and event_id = p_event_id
    ) then
        raise exception 'registration_duplicate' using errcode = 'P0001';
    end if;

    if (select count(*) from public.registrations where event_id = p_event_id)
        >= selected_event.capacity then
        raise exception 'event_full' using errcode = 'P0001';
    end if;

    insert into public.registrations (user_id, event_id)
    values (p_user_id, p_event_id)
    returning * into new_registration;

    return new_registration;
end;
$$;

revoke all on function public.create_event_registration(uuid, uuid) from public;
grant execute on function public.create_event_registration(uuid, uuid) to anon;

-- Make PostgREST discover the newly installed function immediately.
notify pgrst, 'reload schema';

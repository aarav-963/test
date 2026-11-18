-- Events API schema. This project intentionally has no authentication or
-- authorization: these anon policies make the listed API data public.

create table if not exists public.users (
    id uuid primary key default gen_random_uuid(),
    email text not null unique,
    role text
);

create table if not exists public.events (
    id uuid primary key default gen_random_uuid(),
    organizer_id uuid not null references public.users(id) on delete restrict,
    title text not null,
    capacity integer not null check (capacity > 0),
    status text not null default 'open'
);

create table if not exists public.registrations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    event_id uuid not null references public.events(id) on delete cascade,
    created_at timestamptz not null default now(),
    constraint registrations_one_per_user_event unique (user_id, event_id)
);

create index if not exists events_organizer_id_idx
    on public.events (organizer_id);
create index if not exists registrations_event_created_at_idx
    on public.registrations (event_id, created_at);
create index if not exists registrations_user_created_at_idx
    on public.registrations (user_id, created_at desc);

-- Serialize registrations for one event while checking capacity. The unique
-- constraint remains a second line of defense against duplicate signups.
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

-- Tables are in the exposed public schema, so enable RLS and grant the anon
-- role only the operations this backend uses. Policies are intentionally
-- unrestricted because the requested backend has no authorization.
alter table public.users enable row level security;
alter table public.events enable row level security;
alter table public.registrations enable row level security;

drop policy if exists users_public_read on public.users;
create policy users_public_read on public.users
    for select to anon using (true);

drop policy if exists events_public_read on public.events;
create policy events_public_read on public.events
    for select to anon using (true);

drop policy if exists registrations_public_read on public.registrations;
create policy registrations_public_read on public.registrations
    for select to anon using (true);
drop policy if exists registrations_public_insert on public.registrations;
create policy registrations_public_insert on public.registrations
    for insert to anon with check (true);

grant usage on schema public to anon;
grant select (id, email, role) on public.users to anon;
grant select on public.events to anon;
grant select on public.registrations to anon;
revoke insert on public.registrations from anon;
revoke all on function public.create_event_registration(uuid, uuid) from public;
grant execute on function public.create_event_registration(uuid, uuid) to anon;

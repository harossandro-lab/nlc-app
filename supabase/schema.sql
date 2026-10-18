-- Next Level Construction — Supabase (Postgres) schema for team sync.
-- Run once in the Supabase SQL editor. Generic row store: one row per local record,
-- keyed by (table_name, uid). The server clock orders changes (seq), so device clocks never matter.

create table if not exists profiles (
    user_id uuid primary key references auth.users(id) on delete cascade,
    role    text not null check (role in ('admin', 'office', 'field')),
    name    text default ''
);

create sequence if not exists sync_rows_seq_gen;

create table if not exists sync_rows (
    seq        bigint  not null default nextval('sync_rows_seq_gen'),
    table_name text    not null check (table_name in
               ('projects','project_info','suppliers','materials_db','takeoff_items','received_log','audit_log')),
    uid        text    not null,
    project_id text    not null,
    data       jsonb   not null default '{}'::jsonb,
    deleted    boolean not null default false,
    updated_at timestamptz not null default now(),
    updated_by uuid default auth.uid(),
    primary key (table_name, uid)
);
create unique index if not exists sync_rows_seq_idx on sync_rows(seq);
create index if not exists sync_rows_project on sync_rows(project_id);

-- Every write gets a fresh seq (last writer wins) and the server timestamp.
create or replace function sync_rows_touch() returns trigger language plpgsql as $$
begin
    new.seq := nextval('sync_rows_seq_gen');
    new.updated_at := now();
    new.updated_by := auth.uid();
    return new;
end $$;
drop trigger if exists sync_rows_touch on sync_rows;
create trigger sync_rows_touch before insert or update on sync_rows
    for each row execute function sync_rows_touch();

create or replace function my_role() returns text language sql stable security definer as $$
    select role from profiles where user_id = auth.uid()
$$;

alter table profiles  enable row level security;
alter table sync_rows enable row level security;

create policy "read own profile" on profiles for select using (user_id = auth.uid());
create policy "admin manages profiles" on profiles for all using (my_role() = 'admin') with check (my_role() = 'admin');

-- Everyone with a role can read. admin and office write everything; field writes only deliveries (Received).
create policy "read" on sync_rows for select using (my_role() is not null);
create policy "write admin/office" on sync_rows for insert with check (my_role() in ('admin','office'));
create policy "update admin/office" on sync_rows for update using (my_role() in ('admin','office'))
    with check (my_role() in ('admin','office'));
create policy "field writes received" on sync_rows for insert with check (my_role() = 'field' and table_name = 'received_log');
create policy "field updates received" on sync_rows for update using (my_role() = 'field' and table_name = 'received_log')
    with check (my_role() = 'field' and table_name = 'received_log');
-- No delete policy: removals are tombstones (deleted = true), so every device learns about them.

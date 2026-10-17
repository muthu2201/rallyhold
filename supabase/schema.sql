-- Rallyhold - production schema for Supabase (Postgres)
-- Apply with: supabase db push, or paste into the SQL editor.

create extension if not exists "pgcrypto";

-- ---------- reference data ----------
create table if not exists countries (
  id   bigint generated always as identity primary key,
  code text unique not null,           -- ISO-2, e.g. 'US'
  name text not null
);

create table if not exists cities (
  id         bigint generated always as identity primary key,
  country_id bigint not null references countries(id) on delete cascade,
  name       text not null,
  slug       text not null,
  lat        double precision,
  lng        double precision,
  unique (country_id, slug)
);

-- ---------- core listing ----------
create table if not exists courts (
  id            bigint generated always as identity primary key,
  name          text not null,
  slug          text unique not null,
  city_id       bigint references cities(id) on delete set null,
  sport         text not null check (sport in ('pickleball','padel','both')),
  courts_count  int  not null default 1 check (courts_count >= 0),
  indoor        boolean not null default false,
  outdoor       boolean not null default true,
  surface       text,
  price_note    text,
  rating        numeric(2,1) not null default 0 check (rating between 0 and 5),
  reviews_count int not null default 0,
  lat           double precision,
  lng           double precision,
  website       text,
  phone         text,
  amenities     text[] not null default '{}',
  verified      boolean not null default false,
  featured      boolean not null default false,
  status        text not null default 'published' check (status in ('draft','published','hidden')),
  source        text not null default 'manual',   -- 'manual' | 'apify' | 'submission'
  external_id   text,                              -- dedupe key from a scraper
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create unique index if not exists courts_external_uidx
  on courts (source, external_id) where external_id is not null;
create index if not exists courts_city_idx   on courts (city_id);
create index if not exists courts_sport_idx  on courts (sport);
create index if not exists courts_status_idx on courts (status);
create index if not exists courts_feat_idx   on courts (featured, rating desc);
create index if not exists courts_name_trgm  on courts using gin (name gin_trgm_ops);

-- ---------- inbound: leads, submissions, claims ----------
create table if not exists leads (
  id         bigint generated always as identity primary key,
  court_id   bigint references courts(id) on delete set null,
  name       text,
  email      text not null,
  phone      text,
  message    text,
  created_at timestamptz not null default now()
);

create table if not exists submissions (
  id         bigint generated always as identity primary key,
  name       text not null,
  city       text,
  country    text,
  email      text,
  notes      text,
  status     text not null default 'new' check (status in ('new','approved','rejected')),
  created_at timestamptz not null default now()
);

create table if not exists claims (
  id         bigint generated always as identity primary key,
  court_id   bigint not null references courts(id) on delete cascade,
  email      text not null,
  note       text,
  status     text not null default 'pending' check (status in ('pending','approved','rejected')),
  created_at timestamptz not null default now()
);

-- ---------- admin allow-list ----------
create table if not exists admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email   text
);

-- ---------- helpers ----------
create or replace function set_updated_at() returns trigger
language plpgsql as $$ begin new.updated_at = now(); return new; end; $$;

drop trigger if exists courts_updated on courts;
create trigger courts_updated before update on courts
for each row execute function set_updated_at();

create or replace function is_admin() returns boolean
language sql stable as $$
  select exists (select 1 from admins a where a.user_id = auth.uid());
$$;

-- ---------- row level security ----------
alter table countries   enable row level security;
alter table cities      enable row level security;
alter table courts      enable row level security;
alter table leads       enable row level security;
alter table submissions enable row level security;
alter table claims      enable row level security;
alter table admins      enable row level security;

-- public read of the catalogue
create policy "public read countries" on countries for select using (true);
create policy "public read cities"    on cities    for select using (true);
create policy "public read courts"    on courts    for select using (status = 'published');

-- public write for inbound forms (insert only)
create policy "anyone can send a lead"      on leads       for insert with check (true);
create policy "anyone can submit a court"   on submissions for insert with check (true);
create policy "anyone can claim a listing"  on claims      for insert with check (true);

-- admin: full control, gated by the admins allow-list
create policy "admin manages courts"      on courts      for all    using (is_admin()) with check (is_admin());
create policy "admin reads leads"         on leads       for select using (is_admin());
create policy "admin reads submissions"   on submissions for select using (is_admin());
create policy "admin updates submissions" on submissions for update using (is_admin());
create policy "admin reads claims"        on claims      for select using (is_admin());
create policy "admin reads admins"        on admins      for select using (auth.uid() = user_id);

-- Promote your first admin after you sign up (run once, with your auth user id):
--   insert into admins (user_id, email) values ('<uuid-from-auth.users>', 'you@email.com');

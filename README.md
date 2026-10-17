# Rallyhold

A full-stack directory of pickleball and padel courts worldwide: a static
frontend, a Supabase (Postgres) backend with row-level security, and an Apify
pipeline for ingesting real court data. No payment handling anywhere.

## Architecture

```
  Browser (static site)            Supabase                      Apify
  ┌───────────────────┐   REST   ┌──────────────────┐  seed   ┌──────────────┐
  │ index.html        │ ───────▶ │ Postgres + RLS   │ ◀────── │ Google Maps  │
  │ court.html        │  anon    │ courts, cities,  │  python │ places actor │
  │ admin.html (auth) │  key     │ leads, subs...   │         └──────────────┘
  └───────────────────┘          └──────────────────┘
   hosted on GitHub Pages         auto REST via PostgREST
```

- **Frontend** - plain HTML/CSS/JS, no build step, no framework. Talks to
  Supabase's auto-generated REST API. Runs in *demo mode* with bundled sample
  data until you plug in a backend.
- **Backend** - Supabase Postgres. Public read on the catalogue, public insert
  on the inbound forms (leads/submissions/claims), and admin-only writes gated
  by an `admins` allow-list.
- **Ingestion** - Apify runs a Google Maps scraper per city; `seed.py` upserts
  the results into Supabase. Re-runnable and idempotent.

## Repo layout

```
public/            the deployed site (served by GitHub Pages)
  index.html       explore: search, filters, map, ads, affiliate, add-a-court
  court.html       court detail: map, enquiry form, claim-listing
  admin.html       auth-gated dashboard: leads, submissions, listings
  app.js           shared data layer (live Supabase or demo sample data)
  styles.css       shared design system
  config.js        Supabase URL + anon key  <-- the only file you must edit
  sample-data.js   bundled demo listings
supabase/
  schema.sql       tables, indexes, RLS policies, triggers
scripts/
  fetch_apify.py   pull real courts from Google Maps via Apify
seed.py            load a courts JSON file into Supabase
.github/workflows/
  pages.yml        deploys public/ to GitHub Pages on push
```

## Quick start (demo mode)

Open `public/index.html` in a browser. It runs with the bundled sample data -
no backend needed. Everything works except the forms, which no-op until you
connect Supabase.

## Go live

1. **Create a Supabase project** at supabase.com (free tier is fine).
2. **Apply the schema**: paste `supabase/schema.sql` into the project's SQL
   editor and run it (or `supabase db push` with the CLI).
3. **Wire the frontend**: copy the Project URL and the public `anon` key from
   *Project Settings > API* into `public/config.js`. The site flips to live mode.
4. **Seed data**:
   ```
   export SUPABASE_URL=https://xxxx.supabase.co
   export SUPABASE_SERVICE_KEY=...        # service_role key - server-side only
   python seed.py public/sample-data.json # demo data; or a real courts.json
   ```
5. **Create your admin**: sign up once in the app (or Supabase Auth dashboard),
   then in the SQL editor:
   ```sql
   insert into admins (user_id, email)
   values ('<your-auth-user-uuid>', 'you@email.com');
   ```
   Sign in at `admin.html`.
6. **Deploy**: push this repo to GitHub and enable Pages (Settings > Pages >
   Source: GitHub Actions). The workflow publishes `public/`.
7. **Domain + SEO**: add a custom domain in Pages settings, then verify it in
   Google Search Console.

## Data

The bundled `public/sample-data.js` holds **real courts** (219 across 12 cities)
pulled from Google Maps, so the preview shows genuine listings. Three ways to
grow the catalogue, all without paying for a data licence:

1. **Crowdsourced (the long-term engine)** - visitors add courts via the
   "Add a court" form; admins approve them in the dashboard. This is the model
   that scales for free.
2. **Free scraping** - `scripts/fetch_overpass.py` pulls courts from
   OpenStreetMap's Overpass API (no key, no cost). Note: some sandboxes block
   Overpass; run it from your own machine or a small VPS.
3. **Paid scraping (optional)** - `scripts/fetch_apify.py` uses the Google Maps
   actor. It is pay-per-place (~$0.002/place) and the actor's free monthly
   allowance covers a first pass; run it when you want fresh, richer data.

Court records carry `source` and `external_id`, so re-runs update rather than
duplicate. Import in bulk from the admin dashboard, or with `python seed.py courts.json`.

## Monetisation slots

- Display ad placeholders (leaderboard + in-grid native card).
- Affiliate "Gear up" cards - swap the `#` hrefs for your affiliate links.
- "Get featured" upsell for clubs - the `featured` flag drives placement.

## Security notes

- The `anon` key is public by design; RLS is what protects the data.
- The `service_role` key bypasses RLS - keep it server-side only, never in
  `public/`.
- Inbound forms are insert-only for anonymous users; nothing else is exposed.

## Roadmap

- Real photo galleries and opening hours per court.
- Email alerts on new leads (Gmail connector or a transactional provider).
- Scheduled weekly re-scrape via a cron job.
- Programmatic city and country landing pages for SEO.

// Rallyhold shared data layer + helpers.
// Live mode talks to Supabase PostgREST; demo mode uses the bundled sample data.

const CFG = window.RALLYHOLD_CONFIG || {};
const LIVE = !!(CFG.SUPABASE_URL && CFG.SUPABASE_ANON_KEY);
const $  = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));

const SPORT_LABEL = { pickleball: "Pickleball", padel: "Padel", both: "Pickleball + Padel" };
const stars = r => { const n = Math.round(r || 0); return "\u2605".repeat(n) + "\u2606".repeat(5 - n); };
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const dirLink = d => `https://www.google.com/maps/dir/?api=1&destination=${d.lat},${d.lng}`;

async function sb(path) {
  const base = CFG.SUPABASE_URL.replace(/\/$/, "");
  const r = await fetch(`${base}/rest/v1/${path}`, {
    headers: { apikey: CFG.SUPABASE_ANON_KEY, Authorization: "Bearer " + CFG.SUPABASE_ANON_KEY },
  });
  if (!r.ok) throw new Error("Supabase " + r.status + ": " + (await r.text()).slice(0, 120));
  return r.json();
}

async function sbInsert(table, body) {
  const base = CFG.SUPABASE_URL.replace(/\/$/, "");
  const r = await fetch(`${base}/rest/v1/${table}`, {
    method: "POST",
    headers: {
      apikey: CFG.SUPABASE_ANON_KEY,
      Authorization: "Bearer " + CFG.SUPABASE_ANON_KEY,
      "Content-Type": "application/json",
      Prefer: "return=minimal",
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error("Insert " + r.status + ": " + (await r.text()).slice(0, 120));
}

const SELECT = "id,name,slug,sport,courts_count,indoor,outdoor,surface,price_note,rating,reviews_count,lat,lng,website,phone,amenities,verified,featured,city:cities(name,country:countries(name,code))";

function norm(row) {
  if (!LIVE) return row;                 // sample data is already flat
  const city = row.city || {}, country = city.country || {};
  return {
    id: row.id, name: row.name, slug: row.slug,
    city: city.name || "", country: country.name || "", cc: country.code || "",
    lat: row.lat, lng: row.lng,
    sport: SPORT_LABEL[row.sport] || row.sport, sportKey: row.sport,
    courts: row.courts_count, indoor: row.indoor, outdoor: row.outdoor,
    surface: row.surface || "", price: row.price_note || "",
    rating: Number(row.rating) || 0, reviews: row.reviews_count || 0,
    amenities: row.amenities || [], featured: !!row.featured, verified: !!row.verified,
    website: row.website, phone: row.phone,
  };
}

async function getCourts() {
  if (!LIVE) return (window.SAMPLE_COURTS || []).slice();
  const rows = await sb(`courts?select=${SELECT}&status=eq.published&order=featured.desc,rating.desc&limit=1000`);
  return rows.map(norm);
}

async function getCourt(key) {
  if (!LIVE) return (window.SAMPLE_COURTS || []).find(c => String(c.slug) === String(key) || String(c.id) === String(key)) || null;
  const col = /^\d+$/.test(key) ? "id" : "slug";
  const rows = await sb(`courts?select=${SELECT}&${col}=eq.${encodeURIComponent(key)}&limit=1`);
  return rows.length ? norm(rows[0]) : null;
}

function mountMode() {
  const el = $("#modebar");
  if (!el) return;
  el.className = "modebar" + (LIVE ? " live" : "");
  el.textContent = LIVE
    ? "Live \u2014 connected to Supabase"
    : "Preview \u2014 bundled listing data. Add your Supabase URL + anon key in config.js to go live.";
}

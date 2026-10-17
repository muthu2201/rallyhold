#!/usr/bin/env python3
"""Seed a Supabase project with Rallyhold court data.

Usage:
    export SUPABASE_URL=https://xxxx.supabase.co
    export SUPABASE_SERVICE_KEY=...      # service_role key - server-side only, never ship to the browser
    python seed.py courts.json           # or: python seed.py ../public/sample-data.json

Idempotent: re-running upserts on (country code), (city slug), (court slug).
"""
import json, os, re, sys, urllib.request

URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
if not URL or not KEY:
    sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")

def req(method, path, body=None, prefer=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{URL}/rest/v1/{path}", data=data, method=method)
    r.add_header("apikey", KEY)
    r.add_header("Authorization", "Bearer " + KEY)
    r.add_header("Content-Type", "application/json")
    if prefer:
        r.add_header("Prefer", prefer)
    with urllib.request.urlopen(r, timeout=120) as resp:
        txt = resp.read().decode()
    return json.loads(txt) if txt else None

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")

def upsert(table, rows, conflict, cols="*"):
    if not rows:
        return []
    return req("POST", f"{table}?on_conflict={conflict}&select={cols}", rows,
               prefer="resolution=merge-duplicates,return=representation") or []

def main(path):
    rows = json.load(open(path))
    print(f"loaded {len(rows)} courts from {path}")

    # countries
    cc = {}
    for r in rows:
        code = (r.get("cc") or r.get("country") or "")[:2].upper()
        if code and r.get("country"):
            cc[code] = r["country"]
    countries = upsert("countries", [{"code": c, "name": n} for c, n in cc.items()], "code", "id,code")
    cmap = {c["code"]: c["id"] for c in countries}
    print(f"countries: {len(cmap)}")

    # cities
    city_rows, seen = [], set()
    for r in rows:
        code = (r.get("cc") or r.get("country") or "")[:2].upper()
        if not r.get("city") or code not in cmap:
            continue
        key = (cmap[code], slug(r["city"]))
        if key in seen:
            continue
        seen.add(key)
        city_rows.append({"country_id": cmap[code], "name": r["city"], "slug": slug(r["city"]),
                          "lat": r.get("lat"), "lng": r.get("lng")})
    cities = upsert("cities", city_rows, "country_id,slug", "id,country_id,slug")
    city_map = {(c["country_id"], c["slug"]): c["id"] for c in cities}
    print(f"cities: {len(city_map)}")

    # courts
    court_rows = []
    for r in rows:
        code = (r.get("cc") or r.get("country") or "")[:2].upper()
        city_id = city_map.get((cmap.get(code), slug(r.get("city", ""))))
        court_rows.append({
            "name": r["name"],
            "slug": r.get("slug") or f'{slug(r["name"])}-{slug(r.get("city",""))}',
            "city_id": city_id,
            "sport": r.get("sportKey") or r.get("sport") or "pickleball",
            "courts_count": r.get("courts") or r.get("courts_count") or 1,
            "indoor": bool(r.get("indoor")), "outdoor": bool(r.get("outdoor", True)),
            "surface": r.get("surface") or None,
            "price_note": r.get("price") or r.get("price_note") or None,
            "rating": r.get("rating") or 0,
            "reviews_count": r.get("reviews") or r.get("reviews_count") or 0,
            "lat": r.get("lat"), "lng": r.get("lng"),
            "website": r.get("website"), "phone": r.get("phone"),
            "amenities": r.get("amenities") or [],
            "featured": bool(r.get("featured")), "verified": bool(r.get("verified")),
            "source": r.get("source") or "manual",
            "external_id": r.get("external_id"),
            "status": "published",
        })
    done = 0
    for i in range(0, len(court_rows), 200):
        chunk = court_rows[i:i+200]
        upsert("courts", chunk, "slug", "id")
        done += len(chunk)
        print(f"courts upserted: {done}/{len(court_rows)}")
    print("done.")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "courts.json")

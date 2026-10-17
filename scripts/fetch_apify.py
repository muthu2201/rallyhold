#!/usr/bin/env python3
"""Pull real pickleball/padel courts from Google Maps via Apify.

Usage:
    export APIFY_TOKEN=...            # apify.com > Settings > API tokens
    python scripts/fetch_apify.py --cities "Austin TX,London UK,Dubai UAE" --out courts.json

Runs the actor johnvc/google-maps-places-api (cheap, bulk) and normalises the
output into the shape Rallyhold expects (see seed.py).
"""
import argparse, json, os, sys, time, urllib.request, urllib.parse

ACTOR = "johnvc~google-maps-places-api"
BASE = "https://api.apify.com/v2"
TOKEN = os.environ.get("APIFY_TOKEN", "")

def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    url = f"{BASE}/{path}{'&' if '?' in path else '?'}token={TOKEN}"
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.loads(resp.read().decode())

def run(cities, per_city):
    term = ["pickleball court", "padel club"]
    jobs = []
    for city in cities:
        for t in term:
            jobs.append({"searchTerms": [t], "location": city, "maxResultsPerSearch": per_city})
    # one run per (term, city) keeps locations clean; batch here for brevity
    out = []
    for job in jobs:
        run = api("POST", f"acts/{ACTOR}/runs", job)["data"]
        rid = run["id"]
        while True:
            st = api("GET", f"actor-runs/{rid}")["data"]
            if st["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                break
            time.sleep(6)
        if st["status"] != "SUCCEEDED":
            print("run failed:", st["status"], file=sys.stderr); continue
        items = api("GET", f"datasets/{st['defaultDatasetId']}/items?clean=true&limit=1000")
        out.extend(items)
        print(f"{job['location']} / {job['searchTerms'][0]}: {len(items)} places")
    return out

def norm(p):
    def pick(*keys):
        for k in keys:
            if p.get(k) not in (None, "", []):
                return p[k]
        return None
    loc = p.get("location") or {}
    addr = p.get("address") or p.get("fullAddress") or ""
    return {
        "name": pick("title", "name") or "Unnamed court",
        "city": pick("city", "addressLocality") or "",
        "country": pick("countryCode", "country") or "",
        "lat": pick("lat") or loc.get("lat"),
        "lng": pick("lng") or loc.get("lng"),
        "sport": "padel" if "padel" in (pick("categoryName", "category") or "").lower() else "pickleball",
        "rating": pick("totalScore", "rating") or 0,
        "reviews": pick("reviewsCount", "reviewCount") or 0,
        "website": pick("website", "url"),
        "phone": pick("phone", "phoneNumber"),
        "surface": "", "price": "", "amenities": [],
        "source": "apify",
        "external_id": pick("placeId", "id", "cid"),
        "raw_address": addr,
    }

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cities", required=True, help="comma-separated 'City Country' list")
    ap.add_argument("--per-city", type=int, default=30)
    ap.add_argument("--out", default="courts.json")
    a = ap.parse_args()
    if not TOKEN:
        sys.exit("Set APIFY_TOKEN first.")
    cities = [c.strip() for c in a.cities.split(",") if c.strip()]
    raw = run(cities, a.per_city)
    rows = [norm(p) for p in raw if norm(p)["lat"]]
    json.dump(rows, open(a.out, "w"), indent=1)
    print(f"wrote {len(rows)} courts to {a.out}")

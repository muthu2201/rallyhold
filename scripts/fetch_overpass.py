#!/usr/bin/env python3
"""Free court discovery from OpenStreetMap via the Overpass API.

No API key and no cost. Queries pickleball and padel courts either for a whole
country (by ISO code) or a bounding box, and writes them in the Rallyhold shape
that seed.py and the admin bulk-import expect.

Usage:
    python scripts/fetch_overpass.py --country US --out courts.json
    python scripts/fetch_overpass.py --bbox "50.0,13.0,51.0,15.0" --out courts.json

Note: some hosted sandboxes block overpass-api.de. Run this from your own
machine, a small VPS, or GitHub Actions - it needs plain outbound HTTPS.
"""
import argparse, json, re, sys, urllib.parse, urllib.request

ENDPOINT = "https://overpass-api.de/api/interpreter"
ISO_NAME = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom", "IE": "Ireland",
    "FR": "France", "ES": "Spain", "PT": "Portugal", "IT": "Italy", "DE": "Germany",
    "NL": "Netherlands", "BE": "Belgium", "SE": "Sweden", "NO": "Norway", "DK": "Denmark",
    "CH": "Switzerland", "AT": "Austria", "PL": "Poland", "AE": "United Arab Emirates",
    "IN": "India", "SG": "Singapore", "AU": "Australia", "NZ": "New Zealand",
    "JP": "Japan", "BR": "Brazil", "MX": "Mexico", "ZA": "South Africa", "TH": "Thailand",
}

def slug(s): return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")

def run(selector):
    q = f"[out:json][timeout:180];\n({selector}\n);\nout center tags;"
    data = urllib.parse.urlencode({"data": q}).encode()
    req = urllib.request.Request(ENDPOINT, data=data, headers={"User-Agent": "Rallyhold/0.1"})
    with urllib.request.urlopen(req, timeout=220) as r:
        return json.loads(r.read().decode())["elements"]

def selector(country, bbox):
    filt = '["sport"~"pickleball|padel"]'
    if bbox:
        a, b, c, d = bbox
        return f'  node{filt}({a},{b},{c},{d});\n  way{filt}({a},{b},{c},{d});'
    if country:
        code = country.upper()
        return (f'  area["ISO3166-1"="{code}"][admin_level=2]->.a;\n'
                f'  node(area.a){filt};\n  way(area.a){filt};')
    sys.exit("Provide --country or --bbox.")

def norm(e, country_code):
    t = e.get("tags", {})
    if not t.get("name"):
        return None
    lat = e.get("lat") or (e.get("center") or {}).get("lat")
    lng = e.get("lon") or (e.get("center") or {}).get("lon")
    if lat is None or lng is None:
        return None
    sport = "both" if "pickleball" in t.get("sport", "") and "padel" in t.get("sport", "") \
        else ("padel" if "padel" in t.get("sport", "") else "pickleball")
    code = (t.get("addr:country") or country_code or "").upper()[:2]
    city = t.get("addr:city") or t.get("addr:town") or t.get("addr:suburb") or ""
    amap = {"lit": "Lights", "indoor": "Indoor", "toilets": "Restrooms", "parking": "Parking",
            "shower": "Showers", "locker": "Locker rooms", "shop": "Pro shop", "cafe": "Cafe"}
    amen = [v for k, v in amap.items() if t.get(k) in ("yes", "true", "1")]
    return {
        "name": t["name"], "slug": f'{slug(t["name"])}-{slug(city)}',
        "city": city, "country": ISO_NAME.get(code, t.get("addr:country", "")), "cc": code,
        "lat": round(float(lat), 5), "lng": round(float(lng), 5),
        "sport": {"pickleball": "Pickleball", "padel": "Padel", "both": "Pickleball + Padel"}[sport],
        "sportKey": sport,
        "courts": int(re.sub(r"\D", "", t.get("courts", "1")) or 1),
        "indoor": t.get("indoor") in ("yes", "true", "1"),
        "outdoor": t.get("indoor") not in ("yes", "true", "1"),
        "surface": t.get("surface", ""), "price": "", "amenities": amen[:5],
        "rating": 0, "reviews": 0, "featured": False, "verified": False,
        "website": t.get("website") or t.get("contact:website"),
        "phone": t.get("phone") or t.get("contact:phone"),
        "source": "osm", "external_id": f'{e["type"]}/{e["id"]}',
    }

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", help="ISO-2 code, e.g. US")
    ap.add_argument("--bbox", help="south,west,north,east")
    ap.add_argument("--out", default="courts.json")
    a = ap.parse_args()
    bbox = [x.strip() for x in a.bbox.split(",")] if a.bbox else None
    els = run(selector(a.country, bbox))
    rows, seen = [], set()
    for e in els:
        r = norm(e, a.country)
        if r and r["slug"] not in seen:
            seen.add(r["slug"]); rows.append(r)
    json.dump(rows, open(a.out, "w"), indent=1)
    print(f"wrote {len(rows)} courts to {a.out} (from {len(els)} OSM elements)")

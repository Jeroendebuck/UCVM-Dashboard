#!/usr/bin/env python3
"""
Fetch last-5-year works for each author in the roster and write:
  - data/compiled/openalex_all_authors_last5y_key_fields.csv
  - data/compiled/openalex_all_authors_last5y_key_fields_dedup.csv

Logs per-author counts so you can see progress in Actions.
"""

import os, sys, time, argparse
import pandas as pd
import requests
from datetime import datetime

COLUMNS = [
    "id", "display_name", "publication_year", "type", "cited_by_count",
    "host_venue_display_name", "author_openalex_id", "author_name"
]

OA_COL_CANDIDATES = [
    "openalexid", "openalex_id", "author_openalex_id", "openalex id", "oaid"
]

def find_oa_col(cols):
    low = [str(c).strip().lower() for c in cols]
    for cand in OA_COL_CANDIDATES:
        if cand in low:
            return cols[low.index(cand)]
    return None

def find_name_col(cols):
    low = [str(c).strip().lower() for c in cols]
    for cand in ["name", "author_name", "faculty_name", "full_name"]:
        if cand in low:
            return cols[low.index(cand)]
    return None

def fetch_author_works(aid, aname, y_from, y_to, email, delay):
    base = "https://api.openalex.org/works"
    headers = {"User-Agent": f"UCVM-Dashboard/ETL ({email})"}
    params = {
        "filter": f"author.id:{aid},from_publication_date:{y_from}-01-01,to_publication_date:{y_to}-12-31",
        "per-page": 200,
        "cursor": "*",
        "select": "id,display_name,publication_year,type,cited_by_count,host_venue.display_name",
        "mailto": email
    }
    rows, total = [], 0
    while True:
        r = requests.get(base, params=params, headers=headers, timeout=60)
        r.raise_for_status()
        js = r.json()
        for it in js.get("results", []):
            rows.append({
                "id": it.get("id",""),
                "display_name": it.get("display_name",""),
                "publication_year": it.get("publication_year",""),
                "type": it.get("type",""),
                "cited_by_count": it.get("cited_by_count",""),
                "host_venue_display_name": (it.get("host_venue") or {}).get("display_name",""),
                "author_openalex_id": aid,
                "author_name": aname or "",
            })
        n = len(js.get("results", []))
        total += n
        cur = js.get("meta",{}).get("next_cursor")
        if not cur:
            break
        params["cursor"] = cur
        time.sleep(delay)
    return rows, total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", default="data/roster_with_metrics.csv")
    ap.add_argument("--outdir", default="data")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--delay", type=float, default=0.15)
    ap.add_argument("--email", default=os.environ.get("OPENALEX_POLITE_EMAIL", "you@example.com"))
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    compiled_dir = os.path.join(args.outdir, "compiled")
    os.makedirs(compiled_dir, exist_ok=True)

    compiled = os.path.join(compiled_dir, "openalex_all_authors_last5y_key_fields.csv")
    dedup    = os.path.join(compiled_dir, "openalex_all_authors_last5y_key_fields_dedup.csv")

    # Date window: last N calendar years inclusive
    y_to = datetime.utcnow().year
    y_from = y_to - (args.years - 1)

    df = pd.read_csv(args.roster)
    oa_col = find_oa_col(df.columns)
    nm_col = find_name_col(df.columns)

    if not oa_col:
        print("[error] Could not find an OpenAlex ID column in roster. Looked for:", OA_COL_CANDIDATES, file=sys.stderr)
        print("[roster columns]", list(df.columns), file=sys.stderr)
        sys.exit(2)

    sub = df[[c for c in [oa_col, nm_col] if c]].copy()
    sub = sub.dropna(subset=[oa_col])
    sub[oa_col] = sub[oa_col].astype(str).str.strip()

    ids = sub[oa_col].unique().tolist()
    print(f"[info] Authors with OpenAlex IDs: {len(ids)} (years {y_from}-{y_to})")
    print("[info] Sample IDs:", ids[:5])

    all_rows = []
    for i, aid in enumerate(ids, 1):
        name = ""
        if nm_col:
            # first matching name
            name = sub[sub[oa_col] == aid][nm_col].astype(str).head(1).tolist()[0]
        try:
            rows, total = fetch_author_works(aid, name, y_from, y_to, args.email, args.delay)
            all_rows.extend(rows)
            print(f"[works] {i:03d}/{len(ids)}  {aid}  → {total} works")
        except Exception as e:
            print(f"[warn]  {i:03d}/{len(ids)}  {aid}  failed: {e}", file=sys.stderr)
            # continue to next author

    out = pd.DataFrame(all_rows, columns=COLUMNS)
    out.to_csv(compiled, index=False)
    print(f"[out] wrote {compiled} rows={len(out)}")

    if len(out):
        ded = out.drop_duplicates(subset=["id"], keep="first")
    else:
        ded = out
    ded.to_csv(dedup, index=False)
    print(f"[out] wrote {dedup} rows={len(ded)}")

if __name__ == "__main__":
    main()

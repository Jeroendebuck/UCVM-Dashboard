# UCVM Dashboard — Option A (Static app + Scheduled ETL)

This repo hosts a **static HTML dashboard** and a **nightly ETL** that refreshes CSVs from OpenAlex.
No servers, no bills.

## Structure
```
/app/UCVM_Dashboard.html        # the static dashboard (patched to auto-fetch from /data)
/data/                           # ETL outputs written here (CSV + JSON)
/etl/UCVM_works.py               # your existing script
/etl/fetch_author_metrics.py     # your existing script
/.github/workflows/etl.yml       # scheduled GitHub Action
requirements.txt                 # Python deps for ETL
```

## One-time setup
1. Create a new GitHub repo and push this tree.
2. Put your faculty seed roster at `data/full_time_faculty.csv` (OpenAlexID column required).
3. In **Settings → Pages**, set GitHub Pages source to `app` (or to root if you move the HTML there).
4. In **Settings → Secrets → Actions**, create `OPENALEX_POLITE_EMAIL` with a contact email (used for OpenAlex polite header).

## How it updates
- The Action runs nightly (see cron in `.github/workflows/etl.yml`).
- It runs `fetch_author_metrics.py` to produce `data/roster_with_metrics.csv` and then `UCVM_works.py`
  via `etl/ucvm_works_wrapper.py` to produce:
  - `data/openalex_all_authors_last5y_key_fields.csv`
  - `data/openalex_all_authors_last5y_key_fields_dedup.csv`
- It writes `data/last_updated.json` with a timestamp and commits changes.

## How the HTML finds data
The dashboard fetches:
- `https://raw.githubusercontent.com/<org>/<repo>/<branch>/data/roster_with_metrics.csv`
- `https://raw.githubusercontent.com/<org>/<repo>/<branch>/data/openalex_all_authors_last5y_key_fields_dedup.csv`
- `https://raw.githubusercontent.com/<org>/<repo>/<branch>/data/last_updated.json`

Update the placeholder `<org>/<repo>/<branch>` inside `app/UCVM_Dashboard.html` (search `AUTO_FETCH_BASE`).

## Local testing
Run the ETL locally to produce the CSVs in `data/`:
```bash
python etl/fetch_author_metrics.py --input data/full_time_faculty.csv --output data/roster_with_metrics.csv --email you@ucalgary.ca --delay 0.25
python etl/ucvm_works_wrapper.py
```

Then open `app/UCVM_Dashboard.html` in a browser. The page fetches files from GitHub raw URLs; for local testing, use the file picker UI instead.

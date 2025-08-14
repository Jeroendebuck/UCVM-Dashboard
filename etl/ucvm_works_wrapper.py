#!/usr/bin/env python3
"""
Run UCVM_works.py inside GitHub Actions with repo-relative paths.
- Rebind OUTPUT_DIR and derived dirs (no /Users/...).
- Print roster diagnostics (how many authors we’ll process).
- Patch append_df_to_csv to write header-only file when df is empty but schema is known.
- List output folders after run.
"""
import os, sys, importlib.util, pandas as pd, glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ETL_DIR   = os.path.join(REPO_ROOT, "etl")
DATA_DIR  = os.path.join(REPO_ROOT, "data")

# Load the existing UCVM_works.py as a module
src_path = os.path.join(ETL_DIR, "UCVM_works.py")
spec = importlib.util.spec_from_file_location("ucvm_works", src_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# ---- Override configuration ----
mod.MAILTO       = os.environ.get("OPENALEX_POLITE_EMAIL", getattr(mod, "MAILTO", "you@example.com"))
mod.OUTPUT_DIR   = DATA_DIR
mod.INPUT_ROSTER = os.environ.get("INPUT_ROSTER", os.path.join(DATA_DIR, "roster_with_metrics.csv"))

# Recompute derived directories
mod.ALL_FIELDS_DIR = os.path.join(mod.OUTPUT_DIR, "authors_all_fields")
mod.LAST5_DIR     = os.path.join(mod.OUTPUT_DIR, "authors_last5y_key_fields")
mod.COMPILED_DIR  = os.path.join(mod.OUTPUT_DIR, "compiled")

# Ensure output dirs exist
os.makedirs(mod.OUTPUT_DIR, exist_ok=True)
os.makedirs(mod.ALL_FIELDS_DIR, exist_ok=True)
os.makedirs(mod.LAST5_DIR, exist_ok=True)
os.makedirs(mod.COMPILED_DIR, exist_ok=True)

# Optional knobs if present in your script
for name, val in [
    ("YEARS", int(os.environ.get("YEARS", "5"))),
    ("DELAY", float(os.environ.get("DELAY", "0.25"))),
    ("DEDUP", True),
]:
    if hasattr(mod, name):
        setattr(mod, name, val)

print("[wrapper] OUTPUT_DIR    =", mod.OUTPUT_DIR)
print("[wrapper] ALL_FIELDS_DIR=", mod.ALL_FIELDS_DIR)
print("[wrapper] LAST5_DIR     =", mod.LAST5_DIR)
print("[wrapper] COMPILED_DIR  =", mod.COMPILED_DIR)
print("[wrapper] INPUT_ROSTER  =", mod.INPUT_ROSTER)

# ---- Roster diagnostics (so we know what will be processed) ----
try:
    df_r = pd.read_csv(mod.INPUT_ROSTER)
    name_col = next((c for c in df_r.columns if str(c).strip().lower() == "name"), None)
    id_col   = next((c for c in df_r.columns if str(c).strip().lower() == "openalexid"), None)
    nonnull_ids = 0
    if id_col: nonnull_ids = int(df_r[id_col].notna().sum())
    print(f"[wrapper] roster rows: {len(df_r)}; Name col: {name_col}; OpenAlexID col: {id_col}; non-null OpenAlexID: {nonnull_ids}")
    if id_col:
        sample = df_r[id_col].dropna().astype(str).head(8).tolist()
        print("[wrapper] sample OpenAlexIDs:", sample)
except Exception as e:
    print("[wrapper] roster read error:", e)

# ---- Patch append_df_to_csv to write header-only when df is empty but schema is known ----
_orig_append = mod.append_df_to_csv
def _patched_append(df, path, fixed_cols=None):
    if (df is None or df.empty) and fixed_cols:
        # Ensure a header-only file exists so downstream steps and the dashboard have a target
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            pd.DataFrame(columns=fixed_cols).to_csv(path, index=False)
            print(f"[wrapper] created header-only compiled file: {path}")
        return
    return _orig_append(df, path, fixed_cols)
mod.append_df_to_csv = _patched_append

# ---- Run main() ----
exit_code = 0
try:
    mod.main()
except Exception as e:
    import traceback
    traceback.print_exc()
    exit_code = 1

# ---- List outputs so logs show what got written ----
def list_dir(p, limit=None):
    try:
        items = sorted(glob.glob(os.path.join(p, "*")))
        print(f"[wrapper] {p} ({len(items)} items)")
        for i, x in enumerate(items):
            print("   ", os.path.basename(x))
            if limit and i+1 >= limit:
                print("   ...")
                break
    except Exception as e:
        print(f"[wrapper] cannot list {p}: {e}")

for p in [mod.OUTPUT_DIR, mod.COMPILED_DIR, mod.LAST5_DIR, mod.ALL_FIELDS_DIR]:
    list_dir(p, limit=50)

sys.exit(exit_code)

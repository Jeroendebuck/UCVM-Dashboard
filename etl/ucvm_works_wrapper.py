#!/usr/bin/env python3
"""
Run UCVM_works.py inside GitHub Actions with repo-relative paths.
Rebinds OUTPUT_DIR and all derived dirs so nothing points to /Users/...
"""
import os, sys, importlib.util

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ETL_DIR   = os.path.join(REPO_ROOT, "etl")
DATA_DIR  = os.path.join(REPO_ROOT, "data")

# Load the existing UCVM_works.py as a module (no __main__ executed on import)
src_path = os.path.join(ETL_DIR, "UCVM_works.py")
spec = importlib.util.spec_from_file_location("ucvm_works", src_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# ---- Override configuration ----
mod.MAILTO       = os.environ.get("OPENALEX_POLITE_EMAIL", getattr(mod, "MAILTO", "you@example.com"))
mod.OUTPUT_DIR   = DATA_DIR
mod.INPUT_ROSTER = os.environ.get("INPUT_ROSTER", os.path.join(DATA_DIR, "roster_with_metrics.csv"))

# Recompute any derived directories that were bound at import time
if hasattr(mod, "ALL_FIELDS_DIR"):
    mod.ALL_FIELDS_DIR = os.path.join(mod.OUTPUT_DIR, "authors_all_fields")
if hasattr(mod, "LAST5_DIR"):
    mod.LAST5_DIR = os.path.join(mod.OUTPUT_DIR, "authors_last5y_key_fields")
if hasattr(mod, "COMPILED_DIR"):
    mod.COMPILED_DIR = os.path.join(mod.OUTPUT_DIR, "compiled")

# Ensure output dirs exist
os.makedirs(mod.OUTPUT_DIR, exist_ok=True)
os.makedirs(getattr(mod, "ALL_FIELDS_DIR", os.path.join(DATA_DIR, "authors_all_fields")), exist_ok=True)
os.makedirs(getattr(mod, "LAST5_DIR", os.path.join(DATA_DIR, "authors_last5y_key_fields")), exist_ok=True)
os.makedirs(getattr(mod, "COMPILED_DIR", os.path.join(DATA_DIR, "compiled")), exist_ok=True)

# Optional knobs if defined in your script
for name, val in [
    ("YEARS", int(os.environ.get("YEARS", "5"))),
    ("DELAY", float(os.environ.get("DELAY", "0.25"))),
    ("DEDUP", True),
]:
    if hasattr(mod, name):
        setattr(mod, name, val)

# Log final paths for troubleshooting
print("[wrapper] OUTPUT_DIR    =", mod.OUTPUT_DIR)
print("[wrapper] ALL_FIELDS_DIR=", getattr(mod, "ALL_FIELDS_DIR", "n/a"))
print("[wrapper] LAST5_DIR     =", getattr(mod, "LAST5_DIR", "n/a"))
print("[wrapper] COMPILED_DIR  =", getattr(mod, "COMPILED_DIR", "n/a"))
print("[wrapper] INPUT_ROSTER  =", mod.INPUT_ROSTER)

# ---- Run main() ----
if __name__ == "__main__":
    try:
        mod.main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

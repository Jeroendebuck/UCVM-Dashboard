#!/usr/bin/env python3
"""
Wrapper to run UCVM_works.py inside GitHub Actions with repo-relative paths.
"""
import os, sys, importlib.util

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ETL_DIR   = os.path.join(REPO_ROOT, "etl")
DATA_DIR  = os.path.join(REPO_ROOT, "data")

# Load the existing UCVM_works.py as a module
src_path = os.path.join(ETL_DIR, "UCVM_works.py")
spec = importlib.util.spec_from_file_location("ucvm_works", src_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Override configuration
mod.MAILTO      = os.environ.get("OPENALEX_POLITE_EMAIL", getattr(mod, "MAILTO", "")) or "you@example.com"
mod.OUTPUT_DIR  = DATA_DIR  # this script expects subdirs 'compiled' & 'authors_last5y_key_fields'
mod.INPUT_ROSTER= os.environ.get("INPUT_ROSTER", os.path.join(DATA_DIR, "roster_with_metrics.csv"))

# Optional knobs if present in the script
for name, val in [
    ("YEARS", int(os.environ.get("YEARS", "5"))),
    ("DELAY", float(os.environ.get("DELAY", "0.25"))),
    ("DEDUP", True),
]:
    if hasattr(mod, name):
        setattr(mod, name, val)

# Ensure output subdirs exist
os.makedirs(os.path.join(mod.OUTPUT_DIR, "compiled"), exist_ok=True)
os.makedirs(os.path.join(mod.OUTPUT_DIR, "authors_last5y_key_fields"), exist_ok=True)

# Run main()
if __name__ == "__main__":
    try:
        mod.main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

"""
Experiment 1 - Data Loading & Ingestion
Zomato Bangalore Restaurants | BI&A Final Project

Loads the raw Kaggle CSV, profiles its structure, emits a data dictionary,
and writes a lightweight staging file for the downstream experiments.
"""

import os
import sys
import textwrap
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "zomato.csv")
PROCESSED = os.path.join(BASE, "data", "processed")
REPORTS = os.path.join(BASE, "outputs", "reports")

# Columns too heavy / unstructured to carry into the BI model
HEAVY_COLS = ["reviews_list", "menu_item"]


def find_raw():
    if os.path.exists(RAW):
        return RAW
    # tolerate a differently-named download sitting in data/raw
    raw_dir = os.path.dirname(RAW)
    candidates = [f for f in os.listdir(raw_dir) if f.lower().endswith(".csv")] if os.path.isdir(raw_dir) else []
    if candidates:
        return os.path.join(raw_dir, candidates[0])
    sys.exit(
        textwrap.dedent(f"""
        Raw dataset not found.

        Download 'zomato.csv' from:
          https://www.kaggle.com/datasets/himanshupoddar/zomato-bangalore-restaurants
        and place it at:
          {RAW}
        """).strip()
    )


def main():
    path = find_raw()
    size_mb = os.path.getsize(path) / 1024**2
    print(f"Reading {os.path.basename(path)} ({size_mb:,.1f} MB) ...")

    df = pd.read_csv(path, low_memory=False)
    lines = []

    def emit(s=""):
        print(s)
        lines.append(str(s))

    emit("=" * 78)
    emit("EXPERIMENT 1 - DATA LOADING & PROFILING")
    emit("=" * 78)
    emit(f"Source file        : {path}")
    emit(f"File size          : {size_mb:,.1f} MB")
    emit(f"Rows               : {df.shape[0]:,}")
    emit(f"Columns            : {df.shape[1]}")
    emit(f"In-memory size     : {df.memory_usage(deep=True).sum() / 1024**2:,.1f} MB")
    emit(f"Duplicate rows     : {df.duplicated().sum():,}")
    emit()

    # ---- Data dictionary -------------------------------------------------
    rows = []
    for col in df.columns:
        s = df[col]
        nulls = int(s.isna().sum())
        sample = s.dropna().astype(str).head(1)
        sample = sample.iloc[0][:70].replace("\n", " ") if len(sample) else ""
        rows.append({
            "column": col,
            "dtype": str(s.dtype),
            "non_null": int(s.notna().sum()),
            "nulls": nulls,
            "null_pct": round(nulls / len(df) * 100, 2),
            "unique": int(s.nunique(dropna=True)),
            "sample_value": sample,
        })
    dd = pd.DataFrame(rows)

    emit("DATA DICTIONARY")
    emit("-" * 78)
    emit(dd.drop(columns=["sample_value"]).to_string(index=False))
    emit()

    emit("SAMPLE VALUES")
    emit("-" * 78)
    for r in rows:
        emit(f"  {r['column']:<28} | {r['sample_value']}")
    emit()

    # ---- Problem columns flagged for Experiment 2 ------------------------
    emit("ISSUES FLAGGED FOR EXPERIMENT 2 (CLEANING)")
    emit("-" * 78)
    issues = []

    if "rate" in df.columns:
        bad = df["rate"].dropna().astype(str)
        non_numeric = sorted(set(bad[~bad.str.match(r"^\d(\.\d)?/5$")]))[:8]
        issues.append(f"'rate' is text ('4.1/5' form). Non-standard values present: {non_numeric}")

    cost_col = next((c for c in df.columns if "cost" in c.lower()), None)
    if cost_col:
        has_comma = df[cost_col].astype(str).str.contains(",", na=False).sum()
        issues.append(f"'{cost_col}' is text; {has_comma:,} values contain thousands separators -> needs numeric cast")

    for c in ("cuisines", "rest_type", "dish_liked"):
        if c in df.columns:
            mx = df[c].dropna().astype(str).str.count(",").max()
            issues.append(f"'{c}' is multi-valued (up to {int(mx) + 1} values per row) -> explode into a bridge table")

    for c in HEAVY_COLS:
        if c in df.columns:
            mb = df[c].memory_usage(deep=True) / 1024**2
            issues.append(f"'{c}' holds {mb:,.0f} MB of unstructured text -> drop before modelling")

    if "url" in df.columns:
        issues.append(f"'url' uniquely identifies a restaurant ({df['url'].nunique():,} unique) -> use as dedup key, then drop")

    for i, msg in enumerate(issues, 1):
        emit(f"  {i}. {msg}")
    emit()

    # ---- Outputs ---------------------------------------------------------
    os.makedirs(PROCESSED, exist_ok=True)
    os.makedirs(REPORTS, exist_ok=True)

    dd_path = os.path.join(REPORTS, "data_dictionary.csv")
    dd.to_csv(dd_path, index=False)

    staging = df.drop(columns=[c for c in HEAVY_COLS if c in df.columns])
    stage_path = os.path.join(PROCESSED, "staging.csv")
    staging.to_csv(stage_path, index=False)

    prof_path = os.path.join(REPORTS, "exp1_profile.txt")
    with open(prof_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    emit("OUTPUTS WRITTEN")
    emit("-" * 78)
    for p in (dd_path, stage_path, prof_path):
        emit(f"  {p}  ({os.path.getsize(p) / 1024**2:,.1f} MB)")

    with open(prof_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()

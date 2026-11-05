"""
One summary, two engines.

Every chart is described once in CHARTS. `dax_summary` turns each spec into a DAX
query against the live Power BI model; `snapshot_summary` computes the identical
result with pandas from zomato_powerbi.csv (the exact file the model imports), so
the page still works when Power BI Desktop is closed. Both return the same JSON.
"""
from __future__ import annotations

import math
import os

import pandas as pd

TABLE = "zomato_powerbi"
T = f"'{TABLE}'"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CSV_PATH = os.path.join(REPO_ROOT, "zomato_powerbi.csv")

# UI filter key -> model column. Whitelisted: user input never becomes a column name.
FILTER_COLUMNS = {
    "location": "location",
    "format": "primary_rest_type",
    "cuisine": "primary_cuisine",
    "listing": "listed_in(type)",
    "online": "online_order",
    "booking": "book_table",
    "cost": "Cost_Bracket",
    "rating": "Rating_Bracket",
}

# measure name -> (DAX expression, pandas reducer over a group of rows)
MEASURES = {
    "n": (f"COUNTROWS({T})", lambda g: float(len(g))),
    "avg": (f"AVERAGE({T}[rate])", lambda g: g["rate"].mean()),
    "cost": (f"AVERAGE({T}[approx_cost])", lambda g: g["approx_cost"].mean()),
    "votes": (f"AVERAGE({T}[votes])", lambda g: g["votes"].mean()),
    "max_votes": (f"MAX({T}[votes])", lambda g: float(g["votes"].max())),
    "top_share": (
        f"DIVIDE(COALESCE(CALCULATE(COUNTROWS({T}), KEEPFILTERS({T}[rate] >= 4)), 0), COUNTROWS({T}))",
        lambda g: float((g["rate"] >= 4).mean()),
    ),
}

# chart key -> spec. by: group-by columns; top: (k, measure) keeps the k largest.
# dims: the filter columns a chart "owns". Like Power BI cross-highlighting, a chart ignores
# its own selection (so the picked bar stays highlighted among its peers) but every
# other chart is filtered by it.
CHARTS = {
    "rating_dist": {"dims": ["Rating_Bracket"], "by": ["Rating_Bracket", "Rating_Bracket_Sort"], "measures": ["n", "avg"], "order": "Rating_Bracket_Sort"},
    "votes": {"by": ["Vote_Bracket", "Vote_Bracket_Sort"], "measures": ["n", "avg"], "order": "Vote_Bracket_Sort"},
    "cost": {"dims": ["Cost_Bracket"], "by": ["Cost_Bracket", "Cost_Bracket_Sort"], "measures": ["n", "avg", "top_share"], "order": "Cost_Bracket_Sort"},
    "cost_online": {"by": ["Cost_Bracket", "Cost_Bracket_Sort", "online_order"], "measures": ["n", "avg"], "order": "Cost_Bracket_Sort"},
    "service": {"dims": ["book_table", "online_order"], "by": ["book_table", "online_order"], "measures": ["n", "avg"], "order": "book_table"},
    "formats": {"dims": ["primary_rest_type"], "by": ["primary_rest_type"], "measures": ["n", "avg", "top_share", "cost"], "top": (10, "n")},
    "locations": {"dims": ["location"], "by": ["location"], "measures": ["n", "avg", "cost", "votes"], "top": (15, "n")},
    "scatter": {"dims": ["location"], "by": ["location"], "measures": ["n", "avg", "cost"], "top": (30, "n")},
    "cuisines": {"dims": ["primary_cuisine"], "by": ["primary_cuisine"], "measures": ["n", "avg"], "top": (10, "n")},
    "listing": {"dims": ["listed_in(type)"], "by": ["listed_in(type)"], "measures": ["n", "avg"], "order": "listed_in(type)"},
    "leaders": {"by": ["name"], "measures": ["max_votes", "avg", "n", "cost"], "top": (10, "max_votes")},
}

KPI_EXPR = {
    "restaurants": f"COUNTROWS({T})",
    "avg_rating": f"AVERAGE({T}[rate])",
    "avg_cost": f"AVERAGE({T}[approx_cost])",
    "votes": f"SUM({T}[votes])",
    "avg_votes": f"AVERAGE({T}[votes])",
    "locations": f"DISTINCTCOUNT({T}[location])",
    "cuisines": f"DISTINCTCOUNT({T}[primary_cuisine])",
    "online_share": f'DIVIDE(COALESCE(CALCULATE(COUNTROWS({T}), KEEPFILTERS({T}[online_order] = "Yes")), 0), COUNTROWS({T}))',
    "booking_share": f'DIVIDE(COALESCE(CALCULATE(COUNTROWS({T}), KEEPFILTERS({T}[book_table] = "Yes")), 0), COUNTROWS({T}))',
    "top_rated_share": f"DIVIDE(COALESCE(CALCULATE(COUNTROWS({T}), KEEPFILTERS({T}[rate] >= 4)), 0), COUNTROWS({T}))",
    "booking_lift": (
        f'VAR WithBooking = CALCULATE(AVERAGE({T}[rate]), KEEPFILTERS({T}[book_table] = "Yes"))\n'
        f'        VAR WithoutBooking = CALCULATE(AVERAGE({T}[rate]), KEEPFILTERS({T}[book_table] = "No"))\n'
        f"        RETURN IF(ISBLANK(WithBooking) || ISBLANK(WithoutBooking), BLANK(), WithBooking - WithoutBooking)"
    ),
    "online_lift": (
        f'VAR WithOnline = CALCULATE(AVERAGE({T}[rate]), KEEPFILTERS({T}[online_order] = "Yes"))\n'
        f'        VAR WithoutOnline = CALCULATE(AVERAGE({T}[rate]), KEEPFILTERS({T}[online_order] = "No"))\n'
        f"        RETURN IF(ISBLANK(WithOnline) || ISBLANK(WithoutOnline), BLANK(), WithOnline - WithoutOnline)"
    ),
}


def clean_filters(args) -> dict:
    out = {}
    for key, col in FILTER_COLUMNS.items():
        val = (args.get(key) or "").strip()
        if val and val.lower() != "all":
            out[col] = val
    return out


def _dax_str(s: str) -> str:
    return '"' + s.replace('"', '""') + '"'


def _filter_list(filters: dict, skip=()) -> list[str]:
    return [f"TREATAS({{{_dax_str(v)}}}, {T}[{c}])" for c, v in filters.items() if c not in skip]


def _num(v):
    if v is None:
        return None
    if isinstance(v, str):
        return v
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _finish(spec: dict, rows: list[dict]) -> list[dict]:
    """Same ordering/trim for both engines, so results are identical."""
    rows = [{k: _num(v) for k, v in r.items()} for r in rows]
    by = spec["by"]
    rows = [r for r in rows if all(r.get(c) not in (None, "") for c in by)]
    if "top" in spec:
        k, m = spec["top"]
        rows.sort(key=lambda r: (-(r.get(m) or 0), str(r[by[0]]).casefold()))  # DAX collation is case-insensitive
        rows = rows[:k]
    else:
        extra = [c for c in by if c != spec["order"]]
        rows.sort(key=lambda r: (r[spec["order"]], *[str(r[c]) for c in extra]))
    for r in rows:
        for c in by:
            if c.endswith("_Sort") and r.get(c) is not None:
                r[c] = int(r[c])
        if "n" in r and r["n"] is not None:
            r["n"] = int(r["n"])
    return rows


# ------------------------------------------------------------------ DAX (live)
def dax_queries(filters: dict) -> dict:
    fl = _filter_list(filters)
    q = {}
    body = "ROW(\n" + ",\n".join(f'    "{k}", {e}' for k, e in KPI_EXPR.items()) + "\n)"
    q["kpis"] = ("EVALUATE\nCALCULATETABLE(\n" + body + ",\n    " + ",\n    ".join(fl) + "\n)") if fl else "EVALUATE\n" + body

    for key, spec in CHARTS.items():
        fl = _filter_list(filters, spec.get("dims", ()))
        cols = [f"{T}[{c}]" for c in spec["by"]]
        meas = [f'"{m}", {MEASURES[m][0]}' for m in spec["measures"]]
        inner = "SUMMARIZECOLUMNS(\n        " + ",\n        ".join(cols + fl + meas) + "\n    )"
        if "top" in spec:
            k, m = spec["top"]
            q[key] = f"EVALUATE\nTOPN({k},\n    {inner},\n    [{m}], DESC, {cols[0]}, ASC\n)\nORDER BY [{m}] DESC"
        else:
            q[key] = f"EVALUATE\n{inner.replace(chr(10) + '    ', chr(10))}\nORDER BY {T}[{spec['order']}]"
    return q


def dax_summary(bridge, filters: dict) -> dict:
    q = dax_queries(filters)
    k = (bridge.query(q["kpis"]) or [{}])[0]
    out = {"kpis": {key: _num(k.get(key)) for key in KPI_EXPR}}
    for key, spec in CHARTS.items():
        out[key] = _finish(spec, bridge.query(q[key]))
    out["dax"] = q
    return out


def dax_options(bridge) -> dict:
    def values(col):
        rows = bridge.query(f'EVALUATE SUMMARIZECOLUMNS({T}[{col}], "n", COUNTROWS({T})) ORDER BY [n] DESC')
        return [r[col] for r in rows if r.get(col)]
    return {key: values(col) for key, col in FILTER_COLUMNS.items() if key not in ("online", "booking")}


# ------------------------------------------------------------- pandas snapshot
_df_cache: dict = {}


def load_snapshot() -> pd.DataFrame:
    mtime = os.path.getmtime(CSV_PATH)
    if _df_cache.get("mtime") != mtime:
        _df_cache["df"] = pd.read_csv(CSV_PATH, encoding="utf-8")
        _df_cache["mtime"] = mtime
    return _df_cache["df"]


def _filtered(filters: dict, skip=()) -> pd.DataFrame:
    df = load_snapshot()
    for c, v in filters.items():
        if c not in skip:
            df = df[df[c] == v]
    return df


def snapshot_summary(filters: dict) -> dict:
    df = _filtered(filters)
    n = len(df)

    def share(mask):
        return float(mask.sum()) / n if n else None

    def lift(col):
        a, b = df.loc[df[col] == "Yes", "rate"].mean(), df.loc[df[col] == "No", "rate"].mean()
        return _num(a - b)

    out = {"kpis": {
        "restaurants": float(n) if n else None,
        "avg_rating": _num(df.rate.mean()),
        "avg_cost": _num(df.approx_cost.mean()),
        "votes": float(df.votes.sum()) if n else None,
        "avg_votes": _num(df.votes.mean()),
        "locations": float(df.location.nunique()) if n else None,
        "cuisines": float(df.primary_cuisine.nunique()) if n else None,
        "online_share": share(df.online_order == "Yes"),
        "booking_share": share(df.book_table == "Yes"),
        "top_rated_share": share(df.rate >= 4),
        "booking_lift": lift("book_table"),
        "online_lift": lift("online_order"),
    }}
    for key, spec in CHARTS.items():
        rows = []
        cdf = _filtered(filters, spec.get("dims", ()))
        if len(cdf):
            for keys, g in cdf.groupby(spec["by"], sort=False):
                keys = keys if isinstance(keys, tuple) else (keys,)
                r = dict(zip(spec["by"], keys))
                r.update({m: MEASURES[m][1](g) for m in spec["measures"]})
                rows.append(r)
        out[key] = _finish(spec, rows)
    out["dax"] = dax_queries(filters)
    return out


def snapshot_options() -> dict:
    df = load_snapshot()
    return {
        key: df[col].value_counts().index.tolist()
        for key, col in FILTER_COLUMNS.items()
        if key not in ("online", "booking")
    }

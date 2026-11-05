"""
Rebuild the report layer of "Zomato dashboard.pbix" as one red & white dashboard page.

    python Zomato_Project/powerbi/build_report.py [source.pbix] [output.pbix]

Only the report definition (PBIR JSON), the theme and the page background are
replaced. The data model (DataModel, queries, SQL Server connections) is copied
byte-for-byte, so nothing about the data changes. SecurityBindings is removed,
because it no longer matches the edited package and Power BI would refuse the file.

Design: the static chrome (icon rail, panels, illustration) is design/background.png,
rendered from design/background.html. Live Power BI visuals sit on its white cards.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "Zomato dashboard.pbix")
OUT = sys.argv[2] if len(sys.argv) > 2 else SRC
BG_PNG = os.path.join(HERE, "design", "background.png")

E = "zomato_powerbi"
PAGE = "9a715c0bb32eabbdcc86"
THEME_FILE = "ZomatoRedWhite2026110501.json"
BG_FILE = "ZomatoDashboardCanvas2026110501.png"
VSCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json"
PSCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"

RED, RED_DEEP, RED_DARK, RED_SOFT, PINK, PINK_LIGHT = "#E23744", "#A3121F", "#7E0D18", "#EE7B85", "#F6B3B9", "#FCE1E4"
INK, INK2, MUTED = "#1D1D22", "#4A4B54", "#8B8C96"

# ------------------------------------------------------------------ helpers
AGG = {"sum": 0, "avg": 1, "count": 5, "min": 3, "max": 4}
AGG_NAME = {"sum": "Sum", "avg": "Avg", "count": "CountNonNull", "min": "Min", "max": "Max"}


def col(p):
    return {"Column": {"Expression": {"SourceRef": {"Entity": E}}, "Property": p}}


def agg(p, f):
    return {"Aggregation": {"Expression": col(p), "Function": AGG[f]}}


def lit(v):
    if isinstance(v, bool):
        s = "true" if v else "false"
    elif isinstance(v, int):
        s = f"{v}L"
    elif isinstance(v, float):
        s = f"{v:g}D"
    else:
        s = "'" + str(v).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": s}}}


def color(hex_):
    return {"solid": {"color": lit(hex_)}}


def C(p):  # column projection
    return {"field": col(p), "queryRef": f"{E}.{p}", "nativeQueryRef": p}


def A(p, f, name):  # aggregated projection with display name
    return {"field": agg(p, f), "queryRef": f"{AGG_NAME[f]}({E}.{p})", "nativeQueryRef": name, "displayName": name}


def M(name, display=None):  # model measure projection (from dax_measures.dax, added by apply_measures.py)
    p = {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": E}}, "Property": name}},
         "queryRef": f"{E}.{name}", "nativeQueryRef": display or name}
    if display:
        p["displayName"] = display
    return p


def props(**kw):
    return [{"properties": {k: v for k, v in kw.items()}}]


def series_color(column, value, hex_):
    return {
        "properties": {"fill": color(hex_)},
        "selector": {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": col(column), "Right": {"Literal": {"Value": "'" + value + "'"}}}}}]},
    }


def gradient(measure_field, lo=PINK, hi=RED):
    return {
        "properties": {"fill": {"solid": {"color": {"expr": {"FillRule": {
            "Input": measure_field,
            "FillRule": {"linearGradient2": {
                "min": {"color": {"Literal": {"Value": f"'{lo}'"}}},
                "max": {"color": {"Literal": {"Value": f"'{hi}'"}}},
                "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}},
            }},
        }}}}}},
        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]},
    }


def container(title=None, *, background=False, size=12.0):
    o = {
        "background": props(show=lit(background)),
        "border": props(show=lit(False)),
        "dropShadow": props(show=lit(False)),
        "padding": props(top=lit(6.0), bottom=lit(4.0), left=lit(10.0), right=lit(10.0)),
        "subTitle": props(show=lit(False)),
    }
    if title:
        o["title"] = props(show=lit(True), text=lit(title), fontSize=lit(size), bold=lit(True), fontColor=color(INK), fontFamily=lit("Segoe UI"))
    else:
        o["title"] = props(show=lit(False))
    return o


_z = [0]


def visual(key, pos, vtype, roles, *, sort=None, objects=None, cobjects=None):
    _z[0] += 1000
    x, y, w, h = pos
    v = {"visualType": vtype}
    if roles:
        q = {"queryState": {r: {"projections": p} for r, p in roles.items()}}
        if sort:
            field, direction = sort
            q["sortDefinition"] = {"sort": [{"field": field, "direction": direction}], "isDefaultSort": False}
        v["query"] = q
    if objects:
        v["objects"] = objects
    if cobjects:
        v["visualContainerObjects"] = cobjects
    v["drillFilterOtherVisuals"] = True
    return {
        "$schema": VSCHEMA,
        "name": hashlib.md5(key.encode()).hexdigest()[:20],
        "position": {"x": x, "y": y, "z": _z[0], "height": h, "width": w, "tabOrder": _z[0]},
        "visual": v,
    }


def image_from_measure(key, pos, measure):
    """Image visual whose URL comes from a measure (data:image/svg+xml with SMIL animation)."""
    url = {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": E}}, "Property": measure}}}
    return visual(key, pos, "image", None,
                  objects={"image": props(sourceType=lit("imageUrl"), sourceUrl=url)},
                  cobjects={**container(), "visualHeader": props(show=lit(False))})


def axis_off_value():
    return props(show=lit(False), gridlineShow=lit(False))


def axis_cat(size=9.0):
    return props(show=lit(True), showAxisTitle=lit(False), labelColor=color(INK2), fontSize=lit(size))


def labels(fmt_color=INK, size=9.0, precision=None, units=None):
    """units: None = auto (K/M), 1.0 = show the full number."""
    p = dict(show=lit(True), color=color(fmt_color), fontSize=lit(size))
    if precision is not None:
        p["labelPrecision"] = lit(precision)
    if units is not None:
        p["labelDisplayUnits"] = lit(units)
    return [{"properties": p}]


# ------------------------------------------------------------------ layout
GX, GY, GW, GH, INSET = [776, 1157, 1538], [112, 354, 596, 838], 366, 226, 6


def grid(c, r):
    return (GX[c] + INSET, GY[r] + INSET, GW - 2 * INSET, GH - 2 * INSET)


def build_visuals():
    vs = []
    count = A("name", "count", "Restaurants")
    avg_rate = A("rate", "avg", "Avg Rating")

    # ---- header slicers
    for i, (field, label) in enumerate([("location", "Location"), ("primary_rest_type", "Dining Format"),
                                        ("online_order", "Online Order"), ("book_table", "Table Booking")]):
        p = C(field)
        p["displayName"] = label
        vs.append(visual(f"slicer-{field}", (1072 + i * 208, 20, 196, 76), "slicer", {"Values": [p]},
                         objects={"data": props(mode=lit("Dropdown")),
                                  "header": props(show=lit(True), fontColor=color(RED_DEEP), textSize=lit(10.0), bold=lit(True)),
                                  "items": props(fontColor=color(INK), textSize=lit(10.0))},
                         cobjects={"background": props(show=lit(True), color=color("#FFFFFF"), transparency=lit(0.0)),
                                   "border": props(show=lit(True), color=color("#F1D5D8"), radius=lit(12.0)),
                                   "dropShadow": props(show=lit(False)),
                                   "title": props(show=lit(False))}))

    # ---- overview KPI cards (inside the Overview panel)
    # (projection, decimals, display units): units 1.0 = full number, None = auto K/M
    kpis = [(M("Total Restaurants", "Restaurants"), 0, 1.0), (M("Average Rating", "Avg Rating"), 2, 1.0),
            (M("Average Cost for Two", "Avg Cost for Two"), 0, 1.0), (M("Total Votes"), 1, None)]
    for i, (proj, prec, units) in enumerate(kpis):
        # the Overview panel is dark wine in background.png: white values, pink captions
        objs = {"labels": labels("#FFFFFF", 24.0, prec, units), "categoryLabels": props(show=lit(True), color=color(PINK), fontSize=lit(10.0))}
        vs.append(visual(f"kpi-{i}", (132 + i * 156, 362, 148, 96), "card", {"Values": [proj]}, objects=objs, cobjects=container()))

    # ---- animated gauges: Image visuals whose URL is an animated-SVG measure (see dax_measures.dax 11-14)
    for i, name in enumerate(["Rating Ring SVG", "Top Rated Ring SVG", "Booking Lift SVG"]):
        x = [120, 339, 558][i]
        vs.append(image_from_measure(f"gauge-{i}", (x + 10, 524, 180, 140), name))
    vs.append(image_from_measure("live-pill", (716, 34, 290, 44), "Live Pill SVG"))

    # ---- donuts
    for i, (field, title) in enumerate([("online_order", "Online Ordering Share"), ("book_table", "Table Booking Share")]):
        x = [120, 448][i]
        vs.append(visual(f"donut-{field}", (x + 8, 696, 294, 360), "donutChart",
                         {"Category": [C(field)], "Y": [M("Total Restaurants", "Restaurants")]},
                         objects={"dataPoint": [series_color(field, "Yes", RED), series_color(field, "No", PINK)],
                                  "labels": props(show=lit(True), labelStyle=lit("Percent of total"), color=color(INK), fontSize=lit(11.0)),
                                  "legend": props(show=lit(True), position=lit("Bottom"), labelColor=color(INK2)),
                                  "slices": props(innerRadiusRatio=lit(62)),
                                  "centerValue": props(show=lit(True)),
                                  "value": props(fontSize=lit(16.0), bold=lit(True), fontColor=color(INK), labelDisplayUnits=lit(1.0)),
                                  "label": props(show=lit(True), text=lit("Restaurants"), fontSize=lit(9.0), fontColor=color(MUTED))},
                         cobjects=container(title)))

    # ---- row 1
    rsort = A("Rating_Bracket_Sort", "min", "Rating order")
    vs.append(visual("c-rating-dist", grid(0, 0), "clusteredColumnChart",
                     {"Category": [dict(C("Rating_Bracket"), active=True)], "Y": [count], "Tooltips": [rsort]},
                     sort=(rsort["field"], "Ascending"),
                     objects={"dataPoint": props(fill=color(RED)), "labels": labels(INK2, 8.0, 0, 1.0),
                              "valueAxis": axis_off_value(), "categoryAxis": axis_cat()},
                     cobjects=container("Rating Distribution")))

    vsort = A("Vote_Bracket_Sort", "min", "Vote order")
    vs.append(visual("c-votes-line", grid(1, 0), "lineChart",
                     {"Category": [dict(C("Vote_Bracket"), active=True)], "Y": [avg_rate], "Tooltips": [vsort]},
                     sort=(vsort["field"], "Ascending"),
                     objects={"dataPoint": props(fill=color(RED)), "lineStyles": props(strokeWidth=lit(3), showMarker=lit(True), markerSize=lit(6)),
                              "labels": labels(INK2, 8.0, 2), "valueAxis": axis_off_value(), "categoryAxis": axis_cat(8.0)},
                     cobjects=container("Votes vs Avg Rating")))

    csort = A("Cost_Bracket_Sort", "min", "Price order")
    vs.append(visual("c-cost-rating", grid(2, 0), "clusteredColumnChart",
                     {"Category": [dict(C("Cost_Bracket"), active=True)], "Y": [avg_rate], "Tooltips": [csort]},
                     sort=(csort["field"], "Ascending"),
                     objects={"legend": props(show=lit(False)), "dataPoint": [gradient(avg_rate["field"])], "labels": labels(INK2, 8.0, 2),
                              "valueAxis": axis_off_value(), "categoryAxis": axis_cat(8.0)},
                     cobjects=container("Price Tier vs Avg Rating")))

    # ---- row 2: ranked bars with pink -> red gradient
    for c, (key, field, measure, title, prec) in enumerate([
        ("c-format", "primary_rest_type", avg_rate, "Avg Rating by Dining Format", 2),
        ("c-location", "location", count, "Restaurants by Location", None),
        ("c-cuisine", "primary_cuisine", count, "Top Cuisines", None),
    ]):
        vs.append(visual(key, grid(c, 1), "clusteredBarChart",
                         {"Category": [dict(C(field), active=True)], "Y": [measure]},
                         sort=(measure["field"], "Descending"),
                         objects={"legend": props(show=lit(False)), "dataPoint": [gradient(measure["field"])], "labels": labels(INK2, 8.0, prec),
                                  "valueAxis": axis_off_value(), "categoryAxis": axis_cat(8.5)},
                         cobjects=container(title)))

    # ---- row 3
    vs.append(visual("c-service", grid(0, 2), "clusteredColumnChart",
                     {"Category": [dict(C("book_table"), active=True)], "Series": [C("online_order")], "Y": [avg_rate]},
                     sort=(col("book_table"), "Descending"),
                     objects={"dataPoint": [series_color("online_order", "Yes", RED), series_color("online_order", "No", PINK)],
                              "labels": labels(INK2, 8.0, 2), "valueAxis": axis_off_value(), "categoryAxis": axis_cat(),
                              "legend": props(show=lit(True), position=lit("Top"), labelColor=color(INK2), fontSize=lit(8.0))},
                     cobjects=container("Table Booking × Online Order (Avg Rating)")))

    vs.append(visual("c-listing", grid(1, 2), "clusteredColumnChart",
                     {"Category": [dict(C("listed_in(type)"), active=True)], "Y": [avg_rate]},
                     sort=(avg_rate["field"], "Descending"),
                     objects={"legend": props(show=lit(False)), "dataPoint": [gradient(avg_rate["field"])], "labels": labels(INK2, 8.0, 2),
                              "valueAxis": axis_off_value(), "categoryAxis": axis_cat(7.5)},
                     cobjects=container("Avg Rating by Listing Type")))

    vs.append(visual("c-topshare", grid(2, 2), "hundredPercentStackedBarChart",
                     {"Category": [dict(C("Cost_Bracket"), active=True)], "Series": [C("Performance_Tier")], "Y": [count], "Tooltips": [csort]},
                     sort=(csort["field"], "Ascending"),
                     objects={"dataPoint": [series_color("Performance_Tier", "Top Rated (≥4.0)", RED_DEEP),
                                            series_color("Performance_Tier", "Standard (<4.0)", PINK)],
                              "labels": props(show=lit(True), fontSize=lit(8.0), color=color("#FFFFFF")),
                              "valueAxis": axis_off_value(), "categoryAxis": axis_cat(8.0),
                              "legend": props(show=lit(True), position=lit("Top"), labelColor=color(INK2), fontSize=lit(8.0))},
                     cobjects=container("Top-Rated Share by Price Tier")))

    # ---- row 4
    vs.append(visual("c-scatter", grid(0, 3), "scatterChart",
                     {"Category": [C("location")], "X": [A("approx_cost", "avg", "Avg Cost for Two")],
                      "Y": [A("rate", "avg", "Avg Rating")], "Size": [A("name", "count", "Restaurants")]},
                     objects={"dataPoint": props(fill=color(RED)),
                              "categoryAxis": props(show=lit(True), showAxisTitle=lit(True), fontSize=lit(8.0), labelColor=color(INK2), gridlineShow=lit(False)),
                              "valueAxis": props(show=lit(True), showAxisTitle=lit(True), fontSize=lit(8.0), labelColor=color(INK2), gridlineShow=lit(True), gridlineColor=color("#F3E3E5"))},
                     cobjects=container("Locations: Price vs Rating")))

    votes_max = A("votes", "max", "Votes")
    vs.append(visual("c-leaders", grid(1, 3), "tableEx",
                     {"Values": [dict(C("name"), displayName="Restaurant"), votes_max, A("rate", "avg", "Rating"), A("approx_cost", "avg", "Cost (₹)")]},
                     sort=(votes_max["field"], "Descending"),
                     objects={"columnHeaders": props(fontColor=color("#FFFFFF"), backColor=color(RED), bold=lit(True), fontSize=lit(9.0)),
                              "values": props(fontColor=color(INK), fontSize=lit(9.0), backColorPrimary=color("#FFFFFF"), backColorSecondary=color("#FFF5F6")),
                              "grid": props(gridHorizontal=lit(False), gridVertical=lit(False)),
                              "total": props(totals=lit(False))},
                     cobjects=container("Most-Voted Restaurants")))

    vs.append(visual("c-onlinemix", grid(2, 3), "hundredPercentStackedColumnChart",
                     {"Category": [dict(C("Cost_Bracket"), active=True)], "Series": [C("online_order")], "Y": [count], "Tooltips": [csort]},
                     sort=(csort["field"], "Ascending"),
                     objects={"dataPoint": [series_color("online_order", "Yes", RED), series_color("online_order", "No", PINK)],
                              "labels": props(show=lit(True), fontSize=lit(7.5), color=color("#FFFFFF")),
                              "valueAxis": axis_off_value(), "categoryAxis": axis_cat(7.5),
                              "legend": props(show=lit(True), position=lit("Top"), labelColor=color(INK2), fontSize=lit(8.0))},
                     cobjects=container("Online Ordering Mix by Price Tier")))
    return vs


THEME = {
    "name": "Zomato Red & White",
    "dataColors": [RED, PINK, RED_DEEP, RED_SOFT, RED_DARK, "#CB2A38", PINK_LIGHT, INK2],
    "background": "#FFFFFF",
    "foreground": INK,
    "tableAccent": RED,
    "good": RED_DEEP, "neutral": PINK, "bad": RED_SOFT,
    "maximum": RED, "center": RED_SOFT, "minimum": PINK_LIGHT,
    "textClasses": {
        "callout": {"fontSize": 26, "fontFace": "Segoe UI Semibold", "color": RED},
        "title": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": INK},
        "header": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": INK},
        "label": {"fontSize": 9, "fontFace": "Segoe UI", "color": INK2},
    },
    "visualStyles": {
        "*": {"*": {
            "background": [{"show": False}],
            "border": [{"show": False}],
            "dropShadow": [{"show": False}],
            "title": [{"fontColor": {"solid": {"color": INK}}, "fontFamily": "Segoe UI Semibold", "fontSize": 12}],
            "visualHeader": [{"background": {"solid": {"color": "#FFFFFF"}}, "foreground": {"solid": {"color": RED}}, "border": {"solid": {"color": "#FFFFFF"}}}],
            "visualTooltip": [{"titleFontColor": {"solid": {"color": RED_DEEP}}, "valueFontColor": {"solid": {"color": INK}}, "background": {"solid": {"color": "#FFFFFF"}}}],
        }},
        "page": {"*": {"outspace": [{"color": {"solid": {"color": "#FDE9EC"}}}]}},
    },
}


def page_json():
    return {
        "$schema": PSCHEMA,
        "name": PAGE,
        "displayName": "Dashboard",
        "displayOption": "FitToPage",
        "height": 1080,
        "width": 1920,
        "objects": {
            "background": [{"properties": {
                "image": {"image": {
                    "name": lit("Zomato dashboard canvas"),
                    "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1, "ItemName": BG_FILE}}},
                    "scaling": lit("Fit"),
                }},
                "transparency": lit(0.0),
            }}],
            "outspace": [{"properties": {"color": color("#FDE9EC")}}],
        },
    }


def main():
    if not os.path.isfile(BG_PNG):
        sys.exit(f"Missing {BG_PNG}: render design/background.html first")
    src = zipfile.ZipFile(SRC)
    report = json.loads(src.read("Report/definition/report.json").decode("utf-8-sig"))

    # point the report at the new theme + canvas image
    report["themeCollection"]["customTheme"] = {
        "name": THEME_FILE,
        "reportVersionAtImport": report["themeCollection"].get("customTheme", {}).get("reportVersionAtImport",
                                                                                         {"visual": "2.14.0", "report": "3.4.0", "page": "2.3.1"}),
        "type": "RegisteredResources",
    }
    for pkg in report["resourcePackages"]:
        if pkg["name"] == "RegisteredResources":
            pkg["items"] = [{"name": BG_FILE, "path": BG_FILE, "type": "Image"},
                            {"name": THEME_FILE, "path": THEME_FILE, "type": "CustomTheme"}]

    visuals = build_visuals()
    replaced_prefixes = ("Report/StaticResources/RegisteredResources/", "Report/definition/pages/")
    # SecurityBindings signs the package contents; once the report changes it no longer
    # matches and Power BI rejects the file as "corrupted". Drop it (Power BI recreates it on save).
    replaced_exact = {"Report/definition/report.json", "SecurityBindings", "[Content_Types].xml"}
    content_types = src.read("[Content_Types].xml").decode("utf-8-sig")
    content_types = content_types.replace('<Override PartName="/SecurityBindings" ContentType="" />', "")

    tmp = OUT + ".tmp"
    with zipfile.ZipFile(tmp, "w") as out:
        for info in src.infolist():
            if info.filename == "[Content_Types].xml":
                out.writestr(info, ("﻿" + content_types).encode("utf-8"))
                continue
            if info.filename in replaced_exact or info.filename.startswith(replaced_prefixes):
                continue
            out.writestr(info, src.read(info.filename))  # keeps original compression (DataModel stays stored)

        def put(name, data):
            out.writestr(zipfile.ZipInfo(name, date_time=(2026, 11, 5, 12, 0, 0)), data, compress_type=zipfile.ZIP_DEFLATED)

        put("Report/definition/report.json", json.dumps(report, ensure_ascii=False))
        put(f"Report/StaticResources/RegisteredResources/{THEME_FILE}", json.dumps(THEME, ensure_ascii=False, indent=2))
        with open(BG_PNG, "rb") as fh:
            put(f"Report/StaticResources/RegisteredResources/{BG_FILE}", fh.read())
        put("Report/definition/pages/pages.json", json.dumps({
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
            "pageOrder": [PAGE], "activePageName": PAGE}))
        put(f"Report/definition/pages/{PAGE}/page.json", json.dumps(page_json(), ensure_ascii=False))
        for v in visuals:
            put(f"Report/definition/pages/{PAGE}/visuals/{v['name']}/visual.json", json.dumps(v, ensure_ascii=False))
    src.close()
    os.replace(tmp, OUT)
    charts = sum(1 for v in visuals if v["visual"]["visualType"] not in ("slicer", "card"))
    print(f"Wrote {OUT}: {len(visuals)} visuals ({charts} charts, "
          f"{sum(v['visual']['visualType'] == 'card' for v in visuals)} KPI cards, "
          f"{sum(v['visual']['visualType'] == 'slicer' for v in visuals)} slicers)")


if __name__ == "__main__":
    main()

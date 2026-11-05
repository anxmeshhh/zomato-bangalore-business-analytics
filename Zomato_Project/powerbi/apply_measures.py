"""
Push the DAX measures library (dax_measures.dax) into the open Power BI Desktop model.

    python Zomato_Project/powerbi/apply_measures.py

Open "Zomato dashboard.pbix" in Power BI Desktop first. The script finds the
local Analysis Services engine that holds the `zomato_powerbi` table, then adds
or updates each measure through the Tabular Object Model (TOM). Afterwards press
Save in Power BI Desktop to write the measures into the .pbix.
"""
from __future__ import annotations

import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAX_FILE = os.path.join(HERE, "dax_measures.dax")
TABLE = "zomato_powerbi"
FOLDER = "KPI Measures"

TOM_SEARCH = [
    r"C:\Program Files\Microsoft SQL Server Management Studio *\Release\Common7\IDE",
    r"C:\Program Files (x86)\Microsoft SQL Server Management Studio *\Common7\IDE",
    r"C:\Program Files\Microsoft SQL Server\*\DTS\Binn",
]
WORKSPACES = [
    os.path.expandvars(r"%USERPROFILE%\Microsoft\Power BI Desktop Store App\AnalysisServicesWorkspaces"),
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces"),
]

FORMATS = {
    "Total Restaurants": "#,0",
    "Average Rating": "0.00",
    "Average Cost for Two": "\u20b9#,0",
    "Total Votes": "#,0",
    "Average Votes": "#,0",
    "Online Order Share %": "0.0%",
    "Table Booking Share %": "0.0%",
    "Top Rated Outlets": "#,0",
    "Top Rated Share %": "0.0%",
    "Table Booking Lift": "+0.00;-0.00;0.00",
}


def parse_measures(path):
    """Return [(name, expression, description)] from the `// N. Desc` + `Name = expr` blocks."""
    text = open(path, encoding="utf-8").read()
    out = []
    for block in re.split(r"\n(?=// \d+\.)", text):
        m = re.match(r"// \d+\.\s*(.+?)\n(.+?)\s*=\s*(.*)", block.strip(), re.S)
        if m:
            desc, name, expr = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
            expr = re.sub(r"(\n\s*//[^\n]*)+\s*$", "", expr).strip()  # drop trailing section comments
            out.append((name, expr, desc))
    return out


def load_tom():
    import clr  # pythonnet

    for pattern in TOM_SEARCH:
        for d in sorted(glob.glob(pattern), reverse=True):
            if os.path.isfile(os.path.join(d, "Microsoft.AnalysisServices.Tabular.dll")):
                sys.path.append(d)
                clr.AddReference("Microsoft.AnalysisServices.Tabular")
                return
    sys.exit("Microsoft.AnalysisServices.Tabular.dll not found (install SSMS or the AMO client library)")


def ports():
    for root in WORKSPACES:
        for f in glob.glob(os.path.join(root, "*", "Data", "msmdsrv.port.txt")):
            raw = open(f, "rb").read()
            txt = raw.decode("utf-16-le" if b"\x00" in raw else "ascii", errors="ignore").strip("\ufeff \r\n\x00")
            if txt.isdigit():
                yield int(txt)


def find_model():
    from Microsoft.AnalysisServices.Tabular import Server

    for port in ports():
        s = Server()
        try:
            s.Connect(f"Data Source=localhost:{port}")
        except Exception:
            continue
        for db in s.Databases:
            if db.Model.Tables.Find(TABLE) is not None:
                return s, db, port
        s.Disconnect()
    sys.exit(f"No open Power BI model with a '{TABLE}' table. Open the .pbix in Power BI Desktop first.")


def main():
    measures = parse_measures(DAX_FILE)
    load_tom()
    from Microsoft.AnalysisServices.Tabular import Measure

    server, db, port = find_model()
    table = db.Model.Tables.Find(TABLE)
    added, updated = [], []
    for name, expr, desc in measures:
        m = table.Measures.Find(name)
        if m is None:
            m = Measure()
            m.Name = name
            table.Measures.Add(m)
            added.append(name)
        else:
            updated.append(name)
        m.Expression = expr
        m.Description = desc
        if name.endswith(" SVG"):
            m.DisplayFolder = "Animated Visuals"
            m.DataCategory = "ImageUrl"
        else:
            m.DisplayFolder = FOLDER
        if name in FORMATS:
            m.FormatString = FORMATS[name]
    db.Model.SaveChanges()

    # Validate: the engine reports a parse/semantic error per measure.
    table = db.Model.Tables.Find(TABLE)
    bad = [(m.Name, str(m.ErrorMessage)) for m in table.Measures if m.ErrorMessage]
    print(f"Model on localhost:{port}: {len(added)} added, {len(updated)} updated")
    for name in added + updated:
        print("  -", name)
    if bad:
        print("Measures with errors:")
        for n, e in bad:
            print(f"  ! {n}: {e}")
    server.Disconnect()
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

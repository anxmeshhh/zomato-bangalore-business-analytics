"""
Zomato Bangalore · Power BI Command Center

    python Zomato_Project/dashboard/app.py      ->  http://127.0.0.1:5050

Open "Zomato dashboard.pbix" in Power BI Desktop and the page switches to LIVE mode:
every number is a DAX query against the open model. With Power BI closed it serves
the same summary from zomato_powerbi.csv (the file the model imports).
"""
from __future__ import annotations

import json
import os
import threading
import time
import webbrowser

from flask import Flask, jsonify, request, send_from_directory

import queries
from powerbi_bridge import PowerBIBridge

HERE = os.path.dirname(os.path.abspath(__file__))
PBIX_PATH = os.path.join(queries.REPO_ROOT, "Zomato dashboard.pbix")
CONFIG_PATH = os.path.join(HERE, "dashboard_config.json")

app = Flask(__name__, static_folder=os.path.join(HERE, "static"), static_url_path="/static")
bridge = PowerBIBridge()


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


@app.get("/")
def index():
    return send_from_directory(os.path.join(HERE, "static"), "index.html")


@app.get("/api/status")
def status():
    live = bridge.ensure()
    st = bridge.status
    cfg = load_config()
    return jsonify({
        "live": live,
        "port": st.port,
        "database": st.database,
        "tables": st.tables if live else [],
        "reason": None if live else st.reason,
        "pbix": os.path.basename(PBIX_PATH),
        "pbix_exists": os.path.isfile(PBIX_PATH),
        "pbix_modified": os.path.getmtime(PBIX_PATH) if os.path.isfile(PBIX_PATH) else None,
        "snapshot": os.path.basename(queries.CSV_PATH),
        "embed_url": (cfg.get("embed_url") or "").strip(),
        "server_time": time.time(),
    })


@app.get("/api/options")
def options():
    try:
        if bridge.ensure():
            return jsonify({"source": "powerbi", **queries.dax_options(bridge)})
    except Exception:
        pass
    return jsonify({"source": "snapshot", **queries.snapshot_options()})


@app.get("/api/summary")
def summary():
    filters = queries.clean_filters(request.args)
    want = request.args.get("source", "auto")
    started = time.perf_counter()
    note = None
    if want != "snapshot" and bridge.ensure():
        try:
            data = queries.dax_summary(bridge, filters)
            data.update(source="powerbi", port=bridge.status.port)
            data["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
            return jsonify(data)
        except Exception as exc:
            note = f"Live query failed, showing snapshot ({type(exc).__name__}: {exc})"
    data = queries.snapshot_summary(filters)
    data.update(source="snapshot", note=note or bridge.status.reason)
    data["elapsed_ms"] = round((time.perf_counter() - started) * 1000)
    return jsonify(data)


@app.post("/api/open-powerbi")
def open_powerbi():
    if not os.path.isfile(PBIX_PATH):
        return jsonify({"ok": False, "error": "Zomato dashboard.pbix not found"}), 404
    if bridge.ensure():
        return jsonify({"ok": True, "already_open": True})
    os.startfile(PBIX_PATH)  # Windows: opens with Power BI Desktop
    return jsonify({"ok": True, "already_open": False})


if __name__ == "__main__":
    port = int(os.environ.get("DASHBOARD_PORT", "5050"))
    if os.environ.get("NO_BROWSER") != "1":
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)

"""
Live bridge to Power BI Desktop.

When a .pbix is open, Power BI Desktop runs a private Analysis Services engine
on a random localhost port and writes that port to `msmdsrv.port.txt` inside its
workspace folder. This module finds those engines, connects with ADOMD.NET
(through pythonnet) and runs DAX queries against the open data model, the same
engine that powers the report visuals.
"""
from __future__ import annotations

import glob
import os
import threading
import time
from dataclasses import dataclass, field

MODEL_TABLE = "zomato_powerbi"

WORKSPACE_ROOTS = [
    # Microsoft Store install
    os.path.expandvars(r"%USERPROFILE%\Microsoft\Power BI Desktop Store App\AnalysisServicesWorkspaces"),
    # MSI / exe install
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces"),
]

ADOMD_SEARCH = [
    r"C:\Program Files\Microsoft.NET\ADOMD.NET\*",
    r"C:\Program Files (x86)\Microsoft.NET\ADOMD.NET\*",
    r"C:\Program Files\Microsoft SQL Server Management Studio *\Release\Common7\IDE",
    r"C:\Program Files (x86)\Microsoft SQL Server Management Studio *\Common7\IDE",
]

_clr_ready = False
_clr_error: str | None = None
_AdomdConnection = None
_AdomdCommand = None


def _load_adomd() -> bool:
    """Load the ADOMD.NET client once. Returns False (with a reason) if unavailable."""
    global _clr_ready, _clr_error, _AdomdConnection, _AdomdCommand
    if _clr_ready:
        return True
    if _clr_error:
        return False
    try:
        import sys
        import clr  # pythonnet

        dll_dir = None
        for pattern in ADOMD_SEARCH:
            for d in sorted(glob.glob(pattern), reverse=True):  # newest version first
                if os.path.isfile(os.path.join(d, "Microsoft.AnalysisServices.AdomdClient.dll")):
                    dll_dir = d
                    break
            if dll_dir:
                break
        if not dll_dir:
            raise FileNotFoundError(
                "Microsoft.AnalysisServices.AdomdClient.dll not found. Install ADOMD.NET "
                "(https://learn.microsoft.com/analysis-services/client-libraries)."
            )
        sys.path.append(dll_dir)
        clr.AddReference("Microsoft.AnalysisServices.AdomdClient")
        from Microsoft.AnalysisServices.AdomdClient import AdomdCommand, AdomdConnection

        _AdomdConnection, _AdomdCommand = AdomdConnection, AdomdCommand
        _clr_ready = True
        return True
    except Exception as exc:  # pythonnet missing, DLL missing, runtime issue
        _clr_error = f"{type(exc).__name__}: {exc}"
        return False


def find_engine_ports() -> list[tuple[int, str]]:
    """Return (port, workspace_dir) for every Power BI Desktop engine that has written a port file."""
    found = []
    for root in WORKSPACE_ROOTS:
        for port_file in glob.glob(os.path.join(root, "*", "Data", "msmdsrv.port.txt")):
            try:
                raw = open(port_file, "rb").read()
                text = raw.decode("utf-16-le", errors="ignore") if b"\x00" in raw else raw.decode()
                port = int("".join(ch for ch in text if ch.isdigit()))
                found.append((port, os.path.dirname(os.path.dirname(port_file)), os.path.getmtime(port_file)))
            except (OSError, ValueError):
                continue
    found.sort(key=lambda t: t[2], reverse=True)  # most recently opened first
    return [(p, d) for p, d, _ in found]


def _net_to_py(v):
    """Convert ADOMD cell values (.NET objects) to plain Python values."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    t = type(v).__name__
    if t == "DBNull":
        return None
    if t == "Decimal":
        from System.Globalization import CultureInfo
        return float(v.ToString(CultureInfo.InvariantCulture))
    return str(v)


@dataclass
class PowerBIStatus:
    connected: bool = False
    port: int | None = None
    database: str | None = None
    tables: list = field(default_factory=list)
    reason: str | None = None
    checked_at: float = 0.0


class PowerBIBridge:
    """Thread-safe single connection to the open Power BI Desktop model."""

    def __init__(self):
        self._lock = threading.RLock()
        self._conn = None
        self.status = PowerBIStatus()

    # ---------- connection management ----------
    def _close(self):
        try:
            if self._conn is not None:
                self._conn.Close()
        except Exception:
            pass
        self._conn = None

    def _try_port(self, port: int):
        conn = _AdomdConnection(f"Data Source=localhost:{port};Connect Timeout=3")
        conn.Open()
        return conn

    def connect(self) -> PowerBIStatus:
        with self._lock:
            st = PowerBIStatus(checked_at=time.time())
            if not _load_adomd():
                st.reason = f"ADOMD.NET client unavailable ({_clr_error})"
                self.status = st
                return st
            ports = find_engine_ports()
            if not ports:
                st.reason = "Power BI Desktop is not running (no open .pbix found)"
                self._close()
                self.status = st
                return st
            last_err = None
            for port, _ws in ports:
                try:
                    conn = self._try_port(port)
                except Exception as exc:  # stale port file from a closed session
                    last_err = exc
                    continue
                self._close()
                self._conn = conn
                try:
                    tables = [r["Name"] for r in self._query_raw("SELECT [Name] FROM $SYSTEM.TMSCHEMA_TABLES")]
                except Exception:
                    tables = []
                if MODEL_TABLE not in tables:
                    last_err = RuntimeError(f"model on port {port} has no '{MODEL_TABLE}' table")
                    self._close()
                    continue
                st.connected, st.port, st.database = True, port, conn.Database
                st.tables = self._table_info(tables)
                self.status = st
                return st
            st.reason = f"Could not reach the Power BI engine ({last_err})"
            self.status = st
            return st

    def _table_info(self, tables):
        info = []
        sources = {}
        try:
            for r in self._query_raw("SELECT [TableID],[QueryDefinition] FROM $SYSTEM.TMSCHEMA_PARTITIONS"):
                sources[r["TableID"]] = r["QueryDefinition"] or ""
            ids = {r["Name"]: r["ID"] for r in self._query_raw("SELECT [ID],[Name] FROM $SYSTEM.TMSCHEMA_TABLES")}
        except Exception:
            ids = {}
        for t in tables:
            try:
                n = self._query_raw(f"EVALUATE ROW(\"n\", COUNTROWS('{t}'))")[0]["[n]"]
            except Exception:
                n = None
            src = sources.get(ids.get(t), "")
            kind = "SQL Server" if "Sql.Database" in src else "CSV" if "Csv.Document" in src else "Model"
            info.append({"name": t, "rows": n, "source": kind})
        return info

    def ensure(self) -> bool:
        """Make sure we hold a live connection; re-discover if the old one died."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._query_raw("EVALUATE ROW(\"ok\", 1)")
                    return True
                except Exception:
                    self._close()
            return self.connect().connected

    # ---------- querying ----------
    def _query_raw(self, text: str) -> list[dict]:
        cmd = _AdomdCommand(text, self._conn)
        reader = cmd.ExecuteReader()
        try:
            cols = [reader.GetName(i) for i in range(reader.FieldCount)]
            rows = []
            while reader.Read():
                rows.append({cols[i]: _net_to_py(reader.GetValue(i)) for i in range(reader.FieldCount)})
            return rows
        finally:
            reader.Close()

    def query(self, dax: str) -> list[dict]:
        """Run a DAX query; column keys are simplified ('T'[col] -> col, [measure] -> measure)."""
        with self._lock:
            if not self.ensure():
                raise ConnectionError(self.status.reason or "Power BI not connected")
            try:
                rows = self._query_raw(dax)
            except Exception:
                # engine restarted (e.g. user re-opened the file) -> reconnect once
                self._close()
                if not self.connect().connected:
                    raise
                rows = self._query_raw(dax)
        return [{_simplify(k): v for k, v in r.items()} for r in rows]


def _simplify(col: str) -> str:
    # "zomato_powerbi[location]" -> "location", "[avg]" -> "avg"
    if "[" in col:
        col = col[col.rfind("[") + 1:]
    return col.rstrip("]")

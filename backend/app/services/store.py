"""SQLite persistence for simulated security events (stdlib only)."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, device_id TEXT NOT NULL, device_name TEXT NOT NULL,
  event_type TEXT NOT NULL, protocol TEXT NOT NULL, topic TEXT NOT NULL, source_ip TEXT NOT NULL,
  metrics TEXT NOT NULL, label TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open',
  detection_source TEXT NOT NULL, is_simulated INTEGER NOT NULL DEFAULT 1, run_id TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_events_device ON events(device_id);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
"""
COLS = ("ts", "device_id", "device_name", "event_type", "protocol", "topic", "source_ip", "metrics", "label",
        "severity", "status", "detection_source", "is_simulated", "run_id")
VALID_STATUS = ("open", "acknowledged", "resolved")


def _row(r: sqlite3.Row) -> Dict[str, Any]:
    d = dict(r)
    d["metrics"] = json.loads(d["metrics"])
    d["is_simulated"] = bool(d["is_simulated"])
    return d


class EventStore:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def insert_many(self, events: List[Dict[str, Any]]) -> None:
        rows = [tuple(json.dumps(e[c]) if c == "metrics" else (int(e[c]) if c == "is_simulated" else e[c])
                      for c in COLS) for e in events]
        with self._lock:
            self._db.executemany(f"INSERT INTO events ({','.join(COLS)}) VALUES ({','.join('?' * len(COLS))})", rows)
            self._db.commit()

    def reset(self) -> None:
        with self._lock:
            self._db.execute("DELETE FROM events")
            self._db.execute("DELETE FROM sqlite_sequence WHERE name='events'")
            self._db.commit()

    def get(self, event_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            r = self._db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        return _row(r) if r else None

    def set_status(self, event_id: int, status: str) -> Optional[Dict[str, Any]]:
        if status not in VALID_STATUS:
            raise ValueError(f"invalid status: {status}")
        with self._lock:
            self._db.execute("UPDATE events SET status=? WHERE id=?", (status, event_id))
            self._db.commit()
        return self.get(event_id)

    def query(self, *, q: Optional[str] = None, device_id: Optional[str] = None, event_type: Optional[str] = None,
              label: Optional[str] = None, severity: Optional[str] = None, status: Optional[str] = None,
              since: Optional[str] = None, until: Optional[str] = None, limit: int = 50,
              offset: int = 0) -> Tuple[int, List[Dict[str, Any]]]:
        where, args = [], []
        for col, val in (("device_id", device_id), ("event_type", event_type), ("label", label),
                         ("severity", severity), ("status", status)):
            if val:
                where.append(f"{col}=?")
                args.append(val)
        if since:
            where.append("ts>=?")
            args.append(since)
        if until:
            where.append("ts<=?")
            args.append(until)
        if q:
            like = f"%{q.lower()}%"
            where.append("(lower(device_name) LIKE ? OR lower(event_type) LIKE ? OR lower(topic) LIKE ? "
                         "OR lower(source_ip) LIKE ? OR lower(label) LIKE ?)")
            args += [like] * 5
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        with self._lock:
            total = self._db.execute(f"SELECT COUNT(*) FROM events {clause}", args).fetchone()[0]
            rows = self._db.execute(f"SELECT * FROM events {clause} ORDER BY id DESC LIMIT ? OFFSET ?",
                                    args + [limit, offset]).fetchall()
        return total, [_row(r) for r in rows]

    # ---------------------------------------------------------------- aggregates
    def counts(self) -> Dict[str, Any]:
        with self._lock:
            c = self._db.cursor()
            total = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            susp = c.execute("SELECT COUNT(*) FROM events WHERE label!='normal'").fetchone()[0]
            high = c.execute("SELECT COUNT(*) FROM events WHERE severity='high' AND status='open'").fetchone()[0]
            dist = {r[0]: r[1] for r in c.execute(
                "SELECT label, COUNT(*) FROM events WHERE label!='normal' GROUP BY label")}
        return {"total": total, "suspicious": susp, "high_open": high, "distribution": dist}

    def timeline_rows(self, limit: int = 1500) -> List[Tuple[str, str]]:
        with self._lock:
            rows = self._db.execute("SELECT ts, label FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [(r[0], r[1]) for r in reversed(rows)]

    def device_stats(self, recent_window: int = 200) -> Dict[str, Dict[str, Any]]:
        """Per-device totals. 'open_alerts' only counts the most recent `recent_window` events overall,
        so a device returns to 'normal' once old alerts scroll out of the window or are resolved."""
        with self._lock:
            c = self._db.cursor()
            max_id = c.execute("SELECT COALESCE(MAX(id),0) FROM events").fetchone()[0]
            out: Dict[str, Dict[str, Any]] = {}
            for r in c.execute("SELECT device_id, COUNT(*), MAX(ts) FROM events GROUP BY device_id"):
                out[r[0]] = {"total_events": r[1], "last_activity": r[2], "open_alerts": 0}
            for r in c.execute("SELECT device_id, COUNT(*) FROM events WHERE label!='normal' AND status='open' "
                               "AND id>? GROUP BY device_id", (max_id - recent_window,)):
                out.setdefault(r[0], {"total_events": 0, "last_activity": None, "open_alerts": 0})["open_alerts"] = r[1]
        return out

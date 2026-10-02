"""SQLite-backed append-only run history with content checksums."""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone


class RunStore:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("""CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            mode TEXT NOT NULL,
            label TEXT NOT NULL,
            checksum TEXT NOT NULL,
            input_json TEXT NOT NULL,
            output_json TEXT NOT NULL
        )""")
        self.connection.commit()

    def close(self):
        self.connection.close()

    def save(self, mode, label, input_data, output):
        if mode not in ("single", "scenario", "batch"):
            raise ValueError("unknown run mode")
        if not isinstance(label, str) or len(label) > 200:
            raise ValueError("label must be at most 200 characters")
        source = json.dumps(
            input_data, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        result = json.dumps(
            output, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        checksum = hashlib.sha256(source.encode()).hexdigest()
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO runs(created_at,mode,label,checksum,input_json,output_json) VALUES(?,?,?,?,?,?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    mode,
                    label,
                    checksum,
                    source,
                    result,
                ),
            )
        return cursor.lastrowid

    def list(self, limit=50, before=None):
        if not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if before is None:
            query = "SELECT id,created_at,mode,label,checksum FROM runs ORDER BY id DESC LIMIT ?"
            arguments = (limit,)
        else:
            if not isinstance(before, int) or before <= 0:
                raise ValueError("invalid pagination cursor")
            query = "SELECT id,created_at,mode,label,checksum FROM runs WHERE id < ? ORDER BY id DESC LIMIT ?"
            arguments = (before, limit)
        rows = [dict(row) for row in self.connection.execute(query, arguments)]
        return {
            "runs": rows,
            "next_cursor": rows[-1]["id"] if len(rows) == limit else None,
        }

    def get(self, run_id):
        row = self.connection.execute(
            "SELECT * FROM runs WHERE id=?", (run_id,)
        ).fetchone()
        if row is None:
            raise KeyError("run not found")
        result = dict(row)
        result["input"] = json.loads(result.pop("input_json"))
        result["output"] = json.loads(result.pop("output_json"))
        return result

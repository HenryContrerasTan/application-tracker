#!/usr/bin/env python3
"""
Job / Internship Application Tracker — full-stack, stdlib-only.

Backend:  Python (http.server + sqlite3, no third-party packages)
Frontend: HTML + CSS + JavaScript, served from this same server
Database: SQLite file (tracker.db, created next to app.py on first run)

Run:
    python3 app.py
    # then open http://localhost:8000 in a browser

API:
    GET    /api/applications?search=&status=&type=
    POST   /api/applications          JSON body, creates a row
    PUT    /api/applications/<id>     JSON body, updates a row
    DELETE /api/applications/<id>
"""
import json
import os
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tracker.db")
STATUSES = {"Saved", "Applied", "Interview", "Offer", "Rejected"}
TYPES = {"Full-time", "Internship"}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'Full-time',
            status TEXT NOT NULL DEFAULT 'Saved',
            location TEXT DEFAULT '',
            date_applied TEXT DEFAULT '',
            link TEXT DEFAULT '',
            notes TEXT DEFAULT ''
        )
        """
    )
    conn.commit()
    return conn


def row_to_dict(row):
    return dict(row)


def valid_payload(data, partial=False):
    """Validate a JSON payload. Returns (cleaned_dict, error_string_or_None)."""
    if not isinstance(data, dict):
        return None, "Body must be a JSON object."
    cleaned = {}
    for field in ("company", "role", "type", "status",
                  "location", "date_applied", "link", "notes"):
        if field in data:
            cleaned[field] = str(data[field]).strip()
    if not partial:
        if not cleaned.get("company") or not cleaned.get("role"):
            return None, "company and role are required."
    if cleaned.get("type") and cleaned["type"] not in TYPES:
        return None, f"type must be one of: {', '.join(sorted(TYPES))}."
    if cleaned.get("status") and cleaned["status"] not in STATUSES:
        return None, f"status must be one of: {', '.join(sorted(STATUSES))}."
    return cleaned, None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    # Silence the default per-request log noise, keep errors visible.
    def log_message(self, fmt, *args):
        pass

    def send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/applications":
            query = parse_qs(parsed.query)
            search = query.get("search", [""])[0].strip()
            status = query.get("status", [""])[0].strip()
            app_type = query.get("type", [""])[0].strip()

            sql = "SELECT * FROM applications WHERE 1=1"
            params = []
            if search:
                sql += " AND (company LIKE ? OR role LIKE ? OR notes LIKE ?)"
                like = f"%{search}%"
                params += [like, like, like]
            if status in STATUSES:
                sql += " AND status = ?"
                params.append(status)
            if app_type in TYPES:
                sql += " AND type = ?"
                params.append(app_type)
            sql += " ORDER BY date_applied DESC, id DESC"

            conn = get_db()
            rows = conn.execute(sql, params).fetchall()
            conn.close()
            self.send_json(200, [row_to_dict(r) for r in rows])
            return
        if parsed.path == "/api/stats":
            conn = get_db()
            counts = {
                r["status"]: r["n"]
                for r in conn.execute(
                    "SELECT status, COUNT(*) AS n FROM applications GROUP BY status"
                )
            }
            total = conn.execute("SELECT COUNT(*) AS n FROM applications").fetchone()["n"]
            conn.close()
            self.send_json(200, {"total": total, "by_status": counts})
            return
        # Anything else: serve the frontend files from the project folder.
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/applications":
            self.send_json(404, {"error": "Not found."})
            return
        try:
            data = self.read_json()
        except json.JSONDecodeError:
            self.send_json(400, {"error": "Invalid JSON body."})
            return
        cleaned, error = valid_payload(data)
        if error:
            self.send_json(400, {"error": error})
            return
        conn = get_db()
        cur = conn.execute(
            """INSERT INTO applications
               (company, role, type, status, location, date_applied, link, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (cleaned.get("company"), cleaned.get("role"),
             cleaned.get("type", "Full-time"), cleaned.get("status", "Saved"),
             cleaned.get("location", ""), cleaned.get("date_applied", ""),
             cleaned.get("link", ""), cleaned.get("notes", "")),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM applications WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        conn.close()
        self.send_json(201, row_to_dict(row))

    def do_PUT(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) != 3 or parts[0] != "api" or parts[1] != "applications":
            self.send_json(404, {"error": "Not found."})
            return
        try:
            app_id = int(parts[2])
            data = self.read_json()
        except (ValueError, json.JSONDecodeError):
            self.send_json(400, {"error": "Invalid id or JSON body."})
            return
        cleaned, error = valid_payload(data, partial=True)
        if error or not cleaned:
            self.send_json(400, {"error": error or "Nothing to update."})
            return
        conn = get_db()
        sets = ", ".join(f"{k} = ?" for k in cleaned)
        conn.execute(
            f"UPDATE applications SET {sets} WHERE id = ?",
            (*cleaned.values(), app_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        ).fetchone()
        conn.close()
        if row is None:
            self.send_json(404, {"error": "Application not found."})
            return
        self.send_json(200, row_to_dict(row))

    def do_DELETE(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) != 3 or parts[0] != "api" or parts[1] != "applications":
            self.send_json(404, {"error": "Not found."})
            return
        try:
            app_id = int(parts[2])
        except ValueError:
            self.send_json(400, {"error": "Invalid id."})
            return
        conn = get_db()
        cur = conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        conn.commit()
        conn.close()
        if cur.rowcount == 0:
            self.send_json(404, {"error": "Application not found."})
            return
        self.send_json(200, {"deleted": app_id})


if __name__ == "__main__":
    get_db().close()  # Create tracker.db + table on first run.
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Application Tracker running at http://localhost:8000")
    print("Press Ctrl+C to stop. Data is stored in tracker.db.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")

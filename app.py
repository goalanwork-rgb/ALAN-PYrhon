"""Serve the py_user list page and its read-only JSON endpoint."""

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from mysql.connector import Error as MySQLError

from conn.connect import get_connection


PROJECT_DIR = Path(__file__).resolve().parent


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_DIR), **kwargs)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/users":
            self.send_users()
            return
        if path == "/":
            self.path = "/index.html"
        super().do_GET()

    def send_users(self):
        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT id, name, email, date_time FROM py_user ORDER BY id")
            users = [
                {
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "date_time": date_time.strftime("%Y-%m-%d %H:%M:%S") if date_time else None,
                }
                for user_id, name, email, date_time in cursor.fetchall()
            ]
            self.send_json(200, users)
        except (RuntimeError, MySQLError):
            self.send_json(503, {"error": "Database connection failed."})
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    host = os.getenv("PYTHON_HOST", "127.0.0.1")
    port = int(os.getenv("PYTHON_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Serving py_user list at http://localhost:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
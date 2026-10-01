"""Serve the py_user list page and its read-only JSON endpoint."""

import json
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from mysql.connector import Error as MySQLError

from conn.connect import get_connection


PROJECT_DIR = Path(r"D:\AppServ\www\ALAN-PYrhon")


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

    def do_POST(self):
        if urlsplit(self.path).path != "/api/users":
            self.send_error(404)
            return

        user_data = self.read_user_payload()
        if user_data is None:
            return

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor()
            cursor.execute("INSERT INTO py_user (name, email) VALUES (%s, %s)", user_data)
            connection.commit()
            self.send_json(201, {"id": cursor.lastrowid})
        except (RuntimeError, MySQLError):
            if connection is not None:
                connection.rollback()
            self.send_json(503, {"error": "Could not create member."})
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def do_PUT(self):
        user_id = self.get_user_id()
        if user_id is None:
            self.send_error(404)
            return

        user_data = self.read_user_payload()
        if user_data is None:
            return

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM py_user WHERE id = %s", (user_id,))
            if cursor.fetchone() is None:
                self.send_json(404, {"error": "Member not found."})
                return
            cursor.execute(
                "UPDATE py_user SET name = %s, email = %s WHERE id = %s",
                (*user_data, user_id),
            )
            connection.commit()
            self.send_json(200, {"message": "Member updated."})
        except (RuntimeError, MySQLError):
            if connection is not None:
                connection.rollback()
            self.send_json(503, {"error": "Could not update member."})
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def do_DELETE(self):
        user_id = self.get_user_id()
        if user_id is None:
            self.send_error(404)
            return

        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor()
            cursor.execute("DELETE FROM py_user WHERE id = %s", (user_id,))
            if cursor.rowcount == 0:
                self.send_json(404, {"error": "Member not found."})
                return
            connection.commit()
            self.send_json(200, {"message": "Member deleted."})
        except (RuntimeError, MySQLError):
            if connection is not None:
                connection.rollback()
            self.send_json(503, {"error": "Could not delete member."})
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    def get_user_id(self):
        match = re.fullmatch(r"/api/users/(\d+)", urlsplit(self.path).path)
        return int(match.group(1)) if match else None

    def read_user_payload(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > 16384:
                raise ValueError
            payload = json.loads(self.rfile.read(content_length))
        except (ValueError, UnicodeDecodeError):
            self.send_json(400, {"error": "Invalid JSON request."})
            return None

        if not isinstance(payload, dict):
            self.send_json(400, {"error": "Invalid member data."})
            return None

        name = payload.get("name")
        email = payload.get("email")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 255:
            self.send_json(400, {"error": "Name is required and must be at most 255 characters."})
            return None
        if (not isinstance(email, str) or len(email.strip()) > 255
                or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip())):
            self.send_json(400, {"error": "A valid email is required."})
            return None

        return name.strip(), email.strip()

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
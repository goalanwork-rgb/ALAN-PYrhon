"""MySQL connection helper for the local Python list page."""

import os

import mysql.connector


def get_connection():
    password = os.getenv("MYSQL_PASSWORD", "alan1123")

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=os.getenv("MYSQL_DATABASE", "python_sql"),
        user=os.getenv("MYSQL_USER", "root"),
        password=password,
        connection_timeout=5,
    )
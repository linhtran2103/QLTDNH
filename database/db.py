import os
from contextlib import contextmanager
from pathlib import Path

import pyodbc
from dotenv import load_dotenv


# =========================================================
# ĐỌC FILE .ENV
# Cấu trúc:
# QLTDNH/
#   backend/.env
#   database/db.py
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / "backend" / ".env"

load_dotenv(ENV_FILE, override=True)


# =========================================================
# KẾT NỐI SQL SERVER
# =========================================================

def get_connection():
    driver = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    server = os.getenv("DB_SERVER", r"MSI\QLTDNH")
    database = os.getenv("DB_NAME", "QLTD")
    trusted = os.getenv("DB_TRUSTED_CONNECTION", "yes").lower()

    if trusted in ("yes", "true", "1"):
        connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
    else:
        username = os.getenv("DB_USERNAME", "")
        password = os.getenv("DB_PASSWORD", "")

        connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )

    return pyodbc.connect(connection_string, timeout=5)


@contextmanager
def db_cursor(commit=False):
    """Mở cursor, commit khi được yêu cầu và luôn đóng tài nguyên."""
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        dong_ket_noi(cursor, conn)


# =========================================================
# ĐÓNG KẾT NỐI
# =========================================================

def dong_ket_noi(cursor=None, conn=None):
    try:
        if cursor is not None:
            cursor.close()
    except Exception:
        pass

    try:
        if conn is not None:
            conn.close()
    except Exception:
        pass


# =========================================================
# CHUYỂN DỮ LIỆU SQL SERVER SANG JSON
# =========================================================

def convert_to_json(cursor):
    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()

    result = []

    for row in rows:
        item = {}

        for index, column in enumerate(columns):
            value = row[index]

            if hasattr(value, "isoformat"):
                value = value.isoformat()

            item[column] = value

        result.append(item)

    return result


def convert_one_to_json(cursor):
    columns = [column[0] for column in cursor.description]
    row = cursor.fetchone()

    if row is None:
        return None

    result = {}

    for index, column in enumerate(columns):
        value = row[index]

        if hasattr(value, "isoformat"):
            value = value.isoformat()

        result[column] = value

    return result
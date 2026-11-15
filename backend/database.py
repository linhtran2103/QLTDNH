
import os
import pyodbc
from dotenv import load_dotenv
from decimal import Decimal

# Đọc cấu hình trong file .env
load_dotenv(override=True)


# =====================================================
# 1. KẾT NỐI SQL SERVER
# =====================================================

def get_connection():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    driver = os.getenv(
        "DB_DRIVER",
        "ODBC Driver 17 for SQL Server"
    )

    trusted = os.getenv(
        "DB_TRUSTED_CONNECTION",
        "yes"
    ).lower()

    if not server or not database:
        raise RuntimeError(
            "Thiếu DB_SERVER hoặc DB_NAME trong file .env"
        )

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
    )

    if trusted == "yes":
        connection_string += "Trusted_Connection=yes;"
    else:
        username = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")

        if not username or not password:
            raise RuntimeError(
                "Thiếu DB_USER hoặc DB_PASSWORD trong file .env"
            )

        connection_string += (
            f"UID={username};"
            f"PWD={password};"
        )

    return pyodbc.connect(connection_string)


# =====================================================
# 2. ĐÓNG KẾT NỐI VÀ CURSOR
# =====================================================

def dong_ket_noi(connection, cursor=None):
    try:
        if cursor is not None:
            cursor.close()
    finally:
        if connection is not None:
            connection.close()


# =====================================================
# 3. CHUYỂN KẾT QUẢ SQL SERVER THÀNH DANH SÁCH JSON
# =====================================================

def convert_to_json(cursor):
    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description]

    result = []

    for row in rows:
        item = {}

        for index, column in enumerate(columns):
            value = row[index]

            if isinstance(value, Decimal):
                value = float(value)

            item[column] = value

        result.append(item)

    return result


# =====================================================
# 4. CHUYỂN MỘT DÒNG DỮ LIỆU THÀNH DICTIONARY
# =====================================================

def convert_one_to_json(cursor):
    row = cursor.fetchone()

    if row is None:
        return None

    columns = [column[0] for column in cursor.description]

    item = {}

    for index, column in enumerate(columns):
        value = row[index]

        if isinstance(value, Decimal):
            value = float(value)

        item[column] = value

    return item

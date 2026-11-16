import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.db import get_connection

ten_dang_nhap = input("Tên đăng nhập: ").strip()
mat_khau = input("Mật khẩu: ").strip()
ho_ten = input("Họ tên: ").strip()

conn = None
cursor = None

try:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO NGUOI_DUNG
            (TenDangNhap, MatKhauHash, HoTen, VaiTro, TrangThai)
        VALUES (?, ?, ?, ?, 1)
    """, ten_dang_nhap, mat_khau, ho_ten, "admin")

    conn.commit()
    print("Tạo tài khoản admin thành công!")

except Exception as e:
    if conn:
        conn.rollback()
    print("Lỗi:", e)

finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
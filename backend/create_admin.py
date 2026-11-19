"""Tạo tài khoản Admin đầu tiên. Chạy:  python backend/create_admin.py"""
import sys
from getpass import getpass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from werkzeug.security import generate_password_hash  # noqa: E402

from database.db import db_cursor  # noqa: E402


def main():
    ten_dang_nhap = input("Tên đăng nhập: ").strip()
    ho_ten = input("Họ tên: ").strip()
    mat_khau = getpass("Mật khẩu (tối thiểu 6 ký tự): ")

    if not (ten_dang_nhap and ho_ten and len(mat_khau) >= 6):
        print("Thông tin không hợp lệ.")
        return 1

    try:
        with db_cursor(commit=True) as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM NGUOI_DUNG WHERE TenDangNhap = ?",
                (ten_dang_nhap,),
            )
            if cursor.fetchone()[0] > 0:
                print("Tên đăng nhập đã tồn tại.")
                return 1

            cursor.execute(
                """
                INSERT INTO NGUOI_DUNG
                    (TenDangNhap, MatKhauHash, HoTen, VaiTro, TrangThai, NgayTao)
                VALUES (?, ?, ?, 'admin', 1, GETDATE())
                """,
                (ten_dang_nhap, generate_password_hash(mat_khau), ho_ten),
            )
    except Exception as error:
        print("Lỗi:", error)
        return 1

    print("Tạo tài khoản Admin thành công!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

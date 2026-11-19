from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from database.db import convert_one_to_json, db_cursor
from backend.config import (
    TOKEN_MAX_AGE,
    VAI_TRO_ADMIN,
    VAI_TRO_HOP_LE,
    VAI_TRO_NHAN_VIEN,
)
from backend.utils.response import that_bai


def chuan_hoa_vai_tro(vai_tro):
    value = str(vai_tro or "").strip().lower()
    if value in ("admin", "manager"):
        return value
    if value in ("nhanvien", "nhan_vien", "nhân viên", "employee", "staff", "user"):
        return VAI_TRO_NHAN_VIEN
    return None


def tao_token(ma_nguoi_dung):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps({"MaNguoiDung": ma_nguoi_dung})


def lay_nguoi_dung_tu_token():
    """Đọc Bearer token, trả về user đang hoạt động hoặc None."""
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None

    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        data = serializer.loads(header[7:].strip(), max_age=TOKEN_MAX_AGE)
        ma = data["MaNguoiDung"]
    except (BadSignature, SignatureExpired, KeyError, TypeError):
        return None

    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT MaNguoiDung, TenDangNhap, HoTen, VaiTro, TrangThai
            FROM NGUOI_DUNG WHERE MaNguoiDung = ?
            """,
            (ma,),
        )
        user = convert_one_to_json(cursor)

    if not user or not user["TrangThai"]:
        return None

    role = chuan_hoa_vai_tro(user["VaiTro"])
    if role not in VAI_TRO_HOP_LE:
        return None
    user["VaiTro"] = role
    return user


def yeu_cau_vai_tro(*vai_tros):
    allowed = {chuan_hoa_vai_tro(role) for role in vai_tros}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = lay_nguoi_dung_tu_token()
            if not user:
                return that_bai("Token không hợp lệ hoặc đã hết hạn", 401)
            if user["VaiTro"] not in allowed:
                return that_bai("Bạn không có quyền thực hiện chức năng này", 403)

            g.nguoi_dung = user
            g.ma_nguoi_dung = user["MaNguoiDung"]
            return func(*args, **kwargs)

        return wrapper

    return decorator


def yeu_cau_dang_nhap(func=None, *, admin=False):
    """Yêu cầu đăng nhập, hoặc chỉ cho phép tài khoản admin."""
    decorator = yeu_cau_vai_tro(VAI_TRO_ADMIN) if admin else yeu_cau_vai_tro(*VAI_TRO_HOP_LE)
    return decorator(func) if func else decorator


chi_admin = yeu_cau_dang_nhap(admin=True) 
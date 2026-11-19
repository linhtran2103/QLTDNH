from flask import Blueprint, request

from database.db import convert_to_json, db_cursor
from backend.middleware.auth_middleware import chi_admin
from backend.utils.response import thanh_cong
from backend.utils.validators import chuoi, gioi_han_dong


nhat_ky_bp = Blueprint("nhat_ky", __name__)


# =====================================================

@nhat_ky_bp.route("/api/nhat-ky", methods=["GET"])
@chi_admin
def danh_sach_nhat_ky():
    sql = """
        SELECT TOP (?) A.*, N.TenDangNhap, N.HoTen
        FROM ACTIVITY_LOGS A
        LEFT JOIN NGUOI_DUNG N ON A.MaNguoiDung = N.MaNguoiDung
        WHERE 1 = 1
    """
    params = [gioi_han_dong()]

    for tham_so, cot in (("hanh_dong", "A.HanhDong"),
                         ("bang", "A.BangTacDong")):
        gia_tri = chuoi(request.args.get(tham_so))
        if gia_tri:
            sql += f" AND {cot} LIKE ?"
            params.append(f"%{gia_tri}%")

    with db_cursor() as cursor:
        cursor.execute(sql + " ORDER BY A.ThoiGian DESC", params)
        return thanh_cong(data=convert_to_json(cursor))


@nhat_ky_bp.route("/api/lich-su-dang-nhap", methods=["GET"])
@chi_admin
def danh_sach_lich_su_dang_nhap():
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT TOP (?) L.*, N.TenDangNhap, N.HoTen
            FROM LOGIN_HISTORY L
            LEFT JOIN NGUOI_DUNG N ON L.MaNguoiDung = N.MaNguoiDung
            ORDER BY L.ThoiGianDangNhap DESC
            """,
            (gioi_han_dong(),),
        )
        return thanh_cong(data=convert_to_json(cursor))


# =====================================================


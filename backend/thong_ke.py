from flask import Blueprint, current_app, request

from database.db import convert_to_json, db_cursor
from backend.middleware.auth_middleware import yeu_cau_dang_nhap
from backend.utils.response import thanh_cong, that_bai
from backend.utils.validators import doc_so_nguyen, gioi_han_dong


thong_ke_bp = Blueprint("thong_ke", __name__)


@thong_ke_bp.route("/api/health")
def health():
    try:
        with db_cursor() as cursor:
            cursor.execute("SELECT DB_NAME()")
            ten_db = cursor.fetchone()[0]
    except Exception as error:
        current_app.logger.exception("Lỗi kết nối SQL Server")
        return that_bai(f"Không kết nối được SQL Server: {error}", 500)

    return thanh_cong("Backend đã kết nối SQL Server thành công",
                      database=ten_db)


@thong_ke_bp.route("/api/lich-su-gia", methods=["GET"])
@yeu_cau_dang_nhap
def danh_sach_lich_su_gia():
    sql = """
        SELECT TOP (?) L.*, M.MaMon, M.TenMonAn, N.TenDangNhap
        FROM LICH_SU_GIA L
        LEFT JOIN MON_AN M ON L.MaMonAn = M.MaMonAn
        LEFT JOIN NGUOI_DUNG N ON L.MaNguoiDung = N.MaNguoiDung
        WHERE 1 = 1
    """
    params = [gioi_han_dong()]

    ma_mon_an = doc_so_nguyen(request.args.get("ma_mon_an"))
    if ma_mon_an is not None:
        sql += " AND L.MaMonAn = ?"
        params.append(ma_mon_an)

    with db_cursor() as cursor:
        cursor.execute(sql + " ORDER BY L.ThoiGianThayDoi DESC", params)
        return thanh_cong(data=convert_to_json(cursor))
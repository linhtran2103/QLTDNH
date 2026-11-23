
from datetime import date

from flask import Blueprint, current_app, request

from database.db import convert_to_json, db_cursor
from backend.middleware.auth_middleware import yeu_cau_dang_nhap
from backend.utils.response import thanh_cong, that_bai
from backend.utils.validators import doc_so_nguyen, gioi_han_dong


thong_ke_bp = Blueprint("thong_ke", __name__)


# =========================================================
# KIỂM TRA KẾT NỐI SQL SERVER
# =========================================================

@thong_ke_bp.route("/api/health")
def health():
    try:
        with db_cursor() as cursor:
            cursor.execute("SELECT DB_NAME()")
            ten_db = cursor.fetchone()[0]

    except Exception as error:
        current_app.logger.exception("Lỗi kết nối SQL Server")

        return that_bai(
            f"Không kết nối được SQL Server: {error}",
            500
        )

    return thanh_cong(
        "Backend đã kết nối SQL Server thành công",
        database=ten_db
    )


# =========================================================
# DANH SÁCH LỊCH SỬ GIÁ
# =========================================================

@thong_ke_bp.route("/api/lich-su-gia", methods=["GET"])
@yeu_cau_dang_nhap
def danh_sach_lich_su_gia():

    sql = """
        SELECT TOP (?) 
            L.*,
            M.MaMon,
            M.TenMonAn,
            N.TenDangNhap
        FROM LICH_SU_GIA L
        LEFT JOIN MON_AN M
            ON L.MaMonAn = M.MaMonAn
        LEFT JOIN NGUOI_DUNG N
            ON L.MaNguoiDung = N.MaNguoiDung
        WHERE 1 = 1
    """

    params = [gioi_han_dong()]

    ma_mon_an = doc_so_nguyen(
        request.args.get("ma_mon_an")
    )

    if ma_mon_an is not None:
        sql += " AND L.MaMonAn = ?"
        params.append(ma_mon_an)

    try:
        with db_cursor() as cursor:
            cursor.execute(
                sql + " ORDER BY L.ThoiGianThayDoi DESC",
                params
            )

            return thanh_cong(
                data=convert_to_json(cursor)
            )

    except Exception:
        current_app.logger.exception(
            "Lỗi khi lấy lịch sử giá"
        )

        return that_bai(
            "Không thể lấy danh sách lịch sử giá",
            500
        )


# =========================================================
# THỐNG KÊ DOANH THU
# =========================================================

@thong_ke_bp.route(
    "/api/thong-ke/doanh-thu",
    methods=["GET"]
)
@yeu_cau_dang_nhap
def thong_ke_doanh_thu():

    # -----------------------------------------------------
    # 1. LẤY VÀ KIỂM TRA NGÀY
    # -----------------------------------------------------

    tu_ngay = request.args.get("tu_ngay")
    den_ngay = request.args.get("den_ngay")

    try:
        if tu_ngay:
            tu_ngay = date.fromisoformat(tu_ngay)

        if den_ngay:
            den_ngay = date.fromisoformat(den_ngay)

    except ValueError:
        return that_bai(
            "Ngày không hợp lệ. Định dạng yêu cầu: YYYY-MM-DD",
            400
        )

    if tu_ngay and den_ngay and tu_ngay > den_ngay:
        return that_bai(
            "Ngày bắt đầu không được lớn hơn ngày kết thúc",
            400
        )

    # -----------------------------------------------------
    # 2. TẠO ĐIỀU KIỆN LỌC NGÀY
    # -----------------------------------------------------

    dieu_kien = ""
    params = []

    if tu_ngay:
        dieu_kien += " AND NgayTao >= ?"
        params.append(tu_ngay)

    if den_ngay:
        dieu_kien += " AND NgayTao < DATEADD(DAY, 1, ?)"
        params.append(den_ngay)

    try:
        with db_cursor() as cursor:

            # -------------------------------------------------
            # 3. TỔNG QUAN DOANH THU
            # Chỉ tính đơn hàng đã hoàn thành
            # -------------------------------------------------

            sql_tong_quan = f"""
                SELECT
                    COUNT(*) AS SoDonHoanThanh,
                    COALESCE(SUM(TongTien), 0) AS TongDoanhThu,
                    COALESCE(AVG(TongTien), 0) AS TrungBinhDonHang
                FROM DON_HANG
                WHERE TrangThai = 'hoan_thanh'
                {dieu_kien}
            """

            cursor.execute(
                sql_tong_quan,
                params
            )

            tong_quan = convert_to_json(cursor)

            # -------------------------------------------------
            # 4. THỐNG KÊ DOANH THU THEO NGÀY
            # ĐÃ SỬA LỖI GROUP BY
            # -------------------------------------------------

            sql_theo_ngay = f"""
                SELECT
                    CONVERT(
                        VARCHAR(10),
                        CONVERT(DATE, NgayTao),
                        23
                    ) AS Ngay,

                    COUNT(*) AS SoDon,

                    COALESCE(
                        SUM(TongTien),
                        0
                    ) AS DoanhThu

                FROM DON_HANG

                WHERE TrangThai = 'hoan_thanh'
                {dieu_kien}

                GROUP BY CONVERT(DATE, NgayTao)

                ORDER BY CONVERT(DATE, NgayTao)
            """

            cursor.execute(
                sql_theo_ngay,
                params
            )

            theo_ngay = convert_to_json(cursor)

            # -------------------------------------------------
            # 5. THỐNG KÊ DOANH THU THEO THÁNG
            # -------------------------------------------------

            sql_theo_thang = f"""
                SELECT
                    YEAR(NgayTao) AS Nam,
                    MONTH(NgayTao) AS Thang,
                    COUNT(*) AS SoDon,

                    COALESCE(
                        SUM(TongTien),
                        0
                    ) AS DoanhThu

                FROM DON_HANG

                WHERE TrangThai = 'hoan_thanh'
                {dieu_kien}

                GROUP BY
                    YEAR(NgayTao),
                    MONTH(NgayTao)

                ORDER BY
                    Nam,
                    Thang
            """

            cursor.execute(
                sql_theo_thang,
                params
            )

            theo_thang = convert_to_json(cursor)

            # -------------------------------------------------
            # 6. THỐNG KÊ ĐƠN HÀNG THEO TRẠNG THÁI
            # -------------------------------------------------

            sql_trang_thai = f"""
                SELECT
                    TrangThai,
                    COUNT(*) AS SoDon,

                    COALESCE(
                        SUM(TongTien),
                        0
                    ) AS TongTien

                FROM DON_HANG

                WHERE 1 = 1
                {dieu_kien}

                GROUP BY TrangThai

                ORDER BY TrangThai
            """

            cursor.execute(
                sql_trang_thai,
                params
            )

            theo_trang_thai = convert_to_json(cursor)

        # -----------------------------------------------------
        # 7. TRẢ KẾT QUẢ VỀ FRONTEND
        # -----------------------------------------------------

        return thanh_cong(
            "Lấy thống kê doanh thu thành công",

            data={
                "tong_quan": tong_quan,
                "theo_ngay": theo_ngay,
                "theo_thang": theo_thang,
                "theo_trang_thai": theo_trang_thai
            }
        )

    except Exception:
        current_app.logger.exception(
            "Lỗi khi thống kê doanh thu"
        )

        return that_bai(
            "Không thể lấy dữ liệu thống kê doanh thu",
            500
        )

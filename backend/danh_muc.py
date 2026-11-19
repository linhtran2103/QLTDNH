from flask import Blueprint, request

from database.db import convert_to_json, db_cursor
from backend.middleware.auth_middleware import yeu_cau_vai_tro
from backend.utils.response import thanh_cong, that_bai
from backend.utils.validators import (
    chuyen_bool, chuoi, doc_so_nguyen, ghi_nhat_ky, lay_json, ton_tai,
)


danh_muc_bp = Blueprint("danh_muc", __name__)


# =====================================================

@danh_muc_bp.route("/api/danh-muc", methods=["GET"])
def danh_sach_danh_muc():
    sql = "SELECT * FROM DANH_MUC WHERE 1 = 1"
    params = []

    tu_khoa = chuoi(request.args.get("q"))
    if tu_khoa:
        sql += " AND TenDanhMuc LIKE ?"
        params.append(f"%{tu_khoa}%")

    trang_thai = chuyen_bool(request.args.get("trang_thai"))
    if trang_thai is not None:
        sql += " AND TrangThai = ?"
        params.append(trang_thai)

    with db_cursor() as cursor:
        cursor.execute(sql + " ORDER BY ThuTuHienThi, MaDanhMuc", params)
        return thanh_cong(data=convert_to_json(cursor))


@danh_muc_bp.route("/api/danh-muc", methods=["POST"])
@yeu_cau_vai_tro("admin", "manager")
def them_danh_muc():
    data = lay_json()
    ten = chuoi(data.get("TenDanhMuc"))
    if not ten:
        return that_bai("Tên danh mục không được để trống")

    thu_tu = doc_so_nguyen(data.get("ThuTuHienThi"))

    with db_cursor(commit=True) as cursor:
        if ton_tai(cursor, "DANH_MUC", "TenDanhMuc", ten):
            return that_bai("Tên danh mục đã tồn tại")

        if thu_tu is None:  # không nhập -> xếp cuối danh sách
            cursor.execute(
                "SELECT COALESCE(MAX(ThuTuHienThi), 0) + 1 FROM DANH_MUC")
            thu_tu = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO DANH_MUC (TenDanhMuc, MoTa, ThuTuHienThi, TrangThai)
            VALUES (?, ?, ?, 1)
            """,
            (ten, chuoi(data.get("MoTa")), thu_tu),
        )
        ghi_nhat_ky(cursor, "Thêm", "DANH_MUC", None, f"Thêm danh mục {ten}")

    return thanh_cong("Thêm danh mục thành công", status=201)


@danh_muc_bp.route("/api/danh-muc/<int:ma_danh_muc>", methods=["PUT"])
@yeu_cau_vai_tro("admin", "manager")
def sua_danh_muc(ma_danh_muc):
    data = lay_json()
    ten = chuoi(data.get("TenDanhMuc"))
    if not ten:
        return that_bai("Tên danh mục không được để trống")

    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM DANH_MUC
            WHERE TenDanhMuc = ? AND MaDanhMuc <> ?
            """,
            (ten, ma_danh_muc),
        )
        if cursor.fetchone()[0] > 0:
            return that_bai("Tên danh mục đã tồn tại")

        cursor.execute(
            """
            UPDATE DANH_MUC
            SET TenDanhMuc = ?, MoTa = ?,
                ThuTuHienThi = COALESCE(?, ThuTuHienThi)
            WHERE MaDanhMuc = ?
            """,
            (ten, chuoi(data.get("MoTa")),
             doc_so_nguyen(data.get("ThuTuHienThi")), ma_danh_muc),
        )
        if cursor.rowcount == 0:
            return that_bai("Không tìm thấy danh mục", 404)

        ghi_nhat_ky(cursor, "Cập nhật", "DANH_MUC", ma_danh_muc)

    return thanh_cong("Cập nhật danh mục thành công")


@danh_muc_bp.route("/api/danh-muc/<int:ma_danh_muc>", methods=["DELETE"])
@yeu_cau_vai_tro("admin", "manager")
def xoa_danh_muc(ma_danh_muc):
    """Xóa mềm: chuyển sang ngừng hoạt động."""
    with db_cursor(commit=True) as cursor:
        if ton_tai(cursor, "MON_AN", "MaDanhMuc", ma_danh_muc,
                   "AND ConKinhDoanh = 1"):
            return that_bai("Danh mục đang có món ăn kinh doanh, không thể ngừng")

        cursor.execute(
            "UPDATE DANH_MUC SET TrangThai = 0 "
            "WHERE MaDanhMuc = ? AND TrangThai = 1",
            (ma_danh_muc,),
        )
        if cursor.rowcount == 0:
            return that_bai("Không tìm thấy danh mục đang hoạt động", 404)

        ghi_nhat_ky(cursor, "Ngừng hoạt động", "DANH_MUC", ma_danh_muc)

    return thanh_cong("Đã ngừng hoạt động danh mục")


# =====================================================


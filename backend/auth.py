import hmac

from flask import Blueprint, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import convert_one_to_json, db_cursor
from backend.middleware.auth_middleware import (
    chuan_hoa_vai_tro,
    tao_token,
    yeu_cau_dang_nhap,
)
from backend.utils.response import thanh_cong, that_bai
from backend.utils.validators import chuoi, ghi_nhat_ky, lay_json


auth_bp = Blueprint("auth", __name__)


def kiem_tra_mat_khau(mat_khau_luu, mat_khau_nhap):
    """Kiểm tra hash; hỗ trợ nâng cấp mật khẩu cũ lưu dạng thô."""
    if not mat_khau_luu:
        return False, False

    try:
        if check_password_hash(mat_khau_luu, mat_khau_nhap):
            return True, False
    except (ValueError, TypeError):
        pass

    if hmac.compare_digest(str(mat_khau_luu), str(mat_khau_nhap)):
        return True, True

    return False, False


@auth_bp.route("/api/dang-nhap", methods=["POST"])
def dang_nhap():
    data = lay_json()
    ten_dang_nhap = chuoi(data.get("TenDangNhap"))
    mat_khau = data.get("MatKhau")

    if not ten_dang_nhap or not mat_khau:
        return that_bai("Vui lòng nhập tên đăng nhập và mật khẩu")

    loi_chung = "Tên đăng nhập hoặc mật khẩu không đúng"

    def ghi_lich_su(cursor, ma, thanh_cong_, ghi_chu):
        cursor.execute(
            """
            INSERT INTO LOGIN_HISTORY
                (MaNguoiDung, ThoiGianDangNhap, DiaChiIP,
                 TrangThaiDangNhap, GhiChu)
            VALUES (?, GETDATE(), ?, ?, ?)
            """,
            (ma, request.remote_addr, 1 if thanh_cong_ else 0, ghi_chu),
        )

    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            SELECT MaNguoiDung, TenDangNhap, MatKhauHash, HoTen, VaiTro,
                   TrangThai
            FROM NGUOI_DUNG WHERE TenDangNhap = ?
            """,
            (ten_dang_nhap,),
        )
        user = convert_one_to_json(cursor)

        if not user:
            return that_bai(loi_chung, 401)

        hop_le, can_nang_cap = kiem_tra_mat_khau(user["MatKhauHash"], mat_khau)
        if not hop_le:
            ghi_lich_su(cursor, user["MaNguoiDung"], False, "Sai mật khẩu")
            return that_bai(loi_chung, 401)

        if not user["TrangThai"]:
            ghi_lich_su(cursor, user["MaNguoiDung"], False, "Tài khoản bị khóa")
            return that_bai("Tài khoản đã bị khóa", 403)

        vai_tro = chuan_hoa_vai_tro(user["VaiTro"])
        if not vai_tro:
            ghi_lich_su(cursor, user["MaNguoiDung"], False, "Vai trò không được hỗ trợ")
            return that_bai("Tài khoản không có vai trò được phép đăng nhập", 403)

        if can_nang_cap:
            cursor.execute(
                "UPDATE NGUOI_DUNG SET MatKhauHash = ? WHERE MaNguoiDung = ?",
                (generate_password_hash(mat_khau), user["MaNguoiDung"]),
            )

        ghi_lich_su(cursor, user["MaNguoiDung"], True, "Đăng nhập thành công")

        g.ma_nguoi_dung = user["MaNguoiDung"]
        ghi_nhat_ky(cursor, "Đăng nhập", "NGUOI_DUNG", user["MaNguoiDung"],
                    "Người dùng đăng nhập hệ thống")

    return thanh_cong(
        "Đăng nhập thành công",
        data={**{k: user[k] for k in
                 ("MaNguoiDung", "TenDangNhap", "HoTen")},
              "VaiTro": vai_tro},
        token=tao_token(user["MaNguoiDung"]),
    )


@auth_bp.route("/api/dang-xuat", methods=["POST"])
@yeu_cau_dang_nhap
def dang_xuat():
    with db_cursor(commit=True) as cursor:
        ghi_nhat_ky(cursor, "Đăng xuất", "NGUOI_DUNG", g.ma_nguoi_dung,
                    "Người dùng đăng xuất")
    return thanh_cong("Đăng xuất thành công")


# =====================================================

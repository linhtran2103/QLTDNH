from flask import Blueprint, g
from werkzeug.security import generate_password_hash

from database.db import convert_to_json, db_cursor
from backend.config import VAI_TRO_HOP_LE, VAI_TRO_MAC_DINH
from backend.middleware.auth_middleware import chi_admin, chuan_hoa_vai_tro
from backend.utils.response import thanh_cong, that_bai
from backend.utils.validators import chuoi, ghi_nhat_ky, lay_json, ton_tai


nguoi_dung_bp = Blueprint("nguoi_dung", __name__)


# =====================================================

@nguoi_dung_bp.route("/api/nguoi-dung", methods=["GET"])
@chi_admin
def danh_sach_nguoi_dung():
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT MaNguoiDung, TenDangNhap, HoTen, VaiTro, TrangThai, NgayTao
            FROM NGUOI_DUNG
            WHERE LOWER(LTRIM(RTRIM(VaiTro))) IN
                ('admin', 'manager', 'nhanvien', 'nhan_vien', N'nhân viên',
                 'employee', 'staff', 'user')
            ORDER BY MaNguoiDung DESC
            """
        )
        users = convert_to_json(cursor)
        for user in users:
            user["VaiTro"] = chuan_hoa_vai_tro(user["VaiTro"]) or user["VaiTro"]
        return thanh_cong(data=users)


@nguoi_dung_bp.route("/api/nguoi-dung", methods=["POST"])
@chi_admin
def them_nguoi_dung():
    data = lay_json()
    ten_dang_nhap = chuoi(data.get("TenDangNhap"))
    mat_khau = data.get("MatKhau")
    ho_ten = chuoi(data.get("HoTen"))
    raw_role = chuoi(data.get("VaiTro"))
    vai_tro = chuan_hoa_vai_tro(raw_role) if raw_role else VAI_TRO_MAC_DINH

    if not ten_dang_nhap or not mat_khau or not ho_ten:
        return that_bai("Vui lòng nhập đầy đủ thông tin người dùng")
    if len(ten_dang_nhap) > 50:
        return that_bai("Tên đăng nhập không được vượt quá 50 ký tự")
    if len(str(mat_khau)) < 6:
        return that_bai("Mật khẩu phải có ít nhất 6 ký tự")
    if not vai_tro or vai_tro not in VAI_TRO_HOP_LE:
        return that_bai("Vai trò chỉ được là admin, manager hoặc NhanVien")

    with db_cursor(commit=True) as cursor:
        if ton_tai(cursor, "NGUOI_DUNG", "TenDangNhap", ten_dang_nhap):
            return that_bai("Tên đăng nhập đã tồn tại")

        cursor.execute(
            """
            INSERT INTO NGUOI_DUNG
                (TenDangNhap, MatKhauHash, HoTen, VaiTro, TrangThai, NgayTao)
            VALUES (?, ?, ?, ?, 1, GETDATE())
            """,
            (ten_dang_nhap, generate_password_hash(str(mat_khau)),
             ho_ten, vai_tro),
        )
        ghi_nhat_ky(cursor, "Thêm", "NGUOI_DUNG", None,
                    f"Thêm tài khoản {ten_dang_nhap}")

    return thanh_cong("Thêm người dùng thành công", status=201)


@nguoi_dung_bp.route("/api/nguoi-dung/<int:ma_nguoi_dung>", methods=["PUT"])
@chi_admin
def sua_nguoi_dung(ma_nguoi_dung):
    if ma_nguoi_dung == g.ma_nguoi_dung:
        return that_bai("Không thể tự chỉnh sửa tài khoản của mình tại đây")

    data = lay_json()
    ho_ten = chuoi(data.get("HoTen"))
    vai_tro = chuan_hoa_vai_tro(data.get("VaiTro"))
    mat_khau = data.get("MatKhau")

    if not ho_ten or not vai_tro:
        return that_bai("Vui lòng nhập họ tên và vai trò hợp lệ")
    if vai_tro not in VAI_TRO_HOP_LE:
        return that_bai("Vai trò chỉ được là admin, manager hoặc NhanVien")
    if mat_khau and len(str(mat_khau)) < 6:
        return that_bai("Mật khẩu phải có ít nhất 6 ký tự")

    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE NGUOI_DUNG
            SET HoTen = ?, VaiTro = ?, MatKhauHash = COALESCE(?, MatKhauHash)
            WHERE MaNguoiDung = ?
            """,
            (ho_ten, vai_tro,
             generate_password_hash(str(mat_khau)) if mat_khau else None,
             ma_nguoi_dung),
        )
        if cursor.rowcount == 0:
            return that_bai("Không tìm thấy người dùng", 404)

        ghi_nhat_ky(cursor, "Cập nhật", "NGUOI_DUNG", ma_nguoi_dung)

    return thanh_cong("Cập nhật người dùng thành công")


def _doi_trang_thai_nguoi_dung(ma_nguoi_dung, trang_thai):
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            "UPDATE NGUOI_DUNG SET TrangThai = ? "
            "WHERE MaNguoiDung = ? AND TrangThai = ?",
            (trang_thai, ma_nguoi_dung, 0 if trang_thai else 1),
        )
        if cursor.rowcount == 0:
            return False

        ghi_nhat_ky(cursor, "Mở khóa" if trang_thai else "Khóa",
                    "NGUOI_DUNG", ma_nguoi_dung)
    return True


@nguoi_dung_bp.route("/api/nguoi-dung/<int:ma_nguoi_dung>", methods=["DELETE"])
@chi_admin
def xoa_nguoi_dung(ma_nguoi_dung):
    """Khóa tài khoản (xóa mềm)."""
    if ma_nguoi_dung == g.ma_nguoi_dung:
        return that_bai("Không thể tự khóa tài khoản của mình")

    if not _doi_trang_thai_nguoi_dung(ma_nguoi_dung, 0):
        return that_bai("Không tìm thấy người dùng đang hoạt động", 404)
    return thanh_cong("Đã khóa tài khoản người dùng")


@nguoi_dung_bp.route("/api/nguoi-dung/<int:ma_nguoi_dung>/mo-khoa", methods=["PUT"])
@chi_admin
def mo_khoa_nguoi_dung(ma_nguoi_dung):
    if not _doi_trang_thai_nguoi_dung(ma_nguoi_dung, 1):
        return that_bai("Không tìm thấy tài khoản đang bị khóa", 404)
    return thanh_cong("Mở khóa tài khoản thành công")


# =====================================================


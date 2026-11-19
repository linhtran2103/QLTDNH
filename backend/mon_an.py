import uuid
from decimal import Decimal

from flask import Blueprint, g, request

from database.db import convert_one_to_json, convert_to_json, db_cursor
from backend.config import THU_MUC_ANH
from backend.middleware.auth_middleware import yeu_cau_dang_nhap, yeu_cau_vai_tro
from backend.utils.response import thanh_cong, that_bai
from backend.utils.validators import (
    chuyen_bool, chuoi, doc_gia, doc_ngay, doc_so_nguyen, ghi_nhat_ky,
    lay_json, ton_tai,
)


mon_an_bp = Blueprint("mon_an", __name__)


# =====================================================

SQL_MON_AN = """
    SELECT M.*, D.TenDanhMuc
    FROM MON_AN M
    LEFT JOIN DANH_MUC D ON M.MaDanhMuc = D.MaDanhMuc
"""


@mon_an_bp.route("/api/mon-an", methods=["GET"])
def danh_sach_mon_an():
    sql = SQL_MON_AN + " WHERE 1 = 1"
    params = []

    tu_khoa = chuoi(request.args.get("q"))
    if tu_khoa:
        sql += " AND (M.TenMonAn LIKE ? OR M.MaMon LIKE ?)"
        params += [f"%{tu_khoa}%"] * 2

    ma_danh_muc = doc_so_nguyen(request.args.get("ma_danh_muc"))
    if ma_danh_muc is not None:
        sql += " AND M.MaDanhMuc = ?"
        params.append(ma_danh_muc)

    con_kinh_doanh = chuyen_bool(request.args.get("con_kinh_doanh"))
    if con_kinh_doanh is not None:
        sql += " AND M.ConKinhDoanh = ?"
        params.append(con_kinh_doanh)

    with db_cursor() as cursor:
        cursor.execute(sql + " ORDER BY M.MaMonAn DESC", params)
        return thanh_cong(data=convert_to_json(cursor))


@mon_an_bp.route("/api/mon-an/<int:ma_mon_an>", methods=["GET"])
def chi_tiet_mon_an(ma_mon_an):
    with db_cursor() as cursor:
        cursor.execute(SQL_MON_AN + " WHERE M.MaMonAn = ?", (ma_mon_an,))
        mon_an = convert_one_to_json(cursor)

    if not mon_an:
        return that_bai("Không tìm thấy món ăn", 404)
    return thanh_cong(data=mon_an)


@mon_an_bp.route("/api/mon-an", methods=["POST"])
@yeu_cau_vai_tro("admin", "manager")
def them_mon_an():
    data = lay_json()
    ma_mon = chuoi(data.get("MaMon"))
    ten_mon = chuoi(data.get("TenMonAn"))
    ma_danh_muc = doc_so_nguyen(data.get("MaDanhMuc"))
    gia = doc_gia(data.get("Gia"))

    if not ma_mon or not ten_mon or ma_danh_muc is None:
        return that_bai("Vui lòng nhập đầy đủ thông tin món ăn")
    if gia is None:
        return that_bai("Giá món ăn không hợp lệ")

    with db_cursor(commit=True) as cursor:
        if ton_tai(cursor, "MON_AN", "MaMon", ma_mon):
            return that_bai("Mã món ăn đã tồn tại")

        if not ton_tai(cursor, "DANH_MUC", "MaDanhMuc", ma_danh_muc,
                       "AND TrangThai = 1"):
            return that_bai("Danh mục không tồn tại hoặc đã bị khóa")

        cursor.execute(
            """
            INSERT INTO MON_AN
                (MaMon, TenMonAn, MaDanhMuc, Gia, MoTa, HinhAnh,
                 ConKinhDoanh, NgayTao)
            VALUES (?, ?, ?, ?, ?, ?, 1, GETDATE())
            """,
            (ma_mon, ten_mon, ma_danh_muc, gia, chuoi(data.get("MoTa")),
             chuoi(data.get("HinhAnh"))),
        )
        ghi_nhat_ky(cursor, "Thêm", "MON_AN", None,
                    f"Thêm món {ma_mon} - {ten_mon}")

    return thanh_cong("Thêm món ăn thành công", status=201)


@mon_an_bp.route("/api/mon-an/<int:ma_mon_an>", methods=["PUT"])
@yeu_cau_vai_tro("admin", "manager")
def sua_mon_an(ma_mon_an):
    data = lay_json()
    ten_mon = chuoi(data.get("TenMonAn"))
    ma_danh_muc = doc_so_nguyen(data.get("MaDanhMuc"))
    gia_moi = doc_gia(data.get("Gia"))

    if not ten_mon or ma_danh_muc is None:
        return that_bai("Vui lòng nhập đầy đủ thông tin món ăn")
    if gia_moi is None:
        return that_bai("Giá món ăn không hợp lệ")

    # ConKinhDoanh tùy chọn: không gửi thì giữ nguyên
    con_kinh_doanh = chuyen_bool(data.get("ConKinhDoanh"))

    with db_cursor(commit=True) as cursor:
        cursor.execute("SELECT Gia FROM MON_AN WHERE MaMonAn = ?",
                       (ma_mon_an,))
        hang = cursor.fetchone()
        if hang is None:
            return that_bai("Không tìm thấy món ăn", 404)
        gia_cu = hang[0]

        if not ton_tai(cursor, "DANH_MUC", "MaDanhMuc", ma_danh_muc,
                       "AND TrangThai = 1"):
            return that_bai("Danh mục không tồn tại hoặc đã bị khóa")

        cursor.execute(
            """
            UPDATE MON_AN
            SET TenMonAn = ?, MaDanhMuc = ?, Gia = ?, MoTa = ?, HinhAnh = ?,
                ConKinhDoanh = COALESCE(?, ConKinhDoanh),
                NgayCapNhat = GETDATE()
            WHERE MaMonAn = ?
            """,
            (ten_mon, ma_danh_muc, gia_moi, chuoi(data.get("MoTa")),
             chuoi(data.get("HinhAnh")), con_kinh_doanh, ma_mon_an),
        )

        # Giá đổi -> lưu lịch sử giá
        if gia_cu is None or Decimal(str(gia_cu)) != gia_moi:
            cursor.execute(
                """
                INSERT INTO LICH_SU_GIA
                    (MaMonAn, GiaCu, GiaMoi, MaNguoiDung,
                     ThoiGianThayDoi, GhiChu)
                VALUES (?, ?, ?, ?, GETDATE(), ?)
                """,
                (ma_mon_an, gia_cu, gia_moi, g.ma_nguoi_dung,
                 "Cập nhật giá món ăn"),
            )

        ghi_nhat_ky(cursor, "Cập nhật", "MON_AN", ma_mon_an,
                    "Cập nhật thông tin món ăn")

    return thanh_cong("Cập nhật món ăn thành công")


@mon_an_bp.route("/api/mon-an/<int:ma_mon_an>", methods=["DELETE"])
@yeu_cau_vai_tro("admin", "manager")
def xoa_mon_an(ma_mon_an):
    """Xóa mềm: chuyển sang ngừng kinh doanh."""
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE MON_AN SET ConKinhDoanh = 0, NgayCapNhat = GETDATE()
            WHERE MaMonAn = ? AND ConKinhDoanh = 1
            """,
            (ma_mon_an,),
        )
        if cursor.rowcount == 0:
            return that_bai("Không tìm thấy món ăn đang kinh doanh", 404)

        ghi_nhat_ky(cursor, "Ngừng kinh doanh", "MON_AN", ma_mon_an)

    return thanh_cong("Đã ngừng kinh doanh món ăn")


@mon_an_bp.route("/api/upload-anh", methods=["POST"])
@yeu_cau_vai_tro("admin", "manager")
def upload_anh():
    file = request.files.get("image")
    if not file or not file.filename:
        return that_bai("Chưa chọn file ảnh")

    dau_file = file.stream.read(12)
    file.stream.seek(0)

    # Xác định định dạng theo nội dung file, không tin đuôi tên file
    if dau_file.startswith(b"\xff\xd8\xff"):
        duoi = "jpg"
    elif dau_file.startswith(b"\x89PNG\r\n\x1a\n"):
        duoi = "png"
    elif dau_file[:4] == b"RIFF" and dau_file[8:12] == b"WEBP":
        duoi = "webp"
    else:
        return that_bai("Vui lòng chọn ảnh JPG, PNG hoặc WEBP")

    THU_MUC_ANH.mkdir(parents=True, exist_ok=True)
    ten_file = f"{uuid.uuid4().hex}.{duoi}"
    file.save(THU_MUC_ANH / ten_file)

    return thanh_cong("Tải ảnh lên thành công",
                      data={"url": f"/static/uploads/{ten_file}"}, status=201)


# =====================================================
# 10. ĐẶC ĐIỂM VÀ ĐẶC ĐIỂM CỦA MÓN ĂN
# =====================================================

@mon_an_bp.route("/api/dac-diem", methods=["GET"])
def danh_sach_dac_diem():
    with db_cursor() as cursor:
        cursor.execute("SELECT * FROM DAC_DIEM ORDER BY TenDacDiem")
        return thanh_cong(data=convert_to_json(cursor))


@mon_an_bp.route("/api/dac-diem", methods=["POST"])
@yeu_cau_vai_tro("admin", "manager")
def them_dac_diem():
    data = lay_json()
    ten = chuoi(data.get("TenDacDiem"))
    if not ten:
        return that_bai("Tên đặc điểm không được để trống")

    with db_cursor(commit=True) as cursor:
        if ton_tai(cursor, "DAC_DIEM", "TenDacDiem", ten):
            return that_bai("Đặc điểm đã tồn tại")

        cursor.execute(
            "INSERT INTO DAC_DIEM (TenDacDiem, MoTa) VALUES (?, ?)",
            (ten, chuoi(data.get("MoTa"))),
        )
        ghi_nhat_ky(cursor, "Thêm", "DAC_DIEM", None, f"Thêm đặc điểm {ten}")

    return thanh_cong("Thêm đặc điểm thành công", status=201)


@mon_an_bp.route("/api/dac-diem/<int:ma_dac_diem>", methods=["PUT"])
@yeu_cau_vai_tro("admin", "manager")
def sua_dac_diem(ma_dac_diem):
    data = lay_json()
    ten = chuoi(data.get("TenDacDiem"))
    if not ten:
        return that_bai("Tên đặc điểm không được để trống")

    with db_cursor(commit=True) as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM DAC_DIEM WHERE TenDacDiem = ? AND MaDacDiem <> ?",
            (ten, ma_dac_diem),
        )
        if cursor.fetchone()[0] > 0:
            return that_bai("Đặc điểm đã tồn tại")

        cursor.execute(
            "UPDATE DAC_DIEM SET TenDacDiem = ?, MoTa = ? WHERE MaDacDiem = ?",
            (ten, chuoi(data.get("MoTa")), ma_dac_diem),
        )
        if cursor.rowcount == 0:
            return that_bai("Không tìm thấy đặc điểm", 404)

        ghi_nhat_ky(cursor, "Cập nhật", "DAC_DIEM", ma_dac_diem)

    return thanh_cong("Cập nhật đặc điểm thành công")


@mon_an_bp.route("/api/dac-diem/<int:ma_dac_diem>", methods=["DELETE"])
@yeu_cau_vai_tro("admin", "manager")
def xoa_dac_diem(ma_dac_diem):
    with db_cursor(commit=True) as cursor:
        if ton_tai(cursor, "MON_AN_DAC_DIEM", "MaDacDiem", ma_dac_diem):
            return that_bai("Đặc điểm đang được gán cho món ăn, không thể xóa")

        cursor.execute("DELETE FROM DAC_DIEM WHERE MaDacDiem = ?",
                       (ma_dac_diem,))
        if cursor.rowcount == 0:
            return that_bai("Không tìm thấy đặc điểm", 404)

        ghi_nhat_ky(cursor, "Xóa", "DAC_DIEM", ma_dac_diem)

    return thanh_cong("Xóa đặc điểm thành công")


@mon_an_bp.route("/api/mon-an/<int:ma_mon_an>/dac-diem", methods=["GET"])
def danh_sach_dac_diem_mon_an(ma_mon_an):
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT D.* FROM MON_AN_DAC_DIEM MD
            INNER JOIN DAC_DIEM D ON MD.MaDacDiem = D.MaDacDiem
            WHERE MD.MaMonAn = ? ORDER BY D.TenDacDiem
            """,
            (ma_mon_an,),
        )
        return thanh_cong(data=convert_to_json(cursor))


@mon_an_bp.route("/api/mon-an/<int:ma_mon_an>/dac-diem", methods=["POST"])
@yeu_cau_vai_tro("admin", "manager")
def them_dac_diem_cho_mon_an(ma_mon_an):
    ma_dac_diem = doc_so_nguyen(lay_json().get("MaDacDiem"))
    if ma_dac_diem is None:
        return that_bai("Thiếu mã đặc điểm")

    with db_cursor(commit=True) as cursor:
        if not ton_tai(cursor, "MON_AN", "MaMonAn", ma_mon_an):
            return that_bai("Không tìm thấy món ăn", 404)
        if not ton_tai(cursor, "DAC_DIEM", "MaDacDiem", ma_dac_diem):
            return that_bai("Không tìm thấy đặc điểm", 404)

        cursor.execute(
            "SELECT COUNT(*) FROM MON_AN_DAC_DIEM "
            "WHERE MaMonAn = ? AND MaDacDiem = ?",
            (ma_mon_an, ma_dac_diem),
        )
        if cursor.fetchone()[0] > 0:
            return that_bai("Món ăn đã có đặc điểm này")

        cursor.execute(
            "INSERT INTO MON_AN_DAC_DIEM (MaMonAn, MaDacDiem) VALUES (?, ?)",
            (ma_mon_an, ma_dac_diem),
        )
        ghi_nhat_ky(cursor, "Thêm đặc điểm cho món", "MON_AN_DAC_DIEM",
                    ma_mon_an, f"Đặc điểm {ma_dac_diem}")

    return thanh_cong("Thêm đặc điểm cho món ăn thành công", status=201)


@mon_an_bp.route("/api/mon-an/<int:ma_mon_an>/dac-diem/<int:ma_dac_diem>",
           methods=["DELETE"])
@yeu_cau_vai_tro("admin", "manager")
def xoa_dac_diem_mon_an(ma_mon_an, ma_dac_diem):
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            "DELETE FROM MON_AN_DAC_DIEM WHERE MaMonAn = ? AND MaDacDiem = ?",
            (ma_mon_an, ma_dac_diem),
        )
        if cursor.rowcount == 0:
            return that_bai("Không tìm thấy đặc điểm của món ăn", 404)

        ghi_nhat_ky(cursor, "Gỡ đặc điểm khỏi món", "MON_AN_DAC_DIEM",
                    ma_mon_an, f"Đặc điểm {ma_dac_diem}")

    return thanh_cong("Đã gỡ đặc điểm khỏi món ăn")


# =====================================================
# 11. THỰC ĐƠN VÀ CHI TIẾT THỰC ĐƠN
# =====================================================

def _doc_thuc_don(data):
    """Trả về (tham_số, lỗi)."""
    ten = chuoi(data.get("TenThucDon"))
    if not ten:
        return None, "Tên thực đơn không được để trống"

    try:
        bat_dau = doc_ngay(data.get("NgayBatDau"))
        ket_thuc = doc_ngay(data.get("NgayKetThuc"))
    except ValueError:
        return None, "Ngày không hợp lệ (định dạng YYYY-MM-DD)"

    if bat_dau and ket_thuc and ket_thuc < bat_dau:
        return None, "Ngày kết thúc phải sau ngày bắt đầu"

    return (ten, chuoi(data.get("LoaiThucDon")), chuoi(data.get("MoTa")),
            bat_dau, ket_thuc), None


@mon_an_bp.route("/api/thuc-don", methods=["GET"])
def danh_sach_thuc_don():
    sql = "SELECT * FROM THUC_DON WHERE 1 = 1"
    params = []

    trang_thai = chuyen_bool(request.args.get("trang_thai"))
    if trang_thai is not None:
        sql += " AND TrangThai = ?"
        params.append(trang_thai)

    with db_cursor() as cursor:
        cursor.execute(sql + " ORDER BY MaThucDon DESC", params)
        return thanh_cong(data=convert_to_json(cursor))


@mon_an_bp.route("/api/thuc-don", methods=["POST"])
@yeu_cau_vai_tro("admin", "manager")
def them_thuc_don():
    tham_so, loi = _doc_thuc_don(lay_json())
    if loi:
        return that_bai(loi)

    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO THUC_DON
                (TenThucDon, LoaiThucDon, MoTa, NgayBatDau, NgayKetThuc,
                 TrangThai)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            tham_so,
        )
        ghi_nhat_ky(cursor, "Thêm", "THUC_DON", None,
                    f"Thêm thực đơn {tham_so[0]}")

    return thanh_cong("Thêm thực đơn thành công", status=201)


@mon_an_bp.route("/api/thuc-don/<int:ma_thuc_don>", methods=["PUT"])
@yeu_cau_vai_tro("admin", "manager")
def sua_thuc_don(ma_thuc_don):
    data = lay_json()
    tham_so, loi = _doc_thuc_don(data)
    if loi:
        return that_bai(loi)

    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            UPDATE THUC_DON
            SET TenThucDon = ?, LoaiThucDon = ?, MoTa = ?,
                NgayBatDau = ?, NgayKetThuc = ?,
                TrangThai = COALESCE(?, TrangThai)
            WHERE MaThucDon = ?
            """,
            (*tham_so, chuyen_bool(data.get("TrangThai")), ma_thuc_don),
        )
        if cursor.rowcount == 0:
            return that_bai("Không tìm thấy thực đơn", 404)

        ghi_nhat_ky(cursor, "Cập nhật", "THUC_DON", ma_thuc_don)

    return thanh_cong("Cập nhật thực đơn thành công")


@mon_an_bp.route("/api/thuc-don/<int:ma_thuc_don>", methods=["DELETE"])
@yeu_cau_vai_tro("admin", "manager")
def xoa_thuc_don(ma_thuc_don):
    """Xóa cứng thực đơn cùng chi tiết của nó (trong 1 transaction)."""
    with db_cursor(commit=True) as cursor:
        if not ton_tai(cursor, "THUC_DON", "MaThucDon", ma_thuc_don):
            return that_bai("Không tìm thấy thực đơn", 404)

        cursor.execute("DELETE FROM CHI_TIET_THUC_DON WHERE MaThucDon = ?",
                       (ma_thuc_don,))
        cursor.execute("DELETE FROM THUC_DON WHERE MaThucDon = ?",
                       (ma_thuc_don,))
        ghi_nhat_ky(cursor, "Xóa", "THUC_DON", ma_thuc_don)

    return thanh_cong("Xóa thực đơn thành công")


@mon_an_bp.route("/api/thuc-don/<int:ma_thuc_don>/mon-an", methods=["GET"])
def danh_sach_mon_trong_thuc_don(ma_thuc_don):
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT M.MaMonAn, M.MaMon, M.TenMonAn, M.HinhAnh, M.ConKinhDoanh,
                   M.Gia, CT.GiaApDung, CT.ThuTu,
                   COALESCE(CT.GiaApDung, M.Gia) AS GiaBan
            FROM CHI_TIET_THUC_DON CT
            INNER JOIN MON_AN M ON CT.MaMonAn = M.MaMonAn
            WHERE CT.MaThucDon = ?
            ORDER BY CT.ThuTu, M.TenMonAn
            """,
            (ma_thuc_don,),
        )
        return thanh_cong(data=convert_to_json(cursor))


@mon_an_bp.route("/api/thuc-don/<int:ma_thuc_don>/mon-an", methods=["POST"])
@yeu_cau_vai_tro("admin", "manager")
def them_mon_vao_thuc_don(ma_thuc_don):
    data = lay_json()
    ma_mon_an = doc_so_nguyen(data.get("MaMonAn"))
    if ma_mon_an is None:
        return that_bai("Thiếu mã món ăn")

    gia_ap_dung = None
    if data.get("GiaApDung") not in (None, ""):
        gia_ap_dung = doc_gia(data.get("GiaApDung"))
        if gia_ap_dung is None:
            return that_bai("Giá áp dụng không hợp lệ")

    with db_cursor(commit=True) as cursor:
        if not ton_tai(cursor, "THUC_DON", "MaThucDon", ma_thuc_don):
            return that_bai("Không tìm thấy thực đơn", 404)

        cursor.execute("SELECT Gia FROM MON_AN WHERE MaMonAn = ?", (ma_mon_an,))
        hang = cursor.fetchone()
        if hang is None:
            return that_bai("Không tìm thấy món ăn", 404)

        cursor.execute(
            "SELECT COUNT(*) FROM CHI_TIET_THUC_DON "
            "WHERE MaThucDon = ? AND MaMonAn = ?",
            (ma_thuc_don, ma_mon_an),
        )
        if cursor.fetchone()[0] > 0:
            return that_bai("Món ăn đã có trong thực đơn")

        thu_tu = doc_so_nguyen(data.get("ThuTu"))
        if thu_tu is None:  # không nhập -> xếp cuối thực đơn
            cursor.execute(
                "SELECT COALESCE(MAX(ThuTu), 0) + 1 FROM CHI_TIET_THUC_DON "
                "WHERE MaThucDon = ?",
                (ma_thuc_don,),
            )
            thu_tu = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO CHI_TIET_THUC_DON (MaThucDon, MaMonAn, GiaApDung, ThuTu)
            VALUES (?, ?, ?, ?)
            """,
            (ma_thuc_don, ma_mon_an,
             gia_ap_dung if gia_ap_dung is not None else hang[0], thu_tu),
        )
        ghi_nhat_ky(cursor, "Thêm món vào thực đơn", "CHI_TIET_THUC_DON",
                    ma_thuc_don, f"Món {ma_mon_an}")

    return thanh_cong("Thêm món vào thực đơn thành công", status=201)


@mon_an_bp.route("/api/thuc-don/<int:ma_thuc_don>/mon-an/<int:ma_mon_an>",
           methods=["DELETE"])
@yeu_cau_vai_tro("admin", "manager")
def xoa_mon_khoi_thuc_don(ma_thuc_don, ma_mon_an):
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            "DELETE FROM CHI_TIET_THUC_DON WHERE MaThucDon = ? AND MaMonAn = ?",
            (ma_thuc_don, ma_mon_an),
        )
        if cursor.rowcount == 0:
            return that_bai("Không tìm thấy món trong thực đơn", 404)

        ghi_nhat_ky(cursor, "Gỡ món khỏi thực đơn", "CHI_TIET_THUC_DON",
                    ma_thuc_don, f"Món {ma_mon_an}")

    return thanh_cong("Đã gỡ món khỏi thực đơn")


# =====================================================




from flask import Flask, jsonify, request, g, render_template
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from functools import wraps

import os
from dotenv import load_dotenv

from database import (
    get_connection,
    dong_ket_noi,
    convert_to_json,
    convert_one_to_json
)


# =====================================================
# 1. KHỞI TẠO FLASK VÀ CẤU HÌNH
# =====================================================

load_dotenv(override=True)

# Xác định thư mục gốc của dự án QLTDNH
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

# Khởi tạo Flask và kết nối thư mục giao diện
app = Flask(
    __name__,
    template_folder=os.path.join(
        PROJECT_ROOT, "frontend", "templates"
    ),
    static_folder=os.path.join(
        PROJECT_ROOT, "frontend", "static"
    )
)

CORS(
    app,
    allow_headers=["Content-Type", "Authorization"]
)
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "Chưa cấu hình SECRET_KEY trong file .env"
    )

serializer = URLSafeTimedSerializer(SECRET_KEY)


# =====================================================
# 2. HÀM LẤY DỮ LIỆU JSON
# =====================================================

def lay_du_lieu_json():
    return request.get_json(silent=True) or {}


# =====================================================
# 3. GHI NHẬT KÝ HOẠT ĐỘNG
# =====================================================

def ghi_nhat_ky(ma_nguoi_dung, hanh_dong, chi_tiet=None):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO dbo.NhatKyHoatDong
                (MaNguoiDung, HanhDong, ChiTiet, NgayTao)
            VALUES (?, ?, ?, GETDATE())
        """, (
            ma_nguoi_dung,
            hanh_dong,
            chi_tiet
        ))

        connection.commit()

    except Exception as error:
        print("Lỗi ghi nhật ký:", error)

    finally:
        dong_ket_noi(connection, cursor)


# =====================================================
# 4. TẠO VÀ KIỂM TRA TOKEN
# =====================================================

def tao_token(ma_nguoi_dung):
    return serializer.dumps({
        "MaNguoiDung": ma_nguoi_dung
    })


def lay_ma_nguoi_dung_tu_token():
    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ", 1)[1].strip()

    try:
        data = serializer.loads(token, max_age=28800)
        return data.get("MaNguoiDung")

    except (BadSignature, SignatureExpired):
        return None


# =====================================================
# 5. XÁC THỰC NGƯỜI DÙNG
# =====================================================

def xac_thuc_nguoi_dung():
    ma_nguoi_dung = lay_ma_nguoi_dung_tu_token()

    if not ma_nguoi_dung:
        return None

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                MaNguoiDung,
                TenDangNhap,
                HoTen,
                Email,
                VaiTro,
                TrangThai
            FROM dbo.NguoiDung
            WHERE MaNguoiDung = ?
        """, (ma_nguoi_dung,))

        user = convert_one_to_json(cursor)

        if not user or user["TrangThai"] != 1:
            return None

        return user

    finally:
        dong_ket_noi(connection, cursor)


# =====================================================
# 6. PHÂN QUYỀN
# =====================================================

def yeu_cau_dang_nhap(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            user = xac_thuc_nguoi_dung()

            if not user:
                return jsonify({
                    "status": "error",
                    "message": "Token không hợp lệ hoặc đã hết hạn"
                }), 401

            g.nguoi_dung = user
            g.ma_nguoi_dung = user["MaNguoiDung"]

            return func(*args, **kwargs)

        except Exception as error:
            print("Lỗi xác thực:", error)

            return jsonify({
                "status": "error",
                "message": "Không thể xác thực người dùng"
            }), 500

    return wrapper


def yeu_cau_quyen(*cac_quyen):
    def decorator(func):
        @wraps(func)
        @yeu_cau_dang_nhap
        def wrapper(*args, **kwargs):
            if g.nguoi_dung["VaiTro"] not in cac_quyen:
                return jsonify({
                    "status": "error",
                    "message": "Bạn không có quyền thực hiện chức năng này"
                }), 403

            return func(*args, **kwargs)

        return wrapper

    return decorator


# =====================================================
# 7. TỰ ĐỘNG GHI NHẬT KÝ SAU CÁC THAO TÁC
# =====================================================

@app.after_request
def ghi_nhat_ky_sau_thao_tac(response):
    try:
        if not 200 <= response.status_code < 300:
            return response

        endpoint = request.endpoint

        danh_sach_hanh_dong = {
            "them_mon_an": "Thêm món ăn",
            "sua_mon_an": "Cập nhật món ăn",
            "xoa_mon_an": "Xóa món ăn",

            "them_danh_muc": "Thêm danh mục",
            "sua_danh_muc": "Cập nhật danh mục",
            "xoa_danh_muc": "Xóa danh mục",

            "them_nguoi_dung": "Thêm người dùng",
            "sua_nguoi_dung": "Cập nhật người dùng",
            "xoa_nguoi_dung": "Khóa người dùng",
            "mo_khoa_nguoi_dung": "Mở khóa người dùng"
        }

        if endpoint in danh_sach_hanh_dong:
            ma_nguoi_dung = getattr(
                g,
                "ma_nguoi_dung",
                None
            )

            ghi_nhat_ky(
                ma_nguoi_dung,
                danh_sach_hanh_dong[endpoint],
                f"Đường dẫn: {request.path}; "
                f"Phương thức: {request.method}"
            )

        if endpoint == "dang_nhap":
            data = response.get_json(silent=True) or {}

            if data.get("status") == "success":
                user = data.get("data", {})

                ghi_nhat_ky(
                    user.get("MaNguoiDung"),
                    "Đăng nhập",
                    "Đăng nhập hệ thống thành công"
                )

    except Exception as error:
        print("Lỗi ghi nhật ký tự động:", error)

    return response


# =====================================================
# 8. TRANG CHỦ VÀ KIỂM TRA KẾT NỐI
# =====================================================

# =====================================================
# 9. CÁC ROUTE HIỂN THỊ GIAO DIỆN
# =====================================================

@app.route("/")
def trang_chu():
    return render_template("dashboard.html")


@app.route("/login")
def trang_dang_nhap():
    return render_template("login.html")


@app.route("/foods")
def trang_mon_an():
    return render_template("foods.html")


@app.route("/foods/add")
def trang_them_mon_an():
    return render_template("add_food.html")


@app.route("/foods/edit/<int:food_id>")
def trang_sua_mon_an(food_id):
    return render_template("edit_food.html", food_id=food_id)


@app.route("/categories")
def trang_danh_muc():
    return render_template("categories.html")

@app.route("/api/health", methods=["GET"])
def health():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT DB_NAME()")

        database = cursor.fetchone()[0]

        return jsonify({
            "status": "success",
            "database": database,
            "message": "Backend đã kết nối SQL Server thành công"
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# =====================================================
# 9. API ĐĂNG NHẬP
# =====================================================

@app.route("/api/dang-nhap", methods=["POST"])
def dang_nhap():
    data = lay_du_lieu_json()

    ten_dang_nhap = data.get("TenDangNhap")
    mat_khau = data.get("MatKhau")

    if not ten_dang_nhap or not mat_khau:
        return jsonify({
            "status": "error",
            "message": "Vui lòng nhập tên đăng nhập và mật khẩu"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                MaNguoiDung,
                TenDangNhap,
                MatKhau,
                HoTen,
                Email,
                VaiTro,
                TrangThai
            FROM dbo.NguoiDung
            WHERE TenDangNhap = ?
        """, (ten_dang_nhap,))

        user = convert_one_to_json(cursor)

        if not user:
            return jsonify({
                "status": "error",
                "message": "Tên đăng nhập hoặc mật khẩu không đúng"
            }), 401

        if not check_password_hash(user["MatKhau"], mat_khau):
            return jsonify({
                "status": "error",
                "message": "Tên đăng nhập hoặc mật khẩu không đúng"
            }), 401

        if user["TrangThai"] != 1:
            return jsonify({
                "status": "error",
                "message": "Tài khoản đã bị khóa"
            }), 403

        token = tao_token(user["MaNguoiDung"])

        return jsonify({
            "status": "success",
            "message": "Đăng nhập thành công",
            "token": token,
            "data": {
                "MaNguoiDung": user["MaNguoiDung"],
                "TenDangNhap": user["TenDangNhap"],
                "HoTen": user["HoTen"],
                "Email": user["Email"],
                "VaiTro": user["VaiTro"]
            }
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# =====================================================
# 10. API QUẢN LÝ MÓN ĂN
# =====================================================

# Lấy danh sách món ăn
@app.route("/api/mon-an", methods=["GET"])
def danh_sach_mon_an():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = """
            SELECT *
            FROM dbo.vw_ChiTietMonAn
            WHERE 1 = 1
        """

        params = []

        tu_khoa = request.args.get("q")
        ma_danh_muc = request.args.get("ma_danh_muc")
        con_kinh_doanh = request.args.get("con_kinh_doanh")

        if tu_khoa:
            sql += """
                AND (
                    TenMonAn LIKE ?
                    OR MaMon LIKE ?
                )
            """
            params.extend([
                f"%{tu_khoa}%",
                f"%{tu_khoa}%"
            ])

        if ma_danh_muc:
            sql += " AND MaDanhMuc = ?"
            params.append(ma_danh_muc)

        if con_kinh_doanh is not None:
            gia_tri = (
                1 if con_kinh_doanh.lower() == "true"
                else 0
            )

            sql += " AND ConKinhDoanh = ?"
            params.append(gia_tri)

        sql += " ORDER BY MaMonAn DESC"

        cursor.execute(sql, params)

        return jsonify({
            "status": "success",
            "data": convert_to_json(cursor)
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# Thêm món ăn
@app.route("/api/mon-an", methods=["POST"])
@yeu_cau_quyen("Admin", "Manager")
def them_mon_an():
    data = lay_du_lieu_json()

    ma_mon = data.get("MaMon")
    ten_mon = data.get("TenMonAn")
    ma_danh_muc = data.get("MaDanhMuc")
    gia = data.get("Gia")

    if (
        not ma_mon
        or not ten_mon
        or not ma_danh_muc
        or gia is None
    ):
        return jsonify({
            "status": "error",
            "message": "Vui lòng nhập đầy đủ thông tin món ăn"
        }), 400

    try:
        gia = float(gia)

        if gia < 0:
            raise ValueError()

    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Giá món ăn không hợp lệ"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM dbo.MonAn
            WHERE MaMon = ?
        """, (ma_mon,))

        if cursor.fetchone()[0] > 0:
            return jsonify({
                "status": "error",
                "message": "Mã món ăn đã tồn tại"
            }), 400

        cursor.execute("""
            SELECT COUNT(*)
            FROM dbo.DanhMuc
            WHERE MaDanhMuc = ?
              AND TrangThai = 1
        """, (ma_danh_muc,))

        if cursor.fetchone()[0] == 0:
            return jsonify({
                "status": "error",
                "message": "Danh mục không tồn tại hoặc đã bị khóa"
            }), 400

        cursor.execute("""
            INSERT INTO dbo.MonAn
                (
                    MaMon,
                    TenMonAn,
                    MaDanhMuc,
                    MoTa,
                    Gia,
                    HinhAnh,
                    ConKinhDoanh,
                    NgayTao
                )
            VALUES (?, ?, ?, ?, ?, ?, 1, GETDATE())
        """, (
            ma_mon,
            ten_mon,
            ma_danh_muc,
            data.get("MoTa"),
            gia,
            data.get("HinhAnh")
        ))

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Thêm món ăn thành công"
        }), 201

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# Sửa món ăn
@app.route("/api/mon-an/<int:ma_mon_an>", methods=["PUT"])
@yeu_cau_quyen("Admin", "Manager")
def sua_mon_an(ma_mon_an):
    data = lay_du_lieu_json()

    ten_mon = data.get("TenMonAn")
    ma_danh_muc = data.get("MaDanhMuc")
    gia = data.get("Gia")

    if not ten_mon or not ma_danh_muc or gia is None:
        return jsonify({
            "status": "error",
            "message": "Vui lòng nhập đầy đủ thông tin món ăn"
        }), 400

    try:
        gia = float(gia)

        if gia < 0:
            raise ValueError()

    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Giá món ăn không hợp lệ"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM dbo.DanhMuc
            WHERE MaDanhMuc = ?
              AND TrangThai = 1
        """, (ma_danh_muc,))

        if cursor.fetchone()[0] == 0:
            return jsonify({
                "status": "error",
                "message": "Danh mục không tồn tại hoặc đã bị khóa"
            }), 400

        cursor.execute("""
            UPDATE dbo.MonAn
            SET
                TenMonAn = ?,
                MaDanhMuc = ?,
                MoTa = ?,
                Gia = ?,
                HinhAnh = ?,
                NgayCapNhat = GETDATE()
            WHERE MaMonAn = ?
        """, (
            ten_mon,
            ma_danh_muc,
            data.get("MoTa"),
            gia,
            data.get("HinhAnh"),
            ma_mon_an
        ))

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": "Không tìm thấy món ăn"
            }), 404

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Cập nhật món ăn thành công"
        })

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# Xóa mềm món ăn
@app.route("/api/mon-an/<int:ma_mon_an>", methods=["DELETE"])
@yeu_cau_quyen("Admin", "Manager")
def xoa_mon_an(ma_mon_an):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE dbo.MonAn
            SET
                ConKinhDoanh = 0,
                NgayCapNhat = GETDATE()
            WHERE MaMonAn = ?
              AND ConKinhDoanh = 1
        """, (ma_mon_an,))

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": "Không tìm thấy món ăn đang kinh doanh"
            }), 404

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Đã ngừng kinh doanh món ăn"
        })

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# =====================================================
# 11. API QUẢN LÝ DANH MỤC
# =====================================================

# Lấy danh sách danh mục
@app.route("/api/danh-muc", methods=["GET"])
def danh_sach_danh_muc():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = """
            SELECT *
            FROM dbo.DanhMuc
            WHERE 1 = 1
        """

        params = []

        tu_khoa = request.args.get("q")
        trang_thai = request.args.get("trang_thai")

        if tu_khoa:
            sql += " AND TenDanhMuc LIKE ?"
            params.append(f"%{tu_khoa}%")

        if trang_thai is not None:
            gia_tri = (
                1 if trang_thai.lower() == "true"
                else 0
            )

            sql += " AND TrangThai = ?"
            params.append(gia_tri)

        sql += " ORDER BY MaDanhMuc DESC"

        cursor.execute(sql, params)

        return jsonify({
            "status": "success",
            "data": convert_to_json(cursor)
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# Thêm danh mục
@app.route("/api/danh-muc", methods=["POST"])
@yeu_cau_quyen("Admin", "Manager")
def them_danh_muc():
    data = lay_du_lieu_json()

    ky_hieu = data.get("KyHieuDanhMuc")
    ten_danh_muc = data.get("TenDanhMuc")

    if not ky_hieu or not ten_danh_muc:
        return jsonify({
            "status": "error",
            "message": "Vui lòng nhập mã và tên danh mục"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM dbo.DanhMuc
            WHERE KyHieuDanhMuc = ?
        """, (ky_hieu,))

        if cursor.fetchone()[0] > 0:
            return jsonify({
                "status": "error",
                "message": "Mã danh mục đã tồn tại"
            }), 400

        cursor.execute("""
            INSERT INTO dbo.DanhMuc
                (
                    KyHieuDanhMuc,
                    TenDanhMuc,
                    MoTa,
                    TrangThai,
                    NgayTao
                )
            VALUES (?, ?, ?, 1, GETDATE())
        """, (
            ky_hieu,
            ten_danh_muc,
            data.get("MoTa")
        ))

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Thêm danh mục thành công"
        }), 201

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# Sửa danh mục
@app.route("/api/danh-muc/<int:ma_danh_muc>", methods=["PUT"])
@yeu_cau_quyen("Admin", "Manager")
def sua_danh_muc(ma_danh_muc):
    data = lay_du_lieu_json()

    ten_danh_muc = data.get("TenDanhMuc")

    if not ten_danh_muc:
        return jsonify({
            "status": "error",
            "message": "Vui lòng nhập tên danh mục"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE dbo.DanhMuc
            SET
                TenDanhMuc = ?,
                MoTa = ?,
                NgayCapNhat = GETDATE()
            WHERE MaDanhMuc = ?
        """, (
            ten_danh_muc,
            data.get("MoTa"),
            ma_danh_muc
        ))

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": "Không tìm thấy danh mục"
            }), 404

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Cập nhật danh mục thành công"
        })

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# Xóa mềm danh mục
@app.route("/api/danh-muc/<int:ma_danh_muc>", methods=["DELETE"])
@yeu_cau_quyen("Admin", "Manager")
def xoa_danh_muc(ma_danh_muc):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM dbo.MonAn
            WHERE MaDanhMuc = ?
              AND ConKinhDoanh = 1
        """, (ma_danh_muc,))

        if cursor.fetchone()[0] > 0:
            return jsonify({
                "status": "error",
                "message": "Danh mục đang có món ăn kinh doanh, không thể khóa"
            }), 400

        cursor.execute("""
            UPDATE dbo.DanhMuc
            SET
                TrangThai = 0,
                NgayCapNhat = GETDATE()
            WHERE MaDanhMuc = ?
              AND TrangThai = 1
        """, (ma_danh_muc,))

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": "Không tìm thấy danh mục đang hoạt động"
            }), 404

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Đã ngừng hoạt động danh mục"
        })

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# =====================================================
# 12. API QUẢN LÝ NGƯỜI DÙNG
# =====================================================

# Lấy danh sách người dùng
@app.route("/api/nguoi-dung", methods=["GET"])
@yeu_cau_quyen("Admin")
def danh_sach_nguoi_dung():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                MaNguoiDung,
                TenDangNhap,
                HoTen,
                Email,
                VaiTro,
                TrangThai,
                NgayTao,
                NgayCapNhat
            FROM dbo.NguoiDung
            ORDER BY MaNguoiDung DESC
        """)

        return jsonify({
            "status": "success",
            "data": convert_to_json(cursor)
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# Thêm người dùng
@app.route("/api/nguoi-dung", methods=["POST"])
@yeu_cau_quyen("Admin")
def them_nguoi_dung():
    data = lay_du_lieu_json()

    ten_dang_nhap = data.get("TenDangNhap")
    mat_khau = data.get("MatKhau")
    ho_ten = data.get("HoTen")
    email = data.get("Email")
    vai_tro = data.get("VaiTro", "Staff")

    if not all([ten_dang_nhap, mat_khau, ho_ten, email]):
        return jsonify({
            "status": "error",
            "message": "Vui lòng nhập đầy đủ thông tin người dùng"
        }), 400

    if len(mat_khau) < 6:
        return jsonify({
            "status": "error",
            "message": "Mật khẩu phải có ít nhất 6 ký tự"
        }), 400

    if vai_tro not in ["Admin", "Manager", "Staff"]:
        return jsonify({
            "status": "error",
            "message": "Vai trò không hợp lệ"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM dbo.NguoiDung
            WHERE TenDangNhap = ?
               OR Email = ?
        """, (
            ten_dang_nhap,
            email
        ))

        if cursor.fetchone()[0] > 0:
            return jsonify({
                "status": "error",
                "message": "Tên đăng nhập hoặc email đã tồn tại"
            }), 400

        mat_khau_ma_hoa = generate_password_hash(mat_khau)

        cursor.execute("""
            INSERT INTO dbo.NguoiDung
                (
                    TenDangNhap,
                    MatKhau,
                    HoTen,
                    Email,
                    VaiTro,
                    TrangThai,
                    NgayTao
                )
            VALUES (?, ?, ?, ?, ?, 1, GETDATE())
        """, (
            ten_dang_nhap,
            mat_khau_ma_hoa,
            ho_ten,
            email,
            vai_tro
        ))

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Thêm người dùng thành công"
        }), 201

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# Sửa người dùng
@app.route("/api/nguoi-dung/<int:ma_nguoi_dung>", methods=["PUT"])
@yeu_cau_quyen("Admin")
def sua_nguoi_dung(ma_nguoi_dung):
    data = lay_du_lieu_json()

    if ma_nguoi_dung == g.ma_nguoi_dung:
        return jsonify({
            "status": "error",
            "message": "Không thể tự chỉnh sửa tài khoản của mình tại đây"
        }), 400

    ho_ten = data.get("HoTen")
    email = data.get("Email")
    vai_tro = data.get("VaiTro")

    if not all([ho_ten, email, vai_tro]):
        return jsonify({
            "status": "error",
            "message": "Vui lòng nhập đầy đủ thông tin"
        }), 400

    if vai_tro not in ["Admin", "Manager", "Staff"]:
        return jsonify({
            "status": "error",
            "message": "Vai trò không hợp lệ"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM dbo.NguoiDung
            WHERE Email = ?
              AND MaNguoiDung <> ?
        """, (
            email,
            ma_nguoi_dung
        ))

        if cursor.fetchone()[0] > 0:
            return jsonify({
                "status": "error",
                "message": "Email đã được sử dụng"
            }), 400

        cursor.execute("""
            UPDATE dbo.NguoiDung
            SET
                HoTen = ?,
                Email = ?,
                VaiTro = ?,
                NgayCapNhat = GETDATE()
            WHERE MaNguoiDung = ?
        """, (
            ho_ten,
            email,
            vai_tro,
            ma_nguoi_dung
        ))

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": "Không tìm thấy người dùng"
            }), 404

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Cập nhật người dùng thành công"
        })

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# Khóa người dùng
@app.route("/api/nguoi-dung/<int:ma_nguoi_dung>", methods=["DELETE"])
@yeu_cau_quyen("Admin")
def xoa_nguoi_dung(ma_nguoi_dung):
    if ma_nguoi_dung == g.ma_nguoi_dung:
        return jsonify({
            "status": "error",
            "message": "Không thể tự khóa tài khoản của mình"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE dbo.NguoiDung
            SET
                TrangThai = 0,
                NgayCapNhat = GETDATE()
            WHERE MaNguoiDung = ?
              AND TrangThai = 1
        """, (ma_nguoi_dung,))

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": "Không tìm thấy người dùng đang hoạt động"
            }), 404

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Đã khóa tài khoản người dùng"
        })

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# Mở khóa người dùng
@app.route("/api/nguoi-dung/<int:ma_nguoi_dung>/mo-khoa", methods=["PUT"])
@yeu_cau_quyen("Admin")
def mo_khoa_nguoi_dung(ma_nguoi_dung):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE dbo.NguoiDung
            SET
                TrangThai = 1,
                NgayCapNhat = GETDATE()
            WHERE MaNguoiDung = ?
              AND TrangThai = 0
        """, (ma_nguoi_dung,))

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": "Không tìm thấy tài khoản đang bị khóa"
            }), 404

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Mở khóa tài khoản thành công"
        })

    except Exception as error:
        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)



# 13. API NHẬT KÝ HOẠT ĐỘNG


@app.route("/api/nhat-ky", methods=["GET"])
@yeu_cau_quyen("Admin")
def danh_sach_nhat_ky():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = """
            SELECT
                NK.MaNhatKy,
                NK.MaNguoiDung,
                ND.HoTen,
                NK.HanhDong,
                NK.ChiTiet,
                NK.NgayTao
            FROM dbo.NhatKyHoatDong NK
            LEFT JOIN dbo.NguoiDung ND
                ON NK.MaNguoiDung = ND.MaNguoiDung
            WHERE 1 = 1
        """

        params = []

        hanh_dong = request.args.get("hanh_dong")

        if hanh_dong:
            sql += " AND NK.HanhDong LIKE ?"
            params.append(f"%{hanh_dong}%")

        sql += " ORDER BY NK.NgayTao DESC"

        cursor.execute(sql, params)

        return jsonify({
            "status": "success",
            "data": convert_to_json(cursor)
        })

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        dong_ket_noi(connection, cursor)


# =====================================================
# 14. XỬ LÝ LỖI API
# =====================================================

@app.errorhandler(404)
def loi_404(error):
    return jsonify({
        "status": "error",
        "message": "Không tìm thấy đường dẫn API"
    }), 404


@app.errorhandler(405)
def loi_405(error):
    return jsonify({
        "status": "error",
        "message": "Phương thức HTTP không được hỗ trợ"
    }), 405


@app.errorhandler(500)
def loi_500(error):
    return jsonify({
        "status": "error",
        "message": "Đã xảy ra lỗi phía máy chủ"
    }), 500


# =====================================================
# 15. KHỞI CHẠY BACKEND
# =====================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )

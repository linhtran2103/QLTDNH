
from flask import Flask, jsonify, request, g, render_template
from flask_cors import CORS
from werkzeug.security import check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from functools import wraps
from pathlib import Path
import os

from dotenv import load_dotenv

# =====================================================
# 1. KHOI TAO FLASK VA DATABASE
# =====================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / "backend" / ".env", override=True)

from database.db import (
    get_connection,
    dong_ket_noi,
    convert_to_json,
    convert_one_to_json
)

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "frontend" / "templates"),
    static_folder=str(PROJECT_ROOT / "frontend" / "static")
)

CORS(app, allow_headers=["Content-Type", "Authorization"])

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("Chua cau hinh SECRET_KEY trong backend/.env")

serializer = URLSafeTimedSerializer(SECRET_KEY)


# =====================================================
# 2. CAC HAM DUNG CHUNG
# =====================================================

def lay_du_lieu_json():
    return request.get_json(silent=True) or {}


def phan_hoi_thanh_cong(message="Thanh cong", data=None, status_code=200, **extra):
    ket_qua = {
        "status": "success",
        "success": True,
        "message": message
    }

    if data is not None:
        ket_qua["data"] = data

    ket_qua.update(extra)
    return jsonify(ket_qua), status_code


def phan_hoi_loi(message, status_code=400):
    return jsonify({
        "status": "error",
        "success": False,
        "message": message
    }), status_code


def dong_ket_noi_an_toan(cursor, connection):
    try:
        dong_ket_noi(cursor, connection)
    except Exception as error:
        print("Loi dong ket noi:", error)


# Kiem tra mat khau
def kiem_tra_mat_khau(mat_khau_luu, mat_khau_nhap):
    if not mat_khau_luu:
        return False

    mat_khau_luu = str(mat_khau_luu)

    # Tai khoan cu da ma hoa
    if mat_khau_luu.startswith(("scrypt:", "pbkdf2:")):
        try:
            return check_password_hash(
                mat_khau_luu, mat_khau_nhap
            )
        except Exception:
            return False

    # Tai khoan moi luu mat khau truc tiep
    return mat_khau_luu == str(mat_khau_nhap)


# =====================================================
# 3. NHAT KY HOAT DONG
# =====================================================

def ghi_nhat_ky(ma_nguoi_dung, hanh_dong, noi_dung=None):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO dbo.ACTIVITY_LOGS
                (MaNguoiDung, HanhDong, BangTacDong,
                 MaBanGhi, NoiDung, ThoiGian)
            VALUES (?, ?, NULL, NULL, ?, GETDATE())
        """, (ma_nguoi_dung, hanh_dong, noi_dung))

        connection.commit()

    except Exception as error:
        print("Loi ghi nhat ky:", error)

        if connection:
            connection.rollback()

    finally:
        dong_ket_noi_an_toan(cursor, connection)


# =====================================================
# 4. TOKEN VA PHAN QUYEN
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
            SELECT MaNguoiDung, TenDangNhap, HoTen,
                   VaiTro, TrangThai
            FROM dbo.NGUOI_DUNG
            WHERE MaNguoiDung = ?
        """, (ma_nguoi_dung,))

        user = convert_one_to_json(cursor)

        if not user or not user["TrangThai"]:
            return None

        return user

    finally:
        dong_ket_noi_an_toan(cursor, connection)


def yeu_cau_dang_nhap(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            user = xac_thuc_nguoi_dung()

            if not user:
                return phan_hoi_loi(
                    "Token khong hop le hoac da het han", 401
                )

            g.nguoi_dung = user
            g.ma_nguoi_dung = user["MaNguoiDung"]

            return func(*args, **kwargs)

        except Exception as error:
            print("Loi xac thuc:", error)
            return phan_hoi_loi(
                "Khong the xac thuc nguoi dung", 500
            )

    return wrapper


def yeu_cau_quyen(*cac_quyen):
    def decorator(func):
        @wraps(func)
        @yeu_cau_dang_nhap
        def wrapper(*args, **kwargs):

            vai_tro = str(
                g.nguoi_dung["VaiTro"]
            ).strip().lower()

            danh_sach_quyen = [
                str(quyen).strip().lower()
                for quyen in cac_quyen
            ]

            if vai_tro not in danh_sach_quyen:
                return phan_hoi_loi(
                    "Ban khong co quyen thuc hien chuc nang nay",
                    403
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator


# =====================================================
# 5. TU DONG GHI NHAT KY
# =====================================================

@app.after_request
def ghi_nhat_ky_sau_thao_tac(response):
    try:
        if not 200 <= response.status_code < 300:
            return response

        endpoint = request.endpoint

        danh_sach_hanh_dong = {
            "dang_ky": "Dang ky tai khoan",
            "them_mon_an": "Them mon an",
            "sua_mon_an": "Cap nhat mon an",
            "xoa_mon_an": "Ngung kinh doanh mon an",
            "them_danh_muc": "Them danh muc",
            "sua_danh_muc": "Cap nhat danh muc",
            "xoa_danh_muc": "Khoa danh muc",
            "them_nguoi_dung": "Them nguoi dung",
            "sua_nguoi_dung": "Cap nhat nguoi dung",
            "xoa_nguoi_dung": "Khoa nguoi dung",
            "mo_khoa_nguoi_dung": "Mo khoa nguoi dung"
        }

        if endpoint in danh_sach_hanh_dong:
            ghi_nhat_ky(
                getattr(g, "ma_nguoi_dung", None),
                danh_sach_hanh_dong[endpoint],
                f"{request.method} {request.path}"
            )

        if endpoint == "dang_nhap":
            data = response.get_json(silent=True) or {}

            if data.get("status") == "success":
                user = data.get("data", {})

                ghi_nhat_ky(
                    user.get("MaNguoiDung"),
                    "Dang nhap",
                    "Dang nhap he thong thanh cong"
                )

    except Exception as error:
        print("Loi ghi nhat ky tu dong:", error)

    return response


# =====================================================
# 6. TRANG WEB
# =====================================================

def hien_thi_trang(ten_file, **context):
    duong_dan = PROJECT_ROOT / "frontend" / "templates" / ten_file

    if duong_dan.exists():
        return render_template(ten_file, **context)

    return jsonify({
        "status": "success",
        "message": "Backend dang hoat dong. Khong tim thay template: " + ten_file
    })


@app.route("/")
def trang_chu():
    return render_template("dashboard.html")


@app.route("/login", methods=["GET"])
def trang_dang_nhap():
    return hien_thi_trang("login.html")


@app.route("/foods", methods=["GET"])
def trang_mon_an():
    return hien_thi_trang("foods.html")


@app.route("/foods/add", methods=["GET"])
def trang_them_mon_an():
    return hien_thi_trang("food_form.html")


@app.route("/foods/edit/<int:ma_mon_an>", methods=["GET"])
def trang_sua_mon_an(ma_mon_an):
    return hien_thi_trang("food_form.html", ma_mon_an=ma_mon_an)


@app.route("/categories", methods=["GET"])
def trang_danh_muc():
    return hien_thi_trang("categories.html")


# =====================================================
# 7. KIEM TRA BACKEND VA SQL SERVER
# =====================================================

@app.route("/api/health", methods=["GET"])
def health():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT DB_NAME()")
        database = cursor.fetchone()[0]

        return phan_hoi_thanh_cong(
            "Backend da ket noi SQL Server thanh cong",
            database=database
        )

    except Exception as error:
        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


# =====================================================
# 8. API DANG NHAP
# =====================================================

@app.route("/api/dang-nhap", methods=["POST"])
def dang_nhap():
    data = lay_du_lieu_json()

    ten_dang_nhap = data.get("TenDangNhap")
    mat_khau = data.get("MatKhau")

    if not ten_dang_nhap or not mat_khau:
        return phan_hoi_loi(
            "Vui long nhap ten dang nhap va mat khau"
        )

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT MaNguoiDung, TenDangNhap, MatKhauHash,
                   HoTen, VaiTro, TrangThai
            FROM dbo.NGUOI_DUNG
            WHERE TenDangNhap = ?
        """, (ten_dang_nhap,))

        user = convert_one_to_json(cursor)

        if not user or not kiem_tra_mat_khau(
            user["MatKhauHash"], mat_khau
        ):
            return phan_hoi_loi(
                "Ten dang nhap hoac mat khau khong dung", 401
            )

        if not user["TrangThai"]:
            return phan_hoi_loi(
                "Tai khoan da bi khoa", 403
            )

        token = tao_token(user["MaNguoiDung"])

        return phan_hoi_thanh_cong(
            "Dang nhap thanh cong",
            token=token,
            data={
                "MaNguoiDung": user["MaNguoiDung"],
                "TenDangNhap": user["TenDangNhap"],
                "HoTen": user["HoTen"],
                "VaiTro": user["VaiTro"]
            }
        )

    except Exception as error:
        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


# =====================================================
# 9. API DANG KY TAI KHOAN
# =====================================================

@app.route("/api/dang-ky", methods=["POST"])
def dang_ky():
    data = lay_du_lieu_json()

    ten_dang_nhap = str(
        data.get("TenDangNhap", "")
    ).strip()

    mat_khau = str(data.get("MatKhau", ""))

    ho_ten = str(
        data.get("HoTen", "")
    ).strip()

    if not ten_dang_nhap or not mat_khau or not ho_ten:
        return phan_hoi_loi(
            "Vui long nhap ten dang nhap, mat khau va ho ten"
        )

    if len(ten_dang_nhap) < 3:
        return phan_hoi_loi(
            "Ten dang nhap phai co it nhat 3 ky tu"
        )

    if len(mat_khau) < 6:
        return phan_hoi_loi(
            "Mat khau phai co it nhat 6 ky tu"
        )

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM dbo.NGUOI_DUNG
            WHERE TenDangNhap = ?
        """, (ten_dang_nhap,))

        if cursor.fetchone()[0] > 0:
            return phan_hoi_loi(
                "Ten dang nhap da ton tai"
            )

        # Luu mat khau truc tiep, khong ma hoa
        cursor.execute("""
            INSERT INTO dbo.NGUOI_DUNG
                (TenDangNhap, MatKhauHash, HoTen,
                 VaiTro, TrangThai, NgayTao)
            VALUES (?, ?, ?, 'user', 1, GETDATE())
        """, (
            ten_dang_nhap,
            mat_khau,
            ho_ten
        ))

        connection.commit()

        return phan_hoi_thanh_cong(
            "Dang ky tai khoan thanh cong",
            status_code=201
        )

    except Exception as error:
        if connection:
            connection.rollback()

        print("Loi dang ky:", error)

        return phan_hoi_loi(
            "Khong the dang ky tai khoan", 500
        )

    finally:
        dong_ket_noi_an_toan(cursor, connection)


# =====================================================
# 10. API MON AN
# =====================================================

@app.route("/api/mon-an", methods=["GET"])
def danh_sach_mon_an():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = """
            SELECT MA.MaMonAn, MA.MaMon, MA.TenMonAn,
                   MA.MaDanhMuc, DM.TenDanhMuc, MA.Gia,
                   MA.MoTa, MA.HinhAnh, MA.ConKinhDoanh,
                   MA.NgayTao, MA.NgayCapNhat
            FROM dbo.MON_AN MA
            LEFT JOIN dbo.DANH_MUC DM
                ON DM.MaDanhMuc = MA.MaDanhMuc
            WHERE 1 = 1
        """

        params = []

        tu_khoa = request.args.get("q")
        ma_danh_muc = request.args.get("ma_danh_muc")
        con_kinh_doanh = request.args.get("con_kinh_doanh")

        if tu_khoa:
            sql += """
                AND (MA.TenMonAn LIKE ? OR MA.MaMon LIKE ?)
            """
            params.extend([
                f"%{tu_khoa}%",
                f"%{tu_khoa}%"
            ])

        if ma_danh_muc:
            sql += " AND MA.MaDanhMuc = ?"
            params.append(ma_danh_muc)

        if con_kinh_doanh is not None:
            gia_tri = 1 if con_kinh_doanh.lower() in (
                "true", "1", "yes"
            ) else 0

            sql += " AND MA.ConKinhDoanh = ?"
            params.append(gia_tri)

        sql += " ORDER BY MA.MaMonAn DESC"

        cursor.execute(sql, params)

        return phan_hoi_thanh_cong(
            data=convert_to_json(cursor)
        )

    except Exception as error:
        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


@app.route("/api/mon-an", methods=["POST"])
@yeu_cau_quyen("Admin", "Manager")
def them_mon_an():
    data = lay_du_lieu_json()

    ma_mon = data.get("MaMon")
    ten_mon = data.get("TenMonAn")
    ma_danh_muc = data.get("MaDanhMuc")
    gia = data.get("Gia")

    if not ma_mon or not ten_mon or not ma_danh_muc or gia is None:
        return phan_hoi_loi(
            "Vui long nhap day du thong tin mon an"
        )

    try:
        gia = float(gia)

        if gia < 0:
            raise ValueError

    except (ValueError, TypeError):
        return phan_hoi_loi("Gia mon an khong hop le")

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM dbo.MON_AN WHERE MaMon = ?
        """, (ma_mon,))

        if cursor.fetchone()[0] > 0:
            return phan_hoi_loi("Ma mon an da ton tai")

        cursor.execute("""
            SELECT COUNT(*) FROM dbo.DANH_MUC
            WHERE MaDanhMuc = ? AND TrangThai = 1
        """, (ma_danh_muc,))

        if cursor.fetchone()[0] == 0:
            return phan_hoi_loi(
                "Danh muc khong ton tai hoac da bi khoa"
            )

        cursor.execute("""
            INSERT INTO dbo.MON_AN
                (MaMon, TenMonAn, MaDanhMuc, MoTa, Gia,
                 HinhAnh, ConKinhDoanh, NgayTao)
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

        return phan_hoi_thanh_cong(
            "Them mon an thanh cong", status_code=201
        )

    except Exception as error:
        if connection:
            connection.rollback()

        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


@app.route("/api/mon-an/<int:ma_mon_an>", methods=["PUT"])
@yeu_cau_quyen("Admin", "Manager")
def sua_mon_an(ma_mon_an):
    data = lay_du_lieu_json()

    ten_mon = data.get("TenMonAn")
    ma_danh_muc = data.get("MaDanhMuc")
    gia = data.get("Gia")

    if not ten_mon or not ma_danh_muc or gia is None:
        return phan_hoi_loi(
            "Vui long nhap day du thong tin mon an"
        )

    try:
        gia = float(gia)

        if gia < 0:
            raise ValueError

    except (ValueError, TypeError):
        return phan_hoi_loi("Gia mon an khong hop le")

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM dbo.DANH_MUC
            WHERE MaDanhMuc = ? AND TrangThai = 1
        """, (ma_danh_muc,))

        if cursor.fetchone()[0] == 0:
            return phan_hoi_loi(
                "Danh muc khong ton tai hoac da bi khoa"
            )

        cursor.execute("""
            UPDATE dbo.MON_AN
            SET TenMonAn = ?, MaDanhMuc = ?, MoTa = ?,
                Gia = ?, HinhAnh = ?, NgayCapNhat = GETDATE()
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
            return phan_hoi_loi("Khong tim thay mon an", 404)

        connection.commit()

        return phan_hoi_thanh_cong(
            "Cap nhat mon an thanh cong"
        )

    except Exception as error:
        if connection:
            connection.rollback()

        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


@app.route("/api/mon-an/<int:ma_mon_an>", methods=["DELETE"])
@yeu_cau_quyen("Admin", "Manager")
def xoa_mon_an(ma_mon_an):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE dbo.MON_AN
            SET ConKinhDoanh = 0, NgayCapNhat = GETDATE()
            WHERE MaMonAn = ? AND ConKinhDoanh = 1
        """, (ma_mon_an,))

        if cursor.rowcount == 0:
            return phan_hoi_loi(
                "Khong tim thay mon an dang kinh doanh", 404
            )

        connection.commit()

        return phan_hoi_thanh_cong(
            "Da ngung kinh doanh mon an"
        )

    except Exception as error:
        if connection:
            connection.rollback()

        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


# =====================================================
# 11. API DANH MUC
# =====================================================

@app.route("/api/danh-muc", methods=["GET"])
def danh_sach_danh_muc():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = """
            SELECT MaDanhMuc, TenDanhMuc, MoTa,
                   ThuTuHienThi, TrangThai
            FROM dbo.DANH_MUC
            WHERE 1 = 1
        """

        params = []

        tu_khoa = request.args.get("q")
        trang_thai = request.args.get("trang_thai")

        if tu_khoa:
            sql += " AND TenDanhMuc LIKE ?"
            params.append(f"%{tu_khoa}%")

        if trang_thai is not None:
            gia_tri = 1 if trang_thai.lower() in (
                "true", "1", "yes"
            ) else 0

            sql += " AND TrangThai = ?"
            params.append(gia_tri)

        sql += " ORDER BY MaDanhMuc DESC"

        cursor.execute(sql, params)

        return phan_hoi_thanh_cong(
            data=convert_to_json(cursor)
        )

    except Exception as error:
        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


@app.route("/api/danh-muc", methods=["POST"])
@yeu_cau_quyen("Admin", "Manager")
def them_danh_muc():
    data = lay_du_lieu_json()

    ten_danh_muc = data.get("TenDanhMuc")

    if not ten_danh_muc:
        return phan_hoi_loi("Vui long nhap ten danh muc")

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM dbo.DANH_MUC
            WHERE TenDanhMuc = ?
        """, (ten_danh_muc,))

        if cursor.fetchone()[0] > 0:
            return phan_hoi_loi("Ten danh muc da ton tai")

        thu_tu = data.get("ThuTuHienThi")

        if thu_tu is None:
            cursor.execute("""
                SELECT ISNULL(MAX(ThuTuHienThi), 0) + 1
                FROM dbo.DANH_MUC
            """)

            thu_tu = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO dbo.DANH_MUC
                (TenDanhMuc, MoTa, ThuTuHienThi, TrangThai)
            VALUES (?, ?, ?, 1)
        """, (
            ten_danh_muc,
            data.get("MoTa"),
            thu_tu
        ))

        connection.commit()

        return phan_hoi_thanh_cong(
            "Them danh muc thanh cong", status_code=201
        )

    except Exception as error:
        if connection:
            connection.rollback()

        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


@app.route("/api/danh-muc/<int:ma_danh_muc>", methods=["PUT"])
@yeu_cau_quyen("Admin", "Manager")
def sua_danh_muc(ma_danh_muc):
    data = lay_du_lieu_json()

    ten_danh_muc = data.get("TenDanhMuc")

    if not ten_danh_muc:
        return phan_hoi_loi("Vui long nhap ten danh muc")

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        if "ThuTuHienThi" in data:
            cursor.execute("""
                UPDATE dbo.DANH_MUC
                SET TenDanhMuc = ?, MoTa = ?, ThuTuHienThi = ?
                WHERE MaDanhMuc = ?
            """, (
                ten_danh_muc,
                data.get("MoTa"),
                data.get("ThuTuHienThi"),
                ma_danh_muc
            ))

        else:
            cursor.execute("""
                UPDATE dbo.DANH_MUC
                SET TenDanhMuc = ?, MoTa = ?
                WHERE MaDanhMuc = ?
            """, (
                ten_danh_muc,
                data.get("MoTa"),
                ma_danh_muc
            ))

        if cursor.rowcount == 0:
            return phan_hoi_loi("Khong tim thay danh muc", 404)

        connection.commit()

        return phan_hoi_thanh_cong(
            "Cap nhat danh muc thanh cong"
        )

    except Exception as error:
        if connection:
            connection.rollback()

        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


@app.route("/api/danh-muc/<int:ma_danh_muc>", methods=["DELETE"])
@yeu_cau_quyen("Admin", "Manager")
def xoa_danh_muc(ma_danh_muc):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM dbo.MON_AN
            WHERE MaDanhMuc = ? AND ConKinhDoanh = 1
        """, (ma_danh_muc,))

        if cursor.fetchone()[0] > 0:
            return phan_hoi_loi(
                "Danh muc dang co mon an kinh doanh, khong the khoa"
            )

        cursor.execute("""
            UPDATE dbo.DANH_MUC
            SET TrangThai = 0
            WHERE MaDanhMuc = ? AND TrangThai = 1
        """, (ma_danh_muc,))

        if cursor.rowcount == 0:
            return phan_hoi_loi(
                "Khong tim thay danh muc dang hoat dong", 404
            )

        connection.commit()

        return phan_hoi_thanh_cong(
            "Da ngung hoat dong danh muc"
        )

    except Exception as error:
        if connection:
            connection.rollback()

        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


# =====================================================
# 12. API NGUOI DUNG
# =====================================================

@app.route("/api/nguoi-dung", methods=["GET"])
@yeu_cau_quyen("Admin")
def danh_sach_nguoi_dung():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT MaNguoiDung, TenDangNhap, HoTen,
                   VaiTro, TrangThai, NgayTao
            FROM dbo.NGUOI_DUNG
            ORDER BY MaNguoiDung DESC
        """)

        return phan_hoi_thanh_cong(
            data=convert_to_json(cursor)
        )

    except Exception as error:
        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


@app.route("/api/nguoi-dung", methods=["POST"])
@yeu_cau_quyen("Admin")
def them_nguoi_dung():
    data = lay_du_lieu_json()

    ten_dang_nhap = data.get("TenDangNhap")
    mat_khau = data.get("MatKhau")
    ho_ten = data.get("HoTen")
    vai_tro = data.get("VaiTro", "Staff")

    if not all([ten_dang_nhap, mat_khau, ho_ten]):
        return phan_hoi_loi(
            "Vui long nhap ten dang nhap, mat khau va ho ten"
        )

    if len(mat_khau) < 6:
        return phan_hoi_loi(
            "Mat khau phai co it nhat 6 ky tu"
        )

    if vai_tro not in ["Admin", "Manager", "Staff"]:
        return phan_hoi_loi("Vai tro khong hop le")

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM dbo.NGUOI_DUNG
            WHERE TenDangNhap = ?
        """, (ten_dang_nhap,))

        if cursor.fetchone()[0] > 0:
            return phan_hoi_loi("Ten dang nhap da ton tai")

        # Tai khoan do Admin tao van luu mat khau ma hoa
        from werkzeug.security import generate_password_hash
        mat_khau_ma_hoa = generate_password_hash(mat_khau)

        cursor.execute("""
            INSERT INTO dbo.NGUOI_DUNG
                (TenDangNhap, MatKhauHash, HoTen,
                 VaiTro, TrangThai, NgayTao)
            VALUES (?, ?, ?, ?, 1, GETDATE())
        """, (
            ten_dang_nhap,
            mat_khau_ma_hoa,
            ho_ten,
            vai_tro
        ))

        connection.commit()

        return phan_hoi_thanh_cong(
            "Them nguoi dung thanh cong", status_code=201
        )

    except Exception as error:
        if connection:
            connection.rollback()

        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


@app.route("/api/nguoi-dung/<int:ma_nguoi_dung>", methods=["PUT"])
@yeu_cau_quyen("Admin")
def sua_nguoi_dung(ma_nguoi_dung):
    if ma_nguoi_dung == g.ma_nguoi_dung:
        return phan_hoi_loi(
            "Khong the tu chinh sua tai khoan cua minh tai day"
        )

    data = lay_du_lieu_json()

    ho_ten = data.get("HoTen")
    vai_tro = data.get("VaiTro")

    if not ho_ten or not vai_tro:
        return phan_hoi_loi(
            "Vui long nhap ho ten va vai tro"
        )

    if vai_tro not in ["Admin", "Manager", "Staff"]:
        return phan_hoi_loi("Vai tro khong hop le")

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE dbo.NGUOI_DUNG
            SET HoTen = ?, VaiTro = ?
            WHERE MaNguoiDung = ?
        """, (ho_ten, vai_tro, ma_nguoi_dung))

        if cursor.rowcount == 0:
            return phan_hoi_loi("Khong tim thay nguoi dung", 404)

        connection.commit()

        return phan_hoi_thanh_cong(
            "Cap nhat nguoi dung thanh cong"
        )

    except Exception as error:
        if connection:
            connection.rollback()

        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


@app.route("/api/nguoi-dung/<int:ma_nguoi_dung>", methods=["DELETE"])
@yeu_cau_quyen("Admin")
def xoa_nguoi_dung(ma_nguoi_dung):
    if ma_nguoi_dung == g.ma_nguoi_dung:
        return phan_hoi_loi(
            "Khong the tu khoa tai khoan cua minh"
        )

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE dbo.NGUOI_DUNG
            SET TrangThai = 0
            WHERE MaNguoiDung = ? AND TrangThai = 1
        """, (ma_nguoi_dung,))

        if cursor.rowcount == 0:
            return phan_hoi_loi(
                "Khong tim thay nguoi dung dang hoat dong", 404
            )

        connection.commit()

        return phan_hoi_thanh_cong(
            "Da khoa tai khoan nguoi dung"
        )

    except Exception as error:
        if connection:
            connection.rollback()

        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


@app.route("/api/nguoi-dung/<int:ma_nguoi_dung>/mo-khoa", methods=["PUT"])
@yeu_cau_quyen("Admin")
def mo_khoa_nguoi_dung(ma_nguoi_dung):
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE dbo.NGUOI_DUNG
            SET TrangThai = 1
            WHERE MaNguoiDung = ? AND TrangThai = 0
        """, (ma_nguoi_dung,))

        if cursor.rowcount == 0:
            return phan_hoi_loi(
                "Khong tim thay tai khoan dang bi khoa", 404
            )

        connection.commit()

        return phan_hoi_thanh_cong(
            "Mo khoa tai khoan thanh cong"
        )

    except Exception as error:
        if connection:
            connection.rollback()

        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


# =====================================================
# 13. API NHAT KY
# =====================================================

@app.route("/api/nhat-ky", methods=["GET"])
@yeu_cau_quyen("Admin")
def danh_sach_nhat_ky():
    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        sql = """
            SELECT A.LogID, A.MaNguoiDung, N.HoTen,
                   A.HanhDong, A.BangTacDong, A.MaBanGhi,
                   A.NoiDung, A.ThoiGian
            FROM dbo.ACTIVITY_LOGS A
            LEFT JOIN dbo.NGUOI_DUNG N
                ON A.MaNguoiDung = N.MaNguoiDung
            WHERE 1 = 1
        """

        params = []

        hanh_dong = request.args.get("hanh_dong")

        if hanh_dong:
            sql += " AND A.HanhDong LIKE ?"
            params.append(f"%{hanh_dong}%")

        sql += " ORDER BY A.ThoiGian DESC"

        cursor.execute(sql, params)

        return phan_hoi_thanh_cong(
            data=convert_to_json(cursor)
        )

    except Exception as error:
        return phan_hoi_loi(str(error), 500)

    finally:
        dong_ket_noi_an_toan(cursor, connection)


# =====================================================
# 14. XU LY LOI
# =====================================================

@app.errorhandler(404)
def loi_404(error):
    if request.path.startswith("/api/"):
        return phan_hoi_loi(
            "Khong tim thay duong dan API", 404
        )

    return "Khong tim thay trang", 404


@app.errorhandler(405)
def loi_405(error):
    return phan_hoi_loi(
        "Phuong thuc HTTP khong duoc ho tro", 405
    )


@app.errorhandler(500)
def loi_500(error):
    return phan_hoi_loi(
        "Da xay ra loi phia may chu", 500
    )


# =====================================================
# 15. CHAY BACKEND
# =====================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=True
    )

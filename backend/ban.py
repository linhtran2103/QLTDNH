import socket
import base64
from decimal import Decimal
from io import BytesIO

import qrcode
from flask import Blueprint, current_app, render_template, request, url_for
from itsdangerous import BadSignature, URLSafeSerializer

from database.db import convert_to_json, db_cursor
from backend.middleware.auth_middleware import (
    yeu_cau_dang_nhap,
    yeu_cau_vai_tro,
)
from backend.utils.response import thanh_cong, that_bai
from backend.utils.validators import (
    chuoi,
    doc_gia,
    doc_so_nguyen,
    ghi_nhat_ky,
    lay_json,
)


ban_bp = Blueprint("ban", __name__)
TRANG_THAI_DON = {"moi", "dang_chuan_bi", "hoan_thanh", "huy"}


def _tao_token_ban(ma_ban):
    serializer = URLSafeSerializer(current_app.config["SECRET_KEY"], salt="table-qr")
    return serializer.dumps({"MaBan": ma_ban})


def _token_ban_hop_le(ma_ban, token):
    serializer = URLSafeSerializer(current_app.config["SECRET_KEY"], salt="table-qr")
    try:
        return serializer.loads(token or "") == {"MaBan": ma_ban}
    except BadSignature:
        return False

def _lay_ip_lan():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))  # không gửi dữ liệu, chỉ để biết IP đang dùng
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()
def _tao_qr(url):
    image = qrcode.make(url)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@ban_bp.route("/order/<int:ma_ban>")
def trang_dat_mon(ma_ban):
    return render_template(
        "order.html", ma_ban=ma_ban, qr_token=request.args.get("token", "")
    )


@ban_bp.route("/tables")
def trang_quan_ly_ban():
    return render_template("tables.html")


@ban_bp.route("/orders")
def trang_quan_ly_don():
    return render_template("orders.html")


@ban_bp.route("/api/public/ban/<int:ma_ban>")
def thong_tin_ban(ma_ban):
    if not _token_ban_hop_le(ma_ban, request.args.get("token")):
        return that_bai("Mã QR bàn không hợp lệ", 403)

    with db_cursor() as cursor:
        cursor.execute(
            "SELECT MaBan, TenBan FROM BAN_AN WHERE MaBan = ? AND TrangThai = 1",
            (ma_ban,),
        )
        rows = convert_to_json(cursor)
    if not rows:
        return that_bai("Bàn không tồn tại hoặc đang ngừng phục vụ", 404)
    return thanh_cong(data=rows[0])


@ban_bp.route("/api/public/menu")
def thuc_don_con_mon():
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT M.MaMonAn, M.MaMon, M.TenMonAn, M.Gia, M.MoTa, M.HinhAnh,
                   M.MaDanhMuc, D.TenDanhMuc
            FROM MON_AN M
            INNER JOIN DANH_MUC D ON D.MaDanhMuc = M.MaDanhMuc
            WHERE M.ConKinhDoanh = 1 AND D.TrangThai = 1
            ORDER BY D.ThuTuHienThi, D.MaDanhMuc, M.TenMonAn
            """
        )
        return thanh_cong(data=convert_to_json(cursor))


@ban_bp.route("/api/public/don-hang", methods=["POST"])
def tao_don_dat_mon():
    data = lay_json()
    ma_ban = doc_so_nguyen(data.get("MaBan"))
    qr_token = data.get("QrToken")
    items = data.get("ChiTiet")
    if ma_ban is None or not isinstance(items, list) or not items or len(items) > 30:
        return that_bai("Thông tin bàn hoặc món đặt không hợp lệ")
    if not _token_ban_hop_le(ma_ban, qr_token):
        return that_bai("Mã QR bàn không hợp lệ", 403)

    note = chuoi(data.get("GhiChu"))
    if note and len(note) > 500:
        return that_bai("Ghi chú không được vượt quá 500 ký tự")

    quantities = {}
    item_notes = {}
    for item in items:
        if not isinstance(item, dict):
            return that_bai("Chi tiết món đặt không hợp lệ")
        ma_mon_an = doc_so_nguyen(item.get("MaMonAn"))
        quantity = doc_so_nguyen(item.get("SoLuong"))
        item_note = chuoi(item.get("GhiChu"))
        if ma_mon_an is None or quantity is None or not 1 <= quantity <= 50:
            return that_bai("Món đặt hoặc số lượng không hợp lệ")
        if item_note and len(item_note) > 250:
            return that_bai("Ghi chú món không được vượt quá 250 ký tự")
        quantities[ma_mon_an] = quantities.get(ma_mon_an, 0) + quantity
        if quantities[ma_mon_an] > 50:
            return that_bai("Mỗi món chỉ được đặt tối đa 50 phần")
        if item_note:
            item_notes[ma_mon_an] = item_note

    with db_cursor(commit=True) as cursor:
        cursor.execute(
            "SELECT TenBan FROM BAN_AN WHERE MaBan = ? AND TrangThai = 1",
            (ma_ban,),
        )
        table = cursor.fetchone()
        if table is None:
            return that_bai("Bàn không tồn tại hoặc đang ngừng phục vụ", 404)

        order_items = []
        total = Decimal("0")
        for ma_mon_an, quantity in quantities.items():
            cursor.execute(
                """
                SELECT M.Gia
                FROM MON_AN M
                INNER JOIN DANH_MUC D ON D.MaDanhMuc = M.MaDanhMuc
                WHERE M.MaMonAn = ? AND M.ConKinhDoanh = 1 AND D.TrangThai = 1
                """,
                (ma_mon_an,),
            )
            row = cursor.fetchone()
            if row is None:
                return that_bai(f"Món mã {ma_mon_an} không có sẵn", 400)
            price = doc_gia(row[0])
            if price is None:
                return that_bai(f"Món mã {ma_mon_an} chưa có giá hợp lệ", 400)
            order_items.append(
                (ma_mon_an, quantity, price, item_notes.get(ma_mon_an))
            )
            total += price * quantity

        cursor.execute(
            """
            INSERT INTO DON_HANG (MaBan, GhiChu, TongTien)
            OUTPUT INSERTED.MaDonHang
            VALUES (?, ?, ?)
            """,
            (ma_ban, note, total),
        )
        ma_don_hang = cursor.fetchone()[0]

        for ma_mon_an, quantity, price, item_note in order_items:
            cursor.execute(
                """
                INSERT INTO CHI_TIET_DON_HANG
                    (MaDonHang, MaMonAn, SoLuong, DonGia, GhiChu)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ma_don_hang, ma_mon_an, quantity, price, item_note),
            )

        cursor.execute(
            """
            INSERT INTO ACTIVITY_LOGS
                (MaNguoiDung, HanhDong, BangTacDong, MaBanGhi, NoiDung, ThoiGian)
            VALUES (NULL, ?, ?, ?, ?, GETDATE())
            """,
            ("Khách gửi đơn", "DON_HANG", ma_don_hang,
             f"Đơn mới từ {table[0]}"),
        )

    return thanh_cong(
        "Đã gửi đơn đến nhà hàng",
        data={"MaDonHang": ma_don_hang, "TongTien": str(total)},
        status=201,
    )


@ban_bp.route("/api/ban", methods=["GET"])
@yeu_cau_vai_tro("admin", "manager")
def danh_sach_ban():
    with db_cursor() as cursor:
        cursor.execute(
            "SELECT MaBan, TenBan, TrangThai FROM BAN_AN ORDER BY MaBan"
        )
        tables = convert_to_json(cursor)

    base_url = current_app.config["PUBLIC_BASE_URL"]
    if not base_url or "127.0.0.1" in base_url or "localhost" in base_url:
        port = request.host.split(":")[-1] if ":" in request.host else "5000"
        base_url = f"http://{_lay_ip_lan()}:{port}"

    for table in tables:
        token = _tao_token_ban(table["MaBan"])
        path = url_for(
            "ban.trang_dat_mon",
            ma_ban=table["MaBan"],
            token=token,
            _external=False,
        )
        order_url = f"{base_url}{path}"
        table["UrlDatMon"] = order_url
        table["QRCode"] = _tao_qr(order_url)
    return thanh_cong(data=tables)


@ban_bp.route("/api/ban/<int:ma_ban>", methods=["PUT"])
@yeu_cau_vai_tro("admin", "manager")
def cap_nhat_ten_ban(ma_ban):
    ten_ban = chuoi(lay_json().get("TenBan"))
    if not ten_ban or len(ten_ban) > 50:
        return that_bai("Tên bàn phải có từ 1 đến 50 ký tự")

    with db_cursor(commit=True) as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM BAN_AN WHERE TenBan = ? AND MaBan <> ?",
            (ten_ban, ma_ban),
        )
        if cursor.fetchone()[0]:
            return that_bai("Tên bàn đã được sử dụng")
        cursor.execute(
            "UPDATE BAN_AN SET TenBan = ? WHERE MaBan = ?",
            (ten_ban, ma_ban),
        )
        if cursor.rowcount == 0:
            return that_bai("Không tìm thấy bàn", 404)
        ghi_nhat_ky(cursor, "Đổi tên", "BAN_AN", ma_ban, ten_ban)

    return thanh_cong("Đã cập nhật tên bàn")


@ban_bp.route("/api/don-hang", methods=["GET"])
@yeu_cau_dang_nhap
def danh_sach_don_hang():
    status = chuoi(request.args.get("trang_thai"))
    if status and status not in TRANG_THAI_DON:
        return that_bai("Trạng thái đơn không hợp lệ")

    sql = """
        SELECT TOP (100) O.MaDonHang, O.MaBan, B.TenBan, O.TrangThai,
               O.GhiChu, O.TongTien, O.NgayTao
        FROM DON_HANG O
        INNER JOIN BAN_AN B ON B.MaBan = O.MaBan
        WHERE 1 = 1
    """
    params = []
    if status:
        sql += " AND O.TrangThai = ?"
        params.append(status)

    with db_cursor() as cursor:
        cursor.execute(sql + " ORDER BY O.NgayTao DESC", params)
        orders = convert_to_json(cursor)
        if not orders:
            return thanh_cong(data=[])

        order_ids = [order["MaDonHang"] for order in orders]
        placeholders = ",".join("?" for _ in order_ids)
        cursor.execute(
            f"""
            SELECT D.MaDonHang, D.MaMonAn, M.TenMonAn, D.SoLuong,
                   D.DonGia, D.GhiChu
            FROM CHI_TIET_DON_HANG D
            INNER JOIN MON_AN M ON M.MaMonAn = D.MaMonAn
            WHERE D.MaDonHang IN ({placeholders})
            ORDER BY D.MaChiTiet
            """,
            order_ids,
        )
        details = convert_to_json(cursor)

    details_by_order = {order_id: [] for order_id in order_ids}
    for detail in details:
        details_by_order[detail["MaDonHang"]].append(detail)
    for order in orders:
        order["ChiTiet"] = details_by_order[order["MaDonHang"]]
    return thanh_cong(data=orders)


@ban_bp.route("/api/don-hang/<int:ma_don_hang>/trang-thai", methods=["PUT"])
@yeu_cau_dang_nhap
def cap_nhat_trang_thai_don(ma_don_hang):
    status = chuoi(lay_json().get("TrangThai"))
    if status not in {"dang_chuan_bi", "hoan_thanh", "huy"}:
        return that_bai("Trạng thái mới không hợp lệ")

    with db_cursor(commit=True) as cursor:
        cursor.execute(
            "UPDATE DON_HANG SET TrangThai = ? WHERE MaDonHang = ?",
            (status, ma_don_hang),
        )
        if cursor.rowcount == 0:
            return that_bai("Không tìm thấy đơn hàng", 404)
        ghi_nhat_ky(cursor, "Cập nhật trạng thái", "DON_HANG", ma_don_hang, status)
    return thanh_cong("Đã cập nhật trạng thái đơn hàng")

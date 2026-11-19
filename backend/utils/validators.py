from datetime import date
from decimal import Decimal, InvalidOperation

from flask import g, request


def lay_json():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def chuoi(value):
    """Cắt khoảng trắng; chuỗi rỗng -> None."""
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def doc_gia(value):
    """Chuyển về Decimal >= 0; sai định dạng -> None."""
    try:
        gia = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return gia if gia.is_finite() and gia >= 0 else None


def doc_so_nguyen(value, mac_dinh=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return mac_dinh


def doc_ngay(value):
    """'YYYY-MM-DD' -> date; rỗng -> None; sai -> ValueError."""
    value = chuoi(value)
    return date.fromisoformat(value[:10]) if value else None


def chuyen_bool(value):
    """'true'/'1' -> 1, 'false'/'0' -> 0, còn lại -> None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    value = str(value).strip().lower()
    if value in ("1", "true", "yes"):
        return 1
    if value in ("0", "false", "no"):
        return 0
    return None


def gioi_han_dong(mac_dinh=200):
    return min(max(doc_so_nguyen(request.args.get("limit"), mac_dinh), 1), 1000)


def ghi_nhat_ky(cursor, hanh_dong, bang, ma_ban_ghi=None, noi_dung=None):
    """Ghi ACTIVITY_LOGS cùng transaction với thao tác chính."""
    cursor.execute(
        """
        INSERT INTO ACTIVITY_LOGS
            (MaNguoiDung, HanhDong, BangTacDong, MaBanGhi, NoiDung, ThoiGian)
        VALUES (?, ?, ?, ?, ?, GETDATE())
        """,
        (getattr(g, "ma_nguoi_dung", None), hanh_dong, bang, ma_ban_ghi, noi_dung),
    )


def ton_tai(cursor, bang, cot, gia_tri, them=""):
    """Kiểm tra bản ghi có tồn tại; bang/cot chỉ được dùng từ code."""
    cursor.execute(f"SELECT COUNT(*) FROM {bang} WHERE {cot} = ? {them}",
                   (gia_tri,))
    return cursor.fetchone()[0] > 0

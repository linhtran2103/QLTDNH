import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(ENV_FILE, override=True)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("Chưa cấu hình SECRET_KEY trong file backend/.env")

TOKEN_MAX_AGE = 8 * 60 * 60
VAI_TRO_MAC_DINH = "NhanVien"
VAI_TRO_ADMIN = "admin"
VAI_TRO_QUAN_LY = "manager"
VAI_TRO_NHAN_VIEN = "NhanVien"
VAI_TRO_HOP_LE = {
    VAI_TRO_ADMIN,
    VAI_TRO_QUAN_LY,
    VAI_TRO_NHAN_VIEN,
}

THU_MUC_ANH = PROJECT_ROOT / "frontend" / "static" / "uploads"
DUNG_LUONG_ANH_TOI_DA = 5 * 1024 * 1024
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")

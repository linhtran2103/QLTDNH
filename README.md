# QUẢN LÝ THỰC ĐƠN NHÀ HÀNG (QLTDNH)

Hệ thống quản lý món ăn và danh mục cho nhà hàng, có đăng nhập, phân quyền và nhật ký hoạt động.

## Công nghệ
- Python, Flask, flask-cors
- Microsoft SQL Server + pyodbc
- HTML, CSS, JavaScript, Bootstrap 5

## Cấu trúc thư mục
- `backend/`: ứng dụng Flask theo module (`auth.py`, `mon_an.py`, `danh_muc.py`,
  `nguoi_dung.py`, `nhat_ky.py`, `thong_ke.py`, `ban.py`); cấu hình và xác thực
  nằm trong `config.py` và `middleware/`; response/validator dùng chung ở `utils/`.
  `app.py` là điểm khởi chạy, `.env` chứa cấu hình môi trường và `create_admin.py`
  tạo tài khoản Admin đầu tiên.
- `frontend/`: `templates/` (HTML), `static/` (CSS, JS, ảnh; ảnh món ăn tải lên nằm ở `static/uploads/`).
- `database/`: `db.py` (kết nối SQL Server) và `backup/QLTDNH.bak` (bản sao lưu CSDL).

## Cài đặt
1. Cài Python 3, SQL Server và **ODBC Driver 17 for SQL Server**.
2. Khôi phục `database/backup/QLTDNH.bak` vào SQL Server.
3. Chạy lần lượt `database/migrations/001_tables_and_orders.sql` và
   `database/migrations/002_customer_order_access.sql` trên database QLTDNH.
   Migration đầu tạo 6 bàn/bảng đơn và chuẩn hóa vai trò; migration thứ hai
   thêm trường lưu hash để khách chỉ sửa/xóa đơn của mình bằng token riêng.
4. Cài thư viện:
   ```powershell
   pip install -r requirements.txt
   ```
5. Sửa `backend/.env` cho đúng máy của bạn:
   ```
   DB_DRIVER=ODBC Driver 17 for SQL Server
   DB_SERVER=TEN_MAY\TEN_INSTANCE
   DB_NAME=TEN_DATABASE_SAU_KHI_RESTORE
   DB_TRUSTED_CONNECTION=yes
   SECRET_KEY=chuoi-bi-mat-dai-va-ngau-nhien
   # Để khách dùng điện thoại quét QR trong cùng mạng LAN:
   HOST=0.0.0.0
   PUBLIC_BASE_URL=http://DIA_CHI_IP_LAN_CUA_MAY:5000
   ```
   Nếu dùng đăng nhập SQL: đặt `DB_TRUSTED_CONNECTION=no` và thêm `DB_USERNAME`, `DB_PASSWORD`.

## Chạy chương trình
```powershell
cd backend
python app.py
hoặc 
python -m backend.app
```
- Giao diện: http://127.0.0.1:5000 (tự chuyển sang `/login` nếu chưa đăng nhập)
- Kiểm tra kết nối CSDL: http://127.0.0.1:5000/api/health
- Admin tạo tài khoản ở `/users`; quản lý in QR ở `/tables`; admin, quản lý và
  nhân viên xử lý đơn ở `/orders`.
- Khi khách dùng điện thoại trong cùng mạng LAN, đặt `HOST=0.0.0.0` và
  `PUBLIC_BASE_URL=http://<IP-máy-chạy>:5000` trong `.env` để QR trỏ tới địa chỉ
  mà điện thoại truy cập được. Giữ `FLASK_DEBUG=0` khi mở server ra mạng.

Tạo tài khoản Admin đầu tiên (nếu CSDL chưa có):
```powershell
python backend/create_admin.py
```

## Cơ sở dữ liệu
`NGUOI_DUNG`, `LOGIN_HISTORY`, `ACTIVITY_LOGS`, `DANH_MUC`, `MON_AN`, `LICH_SU_GIA`,
`DAC_DIEM`, `MON_AN_DAC_DIEM`, `THUC_DON`, `CHI_TIET_THUC_DON`, `BAN_AN`,
`DON_HANG`, `CHI_TIET_DON_HANG`.

> Lưu ý: file `database/backup/QLTDNH.bak` là bản cũ (chỉ 4 bảng). Hãy sao lưu lại CSDL hiện tại và ghi đè file này.

## Phân quyền
- Chỉ có ba vai trò: `admin`, `manager` (quản lý), `NhanVien` (nhân viên).
- Admin quản lý tài khoản và nhật ký; quản lý sửa thực đơn, món, danh mục và mã QR;
  nhân viên xem thực đơn và xử lý đơn gọi món.
- Khách quét QR tại `/order/<mã-bàn>` để gửi món; chưa tích hợp thanh toán.
- Tài khoản có vai trò khách hàng cũ được khóa, không xóa cứng khỏi cơ sở dữ liệu.
- Admin tạo tài khoản quản lý/nhân viên tại `/users`; không chia sẻ mật khẩu qua mã QR.

## Các API chính
| Nhóm | Đường dẫn |
|---|---|
| Đăng nhập / đăng xuất | `POST /api/dang-nhap`, `POST /api/dang-xuat` |
| Món ăn | `/api/mon-an`, `/api/mon-an/<id>`, `/api/mon-an/<id>/dac-diem` |
| Danh mục | `/api/danh-muc` |
| Thực đơn | `/api/thuc-don`, `/api/thuc-don/<id>/mon-an` |
| Đặc điểm | `/api/dac-diem` |
| Lịch sử giá | `GET /api/lich-su-gia?ma_mon_an=` (tự ghi khi sửa giá món) |
| Người dùng (admin) | `/api/nguoi-dung` |
| Nhật ký (admin) | `GET /api/nhat-ky`, `GET /api/lich-su-dang-nhap` |
| Bàn và QR (admin/quản lý) | `GET /api/ban`, `PUT /api/ban/<id>` |
| Đặt món công khai qua QR | `GET /api/public/menu`, `POST /api/public/don-hang` |
| Đơn gọi món (nhân sự đã đăng nhập) | `/api/don-hang`, `/api/don-hang/<id>/trang-thai` |

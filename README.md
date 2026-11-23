# QUẢN LÝ THỰC ĐƠN NHÀ HÀNG (QLTDNH)

## 1. Giới thiệu

QLTDNH (Quản lý thực đơn nhà hàng) là hệ thống hỗ trợ quản lý hoạt động thực đơn và gọi món trong nhà hàng.

Hệ thống cung cấp các chức năng quản lý tài khoản, phân quyền người dùng, quản lý món ăn, danh mục, thực đơn, bàn ăn, mã QR, đơn gọi món và nhật ký hoạt động.

Khách hàng có thể quét mã QR tại bàn để xem thực đơn và gửi yêu cầu gọi món. Nhân viên nhà hàng có thể tiếp nhận và xử lý đơn hàng trên hệ thống.

## 2. Công nghệ sử dụng

### Backend
- Python 3
- Flask
- Flask-CORS
- pyodbc
- Microsoft SQL Server

### Frontend
- HTML5
- CSS3
- JavaScript
- Bootstrap 5

### Công cụ và môi trường
- Visual Studio Code
- Microsoft SQL Server Management Studio (SSMS)
- ODBC Driver 17 for SQL Server
- Git và GitHub

## 3. Cấu trúc thư mục

```text
QLTDNH/
│
├── backend/
│   ├── app.py
│   ├── auth.py
│   ├── mon_an.py
│   ├── danh_muc.py
│   ├── nguoi_dung.py
│   ├── nhat_ky.py
│   ├── thong_ke.py
│   ├── ban.py
│   ├── config.py
│   ├── middleware/
│   ├── utils/
│   └── .env
│
├── frontend/
│   ├── templates/
│   └── static/
│       ├── css/
│       ├── js/
│       ├── images/
│       └── uploads/
│
├── database/
│   ├── db.py
│   ├── backup/
│   │   └── QLTDNH.bak
│   └── migrations/
│       ├── 001_tables_and_orders.sql
│       └── 002_customer_order_access.sql
│
├── requirements.txt
└── README.md
```

**Mô tả các thư mục chính:**

- `backend/`: Chứa mã nguồn Flask, các module xử lý nghiệp vụ, cấu hình và xác thực.
- `backend/middleware/`: Chứa các thành phần trung gian phục vụ xác thực và phân quyền.
- `backend/utils/`: Chứa các hàm dùng chung như xử lý phản hồi và kiểm tra dữ liệu.
- `frontend/templates/`: Chứa các trang giao diện HTML.
- `frontend/static/`: Chứa CSS, JavaScript, hình ảnh và ảnh món ăn tải lên.
- `database/`: Chứa mã kết nối SQL Server, bản sao lưu và các file migration.

Một số file quan trọng:
- `backend/app.py`: Điểm khởi chạy ứng dụng Flask.
- `backend/create_admin.py`: Công cụ tạo tài khoản Admin đầu tiên.
- `backend/.env`: Chứa các thông tin cấu hình môi trường.
- `database/db.py`: Xử lý kết nối SQL Server.

## 4. Chức năng hệ thống

### 4.1. Quản lý tài khoản

- Đăng nhập và đăng xuất.
- Quản lý danh sách tài khoản nhân sự.
- Tạo tài khoản Admin, Quản lý và Nhân viên.
- Cập nhật thông tin người dùng.
- Khóa tài khoản.
- Mở khóa tài khoản.
- Xóa hẳn tài khoản khỏi hệ thống.
- Lưu nhật ký hoạt động và lịch sử đăng nhập.

Khi xóa hẳn tài khoản, hệ thống bỏ liên kết người dùng khỏi các dữ liệu lịch sử liên quan để giữ lại đơn hàng và lịch sử nghiệp vụ.

### 4.2. Quản lý món ăn

- Xem danh sách món ăn.
- Quản lý thông tin món ăn.
- Quản lý trạng thái kinh doanh của món ăn.
- Quản lý đặc điểm món ăn.
- Theo dõi lịch sử thay đổi giá.
- Ngừng kinh doanh món ăn khi cần thiết.

### 4.3. Quản lý danh mục

- Xem danh sách danh mục.
- Quản lý danh mục món ăn.
- Theo dõi trạng thái danh mục.

### 4.4. Quản lý thực đơn

- Quản lý thực đơn nhà hàng.
- Quản lý danh sách món ăn thuộc thực đơn.

### 4.5. Quản lý bàn và mã QR

- Xem danh sách bàn ăn.
- Quản lý thông tin bàn.
- Tạo và sử dụng mã QR cho từng bàn.
- Hỗ trợ khách hàng truy cập thực đơn thông qua mã QR.

### 4.6. Quản lý đơn gọi món

- Khách hàng quét mã QR để xem thực đơn.
- Khách hàng gửi yêu cầu gọi món.
- Nhân viên xem danh sách đơn hàng.
- Nhân viên xử lý và cập nhật trạng thái đơn.
- Lưu thông tin đơn hàng và chi tiết món ăn.

### 4.7. Nhật ký và thống kê

- Lưu nhật ký hoạt động của người dùng.
- Theo dõi lịch sử đăng nhập.
- Hỗ trợ theo dõi lịch sử giá món ăn.
- Cung cấp module thống kê của hệ thống.

## 5. Phân quyền người dùng

Hệ thống sử dụng ba vai trò chính:

| Vai trò | Quyền hạn |
|---|---|
| Admin | Quản lý tài khoản, nhật ký và các chức năng quản trị hệ thống. |
| Quản lý (manager) | Quản lý món ăn, danh mục, thực đơn và mã QR; tham gia xử lý đơn hàng. |
| Nhân viên (NhanVien) | Xem thực đơn và tiếp nhận, xử lý đơn gọi món. |

**Khách hàng:**

- Không cần đăng nhập tài khoản nhân sự.
- Quét mã QR tại bàn để truy cập thực đơn.
- Gửi yêu cầu gọi món thông qua giao diện công khai.
- Chưa tích hợp chức năng thanh toán trực tuyến.

## 6. Yêu cầu cài đặt

Trước khi chạy dự án, cần cài đặt:

1. Python 3.
2. Microsoft SQL Server.
3. SQL Server Management Studio (SSMS).
4. ODBC Driver 17 for SQL Server.
5. Visual Studio Code (khuyến nghị).

## 7. Hướng dẫn cài đặt

### Bước 1. Lấy mã nguồn

Clone dự án từ GitHub:

```powershell
git clone https://github.com/linhtran2103/QLTDNH.git
```

Di chuyển vào thư mục dự án:

```powershell
cd QLTDNH
```

### Bước 2. Tạo môi trường ảo

```powershell
python -m venv .venv
```

Kích hoạt môi trường ảo trên Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Nếu PowerShell chặn việc chạy script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Sau đó kích hoạt lại môi trường ảo.

### Bước 3. Cài đặt thư viện

```powershell
pip install -r requirements.txt
```

### Bước 4. Khôi phục cơ sở dữ liệu

1. Mở SQL Server Management Studio.
2. Kết nối tới SQL Server.
3. Khôi phục file `database/backup/QLTDNH.bak`.
4. Đặt tên database sau khi khôi phục là `QLTDNH` hoặc cập nhật đúng tên database trong file cấu hình.

### Bước 5. Chạy các file migration

Trên database QLTDNH, chạy lần lượt:

```text
database/migrations/001_tables_and_orders.sql
database/migrations/002_customer_order_access.sql
```

Mô tả:
- Migration `001_tables_and_orders.sql`: Tạo và cập nhật cấu trúc phục vụ chức năng bàn và đơn hàng, đồng thời chuẩn hóa vai trò.
- Migration `002_customer_order_access.sql`: Bổ sung trường lưu hash để hỗ trợ khách hàng quản lý đơn hàng của mình bằng token riêng.

### Bước 6. Cấu hình kết nối SQL Server

Mở file `backend/.env` và chỉnh sửa thông tin cho phù hợp với máy tính đang chạy:

```env
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_SERVER=TEN_MAY\TEN_INSTANCE
DB_NAME=QLTDNH
DB_TRUSTED_CONNECTION=yes

SECRET_KEY=chuoi-bi-mat-dai-va-ngau-nhien

HOST=0.0.0.0
PUBLIC_BASE_URL=http://DIA_CHI_IP_LAN_CUA_MAY:5000
```

Trong đó:
- `DB_DRIVER`: Tên ODBC Driver.
- `DB_SERVER`: Tên máy hoặc tên instance SQL Server.
- `DB_NAME`: Tên database.
- `DB_TRUSTED_CONNECTION`: Sử dụng xác thực Windows nếu đặt `yes`.
- `SECRET_KEY`: Chuỗi bí mật dùng cho ứng dụng.
- `HOST`: Địa chỉ Flask lắng nghe kết nối.
- `PUBLIC_BASE_URL`: Địa chỉ mà điện thoại có thể truy cập khi quét mã QR.

Nếu sử dụng tài khoản SQL Server, cấu hình:

```env
DB_TRUSTED_CONNECTION=no
DB_USERNAME=TEN_TAI_KHOAN_SQL
DB_PASSWORD=MAT_KHAU_SQL
```

Không đưa file `.env` chứa mật khẩu và thông tin bí mật lên GitHub.

## 8. Hướng dẫn chạy chương trình

Mở Terminal tại thư mục dự án và kích hoạt môi trường ảo.

Di chuyển vào thư mục backend:

```powershell
cd backend
```

Chạy ứng dụng:

```powershell
python app.py
```

Hoặc chạy từ thư mục gốc dự án:

```powershell
python -m backend.app
```

Sau khi chạy thành công, truy cập:

| Nội dung | Địa chỉ |
|---|---|
| Giao diện hệ thống | http://127.0.0.1:5000 |
| Kiểm tra kết nối database | http://127.0.0.1:5000/api/health |
| Quản lý tài khoản | http://127.0.0.1:5000/users |
| Quản lý bàn và QR | http://127.0.0.1:5000/tables |
| Quản lý đơn hàng | http://127.0.0.1:5000/orders |

Nếu chưa đăng nhập, hệ thống sẽ chuyển tới trang đăng nhập.

### Tạo tài khoản Admin đầu tiên

Nếu database chưa có tài khoản Admin, chạy:

```powershell
python backend/create_admin.py
```

Thực hiện thao tác này từ thư mục gốc dự án.

## 9. Sử dụng hệ thống qua điện thoại bằng mã QR

Để khách hàng có thể quét mã QR bằng điện thoại trong cùng mạng LAN:

1. Đặt `HOST=0.0.0.0` trong file `.env`.
2. Xác định địa chỉ IP LAN của máy chạy Flask.
3. Cấu hình `PUBLIC_BASE_URL`:

```env
PUBLIC_BASE_URL=http://IP_MAY_CHU:5000
```

Ví dụ:

```env
PUBLIC_BASE_URL=http://192.168.1.100:5000
```

4. Cho phép cổng 5000 qua Windows Firewall.
5. Đảm bảo điện thoại và máy chủ có thể kết nối với nhau qua mạng.

Khi mở ứng dụng ra mạng, cần giữ chế độ debug tắt (`FLASK_DEBUG=0`) và không chia sẻ các thông tin bí mật trong file cấu hình.

## 10. Cơ sở dữ liệu

Các bảng chính của hệ thống:

| Bảng | Chức năng |
|---|---|
| `NGUOI_DUNG` | Lưu thông tin tài khoản người dùng. |
| `LOGIN_HISTORY` | Lưu lịch sử đăng nhập. |
| `ACTIVITY_LOGS` | Lưu nhật ký hoạt động. |
| `DANH_MUC` | Quản lý danh mục món ăn. |
| `MON_AN` | Lưu thông tin món ăn. |
| `LICH_SU_GIA` | Lưu lịch sử thay đổi giá. |
| `DAC_DIEM` | Lưu các đặc điểm món ăn. |
| `MON_AN_DAC_DIEM` | Liên kết món ăn với đặc điểm. |
| `THUC_DON` | Quản lý thực đơn. |
| `CHI_TIET_THUC_DON` | Chi tiết các món trong thực đơn. |
| `BAN_AN` | Quản lý bàn ăn. |
| `DON_HANG` | Lưu thông tin đơn hàng. |
| `CHI_TIET_DON_HANG` | Lưu các món thuộc từng đơn hàng. |

**Lưu ý về dữ liệu:**

File `database/backup/QLTDNH.bak` có thể là bản sao lưu cũ. Cần sao lưu lại database hiện tại sau khi cập nhật cấu trúc và dữ liệu để tránh mất các thay đổi mới.

## 11. Các API chính

| Nhóm chức năng | Phương thức và đường dẫn |
|---|---|
| Đăng nhập | `POST /api/dang-nhap` |
| Đăng xuất | `POST /api/dang-xuat` |
| Món ăn | `/api/mon-an` |
| Chi tiết món ăn | `/api/mon-an/<id>` |
| Đặc điểm món ăn | `/api/mon-an/<id>/dac-diem` |
| Danh mục | `/api/danh-muc` |
| Thực đơn | `/api/thuc-don` |
| Món trong thực đơn | `/api/thuc-don/<id>/mon-an` |
| Đặc điểm | `/api/dac-diem` |
| Lịch sử giá | `GET /api/lich-su-gia?ma_mon_an=` |
| Danh sách người dùng | `GET /api/nguoi-dung` |
| Thêm người dùng | `POST /api/nguoi-dung` |
| Sửa người dùng | `PUT /api/nguoi-dung/<id>` |
| Khóa người dùng | `DELETE /api/nguoi-dung/<id>` |
| Mở khóa người dùng | `PUT /api/nguoi-dung/<id>/mo-khoa` |
| Xóa hẳn người dùng | `DELETE /api/nguoi-dung/<id>/xoa-han` |
| Nhật ký hoạt động | `GET /api/nhat-ky` |
| Lịch sử đăng nhập | `GET /api/lich-su-dang-nhap` |
| Danh sách bàn | `GET /api/ban` |
| Cập nhật bàn | `PUT /api/ban/<id>` |
| Thực đơn công khai | `GET /api/public/menu` |
| Gửi đơn hàng qua QR | `POST /api/public/don-hang` |
| Đơn hàng nhân sự | `/api/don-hang` |
| Cập nhật trạng thái đơn | `/api/don-hang/<id>/trang-thai` |

Các API quản trị yêu cầu xác thực và phân quyền phù hợp.

## 12. Lưu ý khi sử dụng

- Cần cấu hình đúng SQL Server trước khi chạy ứng dụng.
- Không chia sẻ tài khoản Admin và mật khẩu quản trị.
- Không đưa file `.env`, mật khẩu hoặc thông tin kết nối database lên GitHub.
- Nên sao lưu database trước khi chạy migration hoặc thao tác xóa dữ liệu.
- Xóa hẳn tài khoản là thao tác không thể khôi phục tài khoản đã xóa; dữ liệu nghiệp vụ liên quan được giữ lại theo xử lý của backend.
- Chức năng thanh toán trực tuyến chưa được tích hợp.

## 13. Tác giả và mã nguồn

**Tên dự án:** Quản lý thực đơn nhà hàng (QLTDNH)

**GitHub:** https://github.com/linhtran2103/QLTDNH
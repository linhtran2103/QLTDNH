\# QUẢN LÝ THỰC ĐƠN NHÀ HÀNG (QLTDNH)



\## 1. Giới thiệu

QLTDNH là hệ thống quản lý thực đơn nhà hàng, được xây dựng nhằm hỗ trợ quản lý món ăn, danh mục món ăn, tài khoản người dùng và theo dõi hoạt động của hệ thống.



\## 2. Công nghệ sử dụng

\- Ngôn ngữ: Python

\- Backend: Flask

\- Cơ sở dữ liệu: Microsoft SQL Server

\- Kết nối cơ sở dữ liệu: pyodbc

\- Giao diện: HTML, CSS, JavaScript, Bootstrap



\## 3. Cấu trúc thư mục

\- `backend/`: Mã nguồn Flask và cấu hình kết nối cơ sở dữ liệu.

\- `frontend/`: Giao diện HTML, CSS, JavaScript.

\- `database/`: Các file SQL và bản sao lưu cơ sở dữ liệu.

\- `docs/`: Tài liệu và hình ảnh minh họa dự án.



\## 4. Yêu cầu cài đặt

\- Python 3

\- Microsoft SQL Server

\- ODBC Driver 17 for SQL Server



\## 5. Cấu hình cơ sở dữ liệu

Cấu hình trong file `backend/.env`:

\- DB\_SERVER: localhost\\CSDLPTNHOM5

\- DB\_NAME: QLTDNH

\- DB\_DRIVER: ODBC Driver 17 for SQL Server

\- DB\_TRUSTED\_CONNECTION: yes



\## 6. Cài đặt thư viện

Mở terminal tại thư mục backend và chạy:



```powershell

pip install flask flask-cors python-dotenv pyodbc

```



\## 7. Khởi chạy chương trình



```powershell

cd backend

python app.py

```



Truy cập: http://127.0.0.1:5000



Kiểm tra kết nối cơ sở dữ liệu: http://127.0.0.1:5000/api/health



\## 8. Sao lưu cơ sở dữ liệu

File sao lưu cơ sở dữ liệu được lưu tại `database/backup/QLTDNH.bak`.




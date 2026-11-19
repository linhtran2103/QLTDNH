SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF OBJECT_ID(N'dbo.BAN_AN', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.BAN_AN (
        MaBan INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        TenBan NVARCHAR(50) NOT NULL UNIQUE,
        TrangThai BIT NOT NULL CONSTRAINT DF_BAN_AN_TrangThai DEFAULT 1,
        NgayTao DATETIME2 NOT NULL CONSTRAINT DF_BAN_AN_NgayTao DEFAULT SYSDATETIME()
    );
END;

IF OBJECT_ID(N'dbo.DON_HANG', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.DON_HANG (
        MaDonHang INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        MaBan INT NOT NULL,
        MaNguoiDung INT NULL,
        TrangThai VARCHAR(20) NOT NULL
            CONSTRAINT DF_DON_HANG_TrangThai DEFAULT 'moi',
        GhiChu NVARCHAR(500) NULL,
        TongTien DECIMAL(18,2) NOT NULL
            CONSTRAINT DF_DON_HANG_TongTien DEFAULT 0,
        NgayTao DATETIME2 NOT NULL
            CONSTRAINT DF_DON_HANG_NgayTao DEFAULT SYSDATETIME(),
        CONSTRAINT FK_DON_HANG_BAN_AN FOREIGN KEY (MaBan)
            REFERENCES dbo.BAN_AN(MaBan),
        CONSTRAINT FK_DON_HANG_NGUOI_DUNG FOREIGN KEY (MaNguoiDung)
            REFERENCES dbo.NGUOI_DUNG(MaNguoiDung),
        CONSTRAINT CK_DON_HANG_TrangThai
            CHECK (TrangThai IN ('moi', 'dang_chuan_bi', 'hoan_thanh', 'huy'))
    );
END;

IF OBJECT_ID(N'dbo.CHI_TIET_DON_HANG', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.CHI_TIET_DON_HANG (
        MaChiTiet INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        MaDonHang INT NOT NULL,
        MaMonAn INT NOT NULL,
        SoLuong INT NOT NULL,
        DonGia DECIMAL(18,2) NOT NULL,
        GhiChu NVARCHAR(250) NULL,
        CONSTRAINT FK_CTDH_DON_HANG FOREIGN KEY (MaDonHang)
            REFERENCES dbo.DON_HANG(MaDonHang) ON DELETE CASCADE,
        CONSTRAINT FK_CTDH_MON_AN FOREIGN KEY (MaMonAn)
            REFERENCES dbo.MON_AN(MaMonAn),
        CONSTRAINT CK_CTDH_SoLuong CHECK (SoLuong BETWEEN 1 AND 50),
        CONSTRAINT CK_CTDH_DonGia CHECK (DonGia >= 0)
    );
END;

INSERT INTO dbo.BAN_AN (TenBan)
SELECT N.BanName
FROM (VALUES
    (N'Bàn 1'), (N'Bàn 2'), (N'Bàn 3'),
    (N'Bàn 4'), (N'Bàn 5'), (N'Bàn 6')
) AS N(BanName)
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.BAN_AN AS B WHERE B.TenBan = N.BanName
);

UPDATE dbo.NGUOI_DUNG
SET TrangThai = 0
WHERE LOWER(LTRIM(RTRIM(VaiTro))) IN
    ('customer', 'khach_hang', 'khachhang', N'khách hàng', N'khách_hàng')
  AND TrangThai = 1;

UPDATE dbo.NGUOI_DUNG
SET VaiTro = 'NhanVien'
WHERE LOWER(LTRIM(RTRIM(VaiTro))) IN
    ('user', 'staff', 'employee', 'nhanvien', 'nhan_vien', N'nhân viên');

UPDATE dbo.NGUOI_DUNG
SET VaiTro = 'manager'
WHERE LOWER(LTRIM(RTRIM(VaiTro))) IN ('manager', 'quanly', N'quản lý');

UPDATE dbo.NGUOI_DUNG
SET VaiTro = 'admin'
WHERE LOWER(LTRIM(RTRIM(VaiTro))) = 'admin';

COMMIT TRANSACTION;

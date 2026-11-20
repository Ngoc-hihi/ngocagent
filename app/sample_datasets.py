"""
sample_datasets.py - Tạo 3 bộ dữ liệu mẫu thực tế và lưu trữ
Có sẵn các trường dữ liệu thực tế và các lỗi điển hình (missing, dirty spaces, outliers, inconsistent date)
để minh chứng trọn vẹn quy trình Làm sạch HITL.
"""

import os
import pandas as pd
import numpy as np

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "samples")
os.makedirs(SAMPLE_DIR, exist_ok=True)

def generate_retail_fb_dataset():
    """Mẫu 1: Chuỗi Bán lẻ & F&B (Doanh thu, Chi phí, Vùng miền Bắc-Trung-Nam, Kênh bán)"""
    data = [
        {"Ngay": "2024-01-05", "Ma_Don": "ORD-1001", "Chi_Nhanh": "BD", "Vung_Mien": "Miền Nam", "Kenh_Ban": "shopee", "Nhom_Hang": "Cà phê & Trà", "Doanh_Thu": 8500000, "Chi_Phi_Von": 3400000, "Chi_Phi_Van_Hanh": 2100000, "So_Khach": -5, "Danh_Gia": 4.8},
        {"Ngay": "05/01/2024", "Ma_Don": "ORD-1002", "Chi_Nhanh": "HN", "Vung_Mien": "Miền Bắc", "Kenh_Ban": "GrabFood", "Nhom_Hang": "Bánh & Tráng miệng", "Doanh_Thu": 4200000, "Chi_Phi_Von": 1800000, "Chi_Phi_Van_Hanh": 1200000, "So_Khach": 68, "Danh_Gia": 4.5},
        {"Ngay": "2024-01-06", "Ma_Don": "ORD-1003", "Chi_Nhanh": "HCM", "Vung_Mien": "Miền Nam", "Kenh_Ban": "TikTok Shop", "Nhom_Hang": None, "Doanh_Thu": 6300000, "Chi_Phi_Von": 2600000, "Chi_Phi_Van_Hanh": None, "So_Khach": -2, "Danh_Gia": 4.6},
        {"Ngay": "2024-01-07", "Ma_Don": "ORD-1004", "Chi_Nhanh": "CHI NHÁNH THỦ ĐỨC", "Vung_Mien": "Miền Nam", "Kenh_Ban": "ShopeeFood", "Nhom_Hang": "Cà phê & Trà", "Doanh_Thu": 5100000, "Chi_Phi_Von": 2050000, "Chi_Phi_Van_Hanh": 1400000, "So_Khach": 84, "Danh_Gia": 4.2},
        {"Ngay": "2024-01-08", "Ma_Don": "ORD-1005", "Chi_Nhanh": "Chi nhánh Cầu Giấy", "Vung_Mien": "Miền Bắc", "Kenh_Ban": "Tại chỗ", "Nhom_Hang": "Thức ăn nhẹ", "Doanh_Thu": -250000, "Chi_Phi_Von": 150000, "Chi_Phi_Van_Hanh": 600000, "So_Khach": -12, "Danh_Gia": 2.0}, # Lỗi số âm
        {"Ngay": "2024-01-09", "Ma_Don": "ORD-1006", "Chi_Nhanh": "BD", "Vung_Mien": "Miền Nam", "Kenh_Ban": "Mang về", "Nhom_Hang": "Cà phê & Trà", "Doanh_Thu": 9200000, "Chi_Phi_Von": 3700000, "Chi_Phi_Van_Hanh": 2300000, "So_Khach": 160, "Danh_Gia": 4.9},
        {"Ngay": "2024-01-10", "Ma_Don": "ORD-1007", "Chi_Nhanh": "Chi nhánh Thanh Khê", "Vung_Mien": "Miền Trung", "Kenh_Ban": "Tại chỗ", "Nhom_Hang": "Bánh & Tráng miệng", "Doanh_Thu": 3800000, "Chi_Phi_Von": 1600000, "Chi_Phi_Van_Hanh": 1050000, "So_Khach": 55, "Danh_Gia": 4.4},
        {"Ngay": "2024-01-11", "Ma_Don": "ORD-1008", "Chi_Nhanh": "Chi nhánh Đống Đa", "Vung_Mien": "Miền Bắc", "Kenh_Ban": "GrabFood", "Nhom_Hang": "Combo", "Doanh_Thu": 7100000, "Chi_Phi_Von": 3100000, "Chi_Phi_Van_Hanh": 1900000, "So_Khach": 110, "Danh_Gia": None}, # Missing
        {"Ngay": "2024-01-12", "Ma_Don": "ORD-1009", "Chi_Nhanh": "Chi nhánh Quận 7", "Vung_Mien": "Miền Nam", "Kenh_Ban": "Tại chỗ", "Nhom_Hang": "Cà phê & Trà", "Doanh_Thu": 11500000, "Chi_Phi_Von": 4600000, "Chi_Phi_Van_Hanh": 2800000, "So_Khach": 195, "Danh_Gia": 4.7},
        {"Ngay": "2024-01-13", "Ma_Don": "ORD-1010", "Chi_Nhanh": "Chi nhánh Nha Trang", "Vung_Mien": "Miền Trung", "Kenh_Ban": "Tại chỗ", "Nhom_Hang": "Thức ăn nhẹ", "Doanh_Thu": 4900000, "Chi_Phi_Von": 2100000, "Chi_Phi_Van_Hanh": 1300000, "So_Khach": 72, "Danh_Gia": 4.5},
        {"Ngay": "2024-01-13", "Ma_Don": "ORD-1010", "Chi_Nhanh": "Chi nhánh Nha Trang", "Vung_Mien": "Miền Trung", "Kenh_Ban": "Tại chỗ", "Nhom_Hang": "Thức ăn nhẹ", "Doanh_Thu": 4900000, "Chi_Phi_Von": 2100000, "Chi_Phi_Van_Hanh": 1300000, "So_Khach": 72, "Danh_Gia": 4.5}, # Trùng lặp
        {"Ngay": "2024-01-14", "Ma_Don": "ORD-1011", "Chi_Nhanh": "Chi nhánh Tây Hồ", "Vung_Mien": "Miền Bắc", "Kenh_Ban": "ShopeeFood", "Nhom_Hang": "Cà phê & Trà", "Doanh_Thu": 5800000, "Chi_Phi_Von": 2350000, "Chi_Phi_Van_Hanh": 1500000, "So_Khach": 90, "Danh_Gia": 4.3},
        {"Ngay": "2024-01-15", "Ma_Don": "ORD-1012", "Chi_Nhanh": "Chi nhánh Bình Thạnh", "Vung_Mien": "Miền Nam", "Kenh_Ban": "Tại chỗ", "Nhom_Hang": "Combo", "Doanh_Thu": 8800000, "Chi_Phi_Von": 3600000, "Chi_Phi_Van_Hanh": 2200000, "So_Khach": 150, "Danh_Gia": 4.8},
        {"Ngay": "2024-01-16", "Ma_Don": "ORD-1013", "Chi_Nhanh": "Chi nhánh Huế", "Vung_Mien": "Miền Trung", "Kenh_Ban": "Mang về", "Nhom_Hang": "Cà phê & Trà", "Doanh_Thu": 3400000, "Chi_Phi_Von": 1400000, "Chi_Phi_Van_Hanh": 900000, "So_Khach": 58, "Danh_Gia": 4.1},
        {"Ngay": "2024-01-17", "Ma_Don": "ORD-1014", "Chi_Nhanh": "Chi nhánh Ba Đình", "Vung_Mien": "Miền Bắc", "Kenh_Ban": "Tại chỗ", "Nhom_Hang": "Bánh & Tráng miệng", "Doanh_Thu": 5200000, "Chi_Phi_Von": 2200000, "Chi_Phi_Van_Hanh": 1350000, "So_Khach": 82, "Danh_Gia": 4.6},
        {"Ngay": "2024-01-18", "Ma_Don": "ORD-1015", "Chi_Nhanh": "Chi nhánh Tân Bình", "Vung_Mien": "Miền Nam", "Kenh_Ban": "GrabFood", "Nhom_Hang": "Combo", "Doanh_Thu": 6700000, "Chi_Phi_Von": 2800000, "Chi_Phi_Van_Hanh": None, "So_Khach": 105, "Danh_Gia": 4.4},
        {"Ngay": "2024-01-19", "Ma_Don": "ORD-1016", "Chi_Nhanh": "Chi nhánh Quy Nhơn", "Vung_Mien": "Miền Trung", "Kenh_Ban": "Tại chỗ", "Nhom_Hang": "Cà phê & Trà", "Doanh_Thu": 4100000, "Chi_Phi_Von": 1700000, "Chi_Phi_Van_Hanh": 1100000, "So_Khach": 65, "Danh_Gia": 4.5},
        {"Ngay": "2024-01-20", "Ma_Don": "ORD-1017", "Chi_Nhanh": "Chi nhánh Hai Bà Trưng", "Vung_Mien": "Miền Bắc", "Kenh_Ban": "Tại chỗ", "Nhom_Hang": "Cà phê & Trà", "Doanh_Thu": 7900000, "Chi_Phi_Von": 3200000, "Chi_Phi_Van_Hanh": 2000000, "So_Khach": 130, "Danh_Gia": 4.7},
        {"Ngay": "2024-01-21", "Ma_Don": "ORD-1018", "Chi_Nhanh": "Chi nhánh Phú Nhuận", "Vung_Mien": "Miền Nam", "Kenh_Ban": "Website", "Nhom_Hang": "Bánh & Tráng miệng", "Doanh_Thu": 4600000, "Chi_Phi_Von": 1950000, "Chi_Phi_Van_Hanh": 1250000, "So_Khach": 70, "Danh_Gia": 4.3},
        {"Ngay": "2024-01-22", "Ma_Don": "ORD-1019", "Chi_Nhanh": "Chi nhánh Sơn Trà", "Vung_Mien": "Miền Trung", "Kenh_Ban": "Tại chỗ", "Nhom_Hang": "Combo", "Doanh_Thu": 5500000, "Chi_Phi_Von": 2300000, "Chi_Phi_Van_Hanh": 1450000, "So_Khach": 88, "Danh_Gia": 4.6},
        {"Ngay": "2024-01-23", "Ma_Don": "ORD-1020", "Chi_Nhanh": "Chi nhánh Quận 10", "Vung_Mien": "Miền Nam", "Kenh_Ban": "Tại chỗ", "Nhom_Hang": "Cà phê & Trà", "Doanh_Thu": 10200000, "Chi_Phi_Von": 4100000, "Chi_Phi_Van_Hanh": 2550000, "So_Khach": 175, "Danh_Gia": 4.9},
        {"Ngay": "2024-01-24", "Ma_Don": "ORD-1021", "Chi_Nhanh": "Chi nhánh Hà Đông", "Vung_Mien": "Miền Bắc", "Kenh_Ban": "GrabFood", "Nhom_Hang": "Thức ăn nhẹ", "Doanh_Thu": 3900000, "Chi_Phi_Von": 1650000, "Chi_Phi_Van_Hanh": 1050000, "So_Khach": 60, "Danh_Gia": 4.2},
        {"Ngay": "2024-01-25", "Ma_Don": "ORD-1022", "Chi_Nhanh": "Chi nhánh Gò Vấp", "Vung_Mien": "Miền Nam", "Kenh_Ban": "ShopeeFood", "Nhom_Hang": "Cà phê & Trà", "Doanh_Thu": 6100000, "Chi_Phi_Von": 2500000, "Chi_Phi_Van_Hanh": 1600000, "So_Khach": 98, "Danh_Gia": 4.4},
        {"Ngay": "2024-01-26", "Ma_Don": "ORD-1023", "Chi_Nhanh": "Chi nhánh Cẩm Lệ", "Vung_Mien": "Miền Trung", "Kenh_Ban": "Tại chỗ", "Nhom_Hang": "Bánh & Tráng miệng", "Doanh_Thu": 3200000, "Chi_Phi_Von": 1350000, "Chi_Phi_Van_Hanh": 880000, "So_Khach": 50, "Danh_Gia": 4.3},
        {"Ngay": "2024-01-27", "Ma_Don": "ORD-1024", "Chi_Nhanh": "Chi nhánh Cầu Giấy 2", "Vung_Mien": "Miền Bắc", "Kenh_Ban": "Tại chỗ", "Nhom_Hang": "Combo", "Doanh_Thu": 8200000, "Chi_Phi_Von": 3350000, "Chi_Phi_Van_Hanh": 2100000, "So_Khach": 138, "Danh_Gia": 4.7},
    ]
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(SAMPLE_DIR, "retail_fb_sample.csv"), index=False, encoding="utf-8-sig")
    df.to_excel(os.path.join(SAMPLE_DIR, "retail_fb_sample.xlsx"), index=False)
    return df

def generate_saas_dataset():
    """Mẫu 2: B2B SaaS & Phần mềm dịch vụ (MRR, Churn, Khách hàng, NPS)"""
    data = [
        {"Thang": "2024-01", "Ma_KH": "CUST-001", "Doanh_Nghiep": "Vingroup Retail", "Goi_Dich_Vu": "Enterprise", "Vung_Mien": "Miền Bắc", "MRR": 45000000, "Chi_Phi_CSKH": 6500000, "So_Ticket": 4, "Diem_NPS": 9, "Trang_Thai": "Gia hạn"},
        {"Thang": "2024-01", "Ma_KH": "CUST-002", "Doanh_Nghiep": "FPT Telecom Log", "Goi_Dich_Vu": "Enterprise", "Vung_Mien": "Miền Bắc", "MRR": 50000000, "Chi_Phi_CSKH": 8000000, "So_Ticket": 8, "Diem_NPS": 8, "Trang_Thai": "Gia hạn"},
        {"Thang": "2024-01", "Ma_KH": "CUST-003", "Doanh_Nghiep": "Tiki Logistics", "Goi_Dich_Vu": "Growth", "Vung_Mien": "Miền Nam", "MRR": 18000000, "Chi_Phi_CSKH": 3200000, "So_Ticket": 2, "Diem_NPS": 9, "Trang_Thai": "Gia hạn"},
        {"Thang": "2024-01", "Ma_KH": "CUST-004", "Doanh_Nghiep": "The Coffee House", "Goi_Dich_Vu": "Growth", "Vung_Mien": "Miền Nam", "MRR": 22000000, "Chi_Phi_CSKH": 4100000, "So_Ticket": 12, "Diem_NPS": 6, "Trang_Thai": "Rời bỏ"},
        {"Thang": "2024-01", "Ma_KH": "CUST-005", "Doanh_Nghiep": "Sun Group Travel", "Goi_Dich_Vu": "Enterprise", "Vung_Mien": "Miền Trung", "MRR": 42000000, "Chi_Phi_CSKH": 7200000, "So_Ticket": 5, "Diem_NPS": 9, "Trang_Thai": "Gia hạn"},
        {"Thang": "2024-01", "Ma_KH": "CUST-006", "Doanh_Nghiep": "KiotViet POS", "Goi_Dich_Vu": "Starter", "Vung_Mien": "Miền Bắc", "MRR": 5000000, "Chi_Phi_CSKH": 1200000, "So_Ticket": 1, "Diem_NPS": None, "Trang_Thai": "Gia hạn"}, # missing
        {"Thang": "2024-01", "Ma_KH": "CUST-007", "Doanh_Nghiep": "Giaohangtietkiem", "Goi_Dich_Vu": "Enterprise", "Vung_Mien": "Miền Bắc", "MRR": 55000000, "Chi_Phi_CSKH": 9000000, "So_Ticket": 6, "Diem_NPS": 8, "Trang_Thai": "Gia hạn"},
        {"Thang": "2024-01", "Ma_KH": "CUST-008", "Doanh_Nghiep": "Biti's Footwear", "Goi_Dich_Vu": "Growth", "Vung_Mien": "Miền Nam", "MRR": 20000000, "Chi_Phi_CSKH": 3500000, "So_Ticket": 3, "Diem_NPS": 9, "Trang_Thai": "Gia hạn"},
        {"Thang": "2024-01", "Ma_KH": "CUST-009", "Doanh_Nghiep": "Đà Nẵng Port", "Goi_Dich_Vu": "Growth", "Vung_Mien": "Miền Trung", "MRR": 24000000, "Chi_Phi_CSKH": 4500000, "So_Ticket": 7, "Diem_NPS": 7, "Trang_Thai": "Cân nhắc"},
        {"Thang": "2024-01", "Ma_KH": "CUST-010", "Doanh_Nghiep": " Juno Fashion ", "Goi_Dich_Vu": "Starter", "Vung_Mien": "Miền Nam", "MRR": 6000000, "Chi_Phi_CSKH": 1500000, "So_Ticket": 9, "Diem_NPS": 5, "Trang_Thai": "Rời bỏ"},
        {"Thang": "2024-01", "Ma_KH": "CUST-011", "Doanh_Nghiep": "MobiFone Value", "Goi_Dich_Vu": "Enterprise", "Vung_Mien": "Miền Bắc", "MRR": 48000000, "Chi_Phi_CSKH": 7500000, "So_Ticket": 4, "Diem_NPS": 8, "Trang_Thai": "Gia hạn"},
        {"Thang": "2024-01", "Ma_KH": "CUST-012", "Doanh_Nghiep": "Highlands Central", "Goi_Dich_Vu": "Growth", "Vung_Mien": "Miền Trung", "MRR": 19000000, "Chi_Phi_CSKH": 3100000, "So_Ticket": 3, "Diem_NPS": 8, "Trang_Thai": "Gia hạn"},
        {"Thang": "2024-01", "Ma_KH": "CUST-013", "Doanh_Nghiep": "Sendo Mart", "Goi_Dich_Vu": "Growth", "Vung_Mien": "Miền Nam", "MRR": 21000000, "Chi_Phi_CSKH": 3800000, "So_Ticket": 11, "Diem_NPS": 6, "Trang_Thai": "Rời bỏ"},
        {"Thang": "2024-01", "Ma_KH": "CUST-014", "Doanh_Nghiep": "Viettel Post Da Nang", "Goi_Dich_Vu": "Enterprise", "Vung_Mien": "Miền Trung", "MRR": 46000000, "Chi_Phi_CSKH": 7000000, "So_Ticket": 2, "Diem_NPS": 9, "Trang_Thai": "Gia hạn"},
        {"Thang": "2024-01", "Ma_KH": "CUST-015", "Doanh_Nghiep": "Pharmacity Hub", "Goi_Dich_Vu": "Enterprise", "Vung_Mien": "Miền Nam", "MRR": 52000000, "Chi_Phi_CSKH": 8500000, "So_Ticket": 5, "Diem_NPS": 9, "Trang_Thai": "Gia hạn"},
        {"Thang": "2024-01", "Ma_KH": "CUST-015", "Doanh_Nghiep": "Pharmacity Hub", "Goi_Dich_Vu": "Enterprise", "Vung_Mien": "Miền Nam", "MRR": 52000000, "Chi_Phi_CSKH": 8500000, "So_Ticket": 5, "Diem_NPS": 9, "Trang_Thai": "Gia hạn"}, # Duplicated
        {"Thang": "2024-01", "Ma_KH": "CUST-016", "Doanh_Nghiep": "An Binh Tech", "Goi_Dich_Vu": "Starter", "Vung_Mien": "Miền Bắc", "MRR": -1000000, "Chi_Phi_CSKH": 1100000, "So_Ticket": 0, "Diem_NPS": 7, "Trang_Thai": "Gia hạn"}, # Outlier / negative
        {"Thang": "2024-01", "Ma_KH": "CUST-017", "Doanh_Nghiep": "Vinamilk Logistics", "Goi_Dich_Vu": "Enterprise", "Vung_Mien": "Miền Nam", "MRR": 60000000, "Chi_Phi_CSKH": 9500000, "So_Ticket": 3, "Diem_NPS": 10, "Trang_Thai": "Gia hạn"},
        {"Thang": "2024-01", "Ma_KH": "CUST-018", "Doanh_Nghiep": "Hue Tourism Corp", "Goi_Dich_Vu": "Starter", "Vung_Mien": "Miền Trung", "MRR": 7000000, "Chi_Phi_CSKH": None, "So_Ticket": 2, "Diem_NPS": 8, "Trang_Thai": "Gia hạn"}, # missing
    ]
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(SAMPLE_DIR, "saas_sample.csv"), index=False, encoding="utf-8-sig")
    df.to_excel(os.path.join(SAMPLE_DIR, "saas_sample.xlsx"), index=False)
    return df

def generate_manufacturing_dataset():
    """Mẫu 3: Sản xuất & Chuỗi cung ứng (Sản lượng, Chi phí nguyên liệu, Vận chuyển, Tỷ lệ lỗi)"""
    data = [
        {"Ngay": "2024-01-02", "Lo_Hang": "BATCH-01", "Nha_May": "Nhà máy Bắc Ninh", "Vung_Mien": "Miền Bắc", "Dong_SP": "Tiêu chuẩn", "San_Luong": 12000, "Chi_Phi_NL": 72000000, "Chi_Phi_Van_Chuyen": 14000000, "Ty_Le_Loi_Pct": 1.2, "Thoi_Gian_Giao_Ngay": 3},
        {"Ngay": "2024-01-04", "Lo_Hang": "BATCH-02", "Nha_May": "Nhà máy Bình Dương", "Vung_Mien": "Miền Nam", "Dong_SP": "Cao cấp", "San_Luong": 8500, "Chi_Phi_NL": 68000000, "Chi_Phi_Van_Chuyen": 12500000, "Ty_Le_Loi_Pct": 0.8, "Thoi_Gian_Giao_Ngay": 2},
        {"Ngay": "2024-01-06", "Lo_Hang": "BATCH-03", "Nha_May": "Nhà máy Chu Lai", "Vung_Mien": "Miền Trung", "Dong_SP": "Xuất khẩu", "San_Luong": 15000, "Chi_Phi_NL": 110000000, "Chi_Phi_Van_Chuyen": 22000000, "Ty_Le_Loi_Pct": 1.5, "Thoi_Gian_Giao_Ngay": 4},
        {"Ngay": "2024-01-08", "Lo_Hang": "BATCH-04", "Nha_May": " Nhà máy Hải Phòng ", "Vung_Mien": "Miền Bắc", "Dong_SP": "Tiêu chuẩn", "San_Luong": 11000, "Chi_Phi_NL": 65000000, "Chi_Phi_Van_Chuyen": 13000000, "Ty_Le_Loi_Pct": 2.8, "Thoi_Gian_Giao_Ngay": 5},
        {"Ngay": "2024-01-10", "Lo_Hang": "BATCH-05", "Nha_May": "Nhà máy Đồng Nai", "Vung_Mien": "Miền Nam", "Dong_SP": "Xuất khẩu", "San_Luong": 16500, "Chi_Phi_NL": 125000000, "Chi_Phi_Van_Chuyen": 24000000, "Ty_Le_Loi_Pct": 0.9, "Thoi_Gian_Giao_Ngay": 2},
        {"Ngay": "2024-01-12", "Lo_Hang": "BATCH-06", "Nha_May": "Nhà máy Đà Nẵng", "Vung_Mien": "Miền Trung", "Dong_SP": "Tiêu chuẩn", "San_Luong": 9200, "Chi_Phi_NL": 54000000, "Chi_Phi_Van_Chuyen": 9800000, "Ty_Le_Loi_Pct": None, "Thoi_Gian_Giao_Ngay": 3}, # missing
        {"Ngay": "2024-01-14", "Lo_Hang": "BATCH-07", "Nha_May": "Nhà máy Vĩnh Phúc", "Vung_Mien": "Miền Bắc", "Dong_SP": "Cao cấp", "San_Luong": 7800, "Chi_Phi_NL": 62000000, "Chi_Phi_Van_Chuyen": 11000000, "Ty_Le_Loi_Pct": 1.1, "Thoi_Gian_Giao_Ngay": 3},
        {"Ngay": "2024-01-16", "Lo_Hang": "BATCH-08", "Nha_May": "Nhà máy Long An", "Vung_Mien": "Miền Nam", "Dong_SP": "Tiêu chuẩn", "San_Luong": 13500, "Chi_Phi_NL": 81000000, "Chi_Phi_Van_Chuyen": 15500000, "Ty_Le_Loi_Pct": 1.3, "Thoi_Gian_Giao_Ngay": 3},
        {"Ngay": "2024-01-18", "Lo_Hang": "BATCH-09", "Nha_May": "Nhà máy Quảng Nam", "Vung_Mien": "Miền Trung", "Dong_SP": "Xuất khẩu", "San_Luong": 14200, "Chi_Phi_NL": 105000000, "Chi_Phi_Van_Chuyen": 20000000, "Ty_Le_Loi_Pct": 1.4, "Thoi_Gian_Giao_Ngay": 4},
        {"Ngay": "2024-01-20", "Lo_Hang": "BATCH-10", "Nha_May": "Nhà máy Bắc Ninh", "Vung_Mien": "Miền Bắc", "Dong_SP": "Xuất khẩu", "San_Luong": 17000, "Chi_Phi_NL": 130000000, "Chi_Phi_Van_Chuyen": 25000000, "Ty_Le_Loi_Pct": 1.0, "Thoi_Gian_Giao_Ngay": 3},
        {"Ngay": "2024-01-22", "Lo_Hang": "BATCH-11", "Nha_May": "Nhà máy Bình Dương", "Vung_Mien": "Miền Nam", "Dong_SP": "Tiêu chuẩn", "San_Luong": 11500, "Chi_Phi_NL": -500000, "Chi_Phi_Van_Chuyen": 13500000, "Ty_Le_Loi_Pct": 1.2, "Thoi_Gian_Giao_Ngay": 2}, # Outlier / negative cost
        {"Ngay": "2024-01-24", "Lo_Hang": "BATCH-12", "Nha_May": "Nhà máy Dung Quất", "Vung_Mien": "Miền Trung", "Dong_SP": "Cao cấp", "San_Luong": 8200, "Chi_Phi_NL": 65000000, "Chi_Phi_Van_Chuyen": 12000000, "Ty_Le_Loi_Pct": 0.7, "Thoi_Gian_Giao_Ngay": 3},
        {"Ngay": "2024-01-24", "Lo_Hang": "BATCH-12", "Nha_May": "Nhà máy Dung Quất", "Vung_Mien": "Miền Trung", "Dong_SP": "Cao cấp", "San_Luong": 8200, "Chi_Phi_NL": 65000000, "Chi_Phi_Van_Chuyen": 12000000, "Ty_Le_Loi_Pct": 0.7, "Thoi_Gian_Giao_Ngay": 3}, # Duplicated
        {"Ngay": "2024-01-26", "Lo_Hang": "BATCH-13", "Nha_May": "Nhà máy Thái Nguyên", "Vung_Mien": "Miền Bắc", "Dong_SP": "Tiêu chuẩn", "San_Luong": 12500, "Chi_Phi_NL": 75000000, "Chi_Phi_Van_Chuyen": 14500000, "Ty_Le_Loi_Pct": 1.6, "Thoi_Gian_Giao_Ngay": 4},
        {"Ngay": "2024-01-28", "Lo_Hang": "BATCH-14", "Nha_May": "Nhà máy Tiền Giang", "Vung_Mien": "Miền Nam", "Dong_SP": "Cao cấp", "San_Luong": 9000, "Chi_Phi_NL": 71000000, "Chi_Phi_Van_Chuyen": 13000000, "Ty_Le_Loi_Pct": 0.9, "Thoi_Gian_Giao_Ngay": 2},
    ]
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(SAMPLE_DIR, "manufacturing_sample.csv"), index=False, encoding="utf-8-sig")
    df.to_excel(os.path.join(SAMPLE_DIR, "manufacturing_sample.xlsx"), index=False)
    return df

def init_samples():
    generate_retail_fb_dataset()
    generate_saas_dataset()
    generate_manufacturing_dataset()

if __name__ == "__main__":
    init_samples()
    print("Sample datasets successfully initialized.")

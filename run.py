"""
run.py - Điểm khởi động máy chủ AnoraAI trên localhost
Chạy bằng lệnh: python run.py
Mở trình duyệt truy cập: http://localhost:8000
"""

import uvicorn
import os
import sys

# Đảm bảo đường dẫn gốc được nhận diện
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.sample_datasets import init_samples

if __name__ == "__main__":
    # Khởi tạo các bộ dữ liệu mẫu nếu chưa có
    init_samples()
    print("=" * 65)
    print("🌿 AnoraAI — Hệ Thống Phân Tích Dữ Liệu & Báo Cáo DIID Doanh Nghiệp")
    print("🌐 Đang khởi chạy máy chủ tại: http://localhost:8000 (hoặc http://127.0.0.1:8000)")
    print("✨ Phong cách: Botanical Aesthetic Pastel Luxury")
    print("=" * 65)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False, log_level="info")

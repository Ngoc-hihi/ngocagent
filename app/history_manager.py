"""
history_manager.py - Quản lý Lịch sử chạy (Run History) & Đánh giá phản hồi người dùng (User Feedback)
- Lưu trữ mọi phiên chạy hoàn chỉnh với metadata, số liệu tóm tắt và đường dẫn tệp
- Cho phép xem lại lịch sử, tải lại các file đã xuất (.xlsx, .docx, .html)
- Tiếp nhận đánh giá 1-5 sao và phản hồi từ người dùng
"""

import os
import json
from datetime import datetime

HISTORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history")
FEEDBACK_FILE = os.path.join(HISTORY_DIR, "feedback_log.json")
RUNS_FILE = os.path.join(HISTORY_DIR, "runs_meta.json")

os.makedirs(HISTORY_DIR, exist_ok=True)

class HistoryManager:
    @staticmethod
    def _read_json(filepath: str, default=None):
        if default is None:
            default = []
        if not os.path.exists(filepath):
            return default
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    @staticmethod
    def _write_json(filepath: str, data):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def save_run(cls, run_id: str, business_meta: dict, summary_metrics: dict, file_paths: dict) -> dict:
        runs = cls._read_json(RUNS_FILE, [])
        record = {
            "run_id": run_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "business_name": business_meta.get("name", "Doanh nghiệp"),
            "business_model": business_meta.get("model", "Chưa xác định"),
            "core_problem": business_meta.get("core_problem", "Tối ưu hóa tổng thể"),
            "summary_metrics": summary_metrics,
            "files": file_paths
        }
        # Thêm lên đầu danh sách
        runs.insert(0, record)
        cls._write_json(RUNS_FILE, runs)
        return record

    @classmethod
    def list_runs(cls) -> list:
        return cls._read_json(RUNS_FILE, [])

    @classmethod
    def get_run(cls, run_id: str) -> dict:
        runs = cls.list_runs()
        for r in runs:
            if r.get("run_id") == run_id:
                return r
        return None

    @classmethod
    def save_feedback(cls, stars: int, comments: str, run_id: str = None) -> dict:
        feedbacks = cls._read_json(FEEDBACK_FILE, [])
        entry = {
            "id": f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stars": int(stars),
            "comments": comments.strip(),
            "run_id": run_id
        }
        feedbacks.insert(0, entry)
        cls._write_json(FEEDBACK_FILE, feedbacks)
        return entry

    @classmethod
    def get_feedbacks(cls) -> list:
        return cls._read_json(FEEDBACK_FILE, [])

"""
history_manager.py - Quản lý Lịch sử chạy (Run History) & Đánh giá phản hồi người dùng (User Feedback)
- Hỗ trợ lưu trữ bền vững trên Localhost và tự động chuyển vùng nhớ /tmp / In-memory trên Serverless Vercel
- Cho phép xem lại lịch sử, tải lại các file đã xuất (.xlsx, .docx, .html)
- Tiếp nhận đánh giá 1-5 sao và phản hồi từ người dùng
"""

import os
import json
import tempfile
from datetime import datetime

def _resolve_history_dir():
    candidate = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history")
    try:
        os.makedirs(candidate, exist_ok=True)
        test_p = os.path.join(candidate, ".test_hist")
        with open(test_p, "w") as f:
            f.write("ok")
        os.remove(test_p)
        return candidate
    except Exception:
        fallback = os.path.join(tempfile.gettempdir(), "anora_history")
        os.makedirs(fallback, exist_ok=True)
        return fallback

HISTORY_DIR = _resolve_history_dir()
FEEDBACK_FILE = os.path.join(HISTORY_DIR, "feedback_log.json")
RUNS_FILE = os.path.join(HISTORY_DIR, "runs_meta.json")

# Bộ đệm in-memory dự phòng khi môi trường không có quyền ghi đĩa
_IN_MEMORY_RUNS = []
_IN_MEMORY_FEEDBACKS = []

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
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # Ghi không thành công trên đĩa, dữ liệu vẫn an toàn trong in-memory fallback
            pass

    @classmethod
    def save_run(cls, run_id: str, business_meta: dict, summary_metrics: dict, file_paths: dict) -> dict:
        global _IN_MEMORY_RUNS
        record = {
            "run_id": run_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "business_name": business_meta.get("name", "Doanh nghiệp"),
            "business_model": business_meta.get("model", "Chưa xác định"),
            "core_problem": business_meta.get("core_problem", "Tối ưu hóa tổng thể"),
            "summary_metrics": summary_metrics,
            "files": file_paths
        }
        _IN_MEMORY_RUNS.insert(0, record)
        
        runs = cls._read_json(RUNS_FILE, [])
        runs.insert(0, record)
        cls._write_json(RUNS_FILE, runs)
        return record

    @classmethod
    def list_runs(cls) -> list:
        runs = cls._read_json(RUNS_FILE, [])
        if runs:
            return runs
        return _IN_MEMORY_RUNS

    @classmethod
    def get_run(cls, run_id: str) -> dict:
        runs = cls.list_runs()
        for r in runs:
            if r.get("run_id") == run_id:
                return r
        return None

    @classmethod
    def save_feedback(cls, stars: int, comments: str, run_id: str = None) -> dict:
        global _IN_MEMORY_FEEDBACKS
        entry = {
            "id": f"fb_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stars": int(stars),
            "comments": comments.strip(),
            "run_id": run_id
        }
        _IN_MEMORY_FEEDBACKS.insert(0, entry)
        feedbacks = cls._read_json(FEEDBACK_FILE, [])
        feedbacks.insert(0, entry)
        cls._write_json(FEEDBACK_FILE, feedbacks)
        return entry

    @classmethod
    def get_feedbacks(cls) -> list:
        feedbacks = cls._read_json(FEEDBACK_FILE, [])
        if feedbacks:
            return feedbacks
        return _IN_MEMORY_FEEDBACKS

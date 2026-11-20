"""
directive_engine.py - Bộ xử lý Chỉ đạo Rà soát Dữ liệu HITL thông minh bằng NLP & Gemini AI
- Tầng 1 (Local NLP < 1ms): Hiểu đa dạng chỉ đạo tiếng Việt tự nhiên:
  + So sánh số học: "loại bỏ giá trị cột số lượng nhỏ hơn 5", "chỉ giữ thành tiền >= 10 triệu", "bỏ đơn giá từ 2tr đến 5tr"
  + Lọc theo giá trị chữ / nhiều điều kiện: "bỏ Nghệ An và Hải Phòng", "chỉ giữ ngành hàng Laptop", "bỏ cột chi nhánh Đồng Nai"
  + Vùng miền thông minh: "bỏ miền bắc", "chỉ giữ miền nam"
  + Thay thế / Sửa ô: "thay BD thành Bình Dương", "đổi cột phương thức thanh toán Ví Momo thành Momo"
  + Định dạng ngày & chữ: "cột ngày mua định dạng YYYY-MM", "viết hoa cột mã đơn hàng"
  + Sắp xếp / Xóa cột / Khử trùng / Điền khuyết / Xử lý số âm
- Tầng 2 (Google Gemini AI): Xử lý các yêu cầu ngữ nghĩa phức tạp (hỗ trợ API Key từ .env, biến môi trường Vercel hoặc truyền trực tiếp từ người dùng).
- Tự động hiệu chỉnh lại chỉ số cell_tags và ghi nhận đầy đủ vào Audit Log.
"""

import os
import json
import re
import urllib.request
import urllib.error
import unicodedata
import pandas as pd
import numpy as np

def strip_accents(s: str) -> str:
    if not isinstance(s, str):
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()

def _get_gemini_api_key(override_key: str = "") -> str:
    if override_key and override_key.strip():
        return override_key.strip().strip("\"'")
    key = os.getenv("GEMINI_API_KEY", "").strip().strip("\"'")
    if not key and os.path.exists(".env"):
        try:
            with open(".env", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip("\"'")
                        break
        except Exception:
            pass
    return key

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-3-flash-preview"
]

# Từ điển địa lý phục vụ lọc vùng miền thông minh
NORTH_KEYWORDS = ['miền bắc', 'mien bac', 'hà nội', 'hải phòng', 'quảng ninh', 'bắc ninh', 'hải dương', 'nam định', 'hà nam', 'thái bình']
CENTRAL_KEYWORDS = ['miền trung', 'mien trung', 'đà nẵng', 'huế', 'quảng nam', 'quảng ngãi', 'bình định', 'khánh hòa', 'nha trang', 'nghệ an']
SOUTH_KEYWORDS = ['miền nam', 'mien nam', 'hồ chí minh', 'tp. hồ chí minh', 'sài gòn', 'bình dương', 'cần thơ', 'đồng nai', 'vũng tàu']

NUM_TOKEN_PAT = r"(-?\d[\d\.,]*\s*(?:triệu|trieu|tr|tỷ|ty|nghìn|ngàn|nghin|ngan|k|vnđ|vnd|đ)?)"


class DirectiveEngine:
    @classmethod
    def _parse_numeric_series(cls, series: pd.Series) -> pd.Series:
        """Phân tích chính xác cả số chuẩn và số có dấu chấm/đơn vị tiếng Việt (VD: 18.000.000, 3.600.000)"""
        from app.data_cleaner import DataCleaner
        if pd.api.types.is_numeric_dtype(series):
            return series.astype(float)
        return series.apply(DataCleaner.parse_vn_number)

    @classmethod
    def _remap_tags(cls, kept_mask: pd.Series, old_tags: dict) -> dict:
        """Ánh xạ lại vị trí dòng trong cell_tags sau khi xóa dòng để màu sắc bảng không bị lệch"""
        if not old_tags:
            return {}
        old_to_new = {}
        new_pos = 0
        for old_pos, kept in enumerate(kept_mask.tolist()):
            if kept:
                old_to_new[old_pos] = new_pos
                new_pos += 1
        remapped = {}
        for k, tag_val in old_tags.items():
            if "_" in str(k):
                r_part, col_part = str(k).split("_", 1)
                if r_part.isdigit():
                    old_r = int(r_part)
                    if old_r in old_to_new:
                        remapped[f"{old_to_new[old_r]}_{col_part}"] = tag_val
        return remapped

    @classmethod
    def _find_column_in_text(cls, df: pd.DataFrame, text: str):
        """Tìm tên cột xuất hiện trong câu chỉ đạo (ưu tiên tên cột dài nhất, không phân biệt dấu/hoa thường)"""
        norm_text = strip_accents(text)
        # Sắp xếp cột theo độ dài giảm dần để "Số lượng" khớp trước "Số", "Thành tiền" khớp trước "Tiền"
        sorted_cols = sorted(df.columns.tolist(), key=lambda c: len(str(c)), reverse=True)
        for c in sorted_cols:
            c_norm = strip_accents(str(c)).replace("_", " ").strip()
            c_under = strip_accents(str(c)).strip()
            if c_norm and (re.search(rf"\b{re.escape(c_norm)}\b", norm_text) or c_under in norm_text):
                return c
        return None

    @classmethod
    def execute(cls, df: pd.DataFrame, directive: str, cell_tags: dict = None, api_key: str = "") -> tuple:
        """
        Thực thi chỉ đạo rà soát từ người dùng trên DataFrame hiện hành.
        Trả về: (new_df, new_cell_tags, log_message)
        """
        if cell_tags is None:
            cell_tags = {}
        tags = dict(cell_tags)

        d_text = (directive or "").strip()
        if not d_text:
            return df, tags, "Không có chỉ đạo nào được nhập."

        # 1. TẦNG 1: Thực thi tức thời bằng Bộ phân tích Ngôn ngữ Tự nhiên Cục bộ (< 1ms)
        nlp_res = cls._execute_via_nlp(df, d_text, tags)
        if nlp_res is not None:
            return nlp_res

        # 2. TẦNG 2: Gọi Bộ não Google Gemini AI cho các chỉ đạo phức tạp
        eff_key = _get_gemini_api_key(api_key)
        if eff_key:
            ai_res, ai_err = cls._execute_via_gemini(df, d_text, tags, eff_key)
            if ai_res is not None:
                return ai_res
            if ai_err:
                if "401" in ai_err or "UNAUTHENTICATED" in ai_err or "not valid" in ai_err:
                    return df, tags, (
                        f"⚠️ Bộ não Gemini API chưa xác thực được khóa (Lỗi 401: API Key không hợp lệ hoặc sai quyền truy cập). "
                        f"Gợi ý: Bạn có thể nhập lại API Key chuẩn (AIza...) từ Google AI Studio vào ô cấu hình API hoặc kiểm tra biến GEMINI_API_KEY trên Vercel."
                    )
                return df, tags, f"⚠️ Gemini AI tạm thời không thể thực thi chỉ đạo '{d_text}' ({ai_err}). Vui lòng thử diễn đạt rõ tên cột và điều kiện hơn."

        return df, tags, (
            f"Đã ghi nhận chỉ đạo: '{d_text}' nhưng chưa khớp thao tác hoặc chưa cấu hình Gemini API Key hợp lệ. "
            f"(Gợi ý mẫu câu: 'loại bỏ giá trị cột số lượng nhỏ hơn 5', 'chỉ giữ chi nhánh Hải Phòng', 'thay BD thành Bình Dương', 'bỏ các dòng số âm')."
        )

    @classmethod
    def _execute_via_nlp(cls, df: pd.DataFrame, directive: str, cell_tags: dict):
        """Phân tích đa dạng các chỉ đạo tiếng Việt tự nhiên"""
        from app.data_cleaner import DataCleaner

        d = directive.lower().strip()
        d_norm = strip_accents(d)
        new_df = df.copy()
        new_tags = dict(cell_tags)

        # ------------------------------------------------------------------
        # MẪU 0: ĐỊNH DẠNG NGÀY THÁNG (VD: "cột ngày mua định dạng là YYYY-MM")
        # ------------------------------------------------------------------
        is_format_directive = any(w in d for w in ["định dạng", "dinh dang", "format", "chuẩn hóa định dạng"]) or (
            any(k in d for k in ["yyyy", "mm", "dd"]) and any(w in d for w in ["là", "thành", "sang", "thanh", "bằng"])
        )
        if is_format_directive:
            fmt_m = re.search(r"['\"]?([Yy]{2,4}[\s\-\/\.\:]+[Mm]{1,2}(?:[\s\-\/\.\:]+[Dd]{1,2})?|[Dd]{1,2}[\s\-\/\.\:]+[Mm]{1,2}(?:[\s\-\/\.\:]+[Yy]{2,4})?|[Mm]{1,2}[\s\-\/\.\:]+[Yy]{2,4})['\"]?", directive)
            if fmt_m:
                fmt_str = fmt_m.group(1).strip("\"' ")
                py_fmt = re.sub(r'YYYY', '%Y', fmt_str, flags=re.IGNORECASE)
                py_fmt = re.sub(r'(?<!%)YY', '%y', py_fmt, flags=re.IGNORECASE)
                if 'DD' in fmt_str.upper() or 'YYYY' in fmt_str.upper():
                    py_fmt = re.sub(r'MM', '%m', py_fmt, flags=re.IGNORECASE)
                py_fmt = re.sub(r'DD', '%d', py_fmt, flags=re.IGNORECASE)

                target_col = cls._find_column_in_text(new_df, directive)
                if not target_col:
                    if any(k in d_norm for k in ["thang", "month"]):
                        target_col = next((c for c in new_df.columns if any(k in strip_accents(c) for k in ["thang", "month", "ngay", "date"])), None)
                    elif any(k in d_norm for k in ["ngay", "date"]):
                        target_col = next((c for c in new_df.columns if any(k in strip_accents(c) for k in ["ngay", "date"])), None)

                if not target_col:
                    for c in new_df.columns:
                        s_nonnull = new_df[c].dropna().astype(str).str.strip()
                        if len(s_nonnull) > 0 and s_nonnull.str.match(r'^\d{4}[\-\/\.]\d{2}').sum() >= len(s_nonnull) * 0.5:
                            target_col = c
                            break

                if target_col and target_col in new_df.columns:
                    count = 0
                    for idx, val in new_df[target_col].items():
                        if pd.notnull(val) and str(val).strip() not in ["", "nan", "none", "null"]:
                            try:
                                s_dt = str(val).strip()
                                is_iso = bool(re.match(r'^\d{4}[\-\/\.]', s_dt))
                                dt = pd.to_datetime(s_dt, format='mixed', dayfirst=not is_iso)
                                new_val = dt.strftime(py_fmt)
                                new_df.at[idx, target_col] = new_val
                                new_tags[f"{idx}_{target_col}"] = {
                                    "category": "format", "old": str(val), "new": new_val,
                                    "desc": f"Định dạng theo chỉ đạo HITL: '{fmt_str}'"
                                }
                                count += 1
                            except Exception:
                                pass
                    return new_df, new_tags, f"Đã chuẩn hóa định dạng cột '{target_col}' thành '{fmt_str}' ({count} ô được chuyển đổi)."

        # ------------------------------------------------------------------
        # MẪU 1: XỬ LÝ ĐIỀU KIỆN SO SÁNH SỐ HỌC (VD: "loại bỏ giá trị cột số lượng nhỏ hơn 5", "chỉ giữ thành tiền >= 10tr")
        # ------------------------------------------------------------------
        num_res = cls._try_numeric_condition_filter(new_df, directive, new_tags)
        if num_res is not None:
            return num_res

        # ------------------------------------------------------------------
        # MẪU 2: SẮP XẾP DỮ LIỆU (VD: "sắp xếp cột thành tiền giảm dần")
        # ------------------------------------------------------------------
        if any(w in d_norm for w in ["sap xep", "xep theo", "sort"]):
            col = cls._find_column_in_text(new_df, directive)
            if col:
                asc = not any(w in d_norm for w in ["giam dan", "cao nhat", "lon nhat", "tu cao", "desc"])
                s_num = cls._parse_numeric_series(new_df[col])
                if s_num.notnull().sum() >= max(1, len(new_df) * 0.5):
                    new_df["_sort_key"] = s_num
                    new_df = new_df.sort_values(by="_sort_key", ascending=asc, na_position="last").drop(columns=["_sort_key"]).reset_index(drop=True)
                else:
                    new_df = new_df.sort_values(by=col, ascending=asc).reset_index(drop=True)
                order_txt = "tăng dần" if asc else "giảm dần"
                return new_df, {}, f"Đã sắp xếp bảng dữ liệu theo cột '{col}' ({order_txt})."

        # ------------------------------------------------------------------
        # MẪU 3: XÓA CỘT (CHỈ KHI YÊU CẦU XÓA HẲN CỘT, KHÔNG PHẢI LỌC GIÁ TRỊ)
        # ------------------------------------------------------------------
        drop_col_m = re.match(r"^(?:xóa|xoa|bỏ|bo|ẩn|an|loại bỏ|loai bo)\s+cột\s+['\"]?([^'\"]+)['\"]?$", d)
        if drop_col_m and not any(w in d for w in ["giá trị", "dòng", "nhỏ", "lớn", "bằng", "<", ">", "="]):
            col = cls._find_column_in_text(new_df, drop_col_m.group(1))
            if col and col in new_df.columns:
                new_df = new_df.drop(columns=[col])
                return new_df, new_tags, f"Đã xóa cột '{col}' khỏi bảng dữ liệu theo chỉ đạo HITL."

        # ------------------------------------------------------------------
        # MẪU 4: CHUẨN HÓA KIỂU CHỮ (VIẾT HOA / VIẾT THƯỜNG / TITLE CASE)
        # ------------------------------------------------------------------
        if any(w in d_norm for w in ["viet hoa", "viet thuong", "chu cai dau"]):
            col = cls._find_column_in_text(new_df, directive)
            if col:
                cnt = 0
                mode = "upper" if "viet hoa toan bo" in d_norm or ("viet hoa" in d_norm and "chu cai dau" not in d_norm) else ("lower" if "viet thuong" in d_norm else "title")
                for idx, val in new_df[col].items():
                    if pd.notnull(val) and str(val).strip():
                        s_old = str(val)
                        s_new = s_old.upper() if mode == "upper" else (s_old.lower() if mode == "lower" else s_old.strip().title())
                        if s_new != s_old:
                            new_df.at[idx, col] = s_new
                            new_tags[f"{idx}_{col}"] = {"category": "format", "old": s_old, "new": s_new, "desc": f"Chuẩn hóa kiểu chữ cột '{col}'"}
                            cnt += 1
                return new_df, new_tags, f"Đã chuẩn hóa kiểu chữ ({mode}) cho cột '{col}' ({cnt} ô thay đổi)."

        # ------------------------------------------------------------------
        # MẪU 5: XỬ LÝ GIÁ TRỊ SỐ ÂM
        # ------------------------------------------------------------------
        if ("số âm" in d or "so am" in d or re.search(r"\bâm\b", d)) and any(w in d for w in ["bỏ", "xóa", "loại", "xoa", "bo", "loai"]):
            num_cols = []
            combined_neg = pd.Series([False] * len(new_df), index=new_df.index)
            for col in new_df.columns:
                s_num = cls._parse_numeric_series(new_df[col])
                if s_num.notnull().sum() >= max(1, len(new_df) * 0.3):
                    neg_mask = (s_num < 0).fillna(False)
                    if neg_mask.any():
                        num_cols.append(col)
                        combined_neg = combined_neg | neg_mask
            if combined_neg.any():
                total_removed = int(combined_neg.sum())
                kept_mask = ~combined_neg
                new_df = new_df[kept_mask].reset_index(drop=True)
                new_tags = cls._remap_tags(kept_mask, new_tags)
                return new_df, new_tags, f"Đã loại bỏ {total_removed} dòng có giá trị số âm tại các cột [{', '.join(num_cols)}]."
            return new_df, new_tags, "Bảng dữ liệu hiện tại không còn dòng nào có giá trị số âm để loại bỏ."

        if ("số âm" in d or "so am" in d) and any(w in d for w in ["thành dương", "dương", "tuyệt đối"]):
            count = 0
            for col in new_df.columns:
                s_num = cls._parse_numeric_series(new_df[col])
                for idx, v in s_num.items():
                    if pd.notnull(v) and v < 0:
                        new_df.at[idx, col] = abs(v)
                        new_tags[f"{idx}_{col}"] = {"category": "numeric", "old": str(v), "new": str(abs(v)), "desc": "Chuyển số âm sang dương"}
                        count += 1
            if count > 0:
                return new_df, new_tags, f"Đã chuyển đổi {count} giá trị số âm sang số dương."

        # ------------------------------------------------------------------
        # MẪU 6: KHỬ TRÙNG LẶP
        # ------------------------------------------------------------------
        if any(w in d_norm for w in ["trung lap", "khử trung", "loc trung", "xoa trung"]):
            b_len = len(new_df)
            new_df = new_df.drop_duplicates().reset_index(drop=True)
            return new_df, {}, f"Đã khử {b_len - len(new_df)} dòng trùng lặp khỏi bảng dữ liệu."

        # ------------------------------------------------------------------
        # MẪU 7: THAY THẾ GIÁ TRỊ Ô (VD: "thay BD thành Bình Dương", "đổi cột Chi nhánh HCM thành TP.HCM")
        # ------------------------------------------------------------------
        rep_patterns = [
            r"^(?:hãy|vui lòng|giúp tôi)?\s*(?:thay|đổi|doi|sửa|sua|chuyển|chuyen)\s+(?:các ô|ô|giá trị)?\s*['\"]?(.+?)['\"]?\s+(?:thành|thanh|sang|bằng|bang)\s+['\"]?(.+?)['\"]?(?:\s*được\s*không|\s*giúp\s*tôi|\s*nhé|\s*đi|\.|\!)?$",
            r"^(?:hãy|vui lòng)?\s*(?:thay thế|thay the)\s+(?:giá trị)?\s*['\"]?(.+?)['\"]?\s+(?:bằng|bang|thành|thanh)\s+['\"]?(.+?)['\"]?(?:\s*được\s*không|\s*giúp\s*tôi|\s*nhé|\.|\!)?$"
        ]
        for pat in rep_patterns:
            rep_m = re.search(pat, directive, re.IGNORECASE)
            if rep_m:
                raw_old = rep_m.group(1).strip("\"' ")
                new_val = rep_m.group(2).strip("\"' ")
                target_col = cls._find_column_in_text(new_df, raw_old)
                if target_col:
                    # Loại bỏ tên cột khỏi giá trị cũ cần tìm (VD: "ở cột chi nhánh BD" -> "BD")
                    c_norm_pat = re.escape(strip_accents(target_col).replace("_", " "))
                    cleaned_old = re.sub(r"(?:ở|tại|trong)?\s*(?:cột|cot)\s+", "", raw_old, flags=re.IGNORECASE).strip()
                    # Tách token tên cột nếu nó nằm đầu
                    words_c = str(target_col).split()
                    if cleaned_old.lower().startswith(str(target_col).lower()):
                        cleaned_old = cleaned_old[len(str(target_col)):].strip()
                    old_val = cleaned_old or raw_old
                    search_cols = [target_col]
                else:
                    old_val = raw_old
                    search_cols = new_df.columns.tolist()

                if old_val:
                    total_replaced = 0
                    for col in search_cols:
                        for idx, val in new_df[col].items():
                            if pd.notnull(val) and str(val).lower().strip() == old_val.lower():
                                new_df.at[idx, col] = new_val
                                new_tags[f"{idx}_{col}"] = {
                                    "category": "manual", "old": str(val), "new": str(new_val),
                                    "desc": f"Sửa theo chỉ đạo HITL ({old_val} -> {new_val})"
                                }
                                total_replaced += 1
                    if total_replaced > 0:
                        return new_df, new_tags, f"Đã thay thế thành công {total_replaced} ô từ '{old_val}' thành '{new_val}'."
                    return new_df, new_tags, f"Không tìm thấy ô nào có giá trị '{old_val}' trong bảng dữ liệu."

        # ------------------------------------------------------------------
        # MẪU 8: LỌC VÙNG MIỀN THÔNG MINH
        # ------------------------------------------------------------------
        if not any(w in d for w in ["nhỏ hơn", "lớn hơn", "bé hơn", "<", ">", "="]):
            if "miền bắc" in d or "mien bac" in d:
                if any(w in d for w in ["bỏ", "xóa", "loại", "bo", "xoa", "loai"]):
                    return cls._filter_region(new_df, new_tags, NORTH_KEYWORDS, "remove", "Miền Bắc")
                elif any(w in d for w in ["chỉ giữ", "chi giu", "giữ lại", "giu lai"]):
                    return cls._filter_region(new_df, new_tags, NORTH_KEYWORDS, "keep", "Miền Bắc")
            if "miền trung" in d or "mien trung" in d:
                if any(w in d for w in ["bỏ", "xóa", "loại", "bo", "xoa", "loai"]):
                    return cls._filter_region(new_df, new_tags, CENTRAL_KEYWORDS, "remove", "Miền Trung")
                elif any(w in d for w in ["chỉ giữ", "chi giu", "giữ lại", "giu lai"]):
                    return cls._filter_region(new_df, new_tags, CENTRAL_KEYWORDS, "keep", "Miền Trung")
            if "miền nam" in d or "mien nam" in d:
                if any(w in d for w in ["bỏ", "xóa", "loại", "bo", "xoa", "loai"]):
                    return cls._filter_region(new_df, new_tags, SOUTH_KEYWORDS, "remove", "Miền Nam")
                elif any(w in d for w in ["chỉ giữ", "chi giu", "giữ lại", "giu lai"]):
                    return cls._filter_region(new_df, new_tags, SOUTH_KEYWORDS, "keep", "Miền Nam")

        # ------------------------------------------------------------------
        # MẪU 9: BỎ HOẶC CHỈ GIỮ DÒNG THEO GIÁ TRỊ CHỮ / MÃ DÒNG (HỖ TRỢ TÊN CỘT & NHIỀU GIÁ TRỊ)
        # ------------------------------------------------------------------
        rem_pattern = r"^(?:hãy|vui lòng)?\s*(?:bỏ|xóa|xoa|loại bỏ|loai bo|loại|loai|remove|delete|lọc bỏ)\s+(.+?)(?:\s+đi|\s+giúp\s+tôi|\s+nhé|\s+ạ|\.|\!)?$"
        keep_pattern = r"^(?:hãy|vui lòng)?\s*(?:chỉ giữ lại|chỉ giữ|chi giu|giữ lại|giu lai|chỉ lấy|chi lay|lọc lấy|giữ)\s+(.+?)(?:\s+giúp\s+tôi|\s+nhé|\s+ạ|\.|\!)?$"

        action_type = None
        raw_expr = None
        km = re.search(keep_pattern, d)
        rm = re.search(rem_pattern, d)
        if km:
            action_type = "keep"
            raw_expr = km.group(1).strip()
        elif rm:
            action_type = "remove"
            raw_expr = rm.group(1).strip()

        if action_type and raw_expr and not any(w in d for w in ["nhỏ hơn", "lớn hơn", "bé hơn", "<", ">", "dưới ", "trên "]):
            explicit_col = cls._find_column_in_text(new_df, raw_expr)
            target_clean = raw_expr
            if explicit_col:
                # Loại bỏ tên cột và các từ đệm xung quanh khỏi chuỗi giá trị cần tìm
                col_pat = re.escape(explicit_col.lower())
                target_clean = re.sub(rf"(?:ở|tại|trong)?\s*(?:cột|cot)?\s*{col_pat}\s*(?:là|bằng|=|có giá trị)?", "", target_clean, flags=re.IGNORECASE).strip()

            target_clean = re.sub(r"^(các dòng|dòng|giá trị|nhóm|kênh|khu vực|chi nhánh|trạng thái|phương thức|bản ghi|dữ liệu|hàng|thứ|có mã|có giá trị|có|là)\s+", "", target_clean, flags=re.IGNORECASE).strip()
            target_clean = re.sub(r"\s+(đi|lại)$", "", target_clean, flags=re.IGNORECASE).strip("\"' ")

            if target_clean and target_clean not in ["dữ liệu", "tất cả"]:
                # Kiểm tra trường hợp xóa dòng theo STT / Mã dòng (chỉ 1 số nguyên)
                if action_type == "remove" and target_clean.isdigit() and not explicit_col:
                    row_num = int(target_clean)
                    for col in new_df.columns:
                        series_str = new_df[col].astype(str).str.lower()
                        m_id = series_str.str.contains(f"{row_num:03d}", na=False) | (series_str == str(row_num)) | series_str.str.endswith(f"-{row_num}")
                        if m_id.any():
                            count = int(m_id.sum())
                            kept_mask = ~m_id
                            new_df = new_df[kept_mask].reset_index(drop=True)
                            new_tags = cls._remap_tags(kept_mask, new_tags)
                            return new_df, new_tags, f"Đã loại bỏ {count} dòng có '{col}' chứa '{target_clean}' theo chỉ đạo HITL."
                    if 1 <= row_num <= len(new_df):
                        kept_mask = pd.Series([i != (row_num - 1) for i in range(len(new_df))], index=new_df.index)
                        new_df = new_df.drop(new_df.index[row_num - 1]).reset_index(drop=True)
                        new_tags = cls._remap_tags(kept_mask, new_tags)
                        return new_df, new_tags, f"Đã loại bỏ dòng thứ {row_num} trên bảng dữ liệu theo chỉ đạo HITL."

                # Hỗ trợ nhiều giá trị phân tách bởi ' và ', ' hoặc ', ','
                vals = [v.strip("\"' ") for v in re.split(r"\s+(?:và|hoặc)\s+|,", target_clean) if v.strip("\"' ")]
                search_cols = [explicit_col] if explicit_col else new_df.columns.tolist()

                for col in search_cols:
                    series_str = new_df[col].astype(str).str.strip().str.lower()
                    combined_m = pd.Series([False] * len(new_df), index=new_df.index)
                    for v in vals:
                        combined_m = combined_m | series_str.str.contains(re.escape(v.lower()), na=False)
                    if combined_m.any():
                        if action_type == "remove":
                            count = int(combined_m.sum())
                            kept_mask = ~combined_m
                            new_df = new_df[kept_mask].reset_index(drop=True)
                            new_tags = cls._remap_tags(kept_mask, new_tags)
                            return new_df, new_tags, f"Đã loại bỏ {count} dòng có '{col}' chứa [{', '.join(vals)}] theo chỉ đạo HITL."
                        else:
                            kept_mask = combined_m
                            new_df = new_df[kept_mask].reset_index(drop=True)
                            new_tags = cls._remap_tags(kept_mask, new_tags)
                            return new_df, new_tags, f"Đã giữ lại {len(new_df)} dòng có '{col}' chứa [{', '.join(vals)}] (loại bỏ các bản ghi còn lại)."

        # ------------------------------------------------------------------
        # MẪU 10: ĐIỀN GIÁ TRỊ KHUYẾT / Ô TRỐNG
        # ------------------------------------------------------------------
        if any(w in d for w in ["điền thiếu", "điền khuyết", "điền null", "điền trống", "điền ô trống", "ô trống", "giá trị thiếu", "dien thieu", "dien trong", "dien o trong"]):
            fill_val = "Chưa xác định"
            if "trung vị" in d or "median" in d:
                res = DataCleaner.auto_clean(new_df, {"handle_missing": "median", "fix_negatives": True})
                return res["df"], res["cell_tags"], "Đã điền các giá trị thiếu bằng giá trị trung vị (Median)."
            elif "trung bình" in d or "mean" in d:
                res = DataCleaner.auto_clean(new_df, {"handle_missing": "mean", "fix_negatives": True})
                return res["df"], res["cell_tags"], "Đã điền các giá trị thiếu bằng giá trị trung bình (Mean)."

            val_match = re.search(r"(?:bằng|thành|là)\s+['\"]?([^'\"]+)['\"]?", directive, re.IGNORECASE)
            if val_match:
                fill_val = val_match.group(1).strip()

            fill_count = 0
            for col in new_df.columns:
                for idx, val in new_df[col].items():
                    if pd.isnull(val) or str(val).strip() in ["", "nan", "null", "none", "None"]:
                        new_df.at[idx, col] = fill_val
                        new_tags[f"{idx}_{col}"] = {
                            "category": "missing", "old": "Trống (Null)", "new": fill_val,
                            "desc": f"Điền theo chỉ đạo HITL: '{fill_val}'"
                        }
                        fill_count += 1
            if fill_count > 0:
                return new_df, new_tags, f"Đã điền {fill_count} ô khuyết bằng '{fill_val}'."
            return new_df, new_tags, "Bảng dữ liệu hiện tại không còn ô trống (null) nào."

        return None

    @classmethod
    def _try_numeric_condition_filter(cls, df: pd.DataFrame, directive: str, tags: dict):
        """
        Phân tích chỉ đạo điều kiện số học bằng tiếng Việt tự nhiên (hỗ trợ cả điều kiện đơn & kép).
        VD: "loại bỏ giá trị cột số lượng nhỏ hơn 5", "chỉ giữ thành tiền >= 10 triệu", "bỏ đơn giá từ 2tr trở xuống"
        """
        from app.data_cleaner import DataCleaner

        d = directive.lower().strip()
        d_norm = strip_accents(d)

        # Kiểm tra câu có chứa chỉ báo so sánh số học hay không
        has_num_op = any(k in d_norm for k in [
            "nho hon", "be hon", "lon hon", "thap hon", "cao hon", "it hon", "nhieu hon",
            "duoi ", "tren ", "tro len", "tro xuong", "toi da", "toi thieu", "it nhat",
            "khong qua", "vuot qua", "khong bang", "khac ", "bang ", "<", ">", "=", "!="
        ]) or bool(re.search(rf"\btu\s+{NUM_TOKEN_PAT}\s+(?:den|toi)\s+{NUM_TOKEN_PAT}", d_norm))
        if not has_num_op:
            return None

        # Xác định hành động remove vs keep
        if any(w in d_norm for w in ["chi giu", "giu lai", "chi lay", "loc lay"]):
            action = "keep"
        elif any(w in d_norm for w in ["bo", "xoa", "loai", "remove", "delete"]):
            action = "remove"
        else:
            return None

        logic = "OR" if " hoac " in d_norm else "AND"
        clauses = re.split(r"\s+(?:và|hoặc|va|hoac)\s+", directive, flags=re.IGNORECASE)

        combined_mask = None
        last_col = None
        desc_parts = []

        for clause in clauses:
            c_col = cls._find_column_in_text(df, clause) or last_col or cls._find_column_in_text(df, directive)
            if not c_col:
                continue
            last_col = c_col

            cl_norm = strip_accents(clause.lower())
            num_series = cls._parse_numeric_series(df[c_col])
            if num_series.notnull().sum() == 0:
                continue

            clause_mask = None

            # Trường hợp 1: Khoảng "từ A đến B"
            range_m = re.search(rf"\btu\s+{NUM_TOKEN_PAT}\s+(?:den|toi)\s+{NUM_TOKEN_PAT}", cl_norm)
            if range_m:
                v1 = DataCleaner.parse_vn_number(range_m.group(1))
                v2 = DataCleaner.parse_vn_number(range_m.group(2))
                if not (np.isnan(v1) or np.isnan(v2)):
                    lo, hi = min(v1, v2), max(v1, v2)
                    clause_mask = ((num_series >= lo) & (num_series <= hi)).fillna(False)
                    desc_parts.append(f"'{c_col}' từ {lo:,.0f} đến {hi:,.0f}")

            # Trường hợp 2: "từ V trở lên" / "từ V trở xuống"
            if clause_mask is None:
                m_up = re.search(rf"tu\s+{NUM_TOKEN_PAT}\s+tro\s+len", cl_norm)
                m_down = re.search(rf"tu\s+{NUM_TOKEN_PAT}\s+tro\s+xuong", cl_norm)
                if m_up:
                    v = DataCleaner.parse_vn_number(m_up.group(1))
                    if not np.isnan(v):
                        clause_mask = (num_series >= v).fillna(False)
                        desc_parts.append(f"'{c_col}' >= {v:,.0f}")
                elif m_down:
                    v = DataCleaner.parse_vn_number(m_down.group(1))
                    if not np.isnan(v):
                        clause_mask = (num_series <= v).fillna(False)
                        desc_parts.append(f"'{c_col}' <= {v:,.0f}")

            # Trường hợp 3: Các toán tử so sánh chuẩn (ưu tiên mẫu dài trước!)
            if clause_mask is None:
                op_patterns = [
                    (r"(?:nho hon hoac bang|be hon hoac bang|khong lon hon|toi da|<=)\s*" + NUM_TOKEN_PAT, "<="),
                    (r"(?:lon hon hoac bang|khong nho hon|it nhat|toi thieu|>=)\s*" + NUM_TOKEN_PAT, ">="),
                    (r"(?:nho hon|be hon|thap hon|it hon|duoi|<)\s*" + NUM_TOKEN_PAT, "<"),
                    (r"(?:lon hon|cao hon|nhieu hon|vuot qua|tren|>)\s*" + NUM_TOKEN_PAT, ">"),
                    (r"(?:khac|không bằng|khong bang|!=|<>)\s*" + NUM_TOKEN_PAT, "!="),
                    (r"(?:bang|=)\s*" + NUM_TOKEN_PAT, "=="),
                ]
                for pat, op_sym in op_patterns:
                    m_op = re.search(pat, cl_norm)
                    if m_op:
                        num_val = DataCleaner.parse_vn_number(m_op.group(1))
                        if not np.isnan(num_val):
                            if op_sym == "<":
                                clause_mask = (num_series < num_val).fillna(False)
                            elif op_sym == "<=":
                                clause_mask = (num_series <= num_val).fillna(False)
                            elif op_sym == ">":
                                clause_mask = (num_series > num_val).fillna(False)
                            elif op_sym == ">=":
                                clause_mask = (num_series >= num_val).fillna(False)
                            elif op_sym == "!=":
                                clause_mask = (num_series != num_val).fillna(False)
                            else:
                                clause_mask = (num_series == num_val).fillna(False)
                            val_fmt = f"{int(num_val):,}" if num_val == int(num_val) else f"{num_val:,.2f}"
                            desc_parts.append(f"'{c_col}' {op_sym} {val_fmt}")
                            break

            if clause_mask is not None:
                if combined_mask is None:
                    combined_mask = clause_mask
                else:
                    combined_mask = (combined_mask | clause_mask) if logic == "OR" else (combined_mask & clause_mask)

        if combined_mask is None or not desc_parts:
            return None

        cond_desc = (" HOẶC " if logic == "OR" else " VÀ ").join(desc_parts)
        if action == "remove":
            removed = int(combined_mask.sum())
            kept_mask = ~combined_mask
            new_df = df[kept_mask].reset_index(drop=True)
            new_tags = cls._remap_tags(kept_mask, tags)
            return new_df, new_tags, f"Đã loại bỏ {removed} dòng thỏa điều kiện [{cond_desc}] theo chỉ đạo HITL (còn lại {len(new_df)} dòng)."
        else:
            kept_mask = combined_mask
            new_df = df[kept_mask].reset_index(drop=True)
            new_tags = cls._remap_tags(kept_mask, tags)
            return new_df, new_tags, f"Đã giữ lại {len(new_df)} dòng thỏa điều kiện [{cond_desc}] theo chỉ đạo HITL."

    @classmethod
    def _filter_region(cls, df: pd.DataFrame, tags: dict, keywords: list, action: str, region_name: str):
        """Lọc vùng miền dựa trên danh sách từ khóa tỉnh thành/vùng"""
        target_cols = [c for c in df.columns if any(k in c.lower() for k in ["chi nhánh", "chi_nhanh", "khu vực", "khu_vuc", "vùng", "vung", "tỉnh", "thành phố", "city", "branch", "region"])]
        if not target_cols:
            target_cols = df.columns.tolist()

        combined_mask = pd.Series([False] * len(df), index=df.index)
        detected_col = None

        for col in target_cols:
            series_str = df[col].astype(str).str.lower()
            for kw in keywords:
                m = series_str.str.contains(kw, na=False)
                if m.any():
                    combined_mask = combined_mask | m
                    detected_col = col

        if combined_mask.any():
            if action == "remove":
                count = int(combined_mask.sum())
                kept_mask = ~combined_mask
                new_df = df[kept_mask].reset_index(drop=True)
                new_tags = cls._remap_tags(kept_mask, tags)
                return new_df, new_tags, f"Đã loại bỏ {count} dòng thuộc {region_name} (dựa trên cột '{detected_col}')."
            else:
                kept_mask = combined_mask
                new_df = df[kept_mask].reset_index(drop=True)
                new_tags = cls._remap_tags(kept_mask, tags)
                return new_df, new_tags, f"Đã giữ lại {len(new_df)} dòng thuộc {region_name} (đã loại bỏ các vùng khác)."

        return df, tags, f"Không tìm thấy bản ghi nào thuộc {region_name} trong bảng dữ liệu."

    @classmethod
    def _execute_via_gemini(cls, df: pd.DataFrame, directive: str, cell_tags: dict, api_key: str) -> tuple:
        """Sử dụng Google Gemini API để phân tích và lập kế hoạch thực thi mọi chỉ đạo phức tạp"""
        if not api_key:
            return None, "Chưa có GEMINI_API_KEY"

        cols = df.columns.tolist()
        sample_rows = df.head(3).fillna("").to_dict(orient="records")
        unique_samples = {}
        for c in cols:
            if df[c].dtype == "object" or str(df[c].dtype) == "str" or df[c].nunique() <= 12:
                unique_samples[c] = [str(v) for v in df[c].dropna().unique()[:8]]

        prompt = f"""Bạn là chuyên gia xử lý dữ liệu bảng (Data Cleaning & HITL Assistant).
Người dùng ra chỉ đạo bằng tiếng Việt tự nhiên: "{directive}"

Thông tin bảng dữ liệu hiện có:
- Tên các cột: {json.dumps(cols, ensure_ascii=False)}
- Các giá trị tiêu biểu của từng cột: {json.dumps(unique_samples, ensure_ascii=False, default=str)}
- 3 dòng dữ liệu mẫu: {json.dumps(sample_rows, ensure_ascii=False, default=str)}

Hãy chuyển chỉ đạo trên thành kế hoạch JSON thuần (chỉ trả về JSON hợp lệ, không markdown):
{{
  "actions": [
    {{
      "action": "filter_remove" | "filter_keep" | "replace" | "fill_na" | "format_date" | "remove_negatives" | "fix_negatives" | "remove_duplicates" | "sort" | "drop_column",
      "column": "tên cột chính xác trong danh sách cột (hoặc 'ALL' nếu áp dụng toàn bảng)",
      "operator": "contains" | "equals" | "not_equals" | "<" | "<=" | ">" | ">=",
      "value": "giá trị điều kiện / giá trị cũ cần thay (quy đổi chữ số tiếng Việt như '5 triệu' -> '5000000', '500k' -> '500000')",
      "replace_with": "giá trị mới (nếu replace / fill_na) hoặc 'asc'/'desc' (nếu sort)",
      "conditions": [
        {{"column": "tên cột", "operator": "<|<=|>|>=|contains|equals|not_equals", "value": "giá trị"}}
      ],
      "logic": "AND" | "OR",
      "description": "mô tả ngắn gọn bằng tiếng Việt về kết quả đã thực hiện"
    }}
  ]
}}"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1000,
                "responseMimeType": "application/json"
            }
        }
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        last_err = ""
        for model_name in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            req = urllib.request.Request(
                url,
                data=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=14) as response:
                    res_json = json.loads(response.read().decode("utf-8"))
                    text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                    m = re.search(r"\{[\s\S]*\}", text)
                    if not m:
                        continue
                    plan_root = json.loads(m.group(0))
                    actions = plan_root.get("actions") if isinstance(plan_root.get("actions"), list) else [plan_root]
                    applied = cls._apply_gemini_actions(df, actions, cell_tags)
                    if applied is not None:
                        return applied, ""
            except urllib.error.HTTPError as e:
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8")
                except Exception:
                    pass
                last_err = f"HTTP {e.code}: {err_body[:160] or e.reason}"
                if e.code == 401:
                    break
                continue
            except Exception as e:
                last_err = str(e)
                continue

        return None, last_err

    @classmethod
    def _match_column(cls, df: pd.DataFrame, col_name: str):
        if not col_name or col_name == "ALL":
            return None
        if col_name in df.columns:
            return col_name
        norm_target = strip_accents(str(col_name))
        for c in df.columns:
            if strip_accents(c) == norm_target or norm_target in strip_accents(c):
                return c
        return None

    @classmethod
    def _build_condition_mask(cls, series: pd.Series, op: str, val) -> pd.Series:
        from app.data_cleaner import DataCleaner
        op = (op or "contains").strip().lower()
        if op in ["<", "<=", ">", ">=", "less_than", "greater_than"]:
            num_val = DataCleaner.parse_vn_number(val)
            if np.isnan(num_val):
                return pd.Series([False] * len(series), index=series.index)
            num_s = cls._parse_numeric_series(series)
            if op in ["<", "less_than"]:
                return (num_s < num_val).fillna(False)
            elif op == "<=":
                return (num_s <= num_val).fillna(False)
            elif op in [">", "greater_than"]:
                return (num_s > num_val).fillna(False)
            elif op == ">=":
                return (num_s >= num_val).fillna(False)

        s_str = series.astype(str).str.strip().str.lower()
        v_str = str(val).strip().lower()
        if op in ["equals", "=", "=="]:
            m = s_str == v_str
            if not m.any():
                try:
                    num_val = DataCleaner.parse_vn_number(val)
                    if not np.isnan(num_val):
                        num_s = cls._parse_numeric_series(series)
                        m = (num_s == num_val).fillna(False)
                except Exception:
                    pass
            return m
        elif op in ["not_equals", "!="]:
            return s_str != v_str
        else:
            return s_str.str.contains(re.escape(v_str), na=False)

    @classmethod
    def _apply_gemini_actions(cls, df: pd.DataFrame, actions: list, cell_tags: dict):
        new_df = df.copy()
        new_tags = dict(cell_tags)
        logs = []

        for act in actions:
            action = (act.get("action") or "").strip().lower()
            raw_col = act.get("column")
            col = cls._match_column(new_df, raw_col)
            op = act.get("operator", "contains")
            val = act.get("value", "")
            rep_with = act.get("replace_with", "")
            desc = act.get("description", "")
            conditions = act.get("conditions")
            logic = (act.get("logic") or "AND").upper()

            if action in ["filter_remove", "filter_keep"]:
                combined_m = None
                if isinstance(conditions, list) and len(conditions) > 0:
                    for cond in conditions:
                        c_match = cls._match_column(new_df, cond.get("column") or raw_col)
                        if c_match:
                            cm = cls._build_condition_mask(new_df[c_match], cond.get("operator", "contains"), cond.get("value", ""))
                            combined_m = cm if combined_m is None else ((combined_m | cm) if logic == "OR" else (combined_m & cm))
                elif col:
                    combined_m = cls._build_condition_mask(new_df[col], op, val)

                if combined_m is not None:
                    if action == "filter_remove":
                        removed = int(combined_m.sum())
                        kept_mask = ~combined_m
                        new_df = new_df[kept_mask].reset_index(drop=True)
                        new_tags = cls._remap_tags(kept_mask, new_tags)
                        logs.append(desc or f"Đã loại bỏ {removed} dòng theo chỉ đạo HITL.")
                    else:
                        kept_mask = combined_m
                        new_df = new_df[kept_mask].reset_index(drop=True)
                        new_tags = cls._remap_tags(kept_mask, new_tags)
                        logs.append(desc or f"Đã giữ lại {len(new_df)} dòng theo chỉ đạo HITL.")

            elif action == "replace":
                target_cols = [col] if col else new_df.columns.tolist()
                cnt = 0
                for c in target_cols:
                    for idx, cur_v in new_df[c].items():
                        if pd.notnull(cur_v) and str(cur_v).strip().lower() == str(val).strip().lower():
                            new_df.at[idx, c] = rep_with
                            new_tags[f"{idx}_{c}"] = {
                                "category": "manual", "old": str(cur_v), "new": str(rep_with),
                                "desc": f"AI HITL: {cur_v} -> {rep_with}"
                            }
                            cnt += 1
                logs.append(desc or f"Đã thay thế {cnt} ô từ '{val}' thành '{rep_with}'.")

            elif action == "fill_na":
                fill_v = rep_with if rep_with else "Chưa xác định"
                target_cols = [col] if col else new_df.columns.tolist()
                cnt = 0
                for c in target_cols:
                    for idx, cur_v in new_df[c].items():
                        if pd.isnull(cur_v) or str(cur_v).strip().lower() in ["", "nan", "null", "none"]:
                            new_df.at[idx, c] = fill_v
                            new_tags[f"{idx}_{c}"] = {
                                "category": "missing", "old": "Trống (Null)", "new": str(fill_v),
                                "desc": f"AI HITL điền '{fill_v}'"
                            }
                            cnt += 1
                logs.append(desc or f"Đã điền {cnt} ô khuyết bằng '{fill_v}'.")

            elif action == "format_date" and col:
                fmt_str = str(val or "YYYY-MM").strip()
                py_fmt = re.sub(r'YYYY', '%Y', fmt_str, flags=re.IGNORECASE)
                py_fmt = re.sub(r'(?<!%)YY', '%y', py_fmt, flags=re.IGNORECASE)
                py_fmt = re.sub(r'MM', '%m', py_fmt, flags=re.IGNORECASE)
                py_fmt = re.sub(r'DD', '%d', py_fmt, flags=re.IGNORECASE)
                cnt = 0
                for idx, cur_v in new_df[col].items():
                    if pd.notnull(cur_v) and str(cur_v).strip():
                        try:
                            s_dt = str(cur_v).strip()
                            is_iso = bool(re.match(r'^\d{4}[\-\/\.]', s_dt))
                            dt = pd.to_datetime(s_dt, format='mixed', dayfirst=not is_iso)
                            nv = dt.strftime(py_fmt)
                            new_df.at[idx, col] = nv
                            new_tags[f"{idx}_{col}"] = {"category": "format", "old": str(cur_v), "new": nv, "desc": f"Định dạng {fmt_str}"}
                            cnt += 1
                        except Exception:
                            pass
                logs.append(desc or f"Đã định dạng {cnt} ô cột '{col}' thành '{fmt_str}'.")

            elif action == "remove_negatives":
                target_cols = [col] if col else new_df.columns.tolist()
                removed = 0
                for c in target_cols:
                    s_num = cls._parse_numeric_series(new_df[c])
                    if s_num.notnull().sum() >= max(1, len(new_df) * 0.3):
                        neg_m = (s_num < 0).fillna(False)
                        if neg_m.any():
                            removed += int(neg_m.sum())
                            kept_mask = ~neg_m
                            new_df = new_df[kept_mask].reset_index(drop=True)
                            new_tags = cls._remap_tags(kept_mask, new_tags)
                logs.append(desc or f"Đã loại bỏ {removed} dòng có giá trị âm.")

            elif action == "fix_negatives":
                target_cols = [col] if col else new_df.columns.tolist()
                cnt = 0
                for c in target_cols:
                    s_num = cls._parse_numeric_series(new_df[c])
                    for idx, v in s_num.items():
                        if pd.notnull(v) and v < 0:
                            new_df.at[idx, c] = abs(v)
                            new_tags[f"{idx}_{c}"] = {"category": "numeric", "old": str(v), "new": str(abs(v)), "desc": "Chuyển số âm thành dương"}
                            cnt += 1
                logs.append(desc or f"Đã chuyển {cnt} giá trị âm thành số dương.")

            elif action == "remove_duplicates":
                b_len = len(new_df)
                new_df = new_df.drop_duplicates().reset_index(drop=True)
                logs.append(desc or f"Đã khử {b_len - len(new_df)} dòng trùng lặp.")

            elif action == "sort" and col:
                asc = str(rep_with or val or "asc").lower() != "desc"
                s_num = cls._parse_numeric_series(new_df[col])
                if s_num.notnull().sum() >= max(1, len(new_df) * 0.5):
                    new_df["_sort_k"] = s_num
                    new_df = new_df.sort_values(by="_sort_k", ascending=asc, na_position="last").drop(columns=["_sort_k"]).reset_index(drop=True)
                else:
                    new_df = new_df.sort_values(by=col, ascending=asc).reset_index(drop=True)
                logs.append(desc or f"Đã sắp xếp cột '{col}' theo thứ tự {'tăng dần' if asc else 'giảm dần'}.")

            elif action == "drop_column" and col:
                new_df = new_df.drop(columns=[col])
                logs.append(desc or f"Đã xóa cột '{col}'.")

        if logs:
            return new_df, new_tags, " ".join(logs)
        return None

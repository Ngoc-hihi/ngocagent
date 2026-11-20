"""
directive_engine.py - Bộ xử lý Chỉ đạo Rà soát Dữ liệu HITL thông minh bằng NLP & AI
- Thực thi tức thời (sub-millisecond) các chỉ đạo rà soát, lọc, sửa dữ liệu bằng tiếng Việt
- Hỗ trợ đa dạng mẫu câu:
  + Lọc bỏ: "bỏ miền bắc", "xóa website", "loại bỏ chi nhánh BD", "bỏ đơn hàng hoàn trả", "bỏ số âm"
  + Chỉ giữ: "chỉ giữ miền nam", "chỉ lấy Shopee", "giữ lại cửa hàng và website"
  + Thay thế ô: "thay BD thành Bình Dương", "đổi Website thành Online", "sửa thiếu thành Chưa xác định"
  + Điền khuyết: "điền ô trống là Chưa xác định", "điền thiếu bằng trung vị"
  + Điều kiện số học: "bỏ thành tiền nhỏ hơn 1000000", "xóa số lượng < 0"
- Tích hợp Fallback Google Gemini AI khi gặp các yêu cầu phân tích ngữ nghĩa phức tạp
- Cập nhật trực tiếp DataFrame, nhãn màu cell_tags và nhật ký Audit Log
"""

import os
import json
import re
import urllib.request
import unicodedata
import pandas as pd
import numpy as np

def strip_accents(s: str) -> str:
    if not isinstance(s, str):
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()

def _get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key and os.path.exists(".env"):
        try:
            with open(".env", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip("\"'")
                        break
        except Exception:
            pass
    return key or "AQ.Ab8RN6LTbwMsX7CvKdD8NtFTQlDacI-x3IAQnhWSEKrdzrDUjA"

GEMINI_API_KEY = _get_gemini_api_key()

# Từ điển địa lý phục vụ lọc vùng miền thông minh
NORTH_KEYWORDS = ['bắc', 'miền bắc', 'hà nội', 'hải phòng', 'quảng ninh', 'bắc ninh', 'hải dương', 'nam định', 'hà nam', 'thái bình', 'hn', 'hp']
CENTRAL_KEYWORDS = ['trung', 'miền trung', 'đà nẵng', 'huế', 'quảng nam', 'quảng ngãi', 'bình định', 'khánh hòa', 'nha trang', 'đn']
SOUTH_KEYWORDS = ['nam', 'miền nam', 'hồ chí minh', 'tp. hồ chí minh', 'sài gòn', 'bình dương', 'cần thơ', 'đồng nai', 'vũng tàu', 'hcm', 'bd', 'ct']

class DirectiveEngine:
    @classmethod
    def execute(cls, df: pd.DataFrame, directive: str, cell_tags: dict = None) -> tuple:
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

        # 1. TẦNG 1: Phân tích và thực thi siêu tốc bằng Local NLP Engine (< 1ms)
        nlp_res = cls._execute_via_nlp(df, d_text, tags)
        if nlp_res is not None:
            return nlp_res

        # 2. TẦNG 2: Google Gemini AI cho các chỉ đạo ngữ nghĩa phức tạp (nếu có API Key)
        if GEMINI_API_KEY:
            try:
                ai_res = cls._execute_via_gemini(df, d_text, tags)
                if ai_res is not None:
                    return ai_res
            except Exception:
                pass

        return df, tags, f"Đã ghi nhận chỉ đạo: '{d_text}'. (Gợi ý: bạn có thể nhập 'bỏ Miền Bắc', 'thay BD thành Bình Dương', 'chỉ giữ Website', 'bỏ các dòng số lượng âm')."

    @classmethod
    def _execute_via_nlp(cls, df: pd.DataFrame, directive: str, cell_tags: dict):
        """Phân tích các mẫu câu phổ biến bằng NLP tiếng Việt"""
        d = directive.lower().strip()
        new_df = df.copy()
        new_tags = dict(cell_tags)

        # Mẫu 0: Định dạng Ngày tháng & Thời gian (VD: "cột tháng định dạng là YYYY - MM", "định dạng cột tháng là YYYY-MM", "định dạng ngày tháng là DD/MM/YYYY")
        is_format_directive = any(w in d for w in ["định dạng", "dinh dang", "format", "chuẩn hóa định dạng"]) or (
            any(k in d for k in ["yyyy", "mm", "dd"]) and any(w in d for w in ["là", "thành", "sang", "thanh", "bằng"])
        )
        if is_format_directive:
            fmt_m = re.search(r"['\"]?([Yy]{2,4}[\s\-\/\.\:]+[Mm]{1,2}(?:[\s\-\/\.\:]+[Dd]{1,2})?|[Dd]{1,2}[\s\-\/\.\:]+[Mm]{1,2}(?:[\s\-\/\.\:]+[Yy]{2,4})?|[Mm]{1,2}[\s\-\/\.\:]+[Yy]{2,4})['\"]?", directive)
            if fmt_m:
                fmt_str = fmt_m.group(1).strip("\"' ")
                py_fmt = fmt_str
                py_fmt = re.sub(r'YYYY', '%Y', py_fmt, flags=re.IGNORECASE)
                py_fmt = re.sub(r'(?<!%)YY', '%y', py_fmt, flags=re.IGNORECASE)
                if 'DD' in fmt_str.upper() or 'YYYY' in fmt_str.upper():
                    py_fmt = re.sub(r'MM', '%m', py_fmt, flags=re.IGNORECASE)
                py_fmt = re.sub(r'DD', '%d', py_fmt, flags=re.IGNORECASE)

                # Xác định cột mục tiêu
                target_col = None
                col_m = re.search(r"(?:cột|cot)\s+([^\s,]+)", d)
                if col_m:
                    kw = col_m.group(1).strip()
                    norm_kw = strip_accents(kw)
                    target_col = next((c for c in new_df.columns if kw in c.lower() or norm_kw in strip_accents(c)), None)

                if not target_col:
                    if "tháng" in d or "thang" in d or "month" in d:
                        target_col = next((c for c in new_df.columns if any(k in strip_accents(c) for k in ["thang", "month"])), None)
                    elif "ngày" in d or "ngay" in d or "date" in d:
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
                                dt = pd.to_datetime(str(val).strip(), format='mixed', dayfirst=True)
                                new_val = dt.strftime(py_fmt)
                                new_df.at[idx, target_col] = new_val
                                new_tags[f"{idx}_{target_col}"] = {
                                    "category": "format",
                                    "old": str(val),
                                    "new": new_val,
                                    "desc": f"Định dạng lại theo chỉ đạo HITL: '{fmt_str}'"
                                }
                                count += 1
                            except Exception:
                                pass
                    return new_df, new_tags, f"Đã chuẩn hóa định dạng cột '{target_col}' thành '{fmt_str}' ({count} ô được chuyển đổi)."
                else:
                    return new_df, new_tags, f"Không tìm thấy cột ngày/tháng nào trong bảng dữ liệu để định dạng thành '{fmt_str}'."

        # Mẫu 1: Thay thế / Đổi giá trị ô (VD: "thay BD thành Bình Dương", "đổi Website sang Web Online")
        rep_patterns = [
            r"(?:thay|đổi|doi|sửa|sua|chuyển|chuyen)\s+(?:các ô|ô|giá trị)?\s*['\"]?(.+?)['\"]?\s+(?:thành|thanh|sang|bằng|bang)\s+['\"]?(.+?)['\"]?(?:\s*được\s*không|\s*giúp\s*tôi|\s*nhé|\.|\!)?$",
            r"(?:thay thế|thay the)\s+['\"]?(.+?)['\"]?\s+(?:bằng|bang|thành|thanh)\s+['\"]?(.+?)['\"]?(?:\s*được\s*không|\s*giúp\s*tôi|\s*nhé|\.|\!)?$"
        ]
        for pat in rep_patterns:
            rep_m = re.search(pat, directive, re.IGNORECASE)
            if rep_m:
                old_val = rep_m.group(1).strip("\"' ")
                new_val = rep_m.group(2).strip("\"' ")
                total_replaced = 0
                for col in new_df.columns:
                    for idx, val in new_df[col].items():
                        if pd.notnull(val) and str(val).lower().strip() == old_val.lower():
                            new_df.at[idx, col] = new_val
                            new_tags[f"{idx}_{col}"] = {
                                "category": "manual",
                                "old": str(val),
                                "new": str(new_val),
                                "desc": f"Sửa theo chỉ đạo HITL ({old_val} -> {new_val})"
                            }
                            total_replaced += 1
                if total_replaced > 0:
                    return new_df, new_tags, f"Đã chuẩn hóa và thay thế thành công {total_replaced} ô từ '{old_val}' thành '{new_val}'."
                else:
                    return new_df, new_tags, f"Không tìm thấy ô nào có giá trị '{old_val}' trong bảng dữ liệu (có thể đã được chuẩn hóa trước đó)."

        # Mẫu 2: Xử lý giá trị số âm (VD: "bỏ số âm", "xóa số lượng âm", "chuyển số âm thành dương")
        if ("số âm" in d or "so am" in d or "âm" in d) and any(w in d for w in ["bỏ", "xóa", "loại", "xoa", "bo", "loai"]):
            num_cols = []
            total_removed = 0
            for col in new_df.columns:
                s_num = pd.to_numeric(new_df[col], errors="coerce")
                if s_num.notnull().sum() >= max(1, len(new_df) * 0.3):
                    neg_mask = s_num < 0
                    if neg_mask.any():
                        num_cols.append(col)
                        total_removed += int(neg_mask.sum())
                        new_df = new_df[~neg_mask].reset_index(drop=True)
            if num_cols:
                return new_df, new_tags, f"Đã loại bỏ {total_removed} dòng có giá trị số âm tại các cột [{', '.join(num_cols)}]."
            else:
                return new_df, new_tags, "Bảng dữ liệu hiện tại không còn dòng nào có giá trị số âm để loại bỏ."

        if ("số âm" in d or "so am" in d) and any(w in d for w in ["thành dương", "dương", "tuyệt đối"]):
            count = 0
            for col in new_df.columns:
                s_num = pd.to_numeric(new_df[col], errors="coerce")
                for idx, v in s_num.items():
                    if pd.notnull(v) and v < 0:
                        new_df.at[idx, col] = abs(v)
                        new_tags[f"{idx}_{col}"] = {
                            "category": "numeric",
                            "old": str(v),
                            "new": str(abs(v)),
                            "desc": "Chuyển số âm sang dương theo chỉ đạo HITL"
                        }
                        count += 1
            if count > 0:
                return new_df, new_tags, f"Đã chuyển đổi {count} giá trị số âm sang số dương."

        # Mẫu 3: Lọc vùng miền thông minh (VD: "bỏ miền bắc", "bỏ miền trung", "chỉ giữ miền nam")
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

        has_complex_condition = any(w in d for w in ["nhỏ hơn", "lớn hơn", "bé hơn", "dưới ", "trên ", "trở lên", "trở xuống", "<", ">", "=", " và ", " hoặc ", "ngoại trừ", "trừ "])

        # Mẫu 4: Bỏ / Xóa dòng theo giá trị bất kỳ (VD: "bỏ website", "xóa shopee", "bỏ chi nhánh hải phòng", "xóa hoàn trả", "xóa dòng 13", "xóa dữ liệu 13 đi")
        rem_pattern = r"(?:bỏ|xóa|xoa|loại bỏ|loai bo|remove|delete)\s+(?:các dòng|dòng|nhóm|kênh|khu vực|chi nhánh|trạng thái|phương thức|bản ghi|dữ liệu|hàng)?\s*['\"]?([^'\"]+?)['\"]?(?:\s+đi|\s+giúp\s+tôi|\s+nhé|\.|\!)?$"
        rem_m = re.search(rem_pattern, d) if not has_complex_condition else None
        if rem_m:
            target = rem_m.group(1).strip()
            target = re.sub(r"^(các\s+dòng|dòng|nhóm|kênh|khu\s+vực|chi\s+nhánh|trạng\s+thái|bản\s+ghi|dữ\s+liệu|hàng|thứ|có\s+mã)\s+", "", target, flags=re.IGNORECASE).strip()
            target = re.sub(r"\s+đi$", "", target, flags=re.IGNORECASE).strip()
            if target and target not in ["dữ liệu", "tất cả"]:
                # Nếu target là một số nguyên (ví dụ: dòng 13, dữ liệu 13)
                if target.isdigit():
                    row_num = int(target)
                    for col in new_df.columns:
                        series_str = new_df[col].astype(str).str.lower()
                        m_id = series_str.str.contains(f"{row_num:03d}", na=False) | (series_str == str(row_num)) | series_str.str.endswith(f"-{row_num}")
                        if m_id.any():
                            count = int(m_id.sum())
                            new_df = new_df[~m_id].reset_index(drop=True)
                            return new_df, new_tags, f"Đã loại bỏ {count} dòng có '{col}' chứa '{target}' theo chỉ đạo."
                    # Xóa theo số thứ tự dòng 1-based hiển thị trên bảng
                    if 1 <= row_num <= len(new_df):
                        new_df = new_df.drop(new_df.index[row_num - 1]).reset_index(drop=True)
                        return new_df, new_tags, f"Đã loại bỏ dòng thứ {row_num} trên bảng dữ liệu theo chỉ đạo."

                for col in new_df.columns:
                    series_str = new_df[col].astype(str).str.lower()
                    matches = series_str.str.contains(re.escape(target), na=False)
                    if matches.any():
                        count = int(matches.sum())
                        new_df = new_df[~matches].reset_index(drop=True)
                        return new_df, new_tags, f"Đã loại bỏ {count} dòng có '{col}' chứa '{target}' theo chỉ đạo."

        # Mẫu 5: Chỉ giữ lại dòng theo giá trị (VD: "chỉ giữ cửa hàng", "giữ lại website", "chỉ giữ hoàn thành")
        keep_pattern = r"(?:chỉ giữ|chi giu|giữ lại|giu lai|chỉ lấy|chi lay|lọc lấy)\s+(?:các dòng|dòng|nhóm|kênh|khu vực|chi nhánh|trạng thái)?\s*['\"]?([^'\"]+)['\"]?"
        keep_m = re.search(keep_pattern, d) if not has_complex_condition else None
        if keep_m:
            target = keep_m.group(1).strip()
            target = re.sub(r"^(các\s+dòng|dòng|nhóm|kênh|khu\s+vực|chi\s+nhánh|trạng\s+thái)\s+", "", target).strip()
            if target and target not in ["dữ liệu", "tất cả"]:
                for col in new_df.columns:
                    series_str = new_df[col].astype(str).str.lower()
                    matches = series_str.str.contains(re.escape(target), na=False)
                    if matches.any():
                        new_df = new_df[matches].reset_index(drop=True)
                        return new_df, new_tags, f"Đã giữ lại {len(new_df)} dòng có '{col}' chứa '{target}' (đã loại bỏ các bản ghi còn lại)."

        # Mẫu 6: Điền giá trị khuyết / ô trống
        if any(w in d for w in ["điền thiếu", "điền khuyết", "điền null", "điền trống", "điền ô trống", "ô trống", "giá trị thiếu", "dien thieu", "dien trong", "dien o trong"]):
            fill_val = "Chưa xác định"
            if "trung vị" in d or "median" in d:
                from app.data_cleaner import DataCleaner
                res = DataCleaner.auto_clean(new_df, {"handle_missing": "median", "fix_negatives": True})
                return res["df"], res["cell_tags"], "Đã điền các giá trị thiếu bằng giá trị trung vị (Median)."
            elif "trung bình" in d or "mean" in d:
                from app.data_cleaner import DataCleaner
                res = DataCleaner.auto_clean(new_df, {"handle_missing": "mean", "fix_negatives": True})
                return res["df"], res["cell_tags"], "Đã điền các giá trị thiếu bằng giá trị trung bình (Mean)."
            
            # Mặc định điền "Chưa xác định" hoặc giá trị người dùng yêu cầu
            val_match = re.search(r"(?:bằng|thành|là)\s+['\"]?([^'\"]+)['\"]?", directive, re.IGNORECASE)
            if val_match:
                fill_val = val_match.group(1).strip()
            
            fill_count = 0
            for col in new_df.columns:
                for idx, val in new_df[col].items():
                    if pd.isnull(val) or str(val).strip() in ["", "nan", "null", "none", "None"]:
                        new_df.at[idx, col] = fill_val
                        new_tags[f"{idx}_{col}"] = {
                            "category": "missing",
                            "old": "Trống (Null)",
                            "new": fill_val,
                            "desc": f"Điền theo chỉ đạo HITL: '{fill_val}'"
                        }
                        fill_count += 1
            if fill_count > 0:
                return new_df, new_tags, f"Đã điền {fill_count} ô khuyết bằng '{fill_val}'."
            else:
                return new_df, new_tags, "Bảng dữ liệu hiện tại không còn ô trống (null) nào."

        return None

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
                new_df = df[~combined_mask].reset_index(drop=True)
                return new_df, tags, f"Đã loại bỏ {count} dòng thuộc {region_name} (dựa trên cột '{detected_col}')."
            else:
                new_df = df[combined_mask].reset_index(drop=True)
                return new_df, tags, f"Đã giữ lại {len(new_df)} dòng thuộc {region_name} (đã loại bỏ các vùng khác)."

        return df, tags, f"Không tìm thấy bản ghi nào thuộc {region_name} trong bảng dữ liệu."

    @classmethod
    def _execute_via_gemini(cls, df: pd.DataFrame, directive: str, cell_tags: dict):
        """Sử dụng Gemini API để hiểu mọi chỉ đạo ngôn ngữ tự nhiên phức tạp của con người"""
        api_key = _get_gemini_api_key()
        if not api_key:
            return None

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

Hãy chuyển chỉ đạo trên thành một kế hoạch hành động JSON chuẩn (trả về JSON object thuần, không markdown):
{{
  "actions": [
    {{
      "action": "filter_remove" | "filter_keep" | "replace" | "fill_na" | "format_date" | "remove_negatives" | "fix_negatives" | "remove_duplicates" | "sort" | "drop_column",
      "column": "tên cột chính xác trong danh sách cột (hoặc 'ALL' nếu áp dụng toàn bảng)",
      "operator": "contains" | "equals" | "not_equals" | "<" | "<=" | ">" | ">=",
      "value": "giá trị điều kiện / giá trị cũ cần thay (quy đổi chữ số tiếng Việt như '5 triệu' -> '5000000', '500k' -> '500000')",
      "replace_with": "giá trị mới (nếu replace / fill_na) hoặc 'asc'/'desc' (nếu sort)",
      "description": "mô tả ngắn gọn bằng tiếng Việt về kết quả đã thực hiện"
    }}
  ]
}}"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 800,
                "responseMimeType": "application/json"
            }
        }
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        for model_name in ["gemini-flash-lite-latest", "gemini-3-flash-preview", "gemini-3.5-flash"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            req = urllib.request.Request(url, data=body_bytes, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_json = json.loads(response.read().decode("utf-8"))
                    text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                    m = re.search(r"\{[\s\S]*\}", text)
                    if not m:
                        continue
                    plan_root = json.loads(m.group(0))
                    actions = plan_root.get("actions") if isinstance(plan_root.get("actions"), list) else [plan_root]
                    return cls._apply_gemini_actions(df, actions, cell_tags)
            except Exception:
                continue

        return None

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
            num_s = pd.to_numeric(series, errors="coerce")
            if num_s.isnull().all() and series.notnull().any():
                num_s = series.apply(DataCleaner.parse_vn_number)
            if op in ["<", "less_than"]:
                return (num_s < num_val).fillna(False)
            elif op in ["<="]:
                return (num_s <= num_val).fillna(False)
            elif op in [">", "greater_than"]:
                return (num_s > num_val).fillna(False)
            elif op in [">="]:
                return (num_s >= num_val).fillna(False)

        s_str = series.astype(str).str.strip().str.lower()
        v_str = str(val).strip().lower()
        if op in ["equals", "="]:
            m = s_str == v_str
            if not m.any():
                try:
                    num_val = DataCleaner.parse_vn_number(val)
                    if not np.isnan(num_val):
                        num_s = series.apply(DataCleaner.parse_vn_number)
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
        from app.data_cleaner import DataCleaner
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

            if action == "filter_remove" and col:
                mask = cls._build_condition_mask(new_df[col], op, val)
                removed = int(mask.sum())
                new_df = new_df[~mask].reset_index(drop=True)
                logs.append(desc or f"Đã loại bỏ {removed} dòng ở cột '{col}' ({op} {val}).")

            elif action == "filter_keep" and col:
                mask = cls._build_condition_mask(new_df[col], op, val)
                new_df = new_df[mask].reset_index(drop=True)
                logs.append(desc or f"Đã lọc giữ lại {len(new_df)} dòng ở cột '{col}' ({op} {val}).")

            elif action == "replace":
                target_cols = [col] if col else new_df.columns.tolist()
                cnt = 0
                for c in target_cols:
                    for idx, cur_v in new_df[c].items():
                        if pd.notnull(cur_v) and str(cur_v).strip().lower() == str(val).strip().lower():
                            new_df.at[idx, c] = rep_with
                            new_tags[f"{idx}_{c}"] = {
                                "category": "manual",
                                "old": str(cur_v),
                                "new": str(rep_with),
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
                                "category": "imputed",
                                "old": "Trống (Null)",
                                "new": str(fill_v),
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
                            dt = pd.to_datetime(str(cur_v).strip(), format='mixed', dayfirst=True)
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
                    s_num = pd.to_numeric(new_df[c], errors="coerce")
                    if s_num.notnull().sum() >= max(1, len(new_df) * 0.3):
                        neg_m = s_num < 0
                        if neg_m.any():
                            removed += int(neg_m.sum())
                            new_df = new_df[~neg_m].reset_index(drop=True)
                logs.append(desc or f"Đã loại bỏ {removed} dòng có giá trị âm.")

            elif action == "fix_negatives":
                target_cols = [col] if col else new_df.columns.tolist()
                cnt = 0
                for c in target_cols:
                    s_num = pd.to_numeric(new_df[c], errors="coerce")
                    for idx, v in s_num.items():
                        if pd.notnull(v) and v < 0:
                            new_df.at[idx, c] = abs(v)
                            new_tags[f"{idx}_{c}"] = {"category": "anomaly", "old": str(v), "new": str(abs(v)), "desc": "Chuyển số âm thành dương"}
                            cnt += 1
                logs.append(desc or f"Đã chuyển {cnt} giá trị âm thành số dương.")

            elif action == "remove_duplicates":
                b_len = len(new_df)
                new_df = new_df.drop_duplicates().reset_index(drop=True)
                logs.append(desc or f"Đã khử {b_len - len(new_df)} dòng trùng lặp.")

            elif action == "sort" and col:
                asc = str(rep_with or val or "asc").lower() != "desc"
                new_df = new_df.sort_values(by=col, ascending=asc).reset_index(drop=True)
                logs.append(desc or f"Đã sắp xếp cột '{col}' theo thứ tự {'tăng dần' if asc else 'giảm dần'}.")

            elif action == "drop_column" and col:
                new_df = new_df.drop(columns=[col])
                logs.append(desc or f"Đã xóa cột '{col}'.")

        if logs:
            return new_df, new_tags, " ".join(logs)
        return None

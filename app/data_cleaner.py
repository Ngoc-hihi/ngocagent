"""
data_cleaner.py - Module Làm sạch Dữ liệu & Cổng kiểm duyệt HITL (Human-in-the-Loop)
Nâng cấp toàn diện:
1. Xử lý cực nhanh (Vectorized & Fast checks, phản hồi tức thời dưới 100ms)
2. Điền "Chưa xác định" cho các ô thiếu / rỗng theo đúng yêu cầu
3. Nhận diện & chuẩn hóa viết tắt tiếng Việt toàn diện (VD: BD -> Bình Dương, HN -> Hà Nội, HCM -> TP. Hồ Chí Minh,...)
4. Tự động phát hiện và hiệu chỉnh số lượng / đơn giá / thành tiền âm thành số dương chuẩn xác
5. Bảng đối chiếu Trước - Sau, Audit Log chi tiết và Cổng kiểm duyệt HITL
"""

import pandas as pd
import numpy as np
from datetime import datetime
import re

# Bảng từ điển chuẩn hóa viết tắt & địa danh tiếng Việt
ABBREVIATION_MAP = {
    # Tỉnh thành / Chi nhánh
    "bd": "Bình Dương",
    "b.d": "Bình Dương",
    "b duong": "Bình Dương",
    "b dương": "Bình Dương",
    "binh duong": "Bình Dương",
    "binhduong": "Bình Dương",
    "bdg": "Bình Dương",
    "hcm": "TP. Hồ Chí Minh",
    "tp.hcm": "TP. Hồ Chí Minh",
    "tphcm": "TP. Hồ Chí Minh",
    "tp hcm": "TP. Hồ Chí Minh",
    "tp. hcm": "TP. Hồ Chí Minh",
    "tp ho chi minh": "TP. Hồ Chí Minh",
    "tp. hồ chí minh": "TP. Hồ Chí Minh",
    "hcmc": "TP. Hồ Chí Minh",
    "sg": "TP. Hồ Chí Minh",
    "sai gon": "TP. Hồ Chí Minh",
    "sài gòn": "TP. Hồ Chí Minh",
    "hn": "Hà Nội",
    "h.n": "Hà Nội",
    "ha noi": "Hà Nội",
    "hanoi": "Hà Nội",
    "dn": "Đà Nẵng",
    "đn": "Đà Nẵng",
    "d.n": "Đà Nẵng",
    "đ.n": "Đà Nẵng",
    "da nang": "Đà Nẵng",
    "đà nẵng": "Đà Nẵng",
    "ct": "Cần Thơ",
    "c.t": "Cần Thơ",
    "can tho": "Cần Thơ",
    "cần thơ": "Cần Thơ",
    "hp": "Hải Phòng",
    "h.p": "Hải Phòng",
    "hai phong": "Hải Phòng",
    "hải phòng": "Hải Phòng",
    "qn": "Quảng Ninh",
    "q.n": "Quảng Ninh",
    "quang ninh": "Quảng Ninh",
    "quảng ninh": "Quảng Ninh",
    "qnam": "Quảng Nam",
    "quang nam": "Quảng Nam",
    "quảng nam": "Quảng Nam",
    "vt": "Bà Rịa - Vũng Tàu",
    "v.t": "Bà Rịa - Vũng Tàu",
    "vung tau": "Bà Rịa - Vũng Tàu",
    "vũng tàu": "Bà Rịa - Vũng Tàu",
    "dnai": "Đồng Nai",
    "đnai": "Đồng Nai",
    "dong nai": "Đồng Nai",
    "đồng nai": "Đồng Nai",
    "hue": "Thừa Thiên Huế",
    "thua thien hue": "Thừa Thiên Huế",
    "thừa thiên huế": "Thừa Thiên Huế",
    "tt hue": "Thừa Thiên Huế",
    "tt huế": "Thừa Thiên Huế",
    "bn": "Bắc Ninh",
    "bac ninh": "Bắc Ninh",
    "bắc ninh": "Bắc Ninh",
    "vp": "Vĩnh Phúc",
    "vinh phuc": "Vĩnh Phúc",
    "vĩnh phúc": "Vĩnh Phúc",
    "la": "Long An",
    "long an": "Long An",
    "tg": "Tiền Giang",
    "tien giang": "Tiền Giang",
    "tiền giang": "Tiền Giang",
    "q1": "Quận 1",
    "quan 1": "Quận 1",
    "quận 1": "Quận 1",
    "q7": "Quận 7",
    "quan 7": "Quận 7",
    "quận 7": "Quận 7",
    "td": "TP. Thủ Đức",
    "thu duc": "TP. Thủ Đức",
    "thủ đức": "TP. Thủ Đức",

    # Kênh bán hàng
    "shopee": "Shopee",
    "shopeefood": "ShopeeFood",
    "tiktok": "TikTok Shop",
    "tiktok shop": "TikTok Shop",
    "tt shop": "TikTok Shop",
    "grab": "GrabFood",
    "grabfood": "GrabFood",
    "web": "Website",
    "website": "Website",
    "cua hang": "Cửa hàng",
    "cửa hàng": "Cửa hàng",
    "ch": "Cửa hàng",
    "b2b": "B2B Direct",
    "b2b direct": "B2B Direct",

    # Phương thức thanh toán
    "tien mat": "Tiền mặt",
    "tiền mặt": "Tiền mặt",
    "tm": "Tiền mặt",
    "chuyen khoan": "Chuyển khoản",
    "chuyển khoản": "Chuyển khoản",
    "ck": "Chuyển khoản",
    "vnpay": "Chuyển khoản VNPay",
    "vn pay": "Chuyển khoản VNPay",
    "chuyen khoan vnpay": "Chuyển khoản VNPay",
    "chuyển khoản vnpay": "Chuyển khoản VNPay",
    "the tin dung": "Thẻ tín dụng",
    "thẻ tín dụng": "Thẻ tín dụng",
    "the": "Thẻ tín dụng",
    "thẻ": "Thẻ tín dụng",
    "cod": "COD",

    # Trạng thái
    "hoan thanh": "Hoàn thành",
    "hoàn thành": "Hoàn thành",
    "dang giao": "Đang giao",
    "đang giao": "Đang giao",
    "hoan tra": "Hoàn trả",
    "hoàn trả": "Hoàn trả",
    "cho xu ly": "Chờ xử lý",
    "chờ xử lý": "Chờ xử lý",
    "da huy": "Đã hủy",
    "đã hủy": "Đã hủy"
}

def to_py_scalar(val):
    """Chuyển đổi numpy scalar sang kiểu dữ liệu Python chuẩn để serialize JSON an toàn"""
    if pd.isna(val) or val is None:
        return "Trống / N/A"
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        return float(val)
    return str(val)

def normalize_text_ascii(text: str) -> str:
    """Loại bỏ dấu tiếng Việt để đối soát cột và giá trị nhanh"""
    s = str(text).lower()
    replacements = {
        'à': 'a', 'á': 'a', 'ạ': 'a', 'ả': 'a', 'ã': 'a', 'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ậ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ặ': 'a', 'ẳ': 'a', 'ẵ': 'a',
        'è': 'e', 'é': 'e', 'ẹ': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ê': 'e', 'ề': 'e', 'ế': 'e', 'ệ': 'e', 'ể': 'e', 'ễ': 'e',
        'ì': 'i', 'í': 'i', 'ị': 'i', 'ỉ': 'i', 'ĩ': 'i',
        'ò': 'o', 'ó': 'o', 'ọ': 'o', 'ỏ': 'o', 'õ': 'o', 'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ộ': 'o', 'ổ': 'o', 'ỗ': 'o', 'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ợ': 'o', 'ở': 'o', 'ỡ': 'o',
        'ù': 'u', 'ú': 'u', 'ụ': 'u', 'ủ': 'u', 'ũ': 'u', 'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ự': 'u', 'ử': 'u', 'ữ': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỵ': 'y', 'ỷ': 'y', 'ỹ': 'y',
        'đ': 'd'
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return re.sub(r'[^a-z0-9]', '_', s).strip('_')

def is_quantity_or_metric_col(col_name: str) -> bool:
    """Nhận diện các cột số lượng, đơn giá, thành tiền, chi phí, doanh thu không được âm"""
    norm = normalize_text_ascii(col_name)
    keywords = [
        "so_luong", "soluong", "sl", "qty", "quantity", "san_luong", "sanluong",
        "don_gia", "dongia", "price", "unit_price", "gia",
        "thanh_tien", "thanhtien", "total", "amount", "tien",
        "doanh_thu", "doanhthu", "revenue", "sales", "mrr", "arr",
        "chi_phi", "chiphi", "cost", "phi", "fee",
        "so_khach", "khach", "so_ticket", "ticket",
        "danh_gia", "danhgia", "rating", "score", "nps", "diem"
    ]
    return any(k in norm for k in keywords)

class DataCleaner:
    @staticmethod
    def inspect_dataset(df: pd.DataFrame) -> dict:
        """Đo lường hiện trạng tập dữ liệu trước khi làm sạch"""
        total_rows = len(df)
        total_cols = len(df.columns)
        null_cells = int(df.isnull().sum().sum())
        
        # Đếm các ô rỗng hoặc khoảng trắng trong chuỗi
        str_cols = df.select_dtypes(include=['object']).columns.tolist()
        empty_str_cells = 0
        whitespace_issues = 0
        abbreviation_issues = 0

        for col in str_cols:
            s_series = df[col].astype(str)
            empty_str_cells += int((s_series.str.strip().isin(["", "nan", "null", "none", "n/a", "na"])).sum())
            whitespace_issues += int((s_series.str.strip() != s_series).sum())
            for val in df[col].dropna():
                if isinstance(val, str) and normalize_text_ascii(val).replace('_', ' ') in ABBREVIATION_MAP:
                    abbreviation_issues += 1
                    break

        null_cells = max(null_cells, empty_str_cells)
        null_per_col = {col: int(df[col].isnull().sum()) for col in df.columns if df[col].isnull().sum() > 0}
        duplicate_rows = int(df.duplicated().sum())

        # Kiểm tra lỗi số âm ở các cột số hoặc chuỗi chứa số âm
        negative_issues = {}
        for col in df.columns:
            if is_quantity_or_metric_col(col):
                nums = pd.to_numeric(df[col], errors='coerce')
                neg_count = int((nums < 0).sum())
                if neg_count > 0:
                    negative_issues[col] = neg_count

        total_issues = null_cells + duplicate_rows + sum(negative_issues.values()) + whitespace_issues + abbreviation_issues
        total_cells = max(1, total_rows * total_cols)
        quality_score = max(10, min(100, int((1 - (total_issues / total_cells)) * 100)))

        return {
            "total_rows": total_rows,
            "total_cols": total_cols,
            "null_cells": null_cells,
            "null_per_col": null_per_col,
            "duplicate_rows": duplicate_rows,
            "negative_issues": negative_issues,
            "whitespace_issues": whitespace_issues,
            "abbreviation_issues": abbreviation_issues,
            "quality_score": quality_score
        }

    @staticmethod
    def auto_clean(df: pd.DataFrame, config: dict = None) -> dict:
        """
        Quy trình làm sạch toàn diện, thông minh & siêu tốc:
        - Chuẩn hóa viết tắt (BD -> Bình Dương, HN -> Hà Nội,...)
        - Hiệu chỉnh số lượng / đơn vị âm thành số dương
        - Điền 'Chưa xác định' cho toàn bộ giá trị thiếu (hoặc median/mean nếu chọn)
        - Chuẩn hóa ngày tháng ISO YYYY-MM-DD
        - Khử trùng lặp
        - Tốc độ cực nhanh trên 5,000+ dòng (dưới 0.2s)
        """
        if config is None:
            config = {
                "remove_duplicates": True,
                "handle_missing": "unspecified",
                "fix_negatives": True,
                "standardize_text": True,
                "standardize_dates": True
            }

        original_df = df.copy()
        # Chuyển đổi toàn bộ sang object để hoàn toàn miễn nhiễm với mọi lỗi kiểu dữ liệu của pandas/pyarrow
        cleaned_df = df.copy().astype(object)
        audit_log = []
        cell_tags = {}
        now_str = datetime.now().strftime("%H:%M:%S")

        # 1. Loại bỏ trùng lặp (Deduplicate)
        if config.get("remove_duplicates", True):
            dup_count = int(cleaned_df.duplicated().sum())
            if dup_count > 0:
                cleaned_df = cleaned_df.drop_duplicates().reset_index(drop=True)
                audit_log.append(f"[{now_str}] Đã phát hiện và loại bỏ {dup_count} dòng trùng lặp.")
            else:
                audit_log.append(f"[{now_str}] Kiểm tra trùng lặp: Dữ liệu không có bản ghi trùng.")
        else:
            cleaned_df = cleaned_df.reset_index(drop=True)

        # 2. Xử lý Viết tắt & Chuẩn hóa Khoảng trắng & Danh xưng Địa danh (Vectorized qua Unique Values)
        if config.get("standardize_text", True):
            abbrev_fixed_count = 0
            text_fixed_count = 0

            for col in cleaned_df.columns:
                is_date = any(k in col.lower() for k in ["ngay", "date", "thang", "thoi_gian"])
                if is_date:
                    continue

                unique_vals = cleaned_df[col].dropna().unique()
                val_map = {}
                for u in unique_vals:
                    if isinstance(u, str):
                        clean_u = re.sub(r'\s+', ' ', u.strip())
                        norm_k = normalize_text_ascii(clean_u).replace('_', ' ')
                        if norm_k in ABBREVIATION_MAP:
                            exp = ABBREVIATION_MAP[norm_k]
                            if u != exp:
                                val_map[u] = (exp, "format", f"Chuẩn hóa viết tắt: '{u}' → '{exp}'")
                        elif clean_u != u:
                            val_map[u] = (clean_u, "format", "Chuẩn hóa khoảng trắng")

                for old_val, (new_val, cat, desc) in val_map.items():
                    match_idxs = cleaned_df.index[cleaned_df[col] == old_val].tolist()
                    cleaned_df.loc[match_idxs, col] = new_val
                    if "Chuẩn hóa viết tắt" in desc:
                        abbrev_fixed_count += len(match_idxs)
                    else:
                        text_fixed_count += len(match_idxs)

                    for idx in match_idxs[:200]:
                        cell_tags[f"{idx}_{col}"] = {
                            "category": cat,
                            "old": to_py_scalar(old_val),
                            "new": to_py_scalar(new_val),
                            "desc": desc
                        }

            if abbrev_fixed_count > 0:
                audit_log.append(f"[{now_str}] Chuẩn hóa viết tắt: Đã chuyển đổi {abbrev_fixed_count} ô viết tắt (ví dụ: 'BD' → 'Bình Dương').")
            if text_fixed_count > 0:
                audit_log.append(f"[{now_str}] Chuẩn hóa văn bản: Đã xử lý {text_fixed_count} ô chứa khoảng trắng lệch.")

        # 3. Chuẩn hóa định dạng Ngày tháng (Fast Check & Vectorized)
        if config.get("standardize_dates", True):
            date_fixed_count = 0
            for col in cleaned_df.columns:
                norm_c = normalize_text_ascii(col)
                if any(k in norm_c for k in ["ngay", "date", "thang", "thoi_gian"]):
                    is_month_only = any(k in norm_c for k in ["thang", "month"]) and not any(k in norm_c for k in ["ngay", "date"])
                    target_pattern = r'^\d{4}-\d{2}$' if is_month_only else r'^\d{4}-\d{2}-\d{2}$'
                    s_col = cleaned_df[col].astype(str).str.strip()
                    mask_need_parse = ~s_col.str.match(target_pattern) & cleaned_df[col].notnull() & (s_col != "") & (~s_col.str.lower().isin(["nan", "none", "null"]))
                    need_idxs = cleaned_df.index[mask_need_parse].tolist()

                    for idx in need_idxs:
                        val = cleaned_df.at[idx, col]
                        try:
                            parsed = pd.to_datetime(str(val).strip(), format='mixed', dayfirst=True)
                            std_date = parsed.strftime("%Y-%m") if is_month_only else parsed.strftime("%Y-%m-%d")
                            if std_date != str(val).strip():
                                cleaned_df.at[idx, col] = std_date
                                cell_tags[f"{idx}_{col}"] = {
                                    "category": "format",
                                    "old": to_py_scalar(val),
                                    "new": std_date,
                                    "desc": f"Chuẩn hóa ISO {'YYYY-MM' if is_month_only else 'YYYY-MM-DD'}"
                                }
                                date_fixed_count += 1
                        except Exception:
                            pass

            if date_fixed_count > 0:
                audit_log.append(f"[{now_str}] Đồng bộ ngày tháng: Đã chuyển đổi {date_fixed_count} bản ghi về chuẩn ISO.")

        # 4. Hiệu chỉnh Số lượng / Đơn giá / Thành tiền âm (Negative Fix - Fast Vectorized)
        if config.get("fix_negatives", True):
            negative_fixed_count = 0
            for col in cleaned_df.columns:
                if is_quantity_or_metric_col(col) or pd.api.types.is_numeric_dtype(cleaned_df[col]):
                    s_num = pd.to_numeric(cleaned_df[col], errors='coerce')
                    neg_mask = s_num < 0
                    neg_idxs = cleaned_df.index[neg_mask].tolist()

                    for idx in neg_idxs:
                        old_val = cleaned_df.at[idx, col]
                        num_v = abs(s_num.at[idx])
                        if isinstance(num_v, float) and num_v.is_integer():
                            num_v = int(num_v)
                        cleaned_df.at[idx, col] = num_v
                        cell_tags[f"{idx}_{col}"] = {
                            "category": "anomaly",
                            "old": to_py_scalar(old_val),
                            "new": to_py_scalar(num_v),
                            "desc": f"Hiệu chỉnh số âm: {old_val} → {num_v}"
                        }
                    negative_fixed_count += len(neg_idxs)

            if negative_fixed_count > 0:
                audit_log.append(f"[{now_str}] Phát hiện & Sửa lỗi số: Đã chuyển đổi {negative_fixed_count} giá trị âm (Số lượng / Tiền) thành số dương hợp lệ.")

        # 5. Xử lý Giá trị thiếu (Điền 'Chưa xác định' theo đúng yêu cầu hoặc Median/Mean)
        missing_method = config.get("handle_missing", "unspecified")
        missing_fixed_count = 0

        if missing_method == "drop":
            before_len = len(cleaned_df)
            cleaned_df = cleaned_df.dropna().reset_index(drop=True)
            dropped = before_len - len(cleaned_df)
            if dropped > 0:
                audit_log.append(f"[{now_str}] Đã loại bỏ {dropped} dòng chứa dữ liệu khuyết.")
        else:
            for col in cleaned_df.columns:
                null_mask = cleaned_df[col].isnull() | cleaned_df[col].astype(str).str.strip().str.lower().isin(['', 'nan', 'null', 'none', 'n/a', 'na', 'undefined', '-'])
                null_idxs = cleaned_df.index[null_mask].tolist()
                if not null_idxs:
                    continue

                is_metric = is_quantity_or_metric_col(col)
                s_num = pd.to_numeric(cleaned_df[col], errors='coerce')
                has_nums = s_num.notnull().sum() > 0

                if missing_method == "median" and (is_metric or has_nums):
                    med = s_num.dropna().median()
                    fill_val = round(float(med), 2) if pd.notnull(med) else 0
                    if isinstance(fill_val, float) and fill_val.is_integer():
                        fill_val = int(fill_val)
                    desc_tag = f"Điền Trung vị ({fill_val})"
                elif missing_method == "mean" and (is_metric or has_nums):
                    mean_val = s_num.dropna().mean()
                    fill_val = round(float(mean_val), 2) if pd.notnull(mean_val) else 0
                    if isinstance(fill_val, float) and fill_val.is_integer():
                        fill_val = int(fill_val)
                    desc_tag = f"Điền Trung bình ({fill_val})"
                else:
                    fill_val = "Chưa xác định"
                    desc_tag = "Điền 'Chưa xác định'"

                cleaned_df.loc[null_idxs, col] = fill_val
                missing_fixed_count += len(null_idxs)
                for idx in null_idxs[:200]:
                    cell_tags[f"{idx}_{col}"] = {
                        "category": "imputed",
                        "old": "Trống / N/A",
                        "new": to_py_scalar(fill_val),
                        "desc": desc_tag
                    }

            if missing_fixed_count > 0:
                audit_log.append(f"[{now_str}] Điền dữ liệu thiếu: Đã xử lý {missing_fixed_count} ô khuyết (Phương pháp: {missing_method}).")

        # Đo lường thống kê Trước - Sau
        before_stats = DataCleaner.inspect_dataset(original_df)
        after_stats = DataCleaner.inspect_dataset(cleaned_df)

        audit_log.append(f"[{now_str}] Hoàn tất làm sạch tối ưu. Chỉ số chất lượng dữ liệu: {before_stats['quality_score']}% → {after_stats['quality_score']}%.")

        return {
            "df": cleaned_df,
            "before_stats": before_stats,
            "after_stats": after_stats,
            "audit_log": audit_log,
            "cell_tags": cell_tags
        }

    @staticmethod
    def parse_vn_number(val) -> float:
        """Phân tích số định dạng Việt Nam/Quốc tế (VD: '5.000.000', '5,000,000', '5tr', '500k', '4,5')"""
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return np.nan
        if isinstance(val, (int, float, np.integer, np.floating)):
            return float(val)
        s = str(val).strip().lower()
        if not s or s in ["nan", "none", "null", "chưa xác định"]:
            return np.nan
        # Loại bỏ đơn vị tiền tệ và khoảng trắng
        s = re.sub(r'(vnđ|vnd|đ|\s+)', '', s)
        multiplier = 1.0
        if s.endswith(('triệu', 'trieu', 'tr')):
            multiplier = 1_000_000.0
            s = re.sub(r'(triệu|trieu|tr)$', '', s)
        elif s.endswith(('tỷ', 'ty')):
            multiplier = 1_000_000_000.0
            s = re.sub(r'(tỷ|ty)$', '', s)
        elif s.endswith(('nghìn', 'ngàn', 'nghin', 'ngan', 'k')):
            multiplier = 1_000.0
            s = re.sub(r'(nghìn|ngàn|nghin|ngan|k)$', '', s)

        # Xử lý dấu chấm / dấu phẩy phân cách hàng nghìn
        if s.count('.') > 1 and ',' not in s:
            s = s.replace('.', '')
        elif s.count(',') > 1 and '.' not in s:
            s = s.replace(',', '')
        elif re.match(r'^-?\d{1,3}(\.\d{3})+$', s):
            s = s.replace('.', '')
        elif re.match(r'^-?\d{1,3}(,\d{3})+$', s):
            s = s.replace(',', '')
        elif ',' in s and '.' not in s:
            s = s.replace(',', '.')
        elif ',' in s and '.' in s:
            if s.rfind(',') > s.rfind('.'):
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')

        return float(s) * multiplier

    @staticmethod
    def filter_and_remove(df: pd.DataFrame, column: str, operator: str, value: str, action: str = "remove", cell_tags: dict = None) -> tuple:
        """Lọc và xóa/giữ dòng theo điều kiện chỉ đạo HITL (hỗ trợ số có dấu chấm/phẩy VN)"""
        if cell_tags is None:
            cell_tags = {}

        now_str = datetime.now().strftime("%H:%M:%S")
        before_count = len(df)

        if column not in df.columns:
            return df, f"Cột '{column}' không tồn tại.", cell_tags

        col_data = df[column]

        try:
            if operator in ["greater_than", "less_than"]:
                num_val = DataCleaner.parse_vn_number(value)
                if np.isnan(num_val):
                    raise ValueError(f"Giá trị '{value}' không phải là số hợp lệ.")
                num_series = pd.to_numeric(col_data, errors='coerce')
                if num_series.isnull().all() and col_data.notnull().any():
                    num_series = col_data.apply(DataCleaner.parse_vn_number)
                mask = (num_series > num_val) if operator == "greater_than" else (num_series < num_val)
                mask = mask.fillna(False)
            elif operator == "equals":
                str_mask = col_data.astype(str).str.strip().str.lower() == str(value).strip().lower()
                if not str_mask.any():
                    try:
                        num_val = DataCleaner.parse_vn_number(value)
                        if not np.isnan(num_val):
                            num_series = col_data.apply(DataCleaner.parse_vn_number)
                            str_mask = (num_series == num_val).fillna(False)
                    except Exception:
                        pass
                mask = str_mask
            elif operator == "not_equals":
                str_mask = col_data.astype(str).str.strip().str.lower() != str(value).strip().lower()
                try:
                    num_val = DataCleaner.parse_vn_number(value)
                    if not np.isnan(num_val):
                        num_series = col_data.apply(DataCleaner.parse_vn_number)
                        if num_series.notnull().any():
                            str_mask = (num_series != num_val).fillna(True)
                except Exception:
                    pass
                mask = str_mask
            elif operator == "contains":
                mask = col_data.astype(str).str.strip().str.lower().str.contains(str(value).strip().lower(), na=False)
            else:
                mask = col_data.astype(str).str.strip().str.lower() == str(value).strip().lower()
        except Exception as e:
            return df, f"Lỗi thực hiện điều kiện: {str(e)}", cell_tags

        if action == "remove":
            kept_mask = ~mask
            new_df = df[kept_mask].reset_index(drop=True)
            deleted = before_count - len(new_df)
            msg = f"[{now_str}] Đã xóa {deleted} dòng có cột '{column}' {operator} '{value}'."
        else:
            kept_mask = mask
            new_df = df[kept_mask].reset_index(drop=True)
            kept = len(new_df)
            deleted = before_count - kept
            msg = f"[{now_str}] Đã lọc giữ lại {kept} dòng có cột '{column}' {operator} '{value}' (Đã loại {deleted} dòng)."

        # Remap lại cell_tags theo chỉ số dòng mới sau khi lọc
        old_to_new_idx = {}
        new_i = 0
        for old_i, is_kept in enumerate(kept_mask):
            if is_kept:
                old_to_new_idx[old_i] = new_i
                new_i += 1

        remapped_tags = {}
        for k, v in cell_tags.items():
            parts = k.split("_", 1)
            if len(parts) == 2 and parts[0].isdigit():
                old_r = int(parts[0])
                if old_r in old_to_new_idx:
                    remapped_tags[f"{old_to_new_idx[old_r]}_{parts[1]}"] = v

        return new_df, msg, remapped_tags

    @staticmethod
    def edit_cell(df: pd.DataFrame, row_idx: int, col_name: str, new_value: any, cell_tags: dict = None) -> tuple:
        """Sửa trực tiếp từng ô bởi người dùng (Inline Editing)"""
        if cell_tags is None:
            cell_tags = {}
        
        if row_idx < 0 or row_idx >= len(df) or col_name not in df.columns:
            return df, "Chỉ mục ô không hợp lệ", cell_tags

        old_val = df.at[row_idx, col_name]

        # Kiểm tra viết tắt ngay khi sửa ô
        norm_val = normalize_text_ascii(new_value).replace('_', ' ')
        final_val = ABBREVIATION_MAP.get(norm_val, new_value)

        # Ép kiểu dữ liệu nếu là số
        if pd.api.types.is_numeric_dtype(df[col_name]):
            try:
                parsed_val = float(final_val)
                if is_quantity_or_metric_col(col_name) and parsed_val < 0:
                    parsed_val = abs(parsed_val)
                if pd.api.types.is_integer_dtype(df[col_name]):
                    parsed_val = int(parsed_val)
                df.at[row_idx, col_name] = parsed_val
                final_val = parsed_val
            except Exception:
                df.at[row_idx, col_name] = final_val
        else:
            df.at[row_idx, col_name] = str(final_val)

        cell_tags[f"{row_idx}_{col_name}"] = {
            "category": "manual",
            "old": to_py_scalar(old_val),
            "new": to_py_scalar(final_val),
            "desc": f"Người dùng chỉnh sửa: '{old_val}' → '{final_val}'"
        }

        now_str = datetime.now().strftime("%H:%M:%S")
        msg = f"[{now_str}] Đã sửa thủ công ô [{row_idx}, '{col_name}'] từ '{old_val}' thành '{final_val}'."
        return df, msg, cell_tags

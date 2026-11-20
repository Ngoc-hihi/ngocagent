import re
import pandas as pd
import unicodedata

def strip_accents(s: str) -> str:
    if not isinstance(s, str):
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()

p = 'data/uploads/20261119_232606_du-lieu-test-ban-le.csv'
df = pd.read_csv(p)

tests = [
    'xóa dòng 13',
    'xóa dữ liệu 13 đi',
    'bỏ dòng 5',
    'xóa dòng có mã DS-013'
]

rem_pattern = r"(?:bỏ|xóa|xoa|loại bỏ|loai bo|remove|delete)\s+(?:các dòng|dòng|nhóm|kênh|khu vực|chi nhánh|trạng thái|phương thức|bản ghi|dữ liệu)?\s*['\"]?([^'\"]+?)['\"]?(?:\s+đi|\s+giúp\s+tôi|\s+nhé|\.|\!)?$"

for t in tests:
    m = re.search(rem_pattern, t, re.IGNORECASE)
    if m:
        target = m.group(1).strip()
        # Clean extra leading words
        target = re.sub(r"^(các\s+dòng|dòng|nhóm|kênh|khu\s+vực|chi\s+nhánh|trạng\s+thái|bản\s+ghi|dữ\s+liệu|hàng|thứ|có\s+mã)\s+", "", target, flags=re.IGNORECASE).strip()
        print(f'"{t}" -> target: "{target}"')
    else:
        print(f'"{t}" -> NO MATCH')

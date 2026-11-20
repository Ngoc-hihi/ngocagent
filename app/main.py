"""
main.py - Máy chủ FastAPI điều phối toàn diện cho ứng dụng AnoraAI
Bao gồm đầy đủ các API cho luồng 5 trang nghiệp vụ, cổng kiểm duyệt HITL,
động cơ phân tích 4 cấp độ, xuất báo cáo DIID và Trợ lý ảo AI.
"""

import os
import io
import uuid
import re
import pandas as pd
import requests
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.sample_datasets import SAMPLE_DIR
from app.data_cleaner import DataCleaner
from app.data_analyzer import DataAnalyzer
from app.docx_generator import create_diid_word_report, generate_chart_images
from app.html_report_generator import generate_standalone_html
from app.history_manager import HistoryManager
from app.assistant_ai import AssistantAI
from app.directive_engine import DirectiveEngine

import tempfile
from datetime import datetime

# Cấu hình thư mục cache Matplotlib trên môi trường máy chủ / Serverless (Vercel)
if "MPLCONFIGDIR" not in os.environ:
    os.environ["MPLCONFIGDIR"] = os.path.join(tempfile.gettempdir(), "matplotlib")
try:
    os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

def get_writable_dir(*subpaths):
    """
    Trả về thư mục có quyền ghi hợp lệ:
    Ưu tiên đường dẫn gốc BASE_DIR (khi chạy Localhost).
    Tự động chuyển vùng sang tempfile (khi chạy trên môi trường Read-only Serverless của Vercel).
    """
    candidate = os.path.join(BASE_DIR, *subpaths)
    try:
        os.makedirs(candidate, exist_ok=True)
        test_file = os.path.join(candidate, f".test_{uuid.uuid4().hex[:6]}")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return candidate
    except Exception:
        fallback = os.path.join(tempfile.gettempdir(), "anora_agent", *subpaths)
        os.makedirs(fallback, exist_ok=True)
        return fallback

UPLOADS_DIR = get_writable_dir("data", "uploads")
EXPORTS_DIR = get_writable_dir("exports")

app = FastAPI(title="AnoraAI - Data Processing & DIID Report Agent")

# Mount thư mục tĩnh
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Bộ nhớ phiên làm việc (Session In-Memory Cache)
CURRENT_SESSION = {
    "session_id": str(uuid.uuid4()),
    "business_meta": {
        "name": "Công ty Cổ phần Anora Retail",
        "model": "B2C Bán lẻ & Chuỗi F&B",
        "core_problem": "Tối ưu hóa cơ cấu chi phí vận hành & Tăng biên lợi nhuận ròng",
        "additional_info": "Dự kiến mở rộng thêm 5 chi nhánh tại miền Trung trong năm nay."
    },
    "raw_df": None,
    "cleaned_df": None,
    "cleaned_stats": {},
    "audit_log": [],
    "cell_tags": {},
    "analysis_data": None,
    "exported_files": {}
}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Trang chủ ứng dụng SPA"""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"session": CURRENT_SESSION}
    )

@app.post("/api/session/reset")
async def reset_session():
    """Làm mới toàn bộ phiên làm việc (Reset Session)"""
    global CURRENT_SESSION
    CURRENT_SESSION = {
        "session_id": str(uuid.uuid4()),
        "business_meta": {
            "name": "",
            "model": "",
            "core_problem": "",
            "additional_info": ""
        },
        "raw_df": None,
        "cleaned_df": None,
        "cleaned_stats": {},
        "audit_log": [],
        "cell_tags": {},
        "analysis_data": None,
        "exported_files": {}
    }
    return {"status": "success", "message": "Phiên làm việc đã được làm mới thành công."}

def ensure_session_ready():
    """
    Đảm bảo phiên làm việc có dữ liệu sạch và phân tích 4 cấp độ.
    Tự động khôi phục nếu Lambda container bị restart hoặc chạy đa tiến trình stateless trên Vercel.
    """
    global CURRENT_SESSION
    if CURRENT_SESSION.get("cleaned_df") is None or CURRENT_SESSION.get("analysis_data") is None:
        from app.sample_datasets import generate_retail_fb_dataset
        raw_df = generate_retail_fb_dataset()
        clean_res = DataCleaner.auto_clean(raw_df)
        cleaned_df = clean_res["df"]
        stats = clean_res["after_stats"]
        meta = CURRENT_SESSION.get("business_meta") or {
            "name": "Công ty Cổ phần Anora Retail",
            "model": "B2C Bán lẻ & Chuỗi F&B",
            "core_problem": "Tối ưu hóa cơ cấu chi phí vận hành & Tăng biên lợi nhuận ròng",
            "additional_info": "Dự kiến mở rộng thêm 5 chi nhánh tại miền Trung trong năm nay."
        }
        if not meta.get("name"):
            meta["name"] = "Công ty Cổ phần Anora Retail"
        if not meta.get("model"):
            meta["model"] = "B2C Bán lẻ & Chuỗi F&B"
        if not meta.get("core_problem"):
            meta["core_problem"] = "Tối ưu hóa cơ cấu chi phí vận hành & Tăng biên lợi nhuận ròng"

        analysis = DataAnalyzer.analyze(
            df=cleaned_df,
            business_name=meta.get("name"),
            business_model=meta.get("model"),
            core_problem=meta.get("core_problem"),
            additional_info=meta.get("additional_info", "")
        )
        CURRENT_SESSION.update({
            "raw_df": raw_df,
            "cleaned_df": cleaned_df,
            "cleaned_stats": stats,
            "audit_log": clean_res.get("audit_log", []),
            "cell_tags": clean_res.get("cell_tags", {}),
            "business_meta": meta,
            "analysis_data": analysis
        })

@app.get("/api/session/current")
async def get_current_session():
    has_raw = CURRENT_SESSION["raw_df"] is not None
    has_clean = CURRENT_SESSION["cleaned_df"] is not None
    return {
        "session_id": CURRENT_SESSION["session_id"],
        "business_meta": CURRENT_SESSION["business_meta"],
        "has_data": has_raw or has_clean,
        "raw_rows": len(CURRENT_SESSION["raw_df"]) if has_raw else 0,
        "cleaned_rows": len(CURRENT_SESSION["cleaned_df"]) if has_clean else 0,
        "has_analysis": CURRENT_SESSION["analysis_data"] is not None
    }

# =============================================================================
# TRANG 2 — BƯỚC 1: TIẾP NHẬN DỮ LIỆU & RÀNG BUỘC CHẶN
# =============================================================================

@app.post("/api/step1/ingest")
async def ingest_data(
    business_name: str = Form(...),
    business_model: str = Form(...),
    core_problem: str = Form(...),
    additional_info: str = Form(""),
    sample_type: str = Form(None),
    gsheet_url: str = Form(None),
    file: UploadFile = File(None)
):
    """
    Tiếp nhận thông tin doanh nghiệp và dữ liệu.
    CHẶN không cho đi tiếp nếu thiếu mô hình kinh doanh hoặc chưa có dữ liệu nạp vào!
    """
    # 1. Ràng buộc Mô hình kinh doanh
    if not business_model or not business_model.strip():
        raise HTTPException(status_code=400, detail="Vui lòng chọn hoặc nhập Mô hình kinh doanh của doanh nghiệp để tiếp tục.")

    if not business_name or not business_name.strip():
        business_name = "Doanh nghiệp Mẫu"

    df = None

    # 2. Xử lý nguồn dữ liệu
    # Nguồn 1: Chọn bộ dữ liệu mẫu có sẵn
    if sample_type:
        from app.sample_datasets import (
            generate_retail_fb_dataset,
            generate_saas_dataset,
            generate_manufacturing_dataset
        )
        if sample_type == "retail":
            p = os.path.join(SAMPLE_DIR, "retail_fb_sample.csv")
            df = pd.read_csv(p, encoding="utf-8-sig") if os.path.exists(p) else generate_retail_fb_dataset()
        elif sample_type == "saas":
            p = os.path.join(SAMPLE_DIR, "saas_sample.csv")
            df = pd.read_csv(p, encoding="utf-8-sig") if os.path.exists(p) else generate_saas_dataset()
        elif sample_type == "manufacturing":
            p = os.path.join(SAMPLE_DIR, "manufacturing_sample.csv")
            df = pd.read_csv(p, encoding="utf-8-sig") if os.path.exists(p) else generate_manufacturing_dataset()
        else:
            p = os.path.join(SAMPLE_DIR, "retail_fb_sample.csv")
            df = pd.read_csv(p, encoding="utf-8-sig") if os.path.exists(p) else generate_retail_fb_dataset()

    # Nguồn 2: Dán link Google Sheets
    elif gsheet_url and gsheet_url.strip():
        url = gsheet_url.strip()
        # Chuyển đổi link Google Sheets sang link xuất CSV
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
        if match:
            sheet_id = match.group(1)
            csv_export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            try:
                resp = requests.get(csv_export_url, timeout=10)
                if resp.status_code == 200:
                    df = pd.read_csv(io.StringIO(resp.text))
                else:
                    raise HTTPException(status_code=400, detail="Không thể tải dữ liệu từ Google Sheets. Vui lòng đảm bảo Sheet đã được bật chia sẻ 'Bất kỳ ai có liên kết' (Public).")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Lỗi khi đọc Google Sheets: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="Đường dẫn Google Sheets không đúng định dạng. Cần chứa /spreadsheets/d/{ID}...")

    # Nguồn 3: Tải file Excel / CSV từ máy tính
    elif file and file.filename:
        filename = file.filename.lower()
        contents = await file.read()
        try:
            # Lưu trữ file tải lên vào uploads (nếu môi trường cho phép ghi)
            try:
                save_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
                with open(os.path.join(UPLOADS_DIR, save_name), "wb") as f_out:
                    f_out.write(contents)
            except Exception:
                pass # Bỏ qua nếu môi trường chỉ đọc

            if filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(contents), encoding="utf-8-sig")
            elif filename.endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(contents))
            else:
                raise HTTPException(status_code=400, detail="Định dạng tệp không được hỗ trợ. Vui lòng tải file .xlsx, .xls hoặc .csv.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Không thể đọc file dữ liệu: {str(e)}")

    # 3. Ràng buộc chặn chưa có dữ liệu
    if df is None or len(df) == 0:
        raise HTTPException(
            status_code=400, 
            detail="Chưa có dữ liệu nào được nạp! Vui lòng tải file Excel/CSV, dán link Google Sheets hoặc bấm chọn một trong 3 bộ dữ liệu mẫu."
        )

    # Lưu vào session
    CURRENT_SESSION["business_meta"] = {
        "name": business_name.strip(),
        "model": business_model.strip(),
        "core_problem": core_problem.strip() if core_problem else "Tối ưu hóa tổng thể hoạt động kinh doanh",
        "additional_info": additional_info.strip()
    }
    CURRENT_SESSION["raw_df"] = df.copy()
    CURRENT_SESSION["cleaned_df"] = df.copy()
    CURRENT_SESSION["cell_tags"] = {}
    CURRENT_SESSION["analysis_data"] = None
    CURRENT_SESSION["exported_files"] = {}

    # Kiểm tra hiện trạng trước làm sạch
    initial_stats = DataCleaner.inspect_dataset(df)
    CURRENT_SESSION["cleaned_stats"] = {
        "before_stats": initial_stats,
        "after_stats": initial_stats
    }
    CURRENT_SESSION["audit_log"] = [
        f"[{pd.Timestamp.now().strftime('%H:%M:%S')}] Đã tiếp nhận tập dữ liệu nguồn gồm {len(df)} dòng và {len(df.columns)} cột từ '{business_name}'."
    ]

    # Trả về xem trước dữ liệu
    preview_rows = df.head(200).fillna("").to_dict(orient="records")
    columns = df.columns.tolist()

    return {
        "status": "success",
        "message": "Tiếp nhận dữ liệu thành công! Bạn có thể chuyển sang Bước 2 để rà soát làm sạch.",
        "business_meta": CURRENT_SESSION["business_meta"],
        "stats": initial_stats,
        "columns": columns,
        "preview_rows": preview_rows,
        "total_rows": len(df)
    }

# =============================================================================
# TRANG 3 — BƯỚC 2: LÀM SẠCH DỮ LIỆU & CỔNG KIỂM DUYỆT HITL
# =============================================================================

@app.post("/api/step2/clean")
async def run_clean(config: dict = None):
    """Thực hiện làm sạch tự động theo cấu hình"""
    if CURRENT_SESSION["raw_df"] is None:
        raise HTTPException(status_code=400, detail="Chưa có dữ liệu. Vui lòng hoàn thành Bước 1 trước.")

    df_to_clean = CURRENT_SESSION["raw_df"].copy()
    res = DataCleaner.auto_clean(df_to_clean, config)

    CURRENT_SESSION["cleaned_df"] = res["df"]
    CURRENT_SESSION["cleaned_stats"]["before_stats"] = res["before_stats"]
    CURRENT_SESSION["cleaned_stats"]["after_stats"] = res["after_stats"]
    CURRENT_SESSION["audit_log"].extend(res["audit_log"])
    CURRENT_SESSION["cell_tags"].update(res["cell_tags"])

    preview_rows = res["df"].head(200).fillna("").to_dict(orient="records")

    return {
        "status": "success",
        "before_stats": res["before_stats"],
        "after_stats": res["after_stats"],
        "audit_log": CURRENT_SESSION["audit_log"],
        "cell_tags": CURRENT_SESSION["cell_tags"],
        "columns": res["df"].columns.tolist(),
        "preview_rows": preview_rows,
        "total_rows": len(res["df"])
    }

@app.post("/api/step2/filter")
async def filter_condition(
    column: str = Form(...),
    operator: str = Form(...),
    value: str = Form(...),
    action: str = Form("remove")
):
    """
    Lọc và xóa/giữ dòng theo điều kiện chỉ đạo của người dùng.
    Ví dụ: bỏ Miền Bắc, giữ Miền Trung và Nam!
    """
    if CURRENT_SESSION["cleaned_df"] is None:
        raise HTTPException(status_code=400, detail="Chưa có dữ liệu đã làm sạch.")

    df = CURRENT_SESSION["cleaned_df"]
    new_df, log_msg, new_tags = DataCleaner.filter_and_remove(
        df, column, operator, value, action, CURRENT_SESSION["cell_tags"]
    )

    CURRENT_SESSION["cleaned_df"] = new_df
    CURRENT_SESSION["cell_tags"] = new_tags
    CURRENT_SESSION["audit_log"].append(log_msg)

    # Cập nhật thống kê sau lọc
    after_stats = DataCleaner.inspect_dataset(new_df)
    CURRENT_SESSION["cleaned_stats"]["after_stats"] = after_stats

    preview_rows = new_df.head(200).fillna("").to_dict(orient="records")

    return {
        "status": "success",
        "message": log_msg,
        "after_stats": after_stats,
        "audit_log": CURRENT_SESSION["audit_log"],
        "cell_tags": CURRENT_SESSION["cell_tags"],
        "columns": new_df.columns.tolist(),
        "preview_rows": preview_rows,
        "total_rows": len(new_df)
    }

@app.post("/api/step2/edit-cell")
async def edit_single_cell(
    row_idx: int = Form(...),
    col_name: str = Form(...),
    new_value: str = Form(...)
):
    """Chỉnh sửa trực tiếp từng ô bởi người dùng (Inline Editing)"""
    if CURRENT_SESSION["cleaned_df"] is None:
        raise HTTPException(status_code=400, detail="Chưa có dữ liệu.")

    df = CURRENT_SESSION["cleaned_df"]
    new_df, log_msg, tags = DataCleaner.edit_cell(
        df, row_idx, col_name, new_value, CURRENT_SESSION["cell_tags"]
    )

    CURRENT_SESSION["cleaned_df"] = new_df
    CURRENT_SESSION["cell_tags"] = tags
    CURRENT_SESSION["audit_log"].append(log_msg)

    after_stats = DataCleaner.inspect_dataset(new_df)
    CURRENT_SESSION["cleaned_stats"]["after_stats"] = after_stats

    return {
        "status": "success",
        "message": log_msg,
        "after_stats": after_stats,
        "audit_log": CURRENT_SESSION["audit_log"],
        "cell_tags": CURRENT_SESSION["cell_tags"]
    }

@app.post("/api/step2/directive")
async def review_directive(directive: str = Form(...)):
    """
    Tiếp nhận và thực thi chỉ đạo rà soát lặp nhiều vòng từ người dùng tại cổng HITL
    """
    if not directive or not directive.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập chỉ đạo rà soát.")

    if CURRENT_SESSION["cleaned_df"] is None:
        raise HTTPException(status_code=400, detail="Chưa có dữ liệu. Vui lòng hoàn thành Bước 1 trước.")

    now_str = pd.Timestamp.now().strftime("%H:%M:%S")
    directive_clean = directive.strip()
    CURRENT_SESSION["audit_log"].append(f"[{now_str}] CỔNG HITL TIẾP NHẬN CHỈ ĐẠO: '{directive_clean}'")

    # Sử dụng Động cơ DirectiveEngine thông minh (NLP + Gemini AI) để thực thi chỉ đạo
    new_df, new_tags, exec_msg = DirectiveEngine.execute(
        df=CURRENT_SESSION["cleaned_df"],
        directive=directive_clean,
        cell_tags=CURRENT_SESSION.get("cell_tags", {})
    )

    CURRENT_SESSION["cleaned_df"] = new_df
    CURRENT_SESSION["cell_tags"] = new_tags
    CURRENT_SESSION["audit_log"].append(f"[{now_str}] THỰC THI HITL: {exec_msg}")

    # Cập nhật thống kê sau chỉ đạo
    after_stats = DataCleaner.inspect_dataset(new_df)
    CURRENT_SESSION["cleaned_stats"]["after_stats"] = after_stats

    preview_rows = new_df.head(200).fillna("").to_dict(orient="records")

    return {
        "status": "success",
        "message": exec_msg,
        "after_stats": after_stats,
        "audit_log": CURRENT_SESSION["audit_log"],
        "cell_tags": new_tags,
        "columns": new_df.columns.tolist(),
        "preview_rows": preview_rows,
        "total_rows": len(new_df)
    }

@app.post("/api/step2/approve")
async def approve_and_proceed():
    """
    Phê duyệt dữ liệu hợp lệ tại Cổng kiểm duyệt HITL
    Khóa dữ liệu sạch và kích hoạt động cơ Phân tích 4 Cấp độ (Bước 3 & Bước 4)
    """
    if CURRENT_SESSION["cleaned_df"] is None or len(CURRENT_SESSION["cleaned_df"]) == 0:
        raise HTTPException(status_code=400, detail="Không có dữ liệu sạch hợp lệ để phê duyệt.")

    df = CURRENT_SESSION["cleaned_df"]
    meta = CURRENT_SESSION["business_meta"]

    now_str = pd.Timestamp.now().strftime("%H:%M:%S")
    CURRENT_SESSION["audit_log"].append(f"[{now_str}] CỔNG KIỂM DUYỆT HITL: Người dùng đã bấm 'PHÊ DUYỆT DỮ LIỆU HỢP LỆ'. Dữ liệu được niêm phong để phân tích.")

    # Chạy động cơ phân tích 4 cấp độ
    analysis = DataAnalyzer.analyze(
        df=df,
        business_name=meta.get("name", "Doanh nghiệp"),
        business_model=meta.get("model", "Mô hình chuẩn"),
        core_problem=meta.get("core_problem", "Tối ưu hóa tổng thể"),
        additional_info=meta.get("additional_info", "")
    )
    CURRENT_SESSION["analysis_data"] = analysis
    CURRENT_SESSION["exported_files"] = {}

    return {
        "status": "success",
        "message": "Phê duyệt thành công! Chuyển sang Bước 3 & Bước 4.",
        "analysis_data": analysis
    }

# =============================================================================
# TRANG 4 — BƯỚC 3 (PHÂN TÍCH 4 CẤP ĐỘ) & BƯỚC 4 (DASHBOARD)
# =============================================================================

@app.get("/api/step4/data")
async def get_dashboard_data():
    if CURRENT_SESSION.get("analysis_data") is None:
        ensure_session_ready()
    return CURRENT_SESSION["analysis_data"]

# =============================================================================
# TRANG 5 — XUẤT BÁO CÁO WORD DIID, XEM TRƯỚC IN & XUẤT 3 TỆP
# =============================================================================

@app.post("/api/step5/export-all")
async def export_all_files():
    """
    Tạo trọn bộ 3 tệp:
    1. [Tên]_DuLieuSach.xlsx (Excel chuẩn định dạng)
    2. [Tên]_BaoCaoDIID.docx (Word chuẩn Times New Roman 13pt kèm 4 biểu đồ & khung ký)
    3. [Tên]_BaoCaoDieuHanh.html (Báo cáo web độc lập)
    Đồng thời lưu đầy đủ vào Lịch sử chạy (Run History)
    """
    try:
        # Nếu phiên làm việc chưa có dữ liệu (hoặc Lambda vừa khởi động lại trong môi trường Stateless)
        if CURRENT_SESSION.get("cleaned_df") is None or CURRENT_SESSION.get("analysis_data") is None:
            ensure_session_ready()

        df = CURRENT_SESSION["cleaned_df"]
        analysis = CURRENT_SESSION["analysis_data"]
        stats = CURRENT_SESSION.get("cleaned_stats", {})
        meta = CURRENT_SESSION.get("business_meta", {})

        run_id = f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
        raw_biz_name = meta.get("name") or "Doanh_Nghiep"
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', raw_biz_name)

        # Đảm bảo thư mục xuất và thư mục ảnh biểu đồ tồn tại và có quyền ghi
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        charts_dir = os.path.join(EXPORTS_DIR, "temp_charts")
        os.makedirs(charts_dir, exist_ok=True)

        # 1. Xuất file Excel (.xlsx)
        excel_filename = f"{clean_name}_DuLieuSach_{run_id}.xlsx"
        excel_path = os.path.join(EXPORTS_DIR, excel_filename)
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Du_Lieu_Sach")
            audit_df = pd.DataFrame({"Nhat_Ky_Xu_Ly": CURRENT_SESSION.get("audit_log", [])})
            audit_df.to_excel(writer, index=False, sheet_name="Audit_Log")

        # 2. Tạo 4 ảnh biểu đồ
        chart_imgs = generate_chart_images(analysis, charts_dir)

        # 3. Xuất file Word (.docx) chuẩn DIID
        docx_filename = f"{clean_name}_BaoCaoDIID_{run_id}.docx"
        docx_path = os.path.join(EXPORTS_DIR, docx_filename)
        create_diid_word_report(analysis, stats, docx_path)

        # 4. Xuất file HTML (.html) độc lập
        html_filename = f"{clean_name}_BaoCaoDieuHanh_{run_id}.html"
        html_path = os.path.join(EXPORTS_DIR, html_filename)
        generate_standalone_html(analysis, stats, chart_imgs, html_path)

        file_paths = {
            "excel": f"/api/download/excel/{excel_filename}",
            "docx": f"/api/download/docx/{docx_filename}",
            "html": f"/api/download/html/{html_filename}",
            "local_paths": {
                "excel": excel_path,
                "docx": docx_path,
                "html": html_path
            }
        }
        CURRENT_SESSION["exported_files"] = file_paths

        # Lưu trữ vào Lịch sử chạy (Run History)
        try:
            summary_metrics = {
                "revenue": analysis["descriptive"]["total_revenue"],
                "cost": analysis["descriptive"]["total_cost"],
                "net_profit": analysis["descriptive"]["net_profit"],
                "profit_margin": analysis["descriptive"]["profit_margin"],
                "records": len(df)
            }
            HistoryManager.save_run(run_id, meta, summary_metrics, file_paths)
        except Exception as e_hist:
            print(f"Warning: History save skipped ({e_hist})")

        return {
            "status": "success",
            "message": "Đã xuất trọn bộ 3 tệp và lưu thành công vào Lịch sử chạy!",
            "run_id": run_id,
            "files": file_paths,
            "html_content_url": f"/api/download/html/{html_filename}"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi xuất báo cáo: {str(e)}")

@app.get("/api/download/{file_type}/{filename}")
async def download_file(file_type: str, filename: str):
    p = os.path.join(EXPORTS_DIR, filename)
    if not os.path.exists(p):
        # Tự động kết xuất lại nếu request rơi vào Lambda worker mới
        try:
            await export_all_files()
        except Exception:
            pass
        if not os.path.exists(p):
            # Nếu tên tệp có timestamp khác, tìm tệp mới nhất cùng định dạng
            ext_map = {"excel": ".xlsx", "docx": ".docx", "html": ".html"}
            target_ext = ext_map.get(file_type, f".{file_type}")
            try:
                candidates = [f for f in os.listdir(EXPORTS_DIR) if f.endswith(target_ext)]
                if candidates:
                    p = os.path.join(EXPORTS_DIR, sorted(candidates)[-1])
            except Exception:
                pass

    if not os.path.exists(p):
        raise HTTPException(status_code=404, detail="Tệp không tồn tại hoặc đã bị xóa.")

    media_types = {
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "html": "text/html; charset=utf-8"
    }
    media_type = media_types.get(file_type, "application/octet-stream")
    return FileResponse(p, media_type=media_type, filename=os.path.basename(p))

@app.get("/api/preview-html")
async def get_preview_html():
    """Xem trước khi in bản HTML trực tiếp trên giao diện"""
    if "exported_files" in CURRENT_SESSION and "local_paths" in CURRENT_SESSION["exported_files"]:
        p = CURRENT_SESSION["exported_files"]["local_paths"].get("html")
        if p and os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return HTMLResponse(
                    f.read(),
                    headers={"Cache-Control": "no-store, no-cache, must-revalidate"}
                )
    # Tự động tạo bản xuất mới nếu rơi vào instance mới
    try:
        await export_all_files()
        p = CURRENT_SESSION.get("exported_files", {}).get("local_paths", {}).get("html")
        if p and os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return HTMLResponse(
                    f.read(),
                    headers={"Cache-Control": "no-store, no-cache, must-revalidate"}
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể khởi tạo bản xem trước: {str(e)}")

    raise HTTPException(status_code=404, detail="Chưa tạo bản xem trước. Vui lòng bấm 'Xuất trọn bộ 3 tệp' trước.")

# =============================================================================
# LỊCH SỬ CHẠY, ĐÁNH GIÁ 1-5 SAO & TRỢ LÝ ẢO ANORA
# =============================================================================

@app.get("/api/history")
async def get_history_runs():
    return HistoryManager.list_runs()

@app.post("/api/feedback")
async def submit_feedback(
    stars: int = Form(...),
    comments: str = Form(""),
    run_id: str = Form(None)
):
    """Tiếp nhận đánh giá 1-5 sao và ý kiến của người dùng"""
    res = HistoryManager.save_feedback(stars, comments, run_id)
    return {
        "status": "success",
        "message": f"Cảm ơn bạn đã gửi đánh giá {stars} sao cho AnoraAI!",
        "feedback": res
    }

@app.post("/api/assistant/chat")
async def chat_assistant(message: str = Form(...)):
    """Trợ lý ảo AI Anora giải đáp mọi câu hỏi (hỗ trợ ngữ cảnh hội thoại nhiều lượt)"""
    context = dict(CURRENT_SESSION.get("analysis_data") or {})
    if not context and CURRENT_SESSION.get("business_meta"):
        context["business_meta"] = CURRENT_SESSION["business_meta"]
    cur_df = CURRENT_SESSION.get("cleaned_df") if CURRENT_SESSION.get("cleaned_df") is not None else CURRENT_SESSION.get("raw_df")
    if cur_df is not None:
        context["columns"] = cur_df.columns.tolist()
        context["total_rows"] = len(cur_df)

    chat_history = CURRENT_SESSION.setdefault("chat_history", [])
    reply = AssistantAI.answer_query(message, context, history=chat_history)
    chat_history.append({"role": "user", "text": message})
    chat_history.append({"role": "assistant", "text": reply})
    if len(chat_history) > 20:
        CURRENT_SESSION["chat_history"] = chat_history[-20:]

    return {
        "status": "success",
        "reply": reply
    }

from datetime import datetime

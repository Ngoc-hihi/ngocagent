"""
docx_generator.py - Tạo Báo cáo Phân tích Kinh doanh chuẩn mẫu doanh nghiệp bằng python-docx
- Font chữ: Times New Roman, Cỡ chữ: 13pt
- Phong cách trình bày trang trọng, chuẩn văn bản điều hành: đen trắng / xám trung tính, không màu sắc lòe loẹt
- Giữ nguyên bảng màu pastel AnoraAI cho 4 biểu đồ trực quan nhúng trong báo cáo
- Cấu trúc đầy đủ 3 phần lớn theo mẫu chuẩn:
  I. Giới thiệu Tổng quan Doanh nghiệp & Bối cảnh Phân tích
  II. Phân tích & Đánh giá Hoạt động Kinh doanh (Tài chính, Khách hàng, Vận hành + Bảng số liệu + 4 Biểu đồ + Phân tích Dashboard)
  III. Đề xuất Giải pháp & Kiến nghị Kinh doanh (Đạt được/Hạn chế, Scale Up/Optimize/Mitigate, Giải pháp KPI) + Khung ký duyệt
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from datetime import datetime

# Màu sắc chuẩn văn bản nghiêm túc (không lòe loẹt)
TEXT_BLACK = RGBColor(0x00, 0x00, 0x00)
TEXT_DARK = RGBColor(0x22, 0x22, 0x22)
TEXT_MUTED = RGBColor(0x44, 0x44, 0x44)
HEADER_FILL_GRAY = "F2F2F2"
BORDER_HEX_GRAY = "BFBFBF"


def set_cell_background(cell, fill_hex):
    """Đặt màu nền cho cell trong bảng docx"""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex.replace("#", "")}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=80, bottom=80, left=120, right=120):
    """Đặt đệm lề cho cell"""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def set_table_borders(table, color=BORDER_HEX_GRAY, sz="4", val="single"):
    """Đặt viền mỏng trang nhã cho bảng"""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def remove_table_borders(table):
    """Xóa toàn bộ viền bảng (dùng cho Header & Khung ký)"""
    set_table_borders(table, color="FFFFFF", sz="0", val="none")


def set_run_font(run, bold=False, italic=False, size_pt=13, color=TEXT_BLACK):
    """Chuẩn hóa font Times New Roman 13pt cho mọi run"""
    run.font.name = 'Times New Roman'
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')
    rFonts.set(qn('w:cs'), 'Times New Roman')
    run.font.size = Pt(size_pt)
    run.font.color.rgb = color
    run.bold = bold
    run.italic = italic
    return run


def add_p(container, text="", bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=0, space_after=6, color=TEXT_BLACK):
    """Thêm đoạn văn chuẩn Times New Roman 13pt"""
    p = container.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    if text:
        r = p.add_run(text)
        set_run_font(r, bold=bold, italic=italic, size_pt=13, color=color)
    return p


def add_labeled_p(container, label, body_text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=5):
    """Thêm đoạn có phần đầu in đậm và phần nội dung thường (Times New Roman 13pt)"""
    p = container.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    r1 = p.add_run(label)
    set_run_font(r1, bold=True, size_pt=13, color=TEXT_BLACK)
    r2 = p.add_run(body_text)
    set_run_font(r2, bold=False, size_pt=13, color=TEXT_BLACK)
    return p


def generate_chart_images(analysis_data: dict, output_dir: str) -> dict:
    """Tạo 4 ảnh biểu đồ matplotlib thực tế (giữ nguyên bảng màu pastel AnoraAI)"""
    os.makedirs(output_dir, exist_ok=True)
    chart_paths = {}

    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Calibri']
    plt.rcParams['axes.edgecolor'] = '#D3C8BE'
    plt.rcParams['axes.linewidth'] = 0.8

    # 1. Donut Chart - Cơ cấu doanh thu/danh mục
    fig, ax = plt.subplots(figsize=(6.5, 4.2), facecolor='#FAF7F2')
    ax.set_facecolor('#FAF7F2')
    donut_info = analysis_data["charts"]["chart_donut"]
    colors = ['#5C6B52', '#D49B9E', '#7D8B74', '#E8C5C8', '#C3B091', '#8B9B84']
    pie_labels = donut_info.get("raw_labels", donut_info["labels"])
    wedges, texts, autotexts = ax.pie(
        donut_info["data"],
        labels=pie_labels,
        labeldistance=1.15,
        autopct='%1.1f%%',
        pctdistance=0.78,
        startangle=140,
        colors=colors[:len(donut_info["data"])],
        wedgeprops=dict(width=0.42, edgecolor='#FAF7F2', linewidth=2.5)
    )
    for t in texts:
        t.set_fontsize(9.5)
        t.set_color('#2E382A')
    for at in autotexts:
        at.set_fontsize(10)
        at.set_color('#FFFFFF')
        at.set_weight('bold')
        at.set_path_effects([path_effects.withStroke(linewidth=2, foreground='#2E382A')])
    ax.set_title(donut_info["title"], fontsize=11, fontweight='bold', color='#2E382A', pad=14)
    p1 = os.path.join(output_dir, "chart_donut.png")
    fig.tight_layout()
    fig.savefig(p1, dpi=200, facecolor=fig.get_facecolor())
    plt.close(fig)
    chart_paths["donut"] = p1

    # 2. Bar Chart - Doanh thu vs Chi phí (hoặc Doanh thu theo kỳ)
    fig, ax = plt.subplots(figsize=(6.5, 3.8), facecolor='#FAF7F2')
    ax.set_facecolor('#FFFFFF')
    bar_info = analysis_data["charts"]["chart_bar_comparison"]
    x = list(range(len(bar_info["labels"])))
    has_cost_series = bool(bar_info.get("series_cost") and any(v > 0 for v in bar_info["series_cost"]))
    if has_cost_series:
        width = 0.35
        ax.bar([i - width/2 for i in x], [v/1e6 for v in bar_info["series_revenue"]], width, label='Doanh thu (Tr VNĐ)', color='#5C6B52', edgecolor='#45523E', alpha=0.9)
        ax.bar([i + width/2 for i in x], [v/1e6 for v in bar_info["series_cost"]], width, label='Chi phí (Tr VNĐ)', color='#D49B9E', edgecolor='#BA8083', alpha=0.9)
    else:
        width = 0.45
        ax.bar(x, [v/1e6 for v in bar_info["series_revenue"]], width, label='Doanh thu (Tr VNĐ)', color='#5C6B52', edgecolor='#45523E', alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(bar_info["labels"], fontsize=8.5, color='#2E382A')
    ax.set_ylabel('Triệu VNĐ', fontsize=9, color='#2E382A')
    ax.set_title(bar_info["title"], fontsize=11, fontweight='bold', color='#2E382A', pad=12)
    ax.legend(frameon=False, fontsize=8.5)
    ax.grid(axis='y', linestyle='--', alpha=0.4, color='#D3C8BE')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    p2 = os.path.join(output_dir, "chart_bar.png")
    fig.tight_layout()
    fig.savefig(p2, dpi=200, facecolor=fig.get_facecolor())
    plt.close(fig)
    chart_paths["bar"] = p2

    # 3. Line Chart - Xu hướng lịch sử & Dự báo
    fig, ax = plt.subplots(figsize=(6.5, 3.8), facecolor='#FAF7F2')
    ax.set_facecolor('#FFFFFF')
    trend_info = analysis_data["charts"]["chart_trend_forecast"]
    split_idx = trend_info.get("split_index", len(trend_info["data"]))
    all_vals = [v / 1e6 for v in trend_info["data"]]
    all_x = list(range(len(trend_info["labels"])))
    if split_idx > 0:
        ax.plot(all_x[:split_idx], all_vals[:split_idx], marker='o', linewidth=2.2, color='#5C6B52', label='Thực tế (Lịch sử)')
    if split_idx < len(all_vals):
        start_fc = max(0, split_idx - 1)
        ax.plot(all_x[start_fc:], all_vals[start_fc:], marker='D', linestyle='--', linewidth=2.2, color='#D49B9E', label='Dự báo AI (3 kỳ tới)')
    ax.set_xticks(all_x)
    ax.set_xticklabels(trend_info["labels"], fontsize=7.5, rotation=15, color='#2E382A')
    ax.set_ylabel('Triệu VNĐ', fontsize=9, color='#2E382A')
    ax.set_title(trend_info["title"], fontsize=11, fontweight='bold', color='#2E382A', pad=12)
    ax.legend(frameon=False, fontsize=8.5)
    ax.grid(axis='y', linestyle='--', alpha=0.4, color='#D3C8BE')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    p3 = os.path.join(output_dir, "chart_line.png")
    fig.tight_layout()
    fig.savefig(p3, dpi=200, facecolor=fig.get_facecolor())
    plt.close(fig)
    chart_paths["line"] = p3

    # 4. Horizontal Bar Chart - Phân bổ theo khu vực/đơn vị
    fig, ax = plt.subplots(figsize=(6.5, 3.8), facecolor='#FAF7F2')
    ax.set_facecolor('#FFFFFF')
    reg_info = analysis_data["charts"]["chart_region_performance"]
    y_pos = list(range(len(reg_info["labels"])))
    reg_colors = ['#5C6B52', '#7D8B74', '#C3B091', '#D49B9E', '#8B9B84'][:len(y_pos)]
    ax.barh(y_pos, [v/1e6 for v in reg_info["data"]], color=reg_colors, height=0.55)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(reg_info["labels"], fontsize=9, color='#2E382A')
    ax.invert_yaxis()
    ax.set_xlabel('Doanh thu (Triệu VNĐ)', fontsize=9, color='#2E382A')
    ax.set_title(reg_info["title"], fontsize=11, fontweight='bold', color='#2E382A', pad=12)
    ax.grid(axis='x', linestyle='--', alpha=0.4, color='#D3C8BE')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    p4 = os.path.join(output_dir, "chart_region.png")
    fig.tight_layout()
    fig.savefig(p4, dpi=200, facecolor=fig.get_facecolor())
    plt.close(fig)
    chart_paths["region"] = p4

    return chart_paths


def create_diid_word_report(analysis_data: dict, cleaning_stats: dict, output_docx_path: str) -> str:
    """
    Tạo báo cáo Word (.docx) theo đúng mẫu chuẩn của người dùng:
    - Font chữ: Times New Roman, Cỡ chữ: 13pt
    - Đen trắng / xám trung tính nghiêm túc, không màu sắc lòe loẹt
    - Giữ nguyên màu của 4 biểu đồ trực quan nhúng bên trong
    """
    charts_dir = os.path.join(os.path.dirname(output_docx_path), "temp_charts")
    chart_paths = generate_chart_images(analysis_data, charts_dir)

    doc = docx.Document()

    # Căn lề chuẩn 2.54cm như file mẫu
    for section in doc.sections:
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.0)

    # Đặt font mặc định Times New Roman 13pt
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(13)
    style.font.color.rgb = TEXT_BLACK
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:ascii'), 'Times New Roman')
    rFonts.set(qn('w:hAnsi'), 'Times New Roman')
    rFonts.set(qn('w:cs'), 'Times New Roman')

    meta = analysis_data["business_meta"]
    desc = analysis_data["descriptive"]
    diag = analysis_data["diagnostic"]
    pred = analysis_data["predictive"]
    pres = analysis_data["prescriptive"]

    biz_name = meta.get("name", "DOANH NGHIỆP").strip()
    biz_model = meta.get("model", "Kinh doanh tổng hợp").strip()
    core_problem = meta.get("core_problem", "Tối ưu doanh thu & hiệu quả vận hành").strip()
    total_records = desc.get("total_records", 0)
    has_cost = desc.get("has_cost_data", False)

    after_s = cleaning_stats.get("after_stats", {})
    before_s = cleaning_stats.get("before_stats", {})
    quality_score = after_s.get("quality_score", 100)
    null_cells = after_s.get("null_cells", 0)
    dup_rows = before_s.get("duplicate_rows", 0)

    now_dt = datetime.now()
    report_code = f"BCPTKD-{now_dt.strftime('%Y%m%d')}"
    report_date = now_dt.strftime('%d/%m/%Y')

    # Trích xuất các chỉ số thực tế để đưa vào văn bản (không bịa đặt)
    b_cat = analysis_data.get("breakdown_by_cat", [])
    b_reg = analysis_data.get("breakdown_by_region", [])
    top_cat = b_cat[0] if b_cat else {"name": "N/A", "value": 0, "pct": 0}
    bot_cat = b_cat[-1] if b_cat else {"name": "N/A", "value": 0, "pct": 0}
    top2_pct = round(sum(float(x["pct"]) for x in b_cat[:2]), 1) if len(b_cat) >= 2 else float(top_cat["pct"])
    cat_ratio = round(float(top_cat["value"]) / float(bot_cat["value"]), 1) if bot_cat.get("value", 0) > 0 else 1.0

    top_reg = b_reg[0] if b_reg else {"name": "N/A", "value": 0, "pct": 0}
    bot_reg = b_reg[-1] if b_reg else {"name": "N/A", "value": 0, "pct": 0}
    top2_reg_pct = round(sum(float(x["pct"]) for x in b_reg[:2]), 1) if len(b_reg) >= 2 else float(top_reg["pct"])
    reg_ratio = round(float(top_reg["value"]) / float(bot_reg["value"]), 1) if bot_reg.get("value", 0) > 0 else 1.0

    bar_info = analysis_data["charts"]["chart_bar_comparison"]
    bar_labels = bar_info.get("labels", [])
    bar_rev = bar_info.get("series_revenue", [])
    if bar_rev and len(bar_rev) >= 2:
        first_rev, last_rev = bar_rev[0], bar_rev[-1]
        rev_change_pct = round(((last_rev - first_rev) / first_rev * 100), 1) if first_rev > 0 else 0.0
        max_rev = max(bar_rev)
        min_rev = min(bar_rev)
        max_period = bar_labels[bar_rev.index(max_rev)]
        min_period = bar_labels[bar_rev.index(min_rev)]
        avg_period_rev = sum(bar_rev) / len(bar_rev)
    else:
        first_rev = last_rev = desc["total_revenue"]
        rev_change_pct = 0.0
        max_rev = min_rev = desc["total_revenue"]
        max_period = min_period = "Kỳ hiện tại"
        avg_period_rev = desc["total_revenue"]

    # =========================================================================
    # HEADER BẢNG 2 CỘT (KHÔNG VIỀN)
    # =========================================================================
    tbl_hdr = doc.add_table(rows=1, cols=2)
    tbl_hdr.alignment = WD_TABLE_ALIGNMENT.CENTER
    remove_table_borders(tbl_hdr)
    c_left, c_right = tbl_hdr.rows[0].cells
    c_left.width = Inches(4.0)
    c_right.width = Inches(2.8)
    set_cell_margins(c_left, 20, 40, 20, 40)
    set_cell_margins(c_right, 20, 40, 40, 20)

    p_l = c_left.paragraphs[0]
    p_l.paragraph_format.space_after = Pt(2)
    set_run_font(p_l.add_run(biz_name.upper()), bold=True, size_pt=13)
    add_p(c_left, f"Lĩnh vực: {biz_model}", space_after=2)
    add_p(c_left, "Đơn vị lập: AnoraAI Data Intelligence Agent", space_after=2)

    p_r = c_right.paragraphs[0]
    p_r.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_r.paragraph_format.space_after = Pt(2)
    set_run_font(p_r.add_run(f"Số: {report_code}"), bold=True, size_pt=13)
    add_p(c_right, f"Ngày lập: {report_date}", align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=2)
    add_p(c_right, f"Nguồn: Dữ liệu sạch HITL ({total_records:,} dòng)", align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=2)

    # =========================================================================
    # TIÊU ĐỀ CHÍNH
    # =========================================================================
    add_p(doc, "BÁO CÁO PHÂN TÍCH KINH DOANH", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=12, space_after=4)
    add_p(doc, f"Mục tiêu phân tích: {core_problem}", align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_p(doc, f'Bài toán kinh doanh đặt ra: "{core_problem}"', italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12, color=TEXT_DARK)

    # =========================================================================
    # I. GIỚI THIỆU TỔNG QUAN DOANH NGHIỆP & BỐI CẢNH PHÂN TÍCH
    # =========================================================================
    add_p(doc, "I. Giới thiệu Tổng quan Doanh nghiệp & Bối cảnh Phân tích", bold=True, space_before=8, space_after=6)

    add_p(doc, "1.1. Tổng quan Doanh nghiệp & Bối cảnh", bold=True, space_before=4, space_after=4)
    add_p(
        doc,
        f'{biz_name} hoạt động trong lĩnh vực {biz_model}. Trong kỳ đánh giá hiện tại, Ban Lãnh đạo đặt ra mục tiêu trọng tâm là "{core_problem}". '
        f'Báo cáo này phân tích toàn diện trên tập dữ liệu đã qua làm sạch và kiểm duyệt HITL gồm {total_records:,} bản ghi giao dịch hợp lệ.',
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6
    )

    add_p(doc, "1.2. Phương pháp Phân tích & Hồ sơ Dữ liệu", bold=True, space_before=4, space_after=4)
    add_p(
        doc,
        f"Báo cáo áp dụng khung phân tích chuẩn mực DIID (Data → Information → Insight → Decision) kết hợp 4 phương pháp bổ trợ: "
        f"(1) Phân tích Mô tả quy mô & cấu trúc kinh doanh; (2) Phân tích Tập trung Pareto (80/20) xác định nhóm động lực chính; "
        f"(3) Phân tích Xu hướng & Dự báo chuỗi thời gian; và (4) Kiểm định độ tin cậy dữ liệu đầu vào. "
        f"Độ tin cậy dữ liệu sau làm sạch đạt {quality_score}/100 ({null_cells} ô thiếu còn lại, đã xử lý {dup_rows} dòng trùng lặp).",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6
    )

    add_p(doc, "1.3. Tổng hợp Phát hiện Trọng tâm", bold=True, space_before=4, space_after=4)

    add_p(doc, "1. Tóm tắt điều hành", bold=True, space_after=3)
    summary_exec = (
        f'Dựa trên bối cảnh của {biz_name} ({biz_model}) với mục tiêu "{core_problem}", phân tích {total_records:,} bản ghi '
        f'(Độ tin cậy: {quality_score}/100) ghi nhận tổng doanh thu đạt {desc["total_revenue"]:,.0f} VNĐ'
    )
    if has_cost:
        summary_exec += f', tổng chi phí {desc["total_cost"]:,.0f} VNĐ, lợi nhuận ròng {desc["net_profit"]:,.0f} VNĐ (biên lãi {desc["profit_margin"]}%)'
    summary_exec += f'. Nhóm "{top_cat["name"]}" đang dẫn đầu cơ cấu với {top_cat["pct"]}% tổng doanh thu, đồng thời xu hướng doanh thu qua các kỳ biến động {rev_change_pct:+.1f}%.'
    add_p(doc, summary_exec, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=5)

    add_p(doc, "2. Phân tích theo chiều ngang (so sánh qua các kỳ)", bold=True, space_after=3)
    add_p(
        doc,
        f"Qua {len(bar_labels)} kỳ vận hành ({bar_labels[0] if bar_labels else 'Kỳ đầu'} đạt {first_rev:,.0f} VNĐ đến {bar_labels[-1] if bar_labels else 'Kỳ cuối'} đạt {last_rev:,.0f} VNĐ), "
        f"doanh thu ghi nhận mức biến động {rev_change_pct:+.1f}%. Kỳ đạt đỉnh là {max_period} ({max_rev:,.0f} VNĐ) và kỳ thấp nhất là {min_period} ({min_rev:,.0f} VNĐ), bình quân đạt {avg_period_rev:,.0f} VNĐ/kỳ.",
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=5
    )

    add_p(doc, "3. Phân tích theo chiều dọc (cơ cấu)", bold=True, space_after=3)
    add_p(
        doc,
        f'Theo cơ cấu phân khúc/kênh, "{top_cat["name"]}" chiếm tỷ trọng cao nhất ({top_cat["pct"]}%, đạt {top_cat["value"]:,.0f} VNĐ). '
        f'Top 2 nhóm dẫn đầu chiếm {top2_pct}% cơ cấu toàn bộ, trong khi nhóm cuối "{bot_cat["name"]}" chỉ chiếm {bot_cat["pct"]}% ({bot_cat["value"]:,.0f} VNĐ). '
        f'Theo đơn vị/khu vực, "{top_reg["name"]}" dẫn đầu với {top_reg["pct"]}% tổng doanh thu ({top_reg["value"]:,.0f} VNĐ).',
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=5
    )

    add_p(doc, "4. Phân tích các nhóm chỉ số cốt lõi", bold=True, space_after=3)
    add_p(doc, f'- Doanh thu (Chỉ số chính): Tổng {desc["total_revenue"]:,.0f} VNĐ, trung bình {desc["avg_value_per_record"]:,.0f} VNĐ/bản ghi.', space_after=2)
    if has_cost:
        add_p(doc, f'- Chi phí & Biên hiệu quả: Tổng chi phí {desc["total_cost"]:,.0f} VNĐ; lợi nhuận ròng đạt {desc["net_profit"]:,.0f} VNĐ (Biên lợi nhuận ròng: {desc["profit_margin"]}%).', space_after=2)
    else:
        add_p(doc, '- Cấu trúc dữ liệu: Tập dữ liệu tập trung hạch toán doanh thu thuần (chưa bao gồm trường chi phí chi tiết).', space_after=2)
    add_p(doc, f'- Sức khỏe dữ liệu đầu vào: Điểm tin cậy đạt {quality_score}/100 ({null_cells} ô thiếu, đã khử {dup_rows} dòng trùng lặp).', space_after=5)

    add_p(doc, "5. Nguyên nhân & đề xuất giải pháp", bold=True, space_after=3)
    rc_text = diag["root_causes"][0] if diag.get("root_causes") else f"Hiệu suất chung bị chi phối mạnh bởi độ tập trung Pareto ({top2_pct}% ở Top 2)."
    add_p(doc, f"- Nguyên nhân cốt lõi: {rc_text}", align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=2)
    add_p(
        doc,
        f'- Đề xuất giải pháp: (1) Bảo vệ nhóm lõi "{top_cat["name"]}" và phân bổ 15–20% ngân sách phát triển nhóm thứ cấp để giảm phụ thuộc dưới 65%; '
        f'(2) Chuẩn hóa định mức vận hành và nhân rộng mô hình từ khu vực hiệu quả nhất ("{top_reg["name"]}").',
        align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=8
    )

    # =========================================================================
    # II. PHÂN TÍCH & ĐÁNH GIÁ HOẠT ĐỘNG KINH DOANH
    # =========================================================================
    add_p(doc, "II. Phân tích & Đánh giá Hoạt động Kinh doanh", bold=True, space_before=8, space_after=6)

    # 2.1 Tài chính
    add_p(doc, "2.1. Khía cạnh Tài chính (Financial Perspective)", bold=True, space_after=4)
    fin_txt = f'Tổng doanh thu toàn kỳ đạt {desc["total_revenue"]:,.0f} VNĐ (trung bình {desc["avg_value_per_record"]:,.0f} VNĐ/giao dịch). '
    if has_cost:
        fin_txt += f'Tổng chi phí đạt {desc["total_cost"]:,.0f} VNĐ, mang lại lợi nhuận ròng {desc["net_profit"]:,.0f} VNĐ (biên lãi ròng {desc["profit_margin"]}%). '
    fin_txt += f'Về động lượng tài chính qua {len(bar_labels)} kỳ, doanh thu ghi nhận mức biến động {rev_change_pct:+.1f}%.'
    add_labeled_p(doc, "- Thực trạng & Số liệu: ", fin_txt)
    add_labeled_p(
        doc, "- Đánh giá chuyên sâu: ",
        f'{"Biên lợi nhuận đạt " + str(desc["profit_margin"]) + "% cần được duy trì thông qua kiểm soát định mức chi phí trực tiếp." if has_cost else "Quy mô doanh thu tập trung rõ nét, cần bổ sung dữ liệu giá vốn để đánh giá biên lãi ròng theo từng nhóm."}'
    )
    add_labeled_p(
        doc, "- Hàm ý quản trị: ",
        f'Ưu tiên bảo vệ dòng tiền từ nhóm doanh thu cao nhất ("{top_cat["name"]}") và rà soát tối ưu hiệu suất tại nhóm thấp nhất ("{bot_cat["name"]}").',
        space_after=6
    )

    # 2.2 Khách hàng & Thị trường
    add_p(doc, "2.2. Khía cạnh Khách hàng & Thị trường (Customer Perspective)", bold=True, space_after=4)
    add_labeled_p(
        doc, "- Thực trạng & Số liệu: ",
        f'Phân tích {len(b_cat)} nhóm phân khúc/kênh cho thấy cấu trúc phân hóa rõ rệt: "{top_cat["name"]}" giữ vai trò đầu tàu với {top_cat["value"]:,.0f} VNĐ ({top_cat["pct"]}%), '
        f'gấp {cat_ratio}x nhóm cuối "{bot_cat["name"]}" ({bot_cat["value"]:,.0f} VNĐ, {bot_cat["pct"]}%). Top 2 nhóm dẫn đầu chiếm {top2_pct}% toàn thị trường.'
    )
    add_labeled_p(
        doc, "- Đánh giá chuyên sâu: ",
        f'Mức độ tập trung vào Top 2 nhóm đang ở mức {top2_pct}% ({"ngưỡng cao > 70%, tiềm ẩn rủi ro phụ thuộc" if top2_pct > 70 else "ngưỡng cân bằng hợp lý"}) nếu phân khúc chủ lực gặp biến động nhu cầu.'
    )
    add_labeled_p(
        doc, "- Hàm ý quản trị: ",
        f'Xây dựng chiến lược giữ chân khách hàng tại "{top_cat["name"]}", đồng thời triển khai chương trình kích thích chuyển đổi riêng cho nhóm quy mô trung bình và thấp.',
        space_after=6
    )

    # 2.3 Quy trình nội bộ & Vận hành
    add_p(doc, "2.3. Khía cạnh Quy trình Nội bộ & Vận hành (Internal Business Processes)", bold=True, space_after=4)
    add_labeled_p(
        doc, "- Thực trạng & Số liệu: ",
        f'Quy trình ghi nhận dữ liệu đạt điểm tin cậy {quality_score}/100 ({null_cells} ô khuyết còn lại, {dup_rows} dòng trùng lặp đã loại bỏ). '
        f'Khu vực/đơn vị "{top_reg["name"]}" dẫn đầu vận hành với doanh thu {top_reg["value"]:,.0f} VNĐ ({top_reg["pct"]}%).'
    )
    add_labeled_p(
        doc, "- Đánh giá chuyên sâu: ",
        "Hệ thống kiểm duyệt HITL đảm bảo dữ liệu sạch và nhất quán trước khi đưa vào tính toán, giảm thiểu sai lệch do lỗi nhập liệu hoặc giá trị ngoại lai."
    )
    add_labeled_p(
        doc, "- Hàm ý quản trị: ",
        f'Chuẩn hóa quy trình kiểm soát chứng từ đầu vào và áp dụng tiêu chuẩn vận hành của "{top_reg["name"]}" làm chuẩn cho các đơn vị còn lại.',
        space_after=8
    )

    # =========================================================================
    # BẢNG 1: TỔNG HỢP SỐ LIỆU THEO ĐƠN VỊ / KHU VỰC
    # =========================================================================
    if b_reg:
        tbl1 = doc.add_table(rows=len(b_reg) + 1, cols=4)
        tbl1.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(tbl1)
        headers1 = ["Đơn vị / Khu vực", "Tổng Doanh thu (VNĐ)", "Tỷ trọng (%)", "Phân loại Hiệu quả"]
        for c_i, h_txt in enumerate(headers1):
            cell = tbl1.rows[0].cells[c_i]
            set_cell_background(cell, HEADER_FILL_GRAY)
            set_cell_margins(cell, 70, 70, 100, 100)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_i > 0 else WD_ALIGN_PARAGRAPH.LEFT
            set_run_font(p.add_run(h_txt), bold=True, size_pt=13)

        for r_i, item in enumerate(b_reg[:8], start=1):
            if r_i >= len(tbl1.rows):
                break
            row_cells = tbl1.rows[r_i].cells
            pct_val = float(item["pct"])
            status_lbl = "Chủ lực (Tốt)" if pct_val >= 20 else ("Tiềm năng" if pct_val >= 10 else "Cần tối ưu")
            vals = [str(item["name"]), f"{item['value']:,.0f}", f"{pct_val}%", status_lbl]
            for c_i, v_txt in enumerate(vals):
                set_cell_margins(row_cells[c_i], 60, 60, 100, 100)
                p = row_cells[c_i].paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if c_i in [1, 2] else (WD_ALIGN_PARAGRAPH.CENTER if c_i == 3 else WD_ALIGN_PARAGRAPH.LEFT)
                set_run_font(p.add_run(v_txt), bold=(c_i == 0), size_pt=13)

        add_p(doc, "", space_after=6)

    # =========================================================================
    # BẢNG 2: 4 BIỂU ĐỒ TRỰC QUAN (2x2 GRID - GIỮ NGUYÊN MÀU BIỂU ĐỒ)
    # =========================================================================
    tbl_charts = doc.add_table(rows=2, cols=2)
    tbl_charts.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_charts)
    chart_grid = [
        [(chart_paths["line"], analysis_data["charts"]["chart_trend_forecast"]["title"]),
         (chart_paths["donut"], analysis_data["charts"]["chart_donut"]["title"])],
        [(chart_paths["region"], analysis_data["charts"]["chart_region_performance"]["title"]),
         (chart_paths["bar"], analysis_data["charts"]["chart_bar_comparison"]["title"])]
    ]
    for r_i in range(2):
        for c_i in range(2):
            img_path, title_txt = chart_grid[r_i][c_i]
            cell = tbl_charts.rows[r_i].cells[c_i]
            set_cell_margins(cell, 80, 80, 80, 80)
            p_title = cell.paragraphs[0]
            p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_title.paragraph_format.space_after = Pt(4)
            set_run_font(p_title.add_run(title_txt), bold=True, size_pt=13)
            p_img = cell.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_after = Pt(2)
            p_img.add_run().add_picture(img_path, width=Inches(3.0))

    add_p(doc, "", space_after=6)

    # =========================================================================
    # BẢNG 3: PHÂN TÍCH CHI TIẾT 4 BIỂU ĐỒ TRÊN DASHBOARD (5x3)
    # =========================================================================
    tbl_dash = doc.add_table(rows=5, cols=3)
    tbl_dash.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_dash)
    dash_headers = ["Khía cạnh Dashboard", "Phát hiện Số liệu & Nguyên nhân", "Tác động & Kiến nghị Kinh doanh"]
    col_widths_dash = [Inches(1.8), Inches(2.6), Inches(2.4)]
    for c_i, h_txt in enumerate(dash_headers):
        cell = tbl_dash.rows[0].cells[c_i]
        cell.width = col_widths_dash[c_i]
        set_cell_background(cell, HEADER_FILL_GRAY)
        set_cell_margins(cell, 70, 70, 90, 90)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_run_font(p.add_run(h_txt), bold=True, size_pt=13)

    fc_base_val = pred["scenarios"]["base_case"]["values"][0] if pred.get("scenarios") else desc["total_revenue"]
    dash_rows_data = [
        (
            f"1. Biểu đồ Xu hướng & Dự báo\nBiến động {rev_change_pct:+.1f}%",
            f"Số liệu: Qua {len(bar_labels)} kỳ, doanh thu biến động {rev_change_pct:+.1f}%. Đỉnh tại {max_period} ({max_rev:,.0f} VNĐ) và đáy tại {min_period} ({min_rev:,.0f} VNĐ). Dự báo T+1 đạt {fc_base_val:,.0f} VNĐ.\nTác động: Giúp Ban Giám đốc thiết lập hạn mức ngân sách và kế hoạch dòng tiền sát thực tế.",
            f"Ngắn hạn (1–2 tuần): Rà soát nguyên nhân chênh lệch tại kỳ thấp điểm {min_period}.\nTrung hạn: Thiết kế chương trình kích cầu cho các kỳ chững lại."
        ),
        (
            f"2. Biểu đồ Cơ cấu Phân khúc\nTop 2 chiếm {top2_pct}% · Chênh {cat_ratio}x",
            f'Số liệu: "{top_cat["name"]}" đóng góp {top_cat["value"]:,.0f} VNĐ ({top_cat["pct"]}%), gấp {cat_ratio} lần "{bot_cat["name"]}" ({bot_cat["pct"]}%).\nTác động: Mức tập trung {top2_pct}% phản ánh nguồn thu chủ lực rõ nét nhưng cần phòng ngừa rủi ro phụ thuộc.',
            f'Ngắn hạn: Bảo vệ thị phần tại "{top_cat["name"]}".\nTrung hạn: Trích 15–20% ngân sách phát triển nhóm thứ cấp để đưa độ tập trung về <65%.'
        ),
        (
            f"3. Biểu đồ Đối chiếu Kỳ vận hành\nTB {avg_period_rev:,.0f} VNĐ/kỳ",
            f'Số liệu: Doanh thu bình quân đạt {avg_period_rev:,.0f} VNĐ/kỳ. {"Biên lợi nhuận ròng đạt " + str(desc["profit_margin"]) + "%." if has_cost else "Theo dõi sát nhịp độ doanh thu từng kỳ."}\nTác động: Nhận diện kịp thời các kỳ chi phí tăng đột biến hoặc hiệu suất suy giảm.',
            f"Ngắn hạn: Kiểm toán cấu trúc chi phí tại các kỳ biên thấp.\nTrung hạn: Chuẩn hóa định mức ngân sách theo kỳ hiệu quả nhất ({max_period})."
        ),
        (
            f"4. Phân bổ theo Khu vực & Rủi ro\nĐiểm tin cậy {quality_score}/100",
            f'Số liệu: "{top_reg["name"]}" dẫn đầu với {top_reg["value"]:,.0f} VNĐ ({top_reg["pct"]}%). Dữ liệu sạch {quality_score}/100 ({null_cells} ô thiếu).\nTác động: Chênh lệch {reg_ratio}x giữa khu vực đầu và cuối cho thấy dư địa mở rộng lớn.',
            f'Ngắn hạn: Rà soát trực tiếp chứng từ ở nhóm ngoại lai.\nTrung hạn: Nhân rộng quy trình bán hàng của "{top_reg["name"]}" sang "{bot_reg["name"]}".'
        )
    ]

    for r_i, (c1_t, c2_t, c3_t) in enumerate(dash_rows_data, start=1):
        row = tbl_dash.rows[r_i]
        for c_i, txt in enumerate([c1_t, c2_t, c3_t]):
            cell = row.cells[c_i]
            cell.width = col_widths_dash[c_i]
            set_cell_margins(cell, 70, 70, 90, 90)
            lines = txt.split("\n")
            p0 = cell.paragraphs[0]
            p0.paragraph_format.space_after = Pt(3)
            set_run_font(p0.add_run(lines[0]), bold=(c_i == 0), size_pt=13)
            for extra_line in lines[1:]:
                p_ex = cell.add_paragraph()
                p_ex.paragraph_format.space_after = Pt(2)
                set_run_font(p_ex.add_run(extra_line), bold=False, size_pt=13)

    add_p(doc, "", space_after=6)

    # =========================================================================
    # III. ĐỀ XUẤT GIẢI PHÁP VÀ KIẾN NGHỊ KINH DOANH
    # =========================================================================
    add_p(doc, "III. Đề xuất Giải pháp và Kiến nghị Kinh doanh", bold=True, space_before=8, space_after=6)

    # Bảng 4 (1x2): 3.1 Mặt đạt được | 3.2 Hạn chế
    tbl_sw = doc.add_table(rows=1, cols=2)
    tbl_sw.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_sw)
    sw_l, sw_r = tbl_sw.rows[0].cells
    set_cell_margins(sw_l, 80, 80, 100, 100)
    set_cell_margins(sw_r, 80, 80, 100, 100)

    p_swl = sw_l.paragraphs[0]
    p_swl.paragraph_format.space_after = Pt(4)
    set_run_font(p_swl.add_run("3.1. Những mặt đạt được"), bold=True, size_pt=13)
    add_p(sw_l, f'- Xác định rõ động lực tăng trưởng chủ lực là "{top_cat["name"]}" ({top_cat["pct"]}%) và khu vực "{top_reg["name"]}" ({top_reg["pct"]}%).', space_after=3)
    add_p(sw_l, f"- Chất lượng dữ liệu đạt mức tin cậy cao ({quality_score}/100), tạo nền tảng chính xác cho quyết định điều hành.", space_after=2)

    p_swr = sw_r.paragraphs[0]
    p_swr.paragraph_format.space_after = Pt(4)
    set_run_font(p_swr.add_run("3.2. Hạn chế & Điểm nghẽn cần khắc phục"), bold=True, size_pt=13)
    add_p(sw_r, f"- Độ tập trung Pareto ở mức {top2_pct}%: cần tránh phụ thuộc quá lớn vào một nhóm dẫn đầu.", space_after=3)
    bottleneck_txt = diag["bottlenecks"][0] if diag.get("bottlenecks") else f'Nhóm "{bot_cat["name"]}" chỉ chiếm {bot_cat["pct"]}%, cần biện pháp kích cầu.'
    add_p(sw_r, f"- {bottleneck_txt}", space_after=2)

    add_p(doc, "", space_after=6)

    # Bảng 5 (1x3): Nhân rộng | Tối ưu | Kiểm soát Rủi ro
    tbl_action3 = doc.add_table(rows=1, cols=3)
    tbl_action3.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_action3)
    a1, a2, a3 = tbl_action3.rows[0].cells
    for c in [a1, a2, a3]:
        set_cell_margins(c, 80, 80, 90, 90)

    p_a1 = a1.paragraphs[0]
    set_run_font(p_a1.add_run("Nhân rộng (Scale Up)"), bold=True, size_pt=13)
    add_p(a1, f'• {top_cat["name"]} ({top_cat["value"]:,.0f} VNĐ, {top_cat["pct"]}%)', space_after=2)
    add_p(a1, f'• Khu vực {top_reg["name"]} ({top_reg["pct"]}%)', space_after=2)

    p_a2 = a2.paragraphs[0]
    set_run_font(p_a2.add_run("Tối ưu (Optimize)"), bold=True, size_pt=13)
    mid_cat = b_cat[1] if len(b_cat) > 1 else top_cat
    add_p(a2, f'• {mid_cat["name"]} ({mid_cat["pct"]}%)', space_after=2)
    add_p(a2, "Có tiềm năng mở rộng quy mô nhưng cần tối ưu tỷ lệ chuyển đổi.", space_after=2)

    p_a3 = a3.paragraphs[0]
    set_run_font(p_a3.add_run("Kiểm soát Rủi ro (Mitigate)"), bold=True, size_pt=13)
    add_p(a3, f'• Nhóm thấp điểm: {bot_cat["name"]} ({bot_cat["pct"]}%)', space_after=2)
    add_p(a3, f'• Rủi ro biến động tại {min_period} ({min_rev:,.0f} VNĐ).', space_after=2)

    add_p(doc, "", space_after=6)

    # 3.3 Giải pháp & KPI
    add_p(doc, "3.3. Giải pháp Nâng cao Hiệu quả Kinh doanh & Chỉ tiêu KPI", bold=True, space_before=4, space_after=4)

    solutions = [
        (
            "3.3.1. Phân tích Tập trung (Pareto) & Đa dạng hóa Nguồn thu (Ưu tiên: Cao — Thời hạn: Tuần 1–2 & Quý tới)",
            f'Top 2 nhóm hiện chiếm {top2_pct}% tổng doanh thu (riêng "{top_cat["name"]}" đạt {top_cat["value"]:,.0f} VNĐ). Doanh nghiệp cần giảm rủi ro phụ thuộc vào nhóm dẫn đầu.',
            "Giai đoạn 1 (Tuần 1–2): Bảo vệ vùng lõi & chất lượng dịch vụ tại nhóm dẫn đầu. Giai đoạn 2 (Tháng 1–2): Phân bổ 15–20% ngân sách kích hoạt nhóm thứ cấp. Giai đoạn 3 (Tháng 3): Theo dõi tỷ trọng tuần và tái cân bằng.",
            f"Hiện tại: Top 2 chiếm {top2_pct}% → Mục tiêu: Đưa tỷ trọng Top 2 về dưới 65% và tăng trưởng ròng tổng doanh thu thêm +10–15%.",
            "Ban Giám đốc & Bộ phận Kinh doanh / Marketing."
        ),
        (
            "3.3.2. Tối ưu Hiệu suất Vận hành & Kiểm soát Định mức (Ưu tiên: Cao — Thời hạn: Tháng 1–2)",
            f'Khoảng cách hiệu suất giữa khu vực dẫn đầu ("{top_reg["name"]}") và khu vực cuối ("{bot_reg["name"]}") lên tới {reg_ratio}x, cho thấy định mức vận hành giữa các đơn vị chưa đồng đều.',
            "Giai đoạn 1: Kiểm toán chi tiết cấu phần chi phí tại nhóm hiệu quả thấp để cắt giảm 10–15% lãng phí. Giai đoạn 2: Đóng gói quy trình chuẩn (SOP) từ đơn vị dẫn đầu. Giai đoạn 3: Thiết lập ngưỡng cảnh báo trên Dashboard.",
            f'Hiện tại: Chênh lệch {reg_ratio}x giữa các khu vực → Mục tiêu: Thu hẹp chênh lệch xuống < 2.5x và nâng hiệu suất nhóm cuối thêm +20%.',
            "Bộ phận Tài chính, Kế toán & Quản lý Vận hành."
        )
    ]

    for title_s, a_txt, b_txt, c_txt, d_txt in solutions:
        add_p(doc, title_s, bold=True, space_before=4, space_after=3)
        add_labeled_p(doc, "a) Căn cứ dữ liệu & Đánh giá nguyên nhân: ", a_txt, space_after=2)
        add_labeled_p(doc, "b) Lộ trình giải pháp & Hành động triển khai: ", b_txt, space_after=2)
        add_labeled_p(doc, "c) Chỉ tiêu KPI đo lường (Hiện tại → Mục tiêu): ", c_txt, space_after=2)
        add_labeled_p(doc, "d) Bộ phận phụ trách & Nguồn lực phối hợp: ", d_txt, space_after=6)

    # =========================================================================
    # KHUNG KÝ DUYỆT (LỆCH PHẢI NHƯ MẪU GOOGLE DOCS)
    # =========================================================================
    add_p(doc, "", space_after=8)
    tbl_sig = doc.add_table(rows=1, cols=2)
    tbl_sig.alignment = WD_TABLE_ALIGNMENT.CENTER
    remove_table_borders(tbl_sig)
    s_left, s_right = tbl_sig.rows[0].cells
    s_left.width = Inches(3.2)
    s_right.width = Inches(3.6)

    p_sr = s_right.paragraphs[0]
    p_sr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sr.paragraph_format.space_after = Pt(2)
    set_run_font(p_sr.add_run("BAN GIÁM ĐỐC / LÃNH ĐẠO PHÊ DUYỆT"), bold=True, size_pt=13)
    add_p(s_right, "(Kiểm duyệt & Ký duyệt ban hành)", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=36)
    add_p(s_right, "(Ký, ghi rõ họ tên & đóng dấu)", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)

    os.makedirs(os.path.dirname(output_docx_path), exist_ok=True)
    doc.save(output_docx_path)
    return output_docx_path

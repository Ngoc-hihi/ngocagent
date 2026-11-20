"""
html_report_generator.py - Tạo file Báo cáo HTML Độc lập & Khung Xem Trước Khi In (Print Preview)
- Đồng bộ 100% với mẫu Báo cáo Phân tích Kinh doanh (.docx) từ Google Docs của người dùng
- Font chữ: Times New Roman, Cỡ chữ: 13pt
- Phong cách trình bày nghiêm túc: đen trắng / xám trung tính, không màu sắc lòe loẹt
- Nhúng đầy đủ 4 biểu đồ PNG (giữ nguyên bảng màu pastel của biểu đồ) bằng Base64
"""

import os
import base64
from datetime import datetime


def generate_standalone_html(analysis_data: dict, cleaned_stats: dict, chart_imgs: dict, output_filepath: str) -> str:
    meta = analysis_data["business_meta"]
    desc = analysis_data["descriptive"]
    diag = analysis_data["diagnostic"]
    pred = analysis_data["predictive"]
    pres = analysis_data["prescriptive"]
    b_stats = cleaned_stats.get("before_stats", {})
    a_stats = cleaned_stats.get("after_stats", {})

    # Chuyển 4 ảnh biểu đồ sang Base64 để file HTML hoạt động độc lập 100%
    b64_charts = {}
    for k, p in chart_imgs.items():
        if p and os.path.exists(p):
            with open(p, "rb") as f:
                b64_charts[k] = base64.b64encode(f.read()).decode('utf-8')
        else:
            b64_charts[k] = ""

    biz_name = meta.get("name", "DOANH NGHIỆP").strip()
    biz_model = meta.get("model", "Kinh doanh tổng hợp").strip()
    core_problem = meta.get("core_problem", "Tối ưu doanh thu & hiệu quả vận hành").strip()
    total_records = desc.get("total_records", 0)
    has_cost = desc.get("has_cost_data", False)

    quality_score = a_stats.get("quality_score", 100)
    null_cells = a_stats.get("null_cells", 0)
    dup_rows = b_stats.get("duplicate_rows", 0)

    now_dt = datetime.now()
    report_code = f"BCPTKD-{now_dt.strftime('%Y%m%d')}"
    report_date = now_dt.strftime('%d/%m/%Y')

    # Chỉ số thực tế từ analysis_data
    b_cat = analysis_data.get("breakdown_by_cat", [])
    b_reg = analysis_data.get("breakdown_by_region", [])
    top_cat = b_cat[0] if b_cat else {"name": "N/A", "value": 0, "pct": 0}
    bot_cat = b_cat[-1] if b_cat else {"name": "N/A", "value": 0, "pct": 0}
    top2_pct = round(sum(float(x["pct"]) for x in b_cat[:2]), 1) if len(b_cat) >= 2 else float(top_cat["pct"])
    cat_ratio = round(float(top_cat["value"]) / float(bot_cat["value"]), 1) if bot_cat.get("value", 0) > 0 else 1.0

    top_reg = b_reg[0] if b_reg else {"name": "N/A", "value": 0, "pct": 0}
    bot_reg = b_reg[-1] if b_reg else {"name": "N/A", "value": 0, "pct": 0}
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

    fc_base_val = pred["scenarios"]["base_case"]["values"][0] if pred.get("scenarios") else desc["total_revenue"]
    rc_text = diag["root_causes"][0] if diag.get("root_causes") else f"Hiệu suất chung bị chi phối mạnh bởi độ tập trung Pareto ({top2_pct}% ở Top 2)."
    bottleneck_txt = diag["bottlenecks"][0] if diag.get("bottlenecks") else f'Nhóm "{bot_cat["name"]}" chỉ chiếm {bot_cat["pct"]}%, cần biện pháp kích cầu.'
    mid_cat = b_cat[1] if len(b_cat) > 1 else top_cat

    # Bảng 1: Tổng hợp số liệu theo Đơn vị / Khu vực
    reg_rows_html = ""
    for item in b_reg[:8]:
        pct_val = float(item["pct"])
        status_lbl = "Chủ lực (Tốt)" if pct_val >= 20 else ("Tiềm năng" if pct_val >= 10 else "Cần tối ưu")
        reg_rows_html += f"""
        <tr>
          <td><strong>{item['name']}</strong></td>
          <td style="text-align: right;">{item['value']:,.0f}</td>
          <td style="text-align: right;">{pct_val}%</td>
          <td style="text-align: center;">{status_lbl}</td>
        </tr>"""

    summary_exec = f'Dựa trên bối cảnh của {biz_name} ({biz_model}) với mục tiêu "{core_problem}", phân tích {total_records:,} bản ghi (Độ tin cậy: {quality_score}/100) ghi nhận tổng doanh thu đạt {desc["total_revenue"]:,.0f} VNĐ'
    if has_cost:
        summary_exec += f', tổng chi phí {desc["total_cost"]:,.0f} VNĐ, lợi nhuận ròng {desc["net_profit"]:,.0f} VNĐ (biên lãi {desc["profit_margin"]}%)'
    summary_exec += f'. Nhóm "{top_cat["name"]}" đang dẫn đầu cơ cấu với {top_cat["pct"]}% tổng doanh thu, đồng thời xu hướng doanh thu qua các kỳ biến động {rev_change_pct:+.1f}%.'

    cost_bullet = (
        f'<li><strong>Chi phí &amp; Biên hiệu quả:</strong> Tổng chi phí {desc["total_cost"]:,.0f} VNĐ; lợi nhuận ròng đạt {desc["net_profit"]:,.0f} VNĐ (Biên lợi nhuận ròng: {desc["profit_margin"]}%).</li>'
        if has_cost else
        '<li><strong>Cấu trúc dữ liệu:</strong> Tập dữ liệu tập trung hạch toán doanh thu thuần (chưa bao gồm trường chi phí chi tiết).</li>'
    )

    fin_txt = f'Tổng doanh thu toàn kỳ đạt {desc["total_revenue"]:,.0f} VNĐ (trung bình {desc["avg_value_per_record"]:,.0f} VNĐ/giao dịch). '
    if has_cost:
        fin_txt += f'Tổng chi phí đạt {desc["total_cost"]:,.0f} VNĐ, mang lại lợi nhuận ròng {desc["net_profit"]:,.0f} VNĐ (biên lãi ròng {desc["profit_margin"]}%). '
    fin_txt += f'Về động lượng tài chính qua {len(bar_labels)} kỳ, doanh thu ghi nhận mức biến động {rev_change_pct:+.1f}%.'

    fin_eval = (
        f'Biên lợi nhuận đạt {desc["profit_margin"]}% cần được duy trì thông qua kiểm soát định mức chi phí trực tiếp.'
        if has_cost else
        'Quy mô doanh thu tập trung rõ nét, cần bổ sung dữ liệu giá vốn để đánh giá biên lãi ròng theo từng nhóm.'
    )

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Báo Cáo Phân Tích Kinh Doanh - {biz_name}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: 'Times New Roman', Times, serif;
  font-size: 13pt;
  line-height: 1.45;
  color: #000000;
  background-color: #FFFFFF;
  padding: 28px 36px;
}}
.report-container {{
  max-width: 860px;
  margin: 0 auto;
  background: #FFFFFF;
}}
.header-tbl {{
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 14px;
  border: none;
}}
.header-tbl td {{
  border: none;
  padding: 2px 4px;
  vertical-align: top;
  font-size: 13pt;
}}
.title-block {{
  text-align: center;
  margin: 14px 0 18px 0;
}}
.title-block h1 {{
  font-size: 13pt;
  font-weight: bold;
  text-transform: uppercase;
  margin-bottom: 4px;
  color: #000000;
}}
.title-block .sub {{
  font-size: 13pt;
  margin-bottom: 2px;
}}
.title-block .problem {{
  font-size: 13pt;
  font-style: italic;
  color: #222222;
}}
h2.sec-h2 {{
  font-size: 13pt;
  font-weight: bold;
  margin: 16px 0 6px 0;
  color: #000000;
}}
h3.sec-h3 {{
  font-size: 13pt;
  font-weight: bold;
  margin: 10px 0 4px 0;
  color: #000000;
}}
p {{
  text-align: justify;
  margin-bottom: 6px;
}}
ul.plain-list {{
  margin: 4px 0 8px 22px;
}}
ul.plain-list li {{
  margin-bottom: 4px;
  text-align: justify;
}}
table.data-tbl {{
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0 14px 0;
  font-size: 13pt;
}}
table.data-tbl th, table.data-tbl td {{
  border: 1px solid #BFBFBF;
  padding: 7px 9px;
  vertical-align: top;
  font-size: 13pt;
}}
table.data-tbl th {{
  background-color: #F2F2F2;
  font-weight: bold;
  color: #000000;
  text-align: center;
}}
table.chart-tbl {{
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0 14px 0;
}}
table.chart-tbl td {{
  width: 50%;
  border: 1px solid #BFBFBF;
  padding: 10px;
  text-align: center;
  vertical-align: top;
}}
table.chart-tbl .chart-title {{
  font-weight: bold;
  font-size: 13pt;
  margin-bottom: 6px;
}}
table.chart-tbl img {{
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0 auto;
}}
.sig-tbl {{
  width: 100%;
  border-collapse: collapse;
  margin-top: 24px;
  border: none;
}}
.sig-tbl td {{
  border: none;
  width: 50%;
  text-align: center;
  vertical-align: top;
  font-size: 13pt;
}}
.print-btn-bar {{
  text-align: right;
  margin-bottom: 12px;
}}
.btn-print {{
  padding: 6px 14px;
  font-family: 'Times New Roman', serif;
  font-size: 12pt;
  cursor: pointer;
  background: #F2F2F2;
  border: 1px solid #999999;
}}
@media print {{
  body {{ padding: 0; }}
  .no-print {{ display: none !important; }}
}}
</style>
</head>
<body>
<div class="report-container">
  <div class="print-btn-bar no-print">
    <button class="btn-print" onclick="window.print()">In báo cáo / Lưu PDF</button>
  </div>

  <table class="header-tbl">
    <tr>
      <td style="width: 58%;">
        <div><strong>{biz_name.upper()}</strong></div>
        <div>Lĩnh vực: {biz_model}</div>
        <div>Đơn vị lập: AnoraAI Data Intelligence Agent</div>
      </td>
      <td style="width: 42%; text-align: right;">
        <div><strong>Số: {report_code}</strong></div>
        <div>Ngày lập: {report_date}</div>
        <div>Nguồn: Dữ liệu sạch HITL ({total_records:,} dòng)</div>
      </td>
    </tr>
  </table>

  <div class="title-block">
    <h1>BÁO CÁO PHÂN TÍCH KINH DOANH</h1>
    <div class="sub">Mục tiêu phân tích: {core_problem}</div>
    <div class="problem">Bài toán kinh doanh đặt ra: "{core_problem}"</div>
  </div>

  <h2 class="sec-h2">I. Giới thiệu Tổng quan Doanh nghiệp &amp; Bối cảnh Phân tích</h2>

  <h3 class="sec-h3">1.1. Tổng quan Doanh nghiệp &amp; Bối cảnh</h3>
  <p>
    {biz_name} hoạt động trong lĩnh vực {biz_model}. Trong kỳ đánh giá hiện tại, Ban Lãnh đạo đặt ra mục tiêu trọng tâm là "{core_problem}".
    Báo cáo này phân tích toàn diện trên tập dữ liệu đã qua làm sạch và kiểm duyệt HITL gồm {total_records:,} bản ghi giao dịch hợp lệ.
  </p>

  <h3 class="sec-h3">1.2. Phương pháp Phân tích &amp; Hồ sơ Dữ liệu</h3>
  <p>
    Báo cáo áp dụng khung phân tích chuẩn mực DIID (Data &rarr; Information &rarr; Insight &rarr; Decision) kết hợp 4 phương pháp bổ trợ:
    (1) Phân tích Mô tả quy mô &amp; cấu trúc kinh doanh; (2) Phân tích Tập trung Pareto (80/20) xác định nhóm động lực chính;
    (3) Phân tích Xu hướng &amp; Dự báo chuỗi thời gian; và (4) Kiểm định độ tin cậy dữ liệu đầu vào.
    Độ tin cậy dữ liệu sau làm sạch đạt {quality_score}/100 ({null_cells} ô thiếu còn lại, đã xử lý {dup_rows} dòng trùng lặp).
  </p>

  <h3 class="sec-h3">1.3. Tổng hợp Phát hiện Trọng tâm</h3>
  <h3 class="sec-h3">1. Tóm tắt điều hành</h3>
  <p>{summary_exec}</p>

  <h3 class="sec-h3">2. Phân tích theo chiều ngang (so sánh qua các kỳ)</h3>
  <p>
    Qua {len(bar_labels)} kỳ vận hành ({bar_labels[0] if bar_labels else 'Kỳ đầu'} đạt {first_rev:,.0f} VNĐ đến {bar_labels[-1] if bar_labels else 'Kỳ cuối'} đạt {last_rev:,.0f} VNĐ),
    doanh thu ghi nhận mức biến động {rev_change_pct:+.1f}%. Kỳ đạt đỉnh là {max_period} ({max_rev:,.0f} VNĐ) và kỳ thấp nhất là {min_period} ({min_rev:,.0f} VNĐ), bình quân đạt {avg_period_rev:,.0f} VNĐ/kỳ.
  </p>

  <h3 class="sec-h3">3. Phân tích theo chiều dọc (cơ cấu)</h3>
  <p>
    Theo cơ cấu phân khúc/kênh, "{top_cat['name']}" chiếm tỷ trọng cao nhất ({top_cat['pct']}%, đạt {top_cat['value']:,.0f} VNĐ).
    Top 2 nhóm dẫn đầu chiếm {top2_pct}% cơ cấu toàn bộ, trong khi nhóm cuối "{bot_cat['name']}" chỉ chiếm {bot_cat['pct']}% ({bot_cat['value']:,.0f} VNĐ).
    Theo đơn vị/khu vực, "{top_reg['name']}" dẫn đầu với {top_reg['pct']}% tổng doanh thu ({top_reg['value']:,.0f} VNĐ).
  </p>

  <h3 class="sec-h3">4. Phân tích các nhóm chỉ số cốt lõi</h3>
  <ul class="plain-list">
    <li><strong>Doanh thu (Chỉ số chính):</strong> Tổng {desc['total_revenue']:,.0f} VNĐ, trung bình {desc['avg_value_per_record']:,.0f} VNĐ/bản ghi.</li>
    {cost_bullet}
    <li><strong>Sức khỏe dữ liệu đầu vào:</strong> Điểm tin cậy đạt {quality_score}/100 ({null_cells} ô thiếu, đã khử {dup_rows} dòng trùng lặp).</li>
  </ul>

  <h3 class="sec-h3">5. Nguyên nhân &amp; đề xuất giải pháp</h3>
  <p><strong>- Nguyên nhân cốt lõi:</strong> {rc_text}</p>
  <p>
    <strong>- Đề xuất giải pháp:</strong> (1) Bảo vệ nhóm lõi "{top_cat['name']}" và phân bổ 15–20% ngân sách phát triển nhóm thứ cấp để giảm phụ thuộc dưới 65%;
    (2) Chuẩn hóa định mức vận hành và nhân rộng mô hình từ khu vực hiệu quả nhất ("{top_reg['name']}").
  </p>

  <h2 class="sec-h2">II. Phân tích &amp; Đánh giá Hoạt động Kinh doanh</h2>

  <h3 class="sec-h3">2.1. Khía cạnh Tài chính (Financial Perspective)</h3>
  <p><strong>- Thực trạng &amp; Số liệu:</strong> {fin_txt}</p>
  <p><strong>- Đánh giá chuyên sâu:</strong> {fin_eval}</p>
  <p><strong>- Hàm ý quản trị:</strong> Ưu tiên bảo vệ dòng tiền từ nhóm doanh thu cao nhất ("{top_cat['name']}") và rà soát tối ưu hiệu suất tại nhóm thấp nhất ("{bot_cat['name']}").</p>

  <h3 class="sec-h3">2.2. Khía cạnh Khách hàng &amp; Thị trường (Customer Perspective)</h3>
  <p>
    <strong>- Thực trạng &amp; Số liệu:</strong> Phân tích {len(b_cat)} nhóm phân khúc/kênh cho thấy cấu trúc phân hóa rõ rệt: "{top_cat['name']}" giữ vai trò đầu tàu với {top_cat['value']:,.0f} VNĐ ({top_cat['pct']}%),
    gấp {cat_ratio}x nhóm cuối "{bot_cat['name']}" ({bot_cat['value']:,.0f} VNĐ, {bot_cat['pct']}%). Top 2 nhóm dẫn đầu chiếm {top2_pct}% toàn thị trường.
  </p>
  <p><strong>- Đánh giá chuyên sâu:</strong> Mức độ tập trung vào Top 2 nhóm đang ở mức {top2_pct}% ({"ngưỡng cao > 70%, tiềm ẩn rủi ro phụ thuộc" if top2_pct > 70 else "ngưỡng cân bằng hợp lý"}) nếu phân khúc chủ lực gặp biến động nhu cầu.</p>
  <p><strong>- Hàm ý quản trị:</strong> Xây dựng chiến lược giữ chân khách hàng tại "{top_cat['name']}", đồng thời triển khai chương trình kích thích chuyển đổi riêng cho nhóm quy mô trung bình và thấp.</p>

  <h3 class="sec-h3">2.3. Khía cạnh Quy trình Nội bộ &amp; Vận hành (Internal Business Processes)</h3>
  <p>
    <strong>- Thực trạng &amp; Số liệu:</strong> Quy trình ghi nhận dữ liệu đạt điểm tin cậy {quality_score}/100 ({null_cells} ô khuyết còn lại, {dup_rows} dòng trùng lặp đã loại bỏ).
    Khu vực/đơn vị "{top_reg['name']}" dẫn đầu vận hành với doanh thu {top_reg['value']:,.0f} VNĐ ({top_reg['pct']}%).
  </p>
  <p><strong>- Đánh giá chuyên sâu:</strong> Hệ thống kiểm duyệt HITL đảm bảo dữ liệu sạch và nhất quán trước khi đưa vào tính toán, giảm thiểu sai lệch do lỗi nhập liệu hoặc giá trị ngoại lai.</p>
  <p><strong>- Hàm ý quản trị:</strong> Chuẩn hóa quy trình kiểm soát chứng từ đầu vào và áp dụng tiêu chuẩn vận hành của "{top_reg['name']}" làm chuẩn cho các đơn vị còn lại.</p>

  {f'''
  <table class="data-tbl">
    <thead>
      <tr>
        <th style="text-align: left;">Đơn vị / Khu vực</th>
        <th>Tổng Doanh thu (VNĐ)</th>
        <th>Tỷ trọng (%)</th>
        <th>Phân loại Hiệu quả</th>
      </tr>
    </thead>
    <tbody>
      {reg_rows_html}
    </tbody>
  </table>
  ''' if b_reg else ''}

  <!-- BẢNG 4 BIỂU ĐỒ TRỰC QUAN (2x2) -->
  <table class="chart-tbl">
    <tr>
      <td>
        <div class="chart-title">{analysis_data['charts']['chart_trend_forecast']['title']}</div>
        <img src="data:image/png;base64,{b64_charts.get('line', '')}" alt="Xu hướng và Dự báo">
      </td>
      <td>
        <div class="chart-title">{analysis_data['charts']['chart_donut']['title']}</div>
        <img src="data:image/png;base64,{b64_charts.get('donut', '')}" alt="Cơ cấu Doanh thu">
      </td>
    </tr>
    <tr>
      <td>
        <div class="chart-title">{analysis_data['charts']['chart_region_performance']['title']}</div>
        <img src="data:image/png;base64,{b64_charts.get('region', '')}" alt="Hiệu quả theo Khu vực">
      </td>
      <td>
        <div class="chart-title">{analysis_data['charts']['chart_bar_comparison']['title']}</div>
        <img src="data:image/png;base64,{b64_charts.get('bar', '')}" alt="Đối chiếu Kỳ vận hành">
      </td>
    </tr>
  </table>

  <!-- BẢNG PHÂN TÍCH DASHBOARD -->
  <table class="data-tbl">
    <thead>
      <tr>
        <th style="width: 26%;">Khía cạnh Dashboard</th>
        <th style="width: 39%;">Phát hiện Số liệu &amp; Nguyên nhân</th>
        <th style="width: 35%;">Tác động &amp; Kiến nghị Kinh doanh</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>1. Biểu đồ Xu hướng &amp; Dự báo</strong><br>Biến động {rev_change_pct:+.1f}%</td>
        <td>
          Số liệu: Qua {len(bar_labels)} kỳ, doanh thu biến động {rev_change_pct:+.1f}%. Đỉnh tại {max_period} ({max_rev:,.0f} VNĐ) và đáy tại {min_period} ({min_rev:,.0f} VNĐ). Dự báo T+1 đạt {fc_base_val:,.0f} VNĐ.<br>
          Tác động: Giúp Ban Giám đốc thiết lập hạn mức ngân sách và kế hoạch dòng tiền sát thực tế.
        </td>
        <td>
          Ngắn hạn (1–2 tuần): Rà soát nguyên nhân chênh lệch tại kỳ thấp điểm {min_period}.<br>
          Trung hạn: Thiết kế chương trình kích cầu cho các kỳ chững lại.
        </td>
      </tr>
      <tr>
        <td><strong>2. Biểu đồ Cơ cấu Phân khúc</strong><br>Top 2 chiếm {top2_pct}% · Chênh {cat_ratio}x</td>
        <td>
          Số liệu: "{top_cat['name']}" đóng góp {top_cat['value']:,.0f} VNĐ ({top_cat['pct']}%), gấp {cat_ratio} lần "{bot_cat['name']}" ({bot_cat['pct']}%).<br>
          Tác động: Mức tập trung {top2_pct}% phản ánh nguồn thu chủ lực rõ nét nhưng cần phòng ngừa rủi ro phụ thuộc.
        </td>
        <td>
          Ngắn hạn: Bảo vệ thị phần tại "{top_cat['name']}".<br>
          Trung hạn: Trích 15–20% ngân sách phát triển nhóm thứ cấp để đưa độ tập trung về &lt;65%.
        </td>
      </tr>
      <tr>
        <td><strong>3. Biểu đồ Đối chiếu Kỳ vận hành</strong><br>TB {avg_period_rev:,.0f} VNĐ/kỳ</td>
        <td>
          Số liệu: Doanh thu bình quân đạt {avg_period_rev:,.0f} VNĐ/kỳ. {"Biên lợi nhuận ròng đạt " + str(desc["profit_margin"]) + "%." if has_cost else "Theo dõi sát nhịp độ doanh thu từng kỳ."}<br>
          Tác động: Nhận diện kịp thời các kỳ chi phí tăng đột biến hoặc hiệu suất suy giảm.
        </td>
        <td>
          Ngắn hạn: Kiểm toán cấu trúc chi phí tại các kỳ biên thấp.<br>
          Trung hạn: Chuẩn hóa định mức ngân sách theo kỳ hiệu quả nhất ({max_period}).
        </td>
      </tr>
      <tr>
        <td><strong>4. Phân bổ theo Khu vực &amp; Rủi ro</strong><br>Điểm tin cậy {quality_score}/100</td>
        <td>
          Số liệu: "{top_reg['name']}" dẫn đầu với {top_reg['value']:,.0f} VNĐ ({top_reg['pct']}%). Dữ liệu sạch {quality_score}/100 ({null_cells} ô thiếu).<br>
          Tác động: Chênh lệch {reg_ratio}x giữa khu vực đầu và cuối cho thấy dư địa mở rộng lớn.
        </td>
        <td>
          Ngắn hạn: Rà soát trực tiếp chứng từ ở nhóm ngoại lai.<br>
          Trung hạn: Nhân rộng quy trình bán hàng của "{top_reg['name']}" sang "{bot_reg['name']}".
        </td>
      </tr>
    </tbody>
  </table>

  <h2 class="sec-h2">III. Đề xuất Giải pháp và Kiến nghị Kinh doanh</h2>

  <table class="data-tbl">
    <tr>
      <td style="width: 50%;">
        <strong>3.1. Những mặt đạt được</strong>
        <ul class="plain-list">
          <li>Xác định rõ động lực tăng trưởng chủ lực là "{top_cat['name']}" ({top_cat['pct']}%) và khu vực "{top_reg['name']}" ({top_reg['pct']}%).</li>
          <li>Chất lượng dữ liệu đạt mức tin cậy cao ({quality_score}/100), tạo nền tảng chính xác cho quyết định điều hành.</li>
        </ul>
      </td>
      <td style="width: 50%;">
        <strong>3.2. Hạn chế &amp; Điểm nghẽn cần khắc phục</strong>
        <ul class="plain-list">
          <li>Độ tập trung Pareto ở mức {top2_pct}%: cần tránh phụ thuộc quá lớn vào một nhóm dẫn đầu.</li>
          <li>{bottleneck_txt}</li>
        </ul>
      </td>
    </tr>
  </table>

  <table class="data-tbl">
    <tr>
      <td style="width: 33.3%;">
        <strong>Nhân rộng (Scale Up)</strong><br>
        • {top_cat['name']} ({top_cat['value']:,.0f} VNĐ, {top_cat['pct']}%)<br>
        • Khu vực {top_reg['name']} ({top_reg['pct']}%)
      </td>
      <td style="width: 33.3%;">
        <strong>Tối ưu (Optimize)</strong><br>
        • {mid_cat['name']} ({mid_cat['pct']}%)<br>
        Có tiềm năng mở rộng quy mô nhưng cần tối ưu tỷ lệ chuyển đổi.
      </td>
      <td style="width: 33.4%;">
        <strong>Kiểm soát Rủi ro (Mitigate)</strong><br>
        • Nhóm thấp điểm: {bot_cat['name']} ({bot_cat['pct']}%)<br>
        • Rủi ro biến động tại {min_period} ({min_rev:,.0f} VNĐ).
      </td>
    </tr>
  </table>

  <h3 class="sec-h3">3.3. Giải pháp Nâng cao Hiệu quả Kinh doanh &amp; Chỉ tiêu KPI</h3>

  <h3 class="sec-h3">3.3.1. Phân tích Tập trung (Pareto) &amp; Đa dạng hóa Nguồn thu (Ưu tiên: Cao — Thời hạn: Tuần 1–2 &amp; Quý tới)</h3>
  <p><strong>a) Căn cứ dữ liệu &amp; Đánh giá nguyên nhân:</strong> Top 2 nhóm hiện chiếm {top2_pct}% tổng doanh thu (riêng "{top_cat['name']}" đạt {top_cat['value']:,.0f} VNĐ). Doanh nghiệp cần giảm rủi ro phụ thuộc vào nhóm dẫn đầu.</p>
  <p><strong>b) Lộ trình giải pháp &amp; Hành động triển khai:</strong> Giai đoạn 1 (Tuần 1–2): Bảo vệ vùng lõi &amp; chất lượng dịch vụ tại nhóm dẫn đầu. Giai đoạn 2 (Tháng 1–2): Phân bổ 15–20% ngân sách kích hoạt nhóm thứ cấp. Giai đoạn 3 (Tháng 3): Theo dõi tỷ trọng tuần và tái cân bằng.</p>
  <p><strong>c) Chỉ tiêu KPI đo lường (Hiện tại &rarr; Mục tiêu):</strong> Hiện tại: Top 2 chiếm {top2_pct}% &rarr; Mục tiêu: Đưa tỷ trọng Top 2 về dưới 65% và tăng trưởng ròng tổng doanh thu thêm +10–15%.</p>
  <p><strong>d) Bộ phận phụ trách &amp; Nguồn lực phối hợp:</strong> Ban Giám đốc &amp; Bộ phận Kinh doanh / Marketing.</p>

  <h3 class="sec-h3">3.3.2. Tối ưu Hiệu suất Vận hành &amp; Kiểm soát Định mức (Ưu tiên: Cao — Thời hạn: Tháng 1–2)</h3>
  <p><strong>a) Căn cứ dữ liệu &amp; Đánh giá nguyên nhân:</strong> Khoảng cách hiệu suất giữa khu vực dẫn đầu ("{top_reg['name']}") và khu vực cuối ("{bot_reg['name']}") lên tới {reg_ratio}x, cho thấy định mức vận hành giữa các đơn vị chưa đồng đều.</p>
  <p><strong>b) Lộ trình giải pháp &amp; Hành động triển khai:</strong> Giai đoạn 1: Kiểm toán chi tiết cấu phần chi phí tại nhóm hiệu quả thấp để cắt giảm 10–15% lãng phí. Giai đoạn 2: Đóng gói quy trình chuẩn (SOP) từ đơn vị dẫn đầu. Giai đoạn 3: Thiết lập ngưỡng cảnh báo trên Dashboard.</p>
  <p><strong>c) Chỉ tiêu KPI đo lường (Hiện tại &rarr; Mục tiêu):</strong> Hiện tại: Chênh lệch {reg_ratio}x giữa các khu vực &rarr; Mục tiêu: Thu hẹp chênh lệch xuống &lt; 2.5x và nâng hiệu suất nhóm cuối thêm +20%.</p>
  <p><strong>d) Bộ phận phụ trách &amp; Nguồn lực phối hợp:</strong> Bộ phận Tài chính, Kế toán &amp; Quản lý Vận hành.</p>

  <table class="sig-tbl">
    <tr>
      <td></td>
      <td>
        <div><strong>BAN GIÁM ĐỐC / LÃNH ĐẠO PHÊ DUYỆT</strong></div>
        <div><em>(Kiểm duyệt &amp; Ký duyệt ban hành)</em></div>
        <div style="height: 60px;"></div>
        <div><em>(Ký, ghi rõ họ tên &amp; đóng dấu)</em></div>
      </td>
    </tr>
  </table>
</div>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_filepath

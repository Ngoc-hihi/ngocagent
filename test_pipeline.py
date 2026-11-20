"""
test_pipeline.py - Kiểm thử tự động toàn diện toàn bộ chu trình xử lý AnoraAI
"""

import os
import pandas as pd
from app.sample_datasets import init_samples, SAMPLE_DIR
from app.data_cleaner import DataCleaner
from app.directive_engine import DirectiveEngine
from app.data_analyzer import DataAnalyzer
from app.docx_generator import create_diid_word_report, generate_chart_images
from app.html_report_generator import generate_standalone_html
from app.history_manager import HistoryManager
from app.assistant_ai import AssistantAI

def run_tests():
    print("[1/7] Testing Sample Datasets Generation...")
    init_samples()
    sample_path = os.path.join(SAMPLE_DIR, "retail_fb_sample.csv")
    assert os.path.exists(sample_path), "Sample retail CSV not found!"
    df = pd.read_csv(sample_path)
    print(f" -> Loaded sample dataset: {len(df)} rows, {len(df.columns)} columns.")

    print("[2/7] Testing Initial Inspection...")
    before_stats = DataCleaner.inspect_dataset(df)
    print(f" -> Initial issues: null={before_stats['null_cells']}, dups={before_stats['duplicate_rows']}, score={before_stats['quality_score']}%")
    assert before_stats['duplicate_rows'] >= 1, "Duplicate row not detected!"

    print("[3/7] Testing Data Cleaning...")
    clean_res = DataCleaner.auto_clean(df)
    cleaned_df = clean_res["df"]
    after_stats = clean_res["after_stats"]
    print(f" -> After clean: rows={len(cleaned_df)}, score={after_stats['quality_score']}%, tags_count={len(clean_res['cell_tags'])}")
    assert after_stats['quality_score'] > before_stats['quality_score'], "Quality score should improve!"

    print("[4/7] Testing Condition Filter & HITL Directive Engine (e.g. Bỏ Miền Bắc, thay thế giá trị)...")
    filtered_df, msg, tags = DataCleaner.filter_and_remove(cleaned_df, "Vung_Mien", "contains", "bắc", "remove")
    print(f" -> Filter result: {msg}")
    print(f" -> Remaining rows: {len(filtered_df)}")
    assert "bắc" not in filtered_df["Vung_Mien"].str.lower().values, "Miền Bắc should be removed!"

    # DirectiveEngine HITL test
    d_df, d_tags, d_msg = DirectiveEngine.execute(cleaned_df, "bỏ Miền Bắc", clean_res["cell_tags"])
    print(f" -> DirectiveEngine 'bỏ Miền Bắc': {d_msg} ({len(d_df)} rows left)")
    assert len(d_df) < len(cleaned_df), "Rows should be removed by directive!"

    print("[5/7] Testing 4-Level Analysis Engine...")
    analysis = DataAnalyzer.analyze(
        df=filtered_df,
        business_name="Công ty Cổ phần Anora Retail",
        business_model="B2C Bán lẻ & Chuỗi F&B",
        core_problem="Tối ưu hóa cơ cấu chi phí vận hành & Tăng biên lợi nhuận ròng"
    )
    assert "descriptive" in analysis
    assert "diagnostic" in analysis
    assert "predictive" in analysis
    assert "prescriptive" in analysis
    assert "correlation_vs_causation" in analysis["diagnostic"]
    print(f" -> Analysis complete: Revenue = {analysis['descriptive']['total_revenue']:,.0f} VNĐ, Margin = {analysis['descriptive']['profit_margin']}%")

    print("[6/7] Testing Docx & Standalone HTML Generation...")
    out_dir = os.path.join(os.path.dirname(__file__), "exports")
    os.makedirs(out_dir, exist_ok=True)
    docx_path = os.path.join(out_dir, "test_report.docx")
    html_path = os.path.join(out_dir, "test_report.html")
    charts_dir = os.path.join(out_dir, "temp_charts")

    chart_imgs = generate_chart_images(analysis, charts_dir)
    assert len(chart_imgs) == 4, "Should generate 4 chart images!"

    create_diid_word_report(analysis, {"before_stats": before_stats, "after_stats": after_stats}, docx_path)
    assert os.path.exists(docx_path), "Docx report file not created!"
    print(f" -> Generated Docx file ({os.path.getsize(docx_path)} bytes)")

    generate_standalone_html(analysis, {"before_stats": before_stats, "after_stats": after_stats}, chart_imgs, html_path)
    assert os.path.exists(html_path), "HTML report file not created!"
    print(f" -> Generated HTML file ({os.path.getsize(html_path)} bytes)")

    print("[7/7] Testing AI Virtual Assistant & History Manager...")
    answer = AssistantAI.answer_query("Phương pháp DIID là gì?", analysis)
    assert "DIID" in answer.upper(), "Assistant should answer DIID!"
    print(" -> AI Assistant response received successfully.")

    HistoryManager.save_feedback(5, "Hệ thống giao diện AnoraAI rất đẹp, đúng phong cách pastel vintage!")
    feedbacks = HistoryManager.get_feedbacks()
    assert len(feedbacks) >= 1, "Feedback not saved!"
    print(f" -> Feedbacks logged: {len(feedbacks)}")

    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! The pipeline is 100% operational.")

if __name__ == "__main__":
    run_tests()

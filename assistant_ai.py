"""
assistant_ai.py - Động cơ Trợ lý ảo AI AnoraAI kết nối Google Gemini API
- Khai thác trực tiếp sức mạnh mô hình Gemini thông qua API Key của người dùng
- Nhận thức ngữ cảnh dữ liệu kinh doanh 360 độ từ các Bước 1, 2, 3, 4
- Phong cách giao tiếp: Nhã nhặn, chuyên sâu về phân tích dữ liệu, phương pháp DIID và chiến lược doanh nghiệp
- Có cơ chế Fallback thông minh đảm bảo hệ thống luôn phản hồi 100% trong mọi tình huống
"""

import os
import json
import urllib.request
import re

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

CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-3-flash-preview"
]

class AssistantAI:
    @classmethod
    def answer_query(cls, user_message: str, context: dict = None, history: list = None, api_key: str = "") -> str:
        msg = (user_message or "").strip()
        if not msg:
            return "Chào bạn, mình là Anora! Bạn cần mình giải đáp câu hỏi gì hôm nay?"

        # 1. Gọi Google Gemini API với đầy đủ lịch sử hội thoại & ngữ cảnh dữ liệu
        eff_key = _get_gemini_api_key(api_key)
        if eff_key:
            gemini_ans = cls._call_gemini(msg, context, history or [], eff_key)
            if gemini_ans:
                return gemini_ans

        # 2. Cơ chế dự phòng thông minh (Rule-based Fallback) nếu mất mạng hoặc API bận
        return cls._rule_based_fallback(msg, context)

    @classmethod
    def _call_gemini(cls, user_message: str, context: dict = None, history: list = None, api_key: str = "") -> str:
        try:
            # Xây dựng ngữ cảnh dữ liệu hiện hành của người dùng (nếu có)
            context_summary = []
            if context:
                meta = context.get("business_meta", {})
                if meta.get("name"):
                    context_summary.append(f"- Doanh nghiệp: {meta.get('name')}")
                if meta.get("model"):
                    context_summary.append(f"- Mô hình kinh doanh: {meta.get('model')}")
                if meta.get("core_problem"):
                    context_summary.append(f"- Bài toán trọng tâm: {meta.get('core_problem')}")

                if context.get("columns"):
                    context_summary.append(f"- Các cột dữ liệu hiện có ({context.get('total_rows', 0)} dòng): {', '.join(context.get('columns', []))}")

                desc = context.get("descriptive", {})
                if desc.get("total_revenue"):
                    context_summary.append(f"- Tổng doanh thu: {desc.get('total_revenue'):,.0f} VNĐ ({desc.get('total_records', 0)} bản ghi)")
                if desc.get("has_cost_data"):
                    context_summary.append(f"- Tổng chi phí: {desc.get('total_cost'):,.0f} VNĐ")
                    context_summary.append(f"- Lợi nhuận ròng: {desc.get('net_profit'):,.0f} VNĐ (Biên lãi: {desc.get('profit_margin')}%)")

                b_cat = context.get("breakdown_by_cat", [])
                if b_cat:
                    cat_items = [f"{item['name']} ({item['pct']}%)" for item in b_cat[:5]]
                    context_summary.append(f"- Cơ cấu phân khúc/kênh: {', '.join(cat_items)}")

                charts = context.get("charts", {})
                region_info = charts.get("chart_region_performance", {})
                if region_info.get("labels"):
                    context_summary.append(f"- Đơn vị/Khu vực: {', '.join(region_info['labels'][:5])}")

            ctx_text = "\n".join(context_summary) if context_summary else "Người dùng chưa nạp tệp dữ liệu nào."

            system_instruction = (
                "Bạn là AnoraAI — Trợ lý ảo AI toàn năng, thông minh, lịch thiệp và am hiểu sâu rộng mọi lĩnh vực "
                "(kinh doanh, tài chính, marketing, phân tích dữ liệu, công nghệ, kiến thức tổng hợp...).\n"
                "NGUYÊN TẮC TRẢ LỜI:\n"
                "1. Trả lời ĐÚNG TRỌNG TÂM, ĐẦY ĐỦ và TRỰC DIỆN mọi câu hỏi mà người dùng đặt ra (kể cả câu hỏi ngoài lề, kiến thức chung, tính toán, hay hỏi tiếp ý trước đó).\n"
                "2. Không tự ý ép buộc mọi câu trả lời thành báo cáo DIID trừ khi người dùng hỏi về DIID hoặc yêu cầu phân tích theo DIID.\n"
                "3. Nếu người dùng hỏi về dữ liệu doanh nghiệp đang nạp, tuyệt đối bám sát số liệu thực tế dưới đây (không bịa đặt số liệu):\n"
                f"{ctx_text}\n"
                "4. Trình bày tiếng Việt rõ ràng, mạch lạc, súc tích nhưng đầy đủ ý (không bỏ lửng câu)."
            )

            contents = []
            for turn in (history or [])[-8:]:
                role = "model" if turn.get("role") == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": turn.get("text", "")}]})
            contents.append({"role": "user", "parts": [{"text": user_message}]})

            payload = {
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.5,
                    "maxOutputTokens": 4096
                }
            }
            body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

            # Thử qua các mô hình Gemini khả dụng
            for model_name in CANDIDATE_MODELS:
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
                    with urllib.request.urlopen(req, timeout=20) as response:
                        res_json = json.loads(response.read().decode("utf-8"))
                        candidates = res_json.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                ans_text = parts[0].get("text", "").strip()
                                if ans_text:
                                    return ans_text
                except Exception:
                    continue
        except Exception:
            pass

        return None

    @classmethod
    def _rule_based_fallback(cls, user_message: str, context: dict = None) -> str:
        msg = user_message.strip().lower()

        has_data = context and "business_meta" in context
        biz_name = context["business_meta"].get("name", "Doanh nghiệp của bạn") if has_data else "doanh nghiệp"
        model_name = context["business_meta"].get("model", "") if has_data else ""
        problem_name = context["business_meta"].get("core_problem", "") if has_data else ""

        # 1. Câu hỏi về DIID
        if any(k in msg for k in ["diid", "phương pháp diid", "khung diid", "báo cáo diid"]):
            return (
                "**Mô hình DIID (Data - Information - Insight - Decision)** là chuẩn mực báo cáo điều hành chiến lược mà AnoraAI áp dụng:\n\n"
                "• **D — DATA (Dữ liệu nền tảng):** Thu thập dữ liệu thô, loại bỏ nhiễu và làm sạch qua cổng HITL để đảm bảo độ tin cậy tuyệt đối.\n"
                "• **I — INFORMATION (Thông tin tổng hợp):** Chuyển đổi dữ liệu sạch thành các chỉ số KPI, tỷ suất lợi nhuận và bảng phân loại Tốt / Cảnh báo.\n"
                "• **I — INSIGHT (Phát hiện cốt lõi):** Đào sâu lý do cốt lõi bằng phân rã đa chiều, kiểm định bất thường, tách bạch rõ tương quan vs nhân quả (Correlation vs Causation), và dự phóng xu hướng tuyến tính thực tế.\n"
                "• **D — DECISION (Quyết định hành động):** Đưa ra khuyến nghị phân bổ nguồn lực và lộ trình thực thi rõ ràng 30 ngày & 90 ngày cho ban giám đốc."
            )

        # 2. Câu hỏi về Tương quan vs Nhân quả
        if any(k in msg for k in ["tương quan", "nhân quả", "correlation", "causation"]):
            return (
                "**Tách bạch Tương quan (Correlation) vs Nhân quả (Causation)** là nguyên tắc tối quan trọng trong khoa học dữ liệu:\n\n"
                "• **Tương quan:** Hai chỉ số di chuyển cùng chiều (hoặc ngược chiều) với nhau. *Ví dụ:* Doanh số bán kem và số vụ cháy nắng cùng tăng vào mùa hè.\n"
                "• **Nhân quả:** Biến số A là nguyên nhân trực tiếp làm thay đổi biến số B.\n\n"
                "Trong phân tích kinh doanh, nếu thấy chi phí marketing và doanh thu tương quan cao, ta không thể vội kết luận rằng cứ tăng ngân sách marketing là lợi nhuận sẽ tăng, bởi nếu sản phẩm chưa phù hợp hoặc chiết khấu quá sâu, việc tăng marketing sẽ làm thu hẹp biên lợi nhuận ròng."
            )

        # 3. Câu hỏi về thao tác làm sạch HITL
        if any(k in msg for k in ["làm sạch", "hitl", "lọc", "xóa dòng", "bỏ miền bắc", "sửa ô"]):
            return (
                "**Hướng dẫn thao tác tại Bước 2 (Làm sạch & Cổng kiểm duyệt HITL):**\n\n"
                "1. **Làm sạch tự động:** Bấm nút *'Thực hiện làm sạch'* để hệ thống tự khử trùng lặp, chuẩn hóa định dạng và xử lý dữ liệu trống.\n"
                "2. **Bộ lọc điều kiện (ví dụ: Bỏ Miền Bắc):** Chọn cột `Khu vực`, điều kiện `Chứa ký tự`, giá trị `Bắc`, rồi bấm *'Xóa dòng thỏa điều kiện'*.\n"
                "3. **Sửa trực tiếp từng ô (Inline Edit):** Nhấp đúp chuột vào bất kỳ ô nào trên bảng dữ liệu để điều chỉnh trực tiếp.\n"
                "4. **Cổng kiểm duyệt:** Bấm *'Phê duyệt dữ liệu hợp lệ'* khi đã hoàn tất để chuyển sang phân tích Dashboard Bước 4."
            )

        # 4. Câu hỏi về bối cảnh doanh nghiệp hiện tại
        if has_data and any(k in msg for k in ["doanh nghiệp", "kết quả", "lợi nhuận", "chi phí", "tôi", "hiện tại", "kênh", "doanh thu"]):
            desc = context.get("descriptive", {})
            rev = desc.get("total_revenue", 0)
            b_cat = context.get("breakdown_by_cat", [])
            cat_desc = f", dẫn đầu bởi nhóm '{b_cat[0]['name']}' ({b_cat[0]['pct']}%)" if b_cat else ""
            return (
                f"**Báo cáo nhanh cho {biz_name} ({model_name}):**\n\n"
                f"• **Bài toán trọng tâm:** {problem_name}\n"
                f"• **Tổng doanh thu thực tế:** {rev:,.0f} VNĐ{cat_desc}\n"
                f"• **Quy mô dữ liệu:** {desc.get('total_records', 0)} bản ghi hợp lệ\n\n"
                f"👉 **Khuyến nghị của Anora:** Bạn có thể qua **Trang 4 (Dashboard)** để xem chi tiết biểu đồ hoặc qua **Trang 5** để xuất báo cáo Word chuẩn DIID nhé!"
            )

        # Trả lời tổng quát
        return (
            f"Anora luôn sẵn sàng đồng hành cùng bạn! Bạn có thể đặt bất kỳ câu hỏi nào cho mình về:\n"
            f"1. Phân tích chuyên sâu về các kênh bán và thị trường của bạn.\n"
            f"2. Ý nghĩa các chỉ số tài chính và dự báo xu hướng trong Dashboard.\n"
            f"3. Bản chất của việc tách biệt tương quan và nhân quả.\n"
            f"4. Phương pháp luận DIID và cách xuất báo cáo điều hành."
        )

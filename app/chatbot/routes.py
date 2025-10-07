from flask import request, jsonify, session, current_app
from . import chatbot_bp
import google.generativeai as genai
from datetime import datetime
import json
import os

# Biến global cho model
model = None


def init_gemini():
    """Khởi tạo Gemini API"""
    global model
    api_key = current_app.config.get('GEMINI_API_KEY')
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # FIX: Đổi tên model sang phiên bản ổn định
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            current_app.logger.info("Gemini API initialized successfully")
        except Exception as e:
            current_app.logger.error(f"Failed to initialize Gemini API: {str(e)}")
            model = None
    else:
        current_app.logger.warning("GEMINI_API_KEY not found in config")
        model = None


def load_company_info():
    """Đọc thông tin công ty từ file JSON"""
    json_path = os.path.join(current_app.root_path, 'chatbot', 'company_info.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        current_app.logger.error(f"company_info.json not found at {json_path}")
        return {}
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Invalid JSON in company_info.json: {str(e)}")
        return {}


def create_system_prompt(company_info):
    """Tạo system prompt để Gemini nhập vai nhân viên tư vấn"""
    if not company_info:
        return "Bạn là trợ lý ảo thân thiện của Hoangvn, chuyên tư vấn về các sản phẩm và dịch vụ."

    services_text = "\n".join([
        f"- {s['name']}: {s['price']} - {s['description']}"
        for s in company_info.get('services', [])
    ])

    strengths_text = "\n".join([
        f"- {s}" for s in company_info.get('strengths', [])
    ])

    prompt = f"""
Bạn là nhân viên tư vấn khách hàng chuyên nghiệp của công ty {company_info.get('company_name', 'Hoangvn')}.

**THÔNG TIN CÔNG TY:**
- Tên công ty: {company_info.get('company_name', 'Hoangvn')}
- Lĩnh vực: {company_info.get('business', 'Kinh doanh đa ngành')}
- Điện thoại: {company_info.get('contact', {}).get('phone', '098.422.6602')}
- Email: {company_info.get('contact', {}).get('email', 'info@hoang.vn')}
- Địa chỉ: {company_info.get('contact', {}).get('address', 'CN 1: 982/l98/a1 Tân Bình, Tân Phú, Nhà Bè, TP.HCM')}
- Giờ làm việc: {company_info.get('working_hours', '8:00 - 17:30 (Thứ 2 - Thứ 7)')}

**DỊCH VỤ/SẢN PHẨM CUNG CẤP:**
{services_text if services_text else "- Vui lòng liên hệ để biết thêm chi tiết"}

**ƯU ĐIỂM:**
{strengths_text if strengths_text else "- Đội ngũ chuyên nghiệp, tận tâm\n- Giá cả cạnh tranh\n- Chất lượng đảm bảo"}

**VAI TRÒ CỦA BẠN:**
1. Tư vấn chuyên nghiệp, thân thiện, lịch sự
2. Trả lời câu hỏi về sản phẩm/dịch vụ, giá cả, quy trình làm việc
3. Nếu khách hỏi ngoài phạm vi (ví dụ: thời tiết, chính trị), hãy lịch sự từ chối và gợi ý quay lại chủ đề sản phẩm/dịch vụ
4. Luôn kết thúc bằng câu hỏi mở để khách hàng tiếp tục trao đổi
5. Nếu khách hàng muốn đặt hàng/dịch vụ, hãy hướng dẫn liên hệ qua:
   - Hotline: {company_info.get('contact', {}).get('phone', '098.422.6602')}
   - Zalo: {company_info.get('contact', {}).get('zalo', '098.422.6602')}
   - Email: {company_info.get('contact', {}).get('email', 'info@hoang.vn')}

**CÁCH TRẢ LỜI:**
- Ngắn gọn, súc tích (2-4 câu)
- Dùng emoji phù hợp (😊, 👍, 🌟, ✅) nhưng không quá nhiều
- Gọi khách là "anh/chị" hoặc "quý khách"
- Không viết dài dòng như văn bản chính thức
- Nếu không biết thông tin chính xác, hãy thành thật nói và đề nghị khách liên hệ trực tiếp

**VÍ DỤ TRẢ LỜI:**
Khách: "Các bạn có những sản phẩm gì?"
Bạn: "Dạ, {company_info.get('company_name', 'Hoangvn')} chúng tôi chuyên cung cấp [liệt kê 2-3 sản phẩm chính] ạ. Tất cả sản phẩm đều được kiểm định chất lượng và có chế độ bảo hành tốt 😊 Anh/chị quan tâm đến sản phẩm nào ạ?"

Khách: "Giá cả thế nào?"
Bạn: "Dạ, giá của chúng tôi rất cạnh tranh và tùy thuộc vào sản phẩm/dịch vụ cụ thể ạ. Để được tư vấn báo giá chính xác nhất, anh/chị vui lòng liên hệ hotline {company_info.get('contact', {}).get('phone', '098.422.6602')} hoặc chat Zalo để được hỗ trợ nhanh chóng nhé 📞"

Bây giờ hãy bắt đầu tư vấn!
"""
    return prompt


@chatbot_bp.route('/send', methods=['POST'])
def send_message():
    """API endpoint xử lý tin nhắn từ chatbot"""
    global model

    # Kiểm tra chatbot có được bật không
    if not current_app.config.get('CHATBOT_ENABLED', True):
        return jsonify({
            'response': 'Chatbot hiện đang bảo trì. Vui lòng liên hệ hotline: 098.422.6602 😊'
        }), 503

    # Khởi tạo model nếu chưa có
    if model is None:
        init_gemini()

    if model is None:
        return jsonify({
            'response': 'Xin lỗi, chatbot hiện không khả dụng. Vui lòng liên hệ trực tiếp qua hotline: 098.422.6602 hoặc Zalo: 098.422.6602 😊'
        }), 500

    try:
        # Lấy tin nhắn từ frontend
        data = request.json
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({'error': 'Tin nhắn không được để trống'}), 400

        # Giới hạn độ dài tin nhắn
        if len(user_message) > 500:
            return jsonify({'error': 'Tin nhắn quá dài. Vui lòng nhập tối đa 500 ký tự'}), 400

        # Kiểm tra giới hạn request
        if 'chatbot_request_count' not in session:
            session['chatbot_request_count'] = 0
            session['chatbot_request_start_time'] = datetime.now().timestamp()

        # Reset counter nếu đã qua 1 giờ
        current_time = datetime.now().timestamp()
        request_limit = current_app.config.get('CHATBOT_REQUEST_LIMIT', 30)
        request_window = current_app.config.get('CHATBOT_REQUEST_WINDOW', 3600)

        if current_time - session['chatbot_request_start_time'] > request_window:
            session['chatbot_request_count'] = 0
            session['chatbot_request_start_time'] = current_time

        # Kiểm tra vượt giới hạn
        if session['chatbot_request_count'] >= request_limit:
            return jsonify({
                'response': f'Xin lỗi, bạn đã vượt quá giới hạn {request_limit} tin nhắn/giờ. Vui lòng thử lại sau hoặc liên hệ trực tiếp:\n📞 Hotline: 098.422.6602\n💬 Zalo: 098.422.6602\n📧 Email: info@hoang.vn'
            })

        # Tăng counter
        session['chatbot_request_count'] += 1

        # Lưu lịch sử chat
        if 'chatbot_history' not in session:
            session['chatbot_history'] = []

        # Tạo context từ lịch sử (lấy 5 tin nhắn gần nhất)
        history_context = "\n".join([
            f"{'Khách hàng' if msg['role'] == 'user' else 'Bạn'}: {msg['content']}"
            for msg in session['chatbot_history'][-5:]
        ])

        # Load company info và tạo prompt
        company_info = load_company_info()
        system_prompt = create_system_prompt(company_info)

        full_prompt = f"{system_prompt}\n\n**LỊCH SỬ HỘI THOẠI:**\n{history_context}\n\n**TIN NHẮN MỚI TỪ KHÁCH HÀNG:**\n{user_message}\n\n**TRẢ LỜI:**"

        # Gọi Gemini API với cấu hình an toàn hơn
        try:
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                    top_p=0.95,
                    top_k=40
                ),
                safety_settings=[
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE"
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE"
                    }
                ]
            )

            # Kiểm tra response có text không
            if hasattr(response, 'text') and response.text:
                bot_reply = response.text
            else:
                current_app.logger.warning(f"Empty response from Gemini API: {response}")
                bot_reply = "Xin lỗi, tôi không thể trả lời câu hỏi này. Vui lòng liên hệ:\n📞 Hotline: 098.422.6602\n💬 Zalo: 098.422.6602 😊"

        except Exception as api_error:
            current_app.logger.error(f"Gemini API error: {str(api_error)}")
            return jsonify({
                'response': 'Xin lỗi, hệ thống đang quá tải. Vui lòng thử lại sau hoặc liên hệ:\n📞 Hotline: 098.422.6602\n💬 Zalo: 098.422.6602'
            }), 500

        # Lưu vào lịch sử
        session['chatbot_history'].append({'role': 'user', 'content': user_message})
        session['chatbot_history'].append({'role': 'assistant', 'content': bot_reply})

        # Giới hạn lịch sử (chỉ giữ 20 tin nhắn gần nhất)
        if len(session['chatbot_history']) > 20:
            session['chatbot_history'] = session['chatbot_history'][-20:]

        # Lưu session
        session.modified = True

        return jsonify({
            'response': bot_reply,
            'remaining_requests': request_limit - session['chatbot_request_count']
        })

    except Exception as e:
        current_app.logger.error(f"Chatbot error: {str(e)}", exc_info=True)
        return jsonify({
            'response': 'Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại sau hoặc liên hệ:\n📞 Hotline: 098.422.6602\n💬 Zalo: 098.422.6602 😊'
        }), 500


@chatbot_bp.route('/reset', methods=['POST'])
def reset_chat():
    """Reset lịch sử chat"""
    try:
        session.pop('chatbot_history', None)
        session.pop('chatbot_request_count', None)
        session.pop('chatbot_request_start_time', None)
        return jsonify({
            'status': 'success',
            'message': 'Đã làm mới hội thoại thành công!'
        })
    except Exception as e:
        current_app.logger.error(f"Reset chat error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Không thể làm mới hội thoại'
        }), 500
"""
AI Grader Service
Hỗ trợ đa mô hình: Gemini 1.5, Claude 3.5 và GROQ (LLaMA 3) để chấm điểm bài nộp lập trình nhúng.
"""
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger(__name__)


def grade_submission_with_ai(mission_description: str, mission_name: str, files: list) -> dict:
    """
    Dùng Claude để chấm điểm bài nộp.

    Args:
        mission_description: Đề bài (markdown text)
        mission_name: Tên bài thi
        files: List of dicts {name, path, content, size}

    Returns:
        dict: {success, score, feedback, criteria} hoặc {success:False, error}
    """
    if not files:
        return {
            'success': True,
            'score': 0.0,
            'feedback': 'Sinh viên không nộp file nào.',
            'criteria': [
                {'name': 'Đúng yêu cầu đề bài', 'score': 0},
                {'name': 'Chất lượng code', 'score': 0},
                {'name': 'Logic và thuật toán', 'score': 0},
                {'name': 'Xử lý lỗi', 'score': 0},
                {'name': 'Sử dụng thư viện', 'score': 0},
            ]
        }

    # Build file content block (giới hạn 10 file, mỗi file 3000 chars)
    files_text = ""
    for i, f in enumerate(files[:10]):
        name = f.get('name', f'file_{i}')
        content = f.get('content', '')[:3000]
        path = f.get('path', '')
        files_text += f"\n### [{i + 1}] {name}  (đường dẫn: {path})\n```\n{content}\n```\n"

    if not files_text.strip():
        files_text = "(Các file đều trống hoặc không đọc được)"

    prompt = f"""Bạn là một Robot Giám khảo Kỹ thuật sở hữu tư duy của trình biên dịch C++ và một chuyên gia hệ thống nhúng "Độc tài" khắt khe nhất.
Nhiệm vụ: Chấm điểm bài lập trình ESP32/Arduino một cách TUYỆT ĐỐI CHÍNH XÁC. Bạn KHÔNG ĐƯỢC PHÉP nương tay cho bất kỳ sai sót nào.

## TÊN BÀI THI: {mission_name}

## ĐỀ BÀI YÊU CẦU:
{mission_description or '(Không có mô tả)'}

## DANH SÁCH FILE BÀI LÀM:
{files_text}

## QUY TẮC CHẤM ĐIỂM "BÀN TAY SẮT" 2.0 (MANDATORY RULES):
1. **Kiểm tra TÍNH TOÀN VẸN và KHỞI TẠO (Functionality & Initialization)**: 
   - Phải có đủ các hàm Task được yêu cầu. ĐẶC BIỆT: Phải có lệnh khởi tạo Task (`xTaskCreate`) và Queue/Semaphore (`xQueueCreate`, `xSemaphoreCreateBinary`) trong `setup()`.
   - Nếu viết hàm Task nhưng QUÊN KHỞI TẠO (`xTaskCreate`) để nó chạy -> ĐIỂM TỔNG KHÔNG ĐƯỢC VƯỢT QUÁ 4.0 (Vì logic không thể thực thi).
   - Thiếu bất kỳ component nào theo yêu cầu -> Trừ 2.0 điểm/yêu cầu.
2. **Kiểm tra Cú pháp & Biên dịch (Compilation Error)**: 
   - Bạn phải phát hiện các lỗi cú pháp (thiếu ngoặc `}}`, thiếu dấu `;`, sai tên hàm, cắt cụt code).
   - Nếu code bị cắt cụt hoặc lỗi cú pháp nặng -> ĐIỂM TỔNG KHÔNG ĐƯỢC VƯỢT QUÁ 3.0. (Ghi rõ lỗi ở Feedback).
3. **Kiểm tra hàm Hệ thống (BẮT BUỘC)**: Phải có đủ `void setup()` và `void loop()`. Thiếu hoặc sai tên -> Tối đa 2.0 điểm.
4. **Kiểm tra Logic Phần cứng & Chân IO**: Sai chân GPIO hoặc sai logic cơ bản -> Trừ 2.0 điểm.

## THANG ĐIỂM KHẮC NGHIỆT (DÀNH CHO CHUYÊN GIA):
- 0.0 - 4.0: Code có LỖI BIÊN DỊCH, thiếu khởi tạo Task/Queue, hoặc sai cấu trúc trầm trọng.
- 4.1 - 6.0: Biên dịch được nhưng logic rỗng tuếch hoặc thiếu các tính năng chính.
- 6.1 - 8.0: Đủ chức năng nhưng code cẩu thả, dùng delay() thay vì vTaskDelay().
- 8.1 - 10.0: Chỉ dành cho bài nộp hoàn hảo, code tối ưu, sạch sẽ.

TRẢ VỀ DUY NHẤT MỘT KHỐI JSON, KHÔNG CÓ VĂN BẢN THỪA:
{{
  "score": <float 0.0-10.0>,
  "feedback": "<Nhận xét kỹ thuật KHẮC NGHIỆT. Chỉ rõ lỗi sai ở đâu, tại sao bị trừ điểm nặng.>",
  "criteria": [
    {{"name": "Khởi tạo và Toàn vẹn chức năng", "score": <0-10>}},
    {{"name": "Cú pháp và Khả năng biên dịch", "score": <0-10>}},
    {{"name": "Logic và Thuật toán phần cứng", "score": <0-10>}},
    {{"name": "Xử lý lỗi và Độ ổn định", "score": <0-10>}},
    {{"name": "Tối ưu hóa và Phong cách code", "score": <0-10>}}
  ]
}}"""

    gemini_key = os.getenv('GEMINI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    groq_key = os.getenv('GROQ_API_KEY')
    
    if not gemini_key and not anthropic_key and not groq_key:
        logger.error("Cả GEMINI, ANTHROPIC và GROQ API KEY đều không được thiết lập")
        return {'success': False, 'error': 'Chưa cấu hình API key chấm điểm AI. Liên hệ quản trị viên.'}

    try:
        raw = ""
        success_api = False
        last_error = ""

        # Cố gắng sử dụng Gemini trước
        if gemini_key:
            try:
                from google import genai
                client = genai.Client(api_key=gemini_key)
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=prompt,
                )
                raw = response.text.strip()
                success_api = True
            except ImportError:
                logger.warning("Thư viện google-genai chưa cài đặt. Fallback sang Anthropic...")
                last_error = "Thiếu thư viện google-genai"
            except Exception as e:
                logger.warning(f"Lỗi Gemini: {e}. Fallback sang Anthropic...")
                last_error = str(e)
                
        # Nếu Gemini thất bại, thử sử dụng Anthropic Claude
        if not success_api and anthropic_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=anthropic_key)
                response = client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    max_tokens=1500,
                    system="Chỉ trả về JSON thuần túy, tuyệt đối không có văn bản giải thích. Không bọc trong ```json.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                raw = response.content[0].text.strip()
                success_api = True
            except ImportError:
                logger.error("Thư viện anthropic chưa cài đặt.")
                last_error = "Thiếu thư viện anthropic"
            except Exception as e:
                logger.error(f"Lỗi Anthropic: {e}")
                last_error = str(e)

        # Nếu cả 2 thất bại, chuyển sang model siêu tốc LLaMA 3 (thông qua API Groq miễn phí)
        if not success_api and groq_key:
            try:
                import urllib.request
                import urllib.error
                
                headers = {
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                data = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "Chỉ trả về JSON thuần túy, tuyệt đối không có văn bản giải thích. Không bọc trong ```json."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                }
                
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    data=json.dumps(data).encode('utf-8')
                )
                try:
                    with urllib.request.urlopen(req, timeout=30) as response:
                        if response.status == 200:
                            resp_json = json.loads(response.read().decode('utf-8'))
                            raw = resp_json['choices'][0]['message']['content'].strip()
                            success_api = True
                        else:
                            last_error = f"Groq Error: {response.status}"
                            logger.error(last_error)
                except urllib.error.HTTPError as e:
                    last_error = f"Groq HTTP Error {e.code}: {e.read().decode('utf-8', errors='ignore')}"
                    logger.error(last_error)
            except Exception as e:
                logger.error(f"Lỗi Groq API: {e}")
                last_error = str(e)

        if not success_api:
            return {'success': False, 'error': f'Không thể gọi AI API. Lỗi gần nhất: {last_error}'}
            
        raw_str = str(raw)
        logger.info(f"Phản hồi thô từ AI (200 ký tự đầu): {raw_str[:200]}")

        # Loại bỏ các dấu rào markdown code nếu có
        if raw.startswith("```"):
            parts = raw.split("```")
            if len(parts) >= 3:
                raw = parts[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)

        # Kiểm tra và giới hạn điểm số trong khoảng 0-10
        criteria = parsed.get('criteria', [])
        for c in criteria:
            c['score'] = max(0.0, min(10.0, float(c.get('score', 0))))

        # Tính toán lại tổng điểm dựa trên trung bình cộng các tiêu chí
        if criteria:
            total = sum(float(c.get('score', 0)) for c in criteria) / len(criteria)
            score = round(total, 1)
        else:
            score = max(0.0, min(10.0, float(parsed.get('score', 0))))

        result = {
            'success': True,
            'score': score,
            'feedback': parsed.get('feedback', ''),
            'criteria': criteria
        }

        # --- THU THẬP DỮ LIỆU ĐỂ TRAINING TRONG TƯƠNG LAI ---
        # Lưu lại tương tác này vào file JSONL theo định dạng Instruction-Input-Output (Alpaca style)
        try:
            dataset_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            os.makedirs(dataset_dir, exist_ok=True)
            dataset_path = os.path.join(dataset_dir, 'ai_training_dataset.jsonl')
            
            # Chỉ lấy nội dung code sạch của sinh viên
            student_code = files_text.strip()
            
            training_record = {
                'instruction': f"Chấm điểm bài thi '{mission_name}'. Yêu cầu đề bài: {mission_description}",
                'input': student_code,
                'output': json.dumps({
                    'score': result.get('score', 0),
                    'feedback': result.get('feedback', ''),
                    'criteria': result.get('criteria', [])
                }, ensure_ascii=False),
                'final_score': result.get('score', 0), # Trường mới giúp đại ca dễ lọc data để train
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'mission_name': mission_name,
                    'model_used': 'gemini' if gemini_key and success_api else ('anthropic' if success_api else 'groq')
                }
            }
            
            with open(dataset_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(training_record, ensure_ascii=False) + '\n')
                
            logger.info(f"Đã lưu bản ghi training chuẩn hóa (Alpaca style) vào {dataset_path}")
        except Exception as e:
            logger.error(f"Không thể lưu dữ liệu training: {e}")
        # -------------------------------------------

        return result
 
    except json.JSONDecodeError as e:
        logger.error(f"Lỗi phân tách JSON từ AI: {e}. Raw: {raw[:300] if 'raw' in dir() else 'N/A'}")
        return {'success': False, 'error': 'AI trả về định dạng không hợp lệ. Vui lòng thử lại.'}
    except ImportError:
        logger.error("Gói google-genai chưa được cài đặt")
        return {'success': False, 'error': 'Thư viện AI chưa được cài đặt. Chạy: pip install google-genai'}
    except Exception as e:
        logger.error(f"Lỗi không xác định từ AI Grader: {e}")
        return {'success': False, 'error': f'Lỗi chấm điểm: {str(e)}'}

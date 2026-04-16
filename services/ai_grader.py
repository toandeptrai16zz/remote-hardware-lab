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

    prompt = f"""Bạn là một Robot Giám khảo Kỹ thuật sở hữu tư duy của trình biên dịch C++ và một chuyên gia hệ thống nhúng khắt khe.
Nhiệm vụ: Chấm điểm bài lập trình ESP32/Arduino một cách TUYỆT ĐỐI CHÍNH XÁC theo tiêu chuẩn kỹ thuật công nghiệp.

## TÊN BÀI THI: {mission_name}

## ĐỀ BÀI YÊU CẦU:
{mission_description or '(Không có mô tả)'}

## DANH SÁCH FILE BÀI LÀM:
{files_text}

## QUY TẮC CHẤM ĐIỂM "BÀN TAY SẮT" (MANDATORY RULES):
1. **Kiểm tra hàm Hệ thống (BẮT BUỘC)**: Một sketch Arduino HỢP LỆ phải có đúng tên hai hàm là `void setup()` và `void loop()`. Bất kỳ biến thể nào (vd: `void setup1()`, `void lopp()`, `void ldfp()`) đều bị coi là LỖI LOGIC NẶNG vì chương trình sẽ không thể chạy.
2. **Kiểm tra Cú pháp & Tên hàm (Syntax Strictness)**: Bạn đóng vai trình biên dịch. Nếu phát hiện sai chính tả hàm API (vd: `digitallWrite` thay vì `digitalWrite`) hoặc thiếu dấu chấm phẩy (;):
   - ĐIỂM TỔNG KHÔNG ĐƯỢC VƯỢT QUÁ 4.0.
   - Đây là quy định cứng, không ngoại lệ cho bất kỳ lý do gì.
3. **Kiểm tra Logic Phần cứng**: 
   - Sinh viên phải sử dụng đúng các chân IO đã quy định trong đề bài. Nếu đề yêu cầu chân #2 mà code khai báo chân #5, trừ 2 điểm tiêu chí Logic.
   - Kiểm tra việc sử dụng các hàm đặc thù (vd: `ledcSetup` cho ESP32, `attachInterrupt` cho ngắt).
4. **Không "Khuyến khích" mù quáng**: Chỉ cho điểm cao khi code thực sự tối ưu. Feedback cần đi thẳng vào vấn đề kỹ thuật, ngắn gọn, súc tích.

## THANG ĐIỂM:
- 0.0 - 4.0: Code có LỖI BIÊN DỊCH, sai tên hàm bắt buộc (`setup`/`loop`), hoặc sai cú pháp cơ bản.
- 4.1 - 6.0: Code đúng cú pháp nhưng chưa hoàn thành đủ các yêu cầu chính của đề bài.
- 6.1 - 8.0: Hoàn thành các tính năng chính, logic đúng nhưng code chưa tối ưu hoặc thiếu xử lý các trường hợp biên (edge cases).
- 8.1 - 9.0: Hoàn thành tốt, code đẹp, xử lý lỗi tốt, có sử dụng kỹ thuật nâng cao (Debounce, Non-blocking delay).
- 9.1 - 10.0: Xuất sắc, tối ưu hóa bộ nhớ/tốc độ, bình luận chuyên nghiệp và giải quyết triệt để bài toán.

TRẢ VỀ DUY NHẤT MỘT KHỐI JSON, KHÔNG CÓ VĂN BẢN THỪA:
{{
  "score": <float 0.0-10.0>,
  "feedback": "<Nhận xét kỹ thuật ngắn gọn, súc tích bằng tiếng Việt. Chỉ ra đúng lỗi sai dòng nào, tại sao sai.>",
  "criteria": [
    {{"name": "Tính hợp lệ của mã nguồn (Setup/Loop/Syntax)", "score": <0-10>}},
    {{"name": "Đáp ứng yêu cầu chức năng", "score": <0-10>}},
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
            
        logger.info(f"AI grader raw response (first 200): {raw[:200]}")

        # Strip markdown code fences if present
        if raw.startswith("```"):
            parts = raw.split("```")
            if len(parts) >= 3:
                raw = parts[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)

        # Validate and clamp
        criteria = parsed.get('criteria', [])
        for c in criteria:
            c['score'] = max(0, min(10, float(c.get('score', 0))))

        # Recalculate total as average of criteria scores
        if criteria:
            total = sum(c['score'] for c in criteria) / len(criteria)
            score = round(total, 1)
        else:
            score = max(0.0, min(10.0, float(parsed.get('score', 0))))

        result = {
            'success': True,
            'score': score,
            'feedback': parsed.get('feedback', ''),
            'criteria': criteria
        }
        
        # --- DATA COLLECTION FOR FUTURE TRAINING ---
        # Save this interaction to a JSONL file
        try:
            dataset_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            os.makedirs(dataset_dir, exist_ok=True)
            dataset_path = os.path.join(dataset_dir, 'ai_training_dataset.jsonl')
            
            training_record = {
                'timestamp': datetime.now().isoformat(),
                'mission_name': mission_name,
                'prompt': prompt,
                'raw_response': raw,
                'parsed_result': result
            }
            
            with open(dataset_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(training_record, ensure_ascii=False) + '\n')
                
            logger.info(f"Saved training data record to {dataset_path}")
        except Exception as e:
            logger.error(f"Failed to save training data: {e}")
        # -------------------------------------------

        return result

    except json.JSONDecodeError as e:
        logger.error(f"AI grader JSON parse error: {e}. Raw: {raw[:300] if 'raw' in dir() else 'N/A'}")
        return {'success': False, 'error': 'AI trả về định dạng không hợp lệ. Vui lòng thử lại.'}
    except ImportError:
        logger.error("google-genai package chưa được cài đặt")
        return {'success': False, 'error': 'Thư viện AI chưa được cài đặt. Chạy: pip install google-genai'}
    except Exception as e:
        logger.error(f"AI grader unexpected error: {e}")
        return {'success': False, 'error': f'Lỗi chấm điểm: {str(e)}'}

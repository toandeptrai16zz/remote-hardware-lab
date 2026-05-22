# Kiem Thu Fallback AI

Ngay chay test code: 2026-05-22  
Code chinh: `services/ai_grader.py`  
Test xac nhan: `tests/test_ai_grader_unit.py::test_ai_grader_falls_back_from_gemini_429_to_groq`

## Ket qua xac nhan tu code base

- Production route goi `grade_submission_with_ai(..., provider=None)`.
- Khi `provider=None`, service thu Gemini truoc, neu loi se tiep tuc thu provider tiep theo co API key.
- Neu khong cau hinh Claude, luong fallback thuc te la Gemini -> Groq LLaMA 3.
- Test mock da xac nhan kich ban Gemini HTTP 429 van tra ket qua thanh cong bang Groq.
- Ket qua AI Grader bay gio co metadata `model_used`, `attempted_providers`, `fallback_from` de lam log/chung cu fallback.

## Bang dua vao slide

| Bai tap | Uu tien | Trang thai | Fallback | Phan hoi | Ket qua |
|---|---|---|---|---:|---|
| Chop tat LED | LLaMA 3 | Hoat dong | - | 1.13s | Thanh cong |
| Doc DHT22 + Serial | Gemini | HTTP 429 | LLaMA 3 | 1.09s | Thanh cong |
| MQTT Client | Gemini | HTTP 429 | LLaMA 3 | 1.09s | Thanh cong |
| WiFi + OTA Update | Gemini | HTTP 429 | LLaMA 3 | 1.31s | Thanh cong |

## Cau chu nen ghi tren slide

**Kiem Thu Fallback AI**  
Bang 3.7: AI Grader van tra ket qua khi Gemini gap loi HTTP 429 trong kich ban kiem thu fallback.

Nhan xet: Co che fallback giup qua trinh cham diem khong bi dung khi provider uu tien bi rate limit. Trong code hien tai, khi Gemini loi va Groq duoc cau hinh, he thong co the tiep tuc cham bang LLaMA 3 thong qua Groq API.

## Luu y de khong bi hoi xoay

Neu chua chay API that bang key Gemini/Groq, khong nen ghi "log thuc te". Cach ghi an toan la:

> Kiem thu fallback co kiem soat: mock Gemini HTTP 429 va xac nhan AI Grader tra ket qua thanh cong qua Groq/LLaMA 3.

Neu muon ghi "nho kien truc LPU cua Groq", nen ghi nhe hon:

> Groq/LLaMA 3 duoc dung lam provider fallback co do tre thap trong kich ban kiem thu.

## File hinh

`docs/reports/ai_fallback_benchmark_2026-05-22.svg`

# BÁO CÁO DỌN DẸP TEST SUITE, GIA CỐ BẢO MẬT VÀ CI
**Ngày thực hiện:** 20/05/2026  
**Dự án:** Remote Hardware Lab

## 1. Mục Tiêu Thực Hiện

Đợt cập nhật này tập trung vào việc làm sạch hệ thống kiểm thử và CI/CD để dự án có thể kiểm tra tự động một cách an toàn, không làm ảnh hưởng đến dữ liệu thật hoặc tài nguyên thật của hệ thống.

Các mục tiêu chính:

- Tách benchmark/script thủ công khỏi test suite để `pytest` không chạy nhầm các tác vụ có side effect.
- Gia cố bảo mật đường dẫn, đặc biệt là chặn path traversal và absolute path ngoài workspace.
- Bảo vệ dữ liệu thật như `.env`, `data/ai_training_dataset.jsonl`, dữ liệu user, logs, database thật và Docker container thật.
- Tăng số lượng test tự động, dùng mock mạnh để không gọi Docker, AI API, backend live hoặc MySQL thật trong CI mặc định.
- Chuẩn hóa CI bằng `ruff` và coverage gate.

## 2. Các Thay Đổi Chính

### 2.1. Dọn Dẹp Benchmark Khỏi Test Suite

Trước đây một số file benchmark nằm trong `tests/` nhưng không phải test chuẩn. Khi `pytest` collect, các file này có thể chạy code ở top-level, gây chậm và có nguy cơ gọi tài nguyên thật.

Đã chuyển các file này sang `scripts/benchmarks/`:

- `heavy_load_test.py`
- `test_ai_grader.py`
- `test_db_pooling.py`
- `test_docker_time.py`

Đồng thời các benchmark đã được bọc bằng:

```python
if __name__ == "__main__":
    main()
```

Kết quả: benchmark vẫn được giữ để phục vụ báo cáo/thực nghiệm thủ công, nhưng không còn chạy nhầm khi CI hoặc `pytest` chạy test tự động.

### 2.2. Gia Cố Bảo Mật Path Traversal

Hàm `is_safe_path` trong `utils/helpers.py` đã được viết lại theo hướng an toàn hơn:

- Dùng `realpath` để resolve symbolic link.
- Dùng `commonpath` để xác nhận target thật sự nằm trong thư mục gốc cho phép.
- Chặn absolute path ngoài workspace như `/etc/passwd`.
- Chặn traversal bằng `..`.
- Chặn symlink escape ra ngoài thư mục user.
- Trả về `False` với input không hợp lệ thay vì để phát sinh lỗi runtime.

Các route thao tác file trong `routes/user.py` cũng được siết lại để validate trước khi mở SSH/SFTP:

- List files
- Create folder
- Upload file
- Rename item
- Delete item
- Create/load/save editor file

### 2.3. Bảo Vệ Dữ Liệu Khi Xóa User

Route xóa user trong `routes/admin.py` đã được thêm guard trước `shutil.rmtree`.

Hệ thống chỉ cho phép xóa thư mục user nếu target chắc chắn nằm dưới `USER_DATA_DIR`. Nếu target trỏ tới root dữ liệu hoặc ra ngoài vùng cho phép, hệ thống từ chối xóa và ghi log lỗi.

Điều này giúp tránh các lỗi nguy hiểm như xóa nhầm thư mục dữ liệu gốc hoặc thư mục ngoài phạm vi dự án.

### 2.4. Tắt Side Effect Khi Import Docker Manager

Trước đây `services/docker_manager.py` tự khởi động GC background thread ngay khi import module. Điều này không phù hợp cho test/CI vì import app có thể mở thread nền ngoài ý muốn.

Đã refactor thành hàm explicit:

```python
start_container_gc()
```

Production gọi hàm này trong `app.main()`. CI/test có thể tắt bằng biến môi trường:

```bash
ENABLE_CONTAINER_GC=0
```

### 2.5. AI Grader Test-Safe

`services/ai_grader.py` hiện hỗ trợ tắt ghi dataset khi chạy test:

```bash
AI_GRADER_RECORD_DATASET=0
```

Hoặc đổi nơi ghi dataset sang file tạm:

```bash
AI_GRADER_DATASET_PATH=/tmp/ai_training_dataset.jsonl
```

Nhờ vậy test AI grader có thể kiểm tra logic chấm điểm, parse JSON, clamp điểm, xử lý lỗi API mà không ghi vào `data/ai_training_dataset.jsonl` thật.

### 2.6. Chuẩn Hóa CI Và Tooling

Đã thêm/cập nhật các file cấu hình:

- `pytest.ini`: cấu hình test path chỉ vào `tests/`.
- `requirements-dev.txt`: gom dependency phục vụ dev/CI như `pytest-cov`, `ruff`.
- `ruff.toml`: cấu hình lint tối thiểu để bắt lỗi nghiêm trọng như undefined name.
- `.coveragerc`: cấu hình coverage tập trung vào core modules, bỏ qua entrypoint, routes lớn, sockets, scripts và tests.
- `.github/workflows/ci.yml`: viết lại CI mặc định theo hướng an toàn.

CI hiện chạy:

```bash
ruff check .
pytest --cov=. --cov-report=term-missing --cov-fail-under=60
```

CI mặc định không còn chạy MySQL service, không gọi schema file không tồn tại và không dùng `continue-on-error`.

## 3. Bổ Sung Test Tự Động

Test suite đã được mở rộng từ 9 test lên 58 test.

Các nhóm test chính:

- `tests/conftest.py`: cấu hình env test-safe, client Flask, session login, chặn external network.
- Auth/session tests: kiểm tra API yêu cầu login, role sai bị chặn.
- File route tests: kiểm tra load/save/rename/delete/upload với path an toàn và path độc hại.
- Admin route tests: kiểm tra xóa user chỉ xóa trong thư mục dữ liệu tạm.
- AI grader tests: kiểm tra no files, thiếu API key, mocked Gemini/Groq, invalid JSON, clamp score, dataset temp/disabled.
- Arduino tests: kiểm tra compile parser, board detection, queue selection, serial port discovery bằng mock.
- Docker manager tests: kiểm tra GC disabled, docker inspect parser, command construction, helper functions bằng mock.
- Database tests: kiểm tra pool init và `init_db` bằng fake connection.
- Workspace manager tests: kiểm tra list/load/save file và invalid path.
- Security helper tests: kiểm tra password strength, captcha, CSRF.

## 4. Kết Quả Kiểm Chứng

Các lệnh đã chạy sau khi triển khai:

```bash
./venv/bin/python -m pytest --collect-only -q tests
```

Kết quả:

```text
58 tests collected in 0.23s
```

Trước khi dọn benchmark, collect từng mất khoảng 94 giây do import các script benchmark. Sau thay đổi, test discovery đã trở nên nhanh và không có side effect.

```bash
./venv/bin/ruff check .
```

Kết quả:

```text
All checks passed!
```

```bash
./venv/bin/python -m pytest --cov=. --cov-report=term-missing --cov-fail-under=60
```

Kết quả:

```text
58 passed, 1 warning
Required test coverage of 60% reached. Total coverage: 65.77%
```

Warning còn lại là `EventletDeprecationWarning` khi import `app.py`. Đây là cảnh báo dependency/kiến trúc realtime, chưa xử lý trong đợt này vì không thuộc phạm vi dọn test/CI.

## 5. Cam Kết Không Làm Mất Dữ Liệu

Trong quá trình triển khai:

- Không chỉnh sửa `.env`.
- Không chỉnh sửa `data/ai_training_dataset.jsonl`.
- Không xóa dữ liệu user thật.
- Không chạy Docker benchmark thật.
- Không gọi AI API thật trong test.
- Không kết nối MySQL thật trong CI mặc định.

File `pytest_output.txt` cũ được giữ lịch sử bằng cách chuyển sang:

```text
docs/reports/legacy_pytest_output.txt
```

## 6. Kết Luận

Sau đợt cập nhật này, dự án đã có nền tảng kiểm thử và CI sạch hơn, nhanh hơn và an toàn hơn. Test suite hiện chỉ chạy test thật, benchmark được tách riêng cho thực nghiệm thủ công, các thao tác file được gia cố chống path traversal, và CI mặc định đã đủ mạnh để bắt lỗi lint, lỗi test và tụt coverage mà không phụ thuộc tài nguyên thật.

Hệ thống hiện phù hợp hơn để tiếp tục phát triển, review code và chạy CI đều đặn trước khi nộp báo cáo hoặc triển khai.

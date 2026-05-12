import pytest
import os
from unittest.mock import MagicMock
from app import app
from utils.helpers import slugify_vn, is_safe_path
from services.workspace_manager import collect_mission_files

# ================= UNIT TESTS =================
def test_slugify_vn():
    """Kiểm tra hàm xử lý tên tiếng Việt có dấu và ký tự đặc biệt"""
    assert slugify_vn("Bài thi số 1!") == "bai_thi_so_1"
    assert slugify_vn("Đồ án NCKH @2026") == "do_an_nckh_2026"
    assert slugify_vn("   Xóa  khoảng  trắng  ") == "xoa_khoang_trang"

def test_is_safe_path():
    """Kiểm tra cơ chế chặn thư mục leo thang (Path Traversal)"""
    basedir = "/home/user1"
    
    # Đường dẫn hợp lệ
    assert is_safe_path(basedir, "folder/file.ino") == True
    assert is_safe_path(basedir, "file.txt") == True
    
    # Đường dẫn độc hại (Leo ra ngoài basedir)
    assert is_safe_path(basedir, "../../../etc/passwd") == False
    # /etc/passwd bị lstrip('/') thành relative path etc/passwd nên an toàn!
    assert is_safe_path(basedir, "/etc/passwd") == True
    assert is_safe_path(basedir, "folder/../../root_file") == False

def test_collect_mission_files():
    """Kiểm tra bộ thu thập file bài làm (Loại bỏ thư mục cấm)"""
    mock_sftp = MagicMock()
    
    # Giả lập sftp.listdir_attr()
    class MockAttr:
        def __init__(self, filename, st_mode, st_size):
            self.filename = filename
            self.st_mode = st_mode
            self.st_size = st_size

    import stat
    mock_sftp.listdir_attr.return_value = [
        MockAttr("main.ino", stat.S_IFREG, 1024),
        MockAttr("node_modules", stat.S_IFDIR, 4096),
        MockAttr(".hidden_file", stat.S_IFREG, 100),
        MockAttr("utils.py", stat.S_IFREG, 2048)
    ]
    
    # Mock open cho file nội dung
    mock_file = MagicMock()
    mock_file.read.return_value = b"Hello Code"
    mock_sftp.open.return_value.__enter__.return_value = mock_file
    
    files = collect_mission_files(mock_sftp, "/home/user", "/home/user", include_content=True)
    
    # node_modules và .hidden_file phải bị loại bỏ
    assert len(files) == 2
    filenames = [f['name'] for f in files]
    assert "main.ino" in filenames
    assert "utils.py" in filenames
    assert "node_modules" not in filenames
    
    # Kiểm tra nội dung có được đọc không
    assert files[0]['content'] == "Hello Code"

# ================= INTEGRATION TESTS =================
@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret'
    with app.test_client() as client:
        yield client

def test_rate_limiter_compile(client):
    """Kiểm tra tính năng chống Spam API /compile"""
    with client.session_transaction() as sess:
        sess['username'] = 'test_spam_user'
        sess['role'] = 'user'
    
    # Lần 1: Thành công (Sẽ trả về 400 vì thiếu params hợp lệ cho compiler thật, nhưng không phải 429)
    res1 = client.post('/user/test_spam_user/compile', json={"sketch_path": "test.ino"})
    assert res1.status_code != 429
    
    # Lần 2 (Ngay lập tức): Bị chặn bởi Rate Limiter
    res2 = client.post('/user/test_spam_user/compile', json={"sketch_path": "test.ino"})
    assert res2.status_code == 429
    assert "quá nhanh" in res2.json.get('error', '')

def test_file_lockdown_api(client):
    """Kiểm tra tính năng khóa file hệ thống không cho đổi tên"""
    with client.session_transaction() as sess:
        sess['username'] = 'test_user'
        sess['role'] = 'user'
        
    res = client.post('/user/test_user/rename-item', json={
        "old_path": "WELCOME.txt",
        "new_name": "hacked.txt"
    })
    
    assert res.status_code == 403
    assert "Không được phép" in res.json.get('error', '')

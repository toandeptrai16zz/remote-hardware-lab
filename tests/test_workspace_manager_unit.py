import stat
from unittest.mock import MagicMock

from services.workspace_manager import list_workspace_files, load_workspace_file, save_workspace_file


class Attr:
    def __init__(self, filename, mode, size=10, mtime=123):
        self.filename = filename
        self.st_mode = mode
        self.st_size = size
        self.st_mtime = mtime


class FileCtx:
    def __init__(self, data=b"content"):
        self.data = data
        self.written = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.data

    def write(self, content):
        self.written = content


def test_list_workspace_files_filters_hidden_and_sorts_directories_first():
    sftp = MagicMock()
    sftp.listdir_attr.return_value = [
        Attr("b.txt", stat.S_IFREG),
        Attr(".hidden", stat.S_IFREG),
        Attr("folder", stat.S_IFDIR),
        Attr("bad:name", stat.S_IFREG),
        Attr("WELCOME.txt", stat.S_IFREG),
    ]

    result = list_workspace_files("student", "student", sftp, ".")

    assert result["success"] is True
    assert [item["name"] for item in result["files"]] == ["folder", "WELCOME.txt", "b.txt"]


def test_list_workspace_files_reports_invalid_and_missing_paths():
    sftp = MagicMock()

    invalid = list_workspace_files("student", "student", sftp, "../../etc")
    assert invalid == {"success": False, "error": "Invalid path", "status_code": 400}

    sftp.listdir_attr.side_effect = FileNotFoundError()
    missing = list_workspace_files("student", "student", sftp, "missing")
    assert missing == {"success": False, "error": "Directory not found", "status_code": 404}


def test_load_and_save_workspace_file_success_and_invalid_path():
    sftp = MagicMock()
    file_ctx = FileCtx(b"abc")
    sftp.open.return_value = file_ctx

    loaded = load_workspace_file("student", "student", sftp, ".", "main.ino")
    saved = save_workspace_file("student", "student", sftp, ".", "main.ino", "new")
    invalid = save_workspace_file("student", "student", sftp, "..", "bad.ino", "x")

    assert loaded == {"success": True, "content": "abc"}
    assert saved == {"success": True}
    assert invalid == {"success": False, "error": "Invalid file path", "status_code": 400}
    assert file_ctx.written == "new"

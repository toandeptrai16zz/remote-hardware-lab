"""
Workspace Manager Service
Handles file operations inside user's container via SSH/SFTP.
Extracts business logic from Fat Controllers to adhere to Clean Code.
"""
import os
import stat
import logging
from config.settings import HIDDEN_SYSTEM_FILES

logger = logging.getLogger(__name__)

# Toan: Duplicate local is_safe_path helper if needed to prevent circular imports,
# but using the one from utils.helpers is better.
from utils.helpers import is_safe_path

def list_workspace_files(username, safe_username, sftp, target_path="."):
    """Liệt kê các tệp trong thư mục workspace của người dùng."""
    try:
        base_path = os.path.join("/home", safe_username, target_path)
        files = []
        try:
            dir_items = sftp.listdir_attr(base_path)
        except FileNotFoundError:
            return {"success": False, "error": "Directory not found", "status_code": 404}
            
        for attr in dir_items:
            filename = attr.filename
            if filename.startswith('.') or filename in HIDDEN_SYSTEM_FILES or ':' in filename:
                continue

            files.append({
                'name': filename, 
                'is_dir': stat.S_ISDIR(attr.st_mode), 
                'size': attr.st_size, 
                'modified': attr.st_mtime
            })
        
        files.sort(key=lambda x: (not x['is_dir'], x['name']))
        return {"success": True, "files": files, "path": target_path}

    except Exception as e:
        logger.error(f"Workspace Manager List Files Error: {e}")
        return {"success": False, "error": str(e), "status_code": 500}


def load_workspace_file(username, safe_username, sftp, relative_path, filename):
    """Read a file from user's workspace."""
    home_dir = f"/home/{safe_username}"
    filepath = os.path.join(home_dir, relative_path, filename)

    if not is_safe_path(home_dir, filepath):
        return {"success": False, "error": "Invalid file path", "status_code": 400}

    try:
        with sftp.open(filepath, 'r') as f: 
            content = f.read().decode('utf-8', errors='ignore')
        return {"success": True, "content": content}
    except Exception as e: 
        logger.error(f"Workspace Manager Load File Error: {e}")
        return {"success": False, "error": str(e), "status_code": 500}


def save_workspace_file(username, safe_username, sftp, relative_path, filename, content):
    """Write content to a file in user's workspace."""
    home_dir = f"/home/{safe_username}"
    filepath = os.path.normpath(os.path.join(home_dir, relative_path, filename))

    if not is_safe_path(home_dir, filepath):
        return {"success": False, "error": "Invalid file path", "status_code": 400}

    try:
        with sftp.open(filepath, 'w') as f: 
            f.write(content)
        return {"success": True}
    except Exception as e: 
        logger.error(f"Workspace Manager Save File Error: {e}")
        return {"success": False, "error": str(e), "status_code": 500}


def collect_mission_files(sftp, base_path, home_dir, include_content=False):
    """
    Duyệt đệ quy để thu thập các file mã nguồn phục vụ việc nộp bài hoặc xem trước.
    Ngăn chặn trùng lặp logic ở user_api_preview_files và user_api_submit_mission.
    """
    result_files = []
    
    def _collect(path, depth=0):
        if depth > 4: return
        try:
            EXCLUDED_DIRS = {'libraries', 'node_modules', 'venv', '__pycache__', '.git', '.arduino15', 'Arduino'}
            for item in sftp.listdir_attr(path):
                if item.filename.startswith('.'): continue
                if item.filename in EXCLUDED_DIRS: continue
                
                fp = f"{path}/{item.filename}"
                if stat.S_ISDIR(item.st_mode):
                    _collect(fp, depth + 1)
                elif item.filename.endswith(('.ino', '.cpp', '.c', '.h', '.py')):
                    if 'libraries/' in fp or 'node_modules/' in fp: continue
                    
                    file_info = {
                        'name': item.filename,
                        'path': fp.replace(home_dir, ''),
                        'size': item.st_size
                    }
                    if include_content:
                        with sftp.open(fp, 'r') as f:
                            file_info['content'] = f.read(50000).decode('utf-8', errors='replace')
                        
                    result_files.append(file_info)
        except Exception as e: 
            logger.error(f"Workspace Manager Collect Files Error at {path}: {e}")
            pass
            
    _collect(base_path)
    return result_files


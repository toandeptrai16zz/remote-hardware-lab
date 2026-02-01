#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script tổ chức lại cấu trúc thư mục cho dự án Flask
Tương thích với Windows
"""

import os
import shutil
from pathlib import Path

# Đường dẫn gốc của project
PROJECT_ROOT = Path(r"D:\Tài Liệu Mật\VERSION14\flask-kerberos-demo")

# Định nghĩa cấu trúc thư mục mới
FOLDERS = {
    'docs': 'Tài liệu và báo cáo',
    'scripts': 'Các script shell và utility',
    'logs': 'File log',
    'docker': 'Docker files',
    'backups': 'File backup'
}

# Định nghĩa các file cần di chuyển
FILE_MOVES = {
    # Di chuyển tài liệu
    '📑 BÁO CÁO KỸ THUẬT_28_12_2025.docx': 'docs',
    'README_REFACTORED.md': 'docs',
    
    # Di chuyển logs
    'app.log': 'logs',
    'login.log': 'logs',
    
    # Di chuyển scripts shell
    'entrypoint.sh': 'scripts',
    'setup-user-arduino.sh': 'scripts',
    'udev_wrapper.sh': 'scripts',
    
    # Di chuyển Docker files
    'docker-compose.yml': 'docker',
    'Dockerfile.api': 'docker',
    'Dockerfile.userenv': 'docker',
    
    # Di chuyển backups
    'app_old_backup.py': 'backups',
    
    # Di chuyển utility scripts
    'set_password.py': 'scripts',
    'filemanager.py': 'scripts',
    'udev_listener.py': 'scripts',
    'watcher.py': 'scripts',
}

def create_folders():
    """Tạo các thư mục mới"""
    print("🔧 Bắt đầu tổ chức lại cấu trúc thư mục...\n")
    
    for folder_name, description in FOLDERS.items():
        folder_path = PROJECT_ROOT / folder_name
        folder_path.mkdir(exist_ok=True)
        print(f"📁 Đã tạo thư mục: {folder_name}/ - {description}")
    
    print()

def move_files():
    """Di chuyển các file vào thư mục tương ứng"""
    moved_count = 0
    skipped_count = 0
    
    for filename, target_folder in FILE_MOVES.items():
        source_path = PROJECT_ROOT / filename
        target_path = PROJECT_ROOT / target_folder / filename
        
        if source_path.exists():
            try:
                shutil.move(str(source_path), str(target_path))
                print(f"✅ Đã chuyển: {filename} → {target_folder}/")
                moved_count += 1
            except Exception as e:
                print(f"❌ Lỗi khi chuyển {filename}: {e}")
        else:
            print(f"⚠️  Không tìm thấy: {filename}")
            skipped_count += 1
    
    print()
    print(f"📊 Tổng kết: Đã chuyển {moved_count} file, bỏ qua {skipped_count} file")

def create_gitignore_updates():
    """Cập nhật .gitignore để ignore logs và backups"""
    gitignore_path = PROJECT_ROOT / '.gitignore'
    
    additions = [
        '\n# Logs',
        'logs/*.log',
        '\n# Backups',
        'backups/*.py',
        'backups/*.sql',
    ]
    
    if gitignore_path.exists():
        with open(gitignore_path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(additions) + '\n')
        print("✅ Đã cập nhật .gitignore")

def create_readme_for_folders():
    """Tạo README.md cho mỗi thư mục mới"""
    readme_content = {
        'docs': """# Tài liệu

Thư mục này chứa tất cả tài liệu liên quan đến dự án:
- Báo cáo kỹ thuật
- Hướng dẫn sử dụng
- Documentation
""",
        'scripts': """# Scripts

Thư mục này chứa các script utility và automation:
- Shell scripts (.sh)
- Python utility scripts
- Setup scripts
""",
        'logs': """# Logs

Thư mục này chứa các file log của ứng dụng.

**Lưu ý**: File log không được commit vào Git.
""",
        'docker': """# Docker

Thư mục này chứa tất cả các file liên quan đến Docker:
- docker-compose.yml
- Dockerfile.api
- Dockerfile.userenv
""",
        'backups': """# Backups

Thư mục này chứa các file backup.

**Lưu ý**: File backup không được commit vào Git.
"""
    }
    
    for folder_name, content in readme_content.items():
        readme_path = PROJECT_ROOT / folder_name / 'README.md'
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📝 Đã tạo README cho {folder_name}/")

def print_new_structure():
    """In ra cấu trúc thư mục mới"""
    print("\n" + "="*60)
    print("✨ Hoàn thành tổ chức lại thư mục!")
    print("="*60)
    print("\n📊 Cấu trúc thư mục mới:\n")
    
    structure = """
flask-kerberos-demo/
├── 📄 app.py                 # Main application
├── 📁 docs/                  # Tài liệu, báo cáo
├── 📁 scripts/               # Các script shell và utility
├── 📁 logs/                  # File log (git ignored)
├── 📁 docker/                # Docker files
├── 📁 backups/               # File backup (git ignored)
├── 📁 config/                # Configuration
├── 📁 routes/                # Flask routes (Blueprint)
├── 📁 services/              # Business logic
├── 📁 models/                # Database models
├── 📁 utils/                 # Utilities & decorators
├── 📁 templates/             # HTML templates
│   └── 📁 admin/            # Admin templates
├── 📁 static/                # Static files (CSS, JS, images)
├── 📁 sockets/               # WebSocket handlers
├── 📁 esp32_core/            # ESP32 related code
└── 📁 venv/                  # Virtual environment
"""
    print(structure)
    
    print("\n💡 Lợi ích của cấu trúc mới:")
    print("   ✓ Dễ tìm kiếm file")
    print("   ✓ Phân tách rõ ràng theo chức năng")
    print("   ✓ Logs và backups được tách riêng")
    print("   ✓ Docker files được tổ chức gọn gàng")
    print("   ✓ Tuân thủ best practices")
    print()

def main():
    """Main function"""
    if not PROJECT_ROOT.exists():
        print(f"❌ Không tìm thấy thư mục: {PROJECT_ROOT}")
        return
    
    print(f"📂 Project: {PROJECT_ROOT}\n")
    
    # Tạo thư mục mới
    create_folders()
    
    # Di chuyển file
    move_files()
    
    # Tạo README cho các thư mục
    print()
    create_readme_for_folders()
    
    # Cập nhật .gitignore
    print()
    create_gitignore_updates()
    
    # In cấu trúc mới
    print_new_structure()

if __name__ == '__main__':
    main()
from flask import Blueprint, jsonify, request

from services.ssh_manager import get_ssh_client


fm_bp = Blueprint("filemanager", __name__)


# API mở file
@fm_bp.route('/user/<username>/open')
def open_file(username):
    filename = request.args.get('file')
    if not filename:
        return jsonify(ok=False, error="No file specified")
    client = get_ssh_client(username)
    sftp = client.open_sftp()
    try:
        with sftp.open(filename, 'r') as f:
            content = f.read().decode()
        return jsonify(ok=True, content=content)
    except Exception as e:
        return jsonify(ok=False, error=str(e))
    finally:
        sftp.close()
        client.close()

# API lưu file
@fm_bp.route('/user/<username>/save', methods=['POST'])
def save_file(username):
    data = request.get_json()
    filename = data.get('filename')
    content = data.get('content')
    if not filename:
        return jsonify(ok=False, error="Filename required")
    client = get_ssh_client(username)
    sftp = client.open_sftp()
    try:
        with sftp.open(filename, 'w') as f:
            f.write(content)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e))
    finally:
        sftp.close()
        client.close()

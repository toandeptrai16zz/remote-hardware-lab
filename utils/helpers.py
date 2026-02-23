"""
Helper utility functions
"""
import os
import re
import socket
import random

def make_safe_name(input_string):
    """Convert username to safe format (remove special characters)"""
    if not input_string:
        return ""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', input_string)

def is_safe_path(basedir, path):
    """Check if path is safe (prevent directory traversal attacks)"""
    # Remove leading slash from input
    if path.startswith('/'): 
        path = path.lstrip('/')
    target = os.path.abspath(os.path.join(basedir, path))
    return target.startswith(os.path.abspath(basedir))

def find_free_port(start=2200, end=2299):
    """Find an available port in the given range"""
    for _ in range(100):
        port = random.randint(start, end)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return None

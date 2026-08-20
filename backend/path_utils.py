import os
import sys

def get_base_dir() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return getattr(sys, "_MEIPASS")
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_user_data_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def get_static_dir() -> str:
    return os.path.join(get_base_dir(), "static")

def get_downloads_dir() -> str:
    d = os.path.join(get_user_data_dir(), "downloads")
    os.makedirs(d, exist_ok=True)
    return d

def get_cookies_dir() -> str:
    c = os.path.join(get_user_data_dir(), "cookies")
    os.makedirs(c, exist_ok=True)
    return c

def get_bin_dir() -> str:
    bundled_bin = os.path.join(get_base_dir(), "bin")
    if os.path.exists(bundled_bin):
        return bundled_bin
    local_bin = os.path.join(get_user_data_dir(), "bin")
    if os.path.exists(local_bin):
        return local_bin
    return bundled_bin

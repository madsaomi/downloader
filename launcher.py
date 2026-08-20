import os
import sys
import time
import socket
import threading
import webbrowser
import multiprocessing

from backend.app import app
import uvicorn

def find_free_port(start_port: int = 8000) -> int:
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    return start_port

def open_browser(port: int):
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{port}")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    os.system("title UniDownloader Portable")
    port = find_free_port(8000)
    print("=" * 56)
    print("             UniDownloader Portable v2.0")
    print("=" * 56)
    print(f"[*] Server running at: http://localhost:{port}")
    print("[*] Opening browser automatically...")
    print("[*] Press Ctrl+C to stop the server.\n")

    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

import os
import sys
import time
import socket
import threading
import webbrowser
import urllib.request
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

def run_server(port: int):
    try:
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            loop="asyncio",
            http="h11",
            lifespan="on"
        )
        server = uvicorn.Server(config)
        server.install_signal_handlers = lambda: None
        loop.run_until_complete(server.serve())
    except Exception as e:
        import traceback
        log_path = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "server_error.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())

def main():
    multiprocessing.freeze_support()
    port = find_free_port(8000)

    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    target_url = f"http://127.0.0.1:{port}"
    server_ready = False
    for _ in range(50):
        try:
            with urllib.request.urlopen(target_url, timeout=0.5) as resp:
                if resp.status == 200:
                    server_ready = True
                    break
        except Exception:
            time.sleep(0.2)

    try:
        import webview
        window = webview.create_window(
            title="UniDownloader",
            url=target_url,
            width=1180,
            height=820,
            min_size=(920, 620),
            background_color="#0b0d14",
            text_select=True
        )
        webview.start(gui="edgechromium")
    except Exception:
        webbrowser.open(target_url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    os._exit(0)

if __name__ == "__main__":
    main()

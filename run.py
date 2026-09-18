"""Convenience launcher: `python run.py` starts the server and opens your
browser to it. Equivalent to `uvicorn app.main:app --host 127.0.0.1 --port 8420`.
"""
import threading
import time
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8420


def _open_browser():
    time.sleep(1.0)
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)

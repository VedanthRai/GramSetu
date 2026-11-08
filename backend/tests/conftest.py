"""Test configuration: isolated DB, NO Gnani key (tests never spend credits), rules reasoning, own server port."""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="gramsetu-test-"))
PORT = 8765
os.environ.update({
    "GNANI_API_KEY": "", "REASONING_PROVIDER": "rules", "ANTHROPIC_API_KEY": "",
    "DB_PATH": str(TMP / "test.db"), "APP_ORIGIN": f"http://127.0.0.1:{PORT}", "BROWSER_HEADLESS": "true",
    "GNANI_FIXTURE_MODE": "false", "RETAIN_TRANSCRIPTS": "false", "DAILY_GNANI_REQUEST_LIMIT": "150",
})
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import httpx  # noqa: E402
import pytest  # noqa: E402
import uvicorn  # noqa: E402


@pytest.fixture(scope="session")
def server():
    from app.main import app
    cfg = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    srv = uvicorn.Server(cfg)
    t = threading.Thread(target=srv.run, daemon=True)
    t.start()
    for _ in range(100):
        try:
            if httpx.get(f"http://127.0.0.1:{PORT}/api/health").status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    yield f"http://127.0.0.1:{PORT}"
    srv.should_exit = True
    t.join(timeout=10)


@pytest.fixture()
def client(server):
    with httpx.Client(base_url=server, timeout=60) as c:
        yield c

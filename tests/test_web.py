import json
import time
import urllib.error
import urllib.request

import pytest

from src.web import make_server
from tests.fakes import FakeLLM, make_db


def call(base, path, body=None, ctype="application/json"):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": ctype} if data is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"{}") if "json" in r.headers.get("Content-Type", "") else r.read()
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def wait(base, job_id, timeout=10):
    t0 = time.time()
    while time.time() - t0 < timeout:
        _, j = call(base, f"/api/jobs/{job_id}")
        if j["status"] in ("done", "error"):
            return j
        time.sleep(0.05)
    raise AssertionError("job timeout")


@pytest.fixture
def server(tmp_path):
    db = make_db(tmp_path / "t.db")
    llm = FakeLLM(replies=["Thought: need headlines\nAction: get_articles(economics)",
                           "Thought: done\nFinal Answer: Headline number 1 about economics"])
    srv = make_server("127.0.0.1", 0, db_path=db, reports_dir=tmp_path / "reports", llm_factory=lambda name: llm, default_model="phi")
    import threading
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_index_and_status(server):
    code, html = call(server, "/")
    assert code == 200 and b"INSIGHT" in html
    code, st = call(server, "/api/status")
    assert code == 200 and st["total"] == 30 and st["categories"]["economics"] == 5 and st["default_model"] == "phi"
    assert call(server, "/api/digest")[1] == {"text": None}


def test_refresh_builds_digest_then_ask_streams_steps(server):
    code, job = call(server, "/api/refresh", {"ingest": False})
    assert code == 202
    j = wait(server, job["id"])
    assert j["status"] == "done"
    code, d = call(server, "/api/digest")
    assert "## economics" in d["text"]

    code, job = call(server, "/api/ask", {"question": "What's new in economics?", "model": "phi"})
    j = wait(server, job["id"])
    assert j["status"] == "done" and j["result"]["finished"] and "Headline number 1" in j["result"]["answer"]
    kinds = [e["kind"] for e in j["events"]]
    assert "status" in kinds and kinds.count("step") >= 3
    code, j2 = call(server, f"/api/jobs/{job['id']}?since={j['next']}")
    assert j2["events"] == []


def test_validation_and_csrf(server):
    assert call(server, "/api/ask", {"question": "x", "model": "phi"})[0] == 400
    assert call(server, "/api/ask", {"question": "hello there", "model": "nope"})[0] == 400
    assert call(server, "/api/ask", {"question": "hello there"}, ctype="text/plain")[0] == 400
    assert call(server, "/api/jobs/aaaaaaaaaaaa")[0] == 404
    assert call(server, "/api/nothing")[0] == 404

import contextlib
import io
import json
import os
import queue
import re
import sqlite3
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from config.config import CATEGORIES, DB_PATH
from config.runtime import DEFAULT_MODEL, MODELS, REPORTS_DIR

INDEX_HTML = Path(__file__).with_name("web_index.html")
STATIC = {"/style.css": ("style.css", "text/css; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8")}
MAX_BODY = 4096
MAX_QUESTION = 500
MAX_JOBS = 50


class Job:
    def __init__(self, kind, params):
        self.id = uuid.uuid4().hex[:12]
        self.kind, self.params = kind, params
        self.status = "queued"  # queued | running | done | error
        self.events, self.result, self.error = [], None, None
        self.created = time.time()
        self.lock = threading.Lock()

    def emit(self, kind, **data):
        with self.lock:
            self.events.append({"i": len(self.events), "t": round(time.time() - self.created, 1), "kind": kind, **data})

    def snapshot(self, since=0):
        with self.lock:
            return {"id": self.id, "kind": self.kind, "status": self.status, "result": self.result, "error": self.error,
                    "events": self.events[since:], "next": len(self.events)}


class App:
    def __init__(self, db_path=DB_PATH, reports_dir=REPORTS_DIR, llm_factory=None, default_model=None):
        self.db_path, self.reports_dir = Path(db_path), Path(reports_dir)
        self.llm_factory = llm_factory
        self.default_model = default_model or os.environ.get("WEB_MODEL", DEFAULT_MODEL)
        self.jobs, self.order = {}, []
        self.queue = queue.Queue(maxsize=5)
        self._llms = {}
        self.current = None
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()

    def status(self):
        info = {"models": list(MODELS), "default_model": self.default_model, "categories": {c: 0 for c in CATEGORIES},
                "total": 0, "unclassified": 0, "last_fetch": None, "report_time": None,
                "busy": self.current is not None, "queued": self.queue.qsize()}
        if self.db_path.exists():
            conn = sqlite3.connect(self.db_path)
            try:
                info["total"] = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
                info["unclassified"] = conn.execute("SELECT COUNT(*) FROM articles WHERE category IS NULL").fetchone()[0]
                info["last_fetch"] = conn.execute("SELECT MAX(fetched_at) FROM articles").fetchone()[0]
                for cat, n in conn.execute("SELECT category, COUNT(*) FROM articles WHERE category IS NOT NULL GROUP BY category"):
                    if cat in info["categories"]:
                        info["categories"][cat] = n
            except sqlite3.Error:
                pass
            finally:
                conn.close()
        latest = self.reports_dir / "latest.md"
        if latest.exists():
            info["report_time"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(latest.stat().st_mtime))
        return info

    def digest(self):
        latest = self.reports_dir / "latest.md"
        if not latest.exists():
            return {"text": None}
        return {"text": latest.read_text(encoding="utf-8"),
                "time": time.strftime("%Y-%m-%d %H:%M", time.localtime(latest.stat().st_mtime))}

    def submit(self, kind, params):
        job = Job(kind, params)
        try:
            self.queue.put_nowait(job)
        except queue.Full:
            return None
        self.jobs[job.id] = job
        self.order.append(job.id)
        while len(self.order) > MAX_JOBS:
            self.jobs.pop(self.order.pop(0), None)
        return job

    def _get_llm(self, name, job):
        if name not in self._llms:
            job.emit("status", text=f"Завантаження моделі {name} (перший раз може тривати хвилину або довше)…")
            factory = self.llm_factory
            if factory is None:
                from src.llm import LLM as factory
            self._llms = {name: factory(name)}
        return self._llms[name]

    def _loop(self):
        while True:
            job = self.queue.get()
            self.current = job
            job.status = "running"
            try:
                if job.kind == "ask":
                    self._run_ask(job)
                else:
                    self._run_pipeline(job)
                job.status = "done"
            except Exception as e:
                job.error = f"{type(e).__name__}: {e}"
                job.status = "error"
            finally:
                self.current = None

    def _run_ask(self, job):
        from src.agent import Agent
        from src.tools import Toolbox
        llm = self._get_llm(job.params["model"], job)
        job.emit("status", text="Агент думає…")
        agent = Agent(llm, Toolbox(db_path=self.db_path).registry)
        res = agent.run(job.params["question"], on_event=lambda e: job.emit("step", **e))
        job.result = {"answer": res["answer"], "finished": res["finished"], "steps": res["steps"], "seconds": res["seconds"]}

    def _run_pipeline(self, job):
        from src import run_daily
        job.emit("status", text="Збір новин і класифікація…" if job.params.get("ingest") else "Перебудова дайджесту…")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_daily.run(model="baseline", digest_model="none", do_ingest=bool(job.params.get("ingest")),
                          db_path=self.db_path, reports_dir=self.reports_dir)
        lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
        job.result = {"log": "\n".join(lines[-25:])}


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = "InsightFlow"

        def log_message(self, fmt, *args):
            pass

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if ctype != "application/json":
                return None, "Content-Type має бути application/json"
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return None, "некоректний Content-Length"
            if n > MAX_BODY:
                return None, "запит завеликий"
            try:
                data = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return None, "некоректний JSON"
            return (data if isinstance(data, dict) else {}), None

        def do_GET(self):
            path = self.path.split("?")[0]
            if path in ("/", "/index.html"):
                return self._send(200, INDEX_HTML.read_bytes(), "text/html; charset=utf-8")
            if path in STATIC:
                name, ctype = STATIC[path]
                return self._send(200, INDEX_HTML.with_name(name).read_bytes(), ctype)
            if path == "/api/status":
                return self._send(200, app.status())
            if path == "/api/digest":
                return self._send(200, app.digest())
            m = re.fullmatch(r"/api/jobs/([0-9a-f]{12})", path)
            if m:
                job = app.jobs.get(m.group(1))
                if not job:
                    return self._send(404, {"error": "завдання не знайдено"})
                since = 0
                q = self.path.partition("?")[2]
                if q.startswith("since=") and q[6:].isdigit():
                    since = int(q[6:])
                return self._send(200, job.snapshot(since))
            return self._send(404, {"error": "не знайдено"})

        def do_POST(self):
            path = self.path.split("?")[0]
            body, err = self._body()
            if err:
                return self._send(400, {"error": err})
            if path == "/api/ask":
                question = str(body.get("question", "")).strip()
                model = body.get("model") or app.default_model
                if not 2 <= len(question) <= MAX_QUESTION:
                    return self._send(400, {"error": f"питання має бути від 2 до {MAX_QUESTION} символів"})
                if model not in MODELS:
                    return self._send(400, {"error": f"невідома модель '{model}'"})
                job = app.submit("ask", {"question": question, "model": model})
            elif path == "/api/refresh":
                job = app.submit("refresh", {"ingest": bool(body.get("ingest", False))})
            else:
                return self._send(404, {"error": "не знайдено"})
            if job is None:
                return self._send(429, {"error": "черга заповнена, зачекайте"})
            return self._send(202, {"id": job.id})

    return Handler


def make_server(host="127.0.0.1", port=8000, **kwargs):
    app = App(**kwargs)
    server = ThreadingHTTPServer((host, port), make_handler(app))
    server.app = app
    return server


def main():
    host, port = os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8000"))
    server = make_server(host, port)
    print(f"InsightFlow: http://{host}:{port}  (модель за замовчуванням: {server.app.default_model})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

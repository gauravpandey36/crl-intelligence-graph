#!/usr/bin/env python3
"""L9 — the CRL Intelligence Graph portal server (stdlib, no deps).

Serves the static portal (home dashboard, Cytoscape explorer, 652-page wiki) AND:
  POST /api/chat   {session, msg}      -> the graph-grounded Claude companion
  POST /api/screen {vendors:[...]}     -> vendor watch-list screen + exposure index

Public FDA data. Educational, not regulatory advice. Reuses the companion + screener.
"""
from __future__ import annotations
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # portal/
PROJ = ROOT.parent
sys.path.insert(0, str(PROJ / "companion"))
sys.path.insert(0, str(PROJ / "screener"))

from guide import Guide, load_anthropic_key       # noqa: E402
from screen import screen_csv, screen_vendor, _load  # noqa: E402
from exposure import exposure                       # noqa: E402

SESSIONS: dict[str, Guide] = {}
_WATCH = None  # lazy-loaded watch lists


def watch():
    global _WATCH
    if _WATCH is None:
        _WATCH = _load()
    return _WATCH


# --- light rate-limit so a forwarded link can't run up the owner's API key ---
GLOBAL_CAP = int(os.environ.get("CRL_CHAT_DAILY_CAP", "600"))
SESSION_CAP = int(os.environ.get("CRL_CHAT_SESSION_CAP", "40"))
_CHAT = {"day": None, "n": 0, "by": {}}


def chat_allowed(sid: str):
    import datetime
    today = datetime.date.today().isoformat()
    if _CHAT["day"] != today:
        _CHAT.update(day=today, n=0, by={})
    if _CHAT["n"] >= GLOBAL_CAP:
        return False
    if _CHAT["by"].get(sid, 0) >= SESSION_CAP:
        return False
    _CHAT["n"] += 1
    _CHAT["by"][sid] = _CHAT["by"].get(sid, 0) + 1
    return True


class H(BaseHTTPRequestHandler):
    def _send(self, code, body: bytes, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/healthz":
            return self._send(200, b"ok", "text/plain")
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        f = (ROOT / rel).resolve()
        if not str(f).startswith(str(ROOT)) or not f.is_file():
            return self._send(404, b"not found", "text/plain")
        ctype = ("text/html" if f.suffix == ".html" else "application/json"
                 if f.suffix == ".json" else "text/css" if f.suffix == ".css"
                 else "application/javascript" if f.suffix == ".js"
                 else "video/mp4" if f.suffix == ".mp4" else "application/octet-stream")
        self._send(200, f.read_bytes(), ctype + ("; charset=utf-8" if "text" in ctype else ""))

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        try:
            req = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            req = {}
        if self.path == "/api/chat":
            sid = req.get("session", "anon")
            if req.get("msg") and not chat_allowed(sid):
                return self._json(200, {"type": "SAY", "offer_upload": False, "text": (
                    "You've reached the demo chat limit for now — the guide runs on a capped key. "
                    "Everything else on the page (the graph, the wiki, and the vendor screener) still "
                    "works without limits. Come back a bit later to keep chatting.")})
            sess = SESSIONS.get(sid)
            try:
                if sess is None:
                    sess = SESSIONS[sid] = Guide()
                    out = sess.open() if not req.get("msg") else sess.say(req["msg"])
                else:
                    out = sess.say(req.get("msg", ""))
                return self._json(200, out)
            except Exception as e:  # noqa: BLE001
                return self._json(200, {"type": "SAY", "text": f"(guide error: {e})",
                                        "offer_upload": False})
        if self.path == "/api/screen":
            vendors = req.get("vendors") or []
            ia, db, rc = watch()
            results = [screen_vendor(v, ia, db, rc) for v in vendors if v and v.strip()]
            ex = exposure(results)
            return self._json(200, {"results": results, "exposure": ex})
        self._send(404, b"not found", "text/plain")

    def log_message(self, *a):
        pass


def main():
    if not load_anthropic_key():
        print("WARN: no Anthropic key — companion will fail.", file=sys.stderr)
    # Cloud platforms (Railway/Render/Heroku) inject the port via $PORT; argv wins locally.
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", "8791"))
    print(f"CRL Intelligence Graph portal on 0.0.0.0:{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()


if __name__ == "__main__":
    main()

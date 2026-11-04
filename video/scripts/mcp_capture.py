"""Capture a real MCP session with Caliper's server for the demo video ($0: cached runs only).

Starts backend/caliper/mcp_server.py over stdio exactly as the Claude Desktop config in
docs/demo_agent.md does (same command, args and env), from a folder outside the repo, plus one
guard: the Meta API address points at a dead port, so a cache miss fails instead of spending.
Then it speaks plain JSON-RPC (newline-delimited, the MCP stdio transport): initialize,
tools/list, tools/call measure on C07, tools/call study on A14. Every message both ways is saved
verbatim to video/data/mcp/session.json; the scene reads that file and nothing else.

The arguments come from the files the cached runs were made from: C07's question from
data/field/truth.csv, its prior from the cached field run, A14's gates and distance from
eval/study_gates.json (committed before scoring), and the vehicle class the cache holds.

Usage: backend/.venv/Scripts/python.exe video/scripts/mcp_capture.py
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "video" / "data" / "mcp" / "session.json"
LOG = ROOT / "video" / "out" / "mcp_server.log"

# docs/demo_agent.md, section 1 (Claude Desktop config)
COMMAND = str(ROOT / "backend" / ".venv" / "Scripts" / "python.exe")
ARGS = ["-m", "caliper.mcp_server"]
ENV = {"PYTHONPATH": str(ROOT / "backend"), "LIVE_RUNS_ENABLED": "true"}
GUARD = {"META_API_BASE_URL": "http://127.0.0.1:9/v1"}  # cache misses fail, never spend
PASS_ENV = ("SYSTEMROOT", "PATH", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA")


def truth_row(clip: str) -> dict[str, str]:
    with open(ROOT / "data" / "field" / "truth.csv", encoding="utf-8", newline="") as fh:
        return next(r for r in csv.DictReader(fh) if r["clip_id"] == clip)


def line(g: list[list[float]]) -> dict[str, list[float]]:
    return {"a": g[0], "b": g[1]}


def calls() -> list[tuple[str, dict]]:
    c07 = truth_row("C07")
    c07_run = json.loads((ROOT / "data/cache/field_runs/C07.json").read_text(encoding="utf-8"))
    a14 = truth_row("A14")
    gates_file = json.loads((ROOT / "eval" / "study_gates.json").read_text(encoding="utf-8"))
    gates = gates_file["clips"]["A14"]
    return [
        ("measure", {
            "video_path": str(ROOT / "data" / "field" / c07["file"]),
            "question": c07["question"],
            "prior": c07_run["prior"],
        }),
        ("study", {
            "video_path": str(ROOT / "data" / "field" / a14["file"]),
            "gates": {"gate_a": line(gates["gate_a"]), "gate_b": line(gates["gate_b"])},
            "distance_m": gates["distance_m"],
            "vehicle_classes": [gates["vehicle_phrase"]],
        }),
    ]  # fmt: skip


class Session:
    def __init__(self) -> None:
        env = {k: v for k, v in os.environ.items() if k.upper() in PASS_ENV}
        env.update(ENV)
        env.update(GUARD)
        LOG.parent.mkdir(parents=True, exist_ok=True)
        self.log = open(LOG, "w", encoding="utf-8")  # noqa: SIM115
        self.cwd = tempfile.mkdtemp(prefix="caliper-mcp-")  # outside the repo, like a desktop app
        self.proc = subprocess.Popen(
            [COMMAND, *ARGS], cwd=self.cwd, env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=self.log, text=True, encoding="utf-8", bufsize=1,
        )  # fmt: skip
        self.messages: list[dict] = []
        self.t0 = time.monotonic()
        self.lines: list[str] = []
        self.ready = threading.Condition()
        threading.Thread(target=self._read, daemon=True).start()
        self.next_id = 1

    def _read(self) -> None:
        assert self.proc.stdout is not None
        for text in self.proc.stdout:
            with self.ready:
                self.lines.append(text)
                self.ready.notify_all()

    def _stamp(self, direction: str, msg: dict) -> None:
        ms = round((time.monotonic() - self.t0) * 1000)
        self.messages.append({"direction": direction, "t_ms": ms, "message": msg})

    def send(self, msg: dict) -> None:
        assert self.proc.stdin is not None
        self._stamp("client_to_server", msg)
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def request(self, method: str, params: dict, timeout: float = 600) -> dict:
        rid = self.next_id
        self.next_id += 1
        self.send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while True:
            with self.ready:
                while not self.lines:
                    left = deadline - time.monotonic()
                    if left <= 0 or not self.ready.wait(left):
                        raise TimeoutError(f"no answer to {method}")
                text = self.lines.pop(0)
            msg = json.loads(text)
            self._stamp("server_to_client", msg)
            if msg.get("id") == rid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg["result"]

    def close(self) -> None:
        if self.proc.stdin:
            self.proc.stdin.close()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.log.close()


def main() -> None:
    s = Session()
    try:
        init = s.request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "caliper-demo-agent", "version": "1.0"},
        })  # fmt: skip
        s.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        tools = s.request("tools/list", {})
        print("server", init.get("serverInfo"), "tools", [t["name"] for t in tools["tools"]])
        for name, args in calls():
            t = time.monotonic()
            out = s.request("tools/call", {"name": name, "arguments": args})
            if out.get("isError"):
                raise RuntimeError(f"{name} failed: {out.get('content')}")
            r = out.get("structuredContent") or {}
            print(f"{name}: {time.monotonic() - t:.1f} s, status {r.get('status')}, "
                  f"value {r.get('value')}, measured {r.get('vehicles_measured')}")  # fmt: skip
    finally:
        s.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    session = {
        "note": "Verbatim JSON-RPC messages of one stdio session with backend/caliper/"
        "mcp_server.py (video/scripts/mcp_capture.py). Cached runs only; the Meta API address "
        "pointed at a dead port, so no call could reach the API.",
        "server": {"command": COMMAND, "args": ARGS, "env": ENV, "guard_env": GUARD},
        "messages": s.messages,
    }
    OUT.write_text(json.dumps(session, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(s.messages)} messages)")


if __name__ == "__main__":
    sys.exit(main())

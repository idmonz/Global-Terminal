from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the local Global Terminal web product and optional FastAPI runtime.")
    parser.add_argument("--api-host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--web-host", default="127.0.0.1")
    parser.add_argument("--web-port", type=int, default=3000)
    parser.add_argument("--production", action="store_true", help="Use next start instead of next dev. Run npm build first.")
    parser.add_argument("--open", action="store_true", help="Open the web URL in the default browser after startup.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands and status without starting processes.")
    parser.add_argument("--wait-seconds", type=int, default=35)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    web_root = repo_root / "apps" / "web"
    api_url = f"http://{args.api_host}:{args.api_port}"
    web_url = f"http://{args.web_host}:{args.web_port}"
    web_probe_url = f"{web_url}/?view=home&mode=fixture"
    npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    api_command = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.api.app:app",
        "--host",
        args.api_host,
        "--port",
        str(args.api_port),
    ]
    web_script = "start" if args.production else "dev"
    web_command = [
        npm,
        "--prefix",
        str(web_root),
        "run",
        web_script,
        "--",
        "--hostname",
        args.web_host,
        "--port",
        str(args.web_port),
    ]
    env_overrides = {
        "GLOBAL_TERMINAL_API_BASE_URL": api_url,
        "NEXT_PUBLIC_GLOBAL_TERMINAL_API_BASE_URL": api_url,
    }
    plan = {
        "repo_root": str(repo_root),
        "api_url": api_url,
        "web_url": web_url,
        "web_probe_url": web_probe_url,
        "mode": "production" if args.production else "dev",
        "api_command": api_command,
        "web_command": web_command,
        "env_overrides": env_overrides,
        "secrets_printed": False,
        "api_port_open": port_open(args.api_host, args.api_port),
        "web_port_open": port_open(args.web_host, args.web_port),
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, **plan}, indent=2))
        return 0

    validate_paths(repo_root, web_root)
    log_dir = repo_root / "review_workspace" / "runtime_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    started: list[dict[str, Any]] = []
    blocked: list[str] = []
    env = os.environ.copy()
    env.update(env_overrides)

    if port_open(args.api_host, args.api_port):
        if http_status(f"{api_url}/api", timeout=2) == 200:
            started.append({"component": "fastapi", "status": "reused", "url": f"{api_url}/api"})
        else:
            blocked.append(f"API port {args.api_port} is already occupied but {api_url}/api did not respond.")
    else:
        process = start_background(api_command, repo_root, env, log_dir / "fastapi.log")
        started.append({"component": "fastapi", "status": "started", "pid": process.pid, "url": f"{api_url}/api"})

    if port_open(args.web_host, args.web_port):
        if http_status(web_probe_url, timeout=15) == 200:
            started.append({"component": "next", "status": "reused", "url": web_url})
        else:
            blocked.append(f"Web port {args.web_port} is already occupied but {web_probe_url} did not respond.")
    else:
        process = start_background(web_command, repo_root, env, log_dir / "next.log")
        started.append({"component": "next", "status": "started", "pid": process.pid, "url": web_url})

    if blocked:
        print(json.dumps({"ok": False, "blocked": blocked, **plan}, indent=2))
        return 2

    probes = wait_for_runtime(api_url, web_url, web_probe_url, args.wait_seconds)
    result = {
        "ok": probes["api"] and probes["web"],
        "started": started,
        "probes": probes,
        "logs": {"fastapi": str(log_dir / "fastapi.log"), "next": str(log_dir / "next.log")},
        "open": web_url,
        "api": f"{api_url}/api/runtime-health",
        "secrets_printed": False,
    }
    print(json.dumps(result, indent=2))
    if args.open and probes["web"]:
        webbrowser.open(web_url)
    return 0 if result["ok"] else 1


def validate_paths(repo_root: Path, web_root: Path) -> None:
    if not (repo_root / "backend" / "api" / "app.py").exists():
        raise SystemExit("backend/api/app.py was not found. Run this from the Global Terminal repository.")
    if not (web_root / "package.json").exists():
        raise SystemExit("apps/web/package.json was not found. Run npm install in apps/web first.")


def start_background(command: list[str], cwd: Path, env: dict[str, str], log_path: Path) -> subprocess.Popen[Any]:
    log_file = log_path.open("a", encoding="utf-8")
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        start_new_session=os.name != "nt",
    )


def port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.45)
        return sock.connect_ex((host, port)) == 0


def http_status(url: str, *, timeout: float) -> int | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return int(response.status)
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def wait_for_runtime(api_url: str, web_url: str, web_probe_url: str, wait_seconds: int) -> dict[str, Any]:
    deadline = time.time() + max(1, wait_seconds)
    api_ok = False
    web_ok = False
    while time.time() < deadline and not (api_ok and web_ok):
        api_ok = api_ok or http_status(f"{api_url}/api/runtime-health", timeout=2) == 200
        web_ok = web_ok or http_status(web_probe_url, timeout=15) == 200
        if not (api_ok and web_ok):
            time.sleep(1)
    return {
        "api": api_ok,
        "web": web_ok,
        "api_health_url": f"{api_url}/api/runtime-health",
        "web_url": web_url,
        "web_probe_url": web_probe_url,
        "wait_seconds": wait_seconds,
    }


if __name__ == "__main__":
    raise SystemExit(main())

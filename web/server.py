#!/usr/bin/env python3

import base64
import json
import os
import subprocess
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "0.0.0.0"
PORT = 8080
CONTROL = "/srv/scripts/server.sh"
BASE_DIR = Path(__file__).resolve().parent


def run_control(command, stack):
    if command not in {"start", "stop", "restart"}:
        raise ValueError("Invalid command")

    if stack not in {"download", "arr", "jdownloader", "all"}:
        raise ValueError("Invalid stack")

    result = subprocess.run(
        [CONTROL, command, stack],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=180,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stdout.strip() or "Command failed")

    return result.stdout.strip()


def _read_int(path):
    try:
        return int(Path(path).read_text().strip())
    except (OSError, ValueError):
        return None


def get_system_stats():
    stats = {}

    temp_raw = _read_int("/sys/class/thermal/thermal_zone0/temp")
    stats["temperature_c"] = (
        round(temp_raw / 1000, 1)
        if temp_raw is not None
        else None
    )

    try:
        values = list(
            map(
                int,
                Path("/proc/stat").read_text().splitlines()[0].split()[1:],
            )
        )
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        total = sum(values)
        previous = getattr(get_system_stats, "_cpu_sample", None)
        get_system_stats._cpu_sample = (total, idle)

        if previous and total > previous[0]:
            stats["cpu_percent"] = round(
                100 * (total - previous[0] - (idle - previous[1]))
                / (total - previous[0]),
                1,
            )
        else:
            stats["cpu_percent"] = None
    except (OSError, ValueError, IndexError):
        stats["cpu_percent"] = None

    try:
        memory = {
            key: int(value.split()[0])
            for key, value in (
                line.split(":", 1)
                for line in Path("/proc/meminfo").read_text().splitlines()
            )
        }

        total = memory["MemTotal"]
        available = memory["MemAvailable"]
        used = total - available
        cached = max(
            memory.get("Cached", 0)
            + memory.get("SReclaimable", 0)
            - memory.get("Shmem", 0),
            0,
        )
        swap_total = memory.get("SwapTotal", 0)
        swap_free = memory.get("SwapFree", 0)
        swap_used = swap_total - swap_free

        stats["memory"] = {
            "used_mb": round(used / 1024, 1),
            "total_mb": round(total / 1024, 1),
            "available_mb": round(available / 1024, 1),
            "cached_mb": round(cached / 1024, 1),
            "percent": round(100 * used / total, 1),
            "swap": {
                "used_mb": round(swap_used / 1024, 1),
                "total_mb": round(swap_total / 1024, 1),
                "percent": round(100 * swap_used / swap_total, 1)
                if swap_total
                else 0.0,
            },
        }
    except (OSError, ValueError, KeyError, ZeroDivisionError):
        stats["memory"] = None

    try:
        stats["load"] = [
            float(value)
            for value in Path("/proc/loadavg").read_text().split()[:3]
        ]
    except (OSError, ValueError, IndexError):
        stats["load"] = None

    try:
        stats["uptime_seconds"] = int(
            float(Path("/proc/uptime").read_text().split()[0])
        )
    except (OSError, ValueError, IndexError):
        stats["uptime_seconds"] = None

    try:
        usage = os.statvfs("/")
        total = usage.f_blocks * usage.f_frsize
        free = usage.f_bavail * usage.f_frsize
        used = total - free

        stats["disk"] = {
            "used_gb": round(used / 1024**3, 1),
            "total_gb": round(total / 1024**3, 1),
            "percent": round(100 * used / total, 1) if total else 0.0,
        }
    except OSError:
        stats["disk"] = None

    return stats


def get_process_stats(limit=15):
    processes = []

    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
    except OSError:
        return []

    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue

        try:
            stat = Path(f"/proc/{pid}/stat").read_text()
            close = stat.rfind(")")
            if close < 0:
                continue

            fields = stat[close + 2:].split()
            rss = int(fields[21]) * page_size / 1024 / 1024
            name = stat[stat.find("(") + 1:close]

            processes.append({
                "pid": int(pid),
                "name": name,
                "memory_mb": round(rss, 1),
            })
        except (OSError, ValueError, IndexError):
            continue

    processes.sort(key=lambda item: item["memory_mb"], reverse=True)
    return processes[:limit]


def get_status():
    result = subprocess.run(
        [CONTROL, "status", "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "Status failed"
        )

    data = json.loads(result.stdout)
    data["system"] = get_system_stats()
    data["processes"] = get_process_stats()
    return data


def authorized(handler):
    username = os.environ.get("RPI_UI_USER", "")
    password = os.environ.get("RPI_UI_PASSWORD", "")

    if not username or not password:
        return False

    raw = handler.headers.get("Authorization", "")
    if not raw.startswith("Basic "):
        return False

    try:
        decoded = base64.b64decode(raw[6:], validate=True).decode()
        user, supplied_password = decoded.split(":", 1)
    except Exception:
        return False

    return user == username and supplied_password == password


def require_auth(handler):
    if authorized(handler):
        return True

    handler.send_response(401)
    handler.send_header(
        "WWW-Authenticate",
        'Basic realm="RPI Server"',
    )
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", "0")
    handler.end_headers()
    return False


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def send_file(self, path, content_type):
        try:
            payload = path.read_bytes()
        except OSError:
            self.send_json({"error": "Not found"}, 404)
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if not require_auth(self):
            return

        path = urllib.parse.urlparse(self.path).path

        if path == "/":
            self.send_file(
                BASE_DIR / "templates" / "index.html",
                "text/html; charset=utf-8",
            )
            return

        if path == "/static/style.css":
            self.send_file(BASE_DIR / "static" / "style.css", "text/css")
            return

        if path == "/static/app.js":
            self.send_file(
                BASE_DIR / "static" / "app.js",
                "application/javascript; charset=utf-8",
            )
            return

        if path == "/api/status":
            try:
                self.send_json(get_status())
            except Exception as error:
                self.send_json({"error": str(error)}, 500)
            return

        self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if not require_auth(self):
            return

        url = urllib.parse.urlparse(self.path)
        if url.path != "/api/action":
            self.send_json({"error": "Not found"}, 404)
            return

        query = urllib.parse.parse_qs(url.query)
        command = query.get("command", [None])[0]
        stack = query.get("stack", [None])[0]

        try:
            self.send_json({
                "ok": True,
                "message": run_control(command, stack),
            })
        except ValueError as error:
            self.send_json({"error": str(error)}, 400)
        except Exception as error:
            self.send_json({"error": str(error)}, 500)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")


if __name__ == "__main__":
    if not os.path.exists(CONTROL):
        raise SystemExit(f"Control script not found: {CONTROL}")

    print(f"RPI Server UI listening on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()

#!/usr/bin/env python3

import json
from pathlib import Path
import base64
from pathlib import Path
import os
from pathlib import Path
import subprocess
from pathlib import Path
import urllib.parse
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"
PORT = 8080
CONTROL = "/srv/scripts/server.sh"


HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RPI Server</title>

<style>
:root {
    color-scheme: dark;
    --bg: #0f1115;
    --panel: #181b22;
    --panel2: #20242d;
    --border: #303642;
    --text: #f1f3f5;
    --muted: #9ba3af;
    --green: #35c759;
    --red: #ff453a;
    --yellow: #ffd60a;
    --blue: #0a84ff;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Roboto,
        sans-serif;
}

header {
    padding: 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

h1 {
    margin: 0;
    font-size: 24px;
}

.subtitle {
    color: var(--muted);
    font-size: 13px;
    margin-top: 4px;
}

#updated {
    color: var(--muted);
    font-size: 12px;
}

main {
    max-width: 1100px;
    margin: auto;
    padding: 24px;
}

.process-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 18px;
}

.process-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.process-table th {
    text-align: left;
    color: var(--muted);
    font-size: 11px;
    font-weight: 600;
    padding: 8px;
    border-bottom: 1px solid var(--border);
}

.process-table td {
    padding: 8px;
    border-bottom: 1px solid var(--border);
}

.process-table td:last-child,
.process-table th:last-child {
    text-align: right;
}

@media (max-width: 800px) {
    .process-grid {
        grid-template-columns: 1fr;
    }
}

.system-card {
    margin-bottom: 24px;
}

.system-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 10px;
}

.system-stat {
    background: var(--panel2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
}

.system-stat-label {
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 6px;
}

.system-stat-value {
    font-size: 20px;
    font-weight: 700;
}

.system-stat-detail {
    color: var(--muted);
    font-size: 11px;
    margin-top: 4px;
}

.global-actions {
    display: flex;
    gap: 10px;
    margin-bottom: 24px;
    flex-wrap: wrap;
}

button {
    border: 0;
    border-radius: 9px;
    padding: 11px 16px;
    color: white;
    font-weight: 600;
    cursor: pointer;
    background: var(--panel2);
}

button:hover {
    filter: brightness(1.15);
}

button:disabled {
    opacity: .5;
    cursor: wait;
}

.start {
    background: #1d8f3d;
}

.stop {
    background: #b8322b;
}

.restart {
    background: #a57900;
}

.card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    margin-bottom: 18px;
    overflow: hidden;
}

.card-header {
    padding: 18px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--border);
}

.card-title {
    font-size: 18px;
    font-weight: 700;
}

.status {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--muted);
}

.dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--muted);
}

.dot.running {
    background: var(--green);
    box-shadow: 0 0 8px rgba(53,199,89,.6);
}

.dot.stopped {
    background: var(--red);
}

.dot.warning {
    background: var(--yellow);
}

.card-body {
    padding: 18px 20px;
}

.actions {
    display: flex;
    gap: 8px;
    margin-bottom: 18px;
}

.containers {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 10px;
}

.container {
    background: var(--panel2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 13px;
}

.container-name {
    font-weight: 600;
    margin-bottom: 7px;
}

.container-info {
    font-size: 12px;
    color: var(--muted);
    line-height: 1.5;
}

.log {
    background: #090a0d;
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px;
    font-family: monospace;
    font-size: 12px;
    white-space: pre-wrap;
    max-height: 180px;
    overflow: auto;
    color: #c9d1d9;
}

footer {
    text-align: center;
    color: var(--muted);
    font-size: 11px;
    padding: 20px;
}

@media (max-width: 600px) {
    main {
        padding: 14px;
    }

    header {
        padding: 18px;
    }

    .actions,
    .global-actions {
        flex-direction: column;
    }

    button {
        width: 100%;
    }
}
</style>
</head>

<body>

<header>
    <div>
        <h1>RPI Server</h1>
        <div class="subtitle">Docker stack control</div>
    </div>
    <div id="updated">Loading...</div>
</header>

<main>

    <div class="global-actions">
        <button class="start" onclick="action('start','all')">
            ▶ Start All
        </button>

        <button class="stop" onclick="confirmAction('stop','all')">
            ■ Stop All
        </button>

        <button class="restart" onclick="confirmAction('restart','all')">
            ↻ Restart All
        </button>
    </div>

    <section class="card system-card">

        <div class="card-header">
            <div class="card-title">System</div>
        </div>

        <div class="card-body">
            <div id="system" class="system-grid">
                <div class="system-stat">
                    <div class="system-stat-label">Loading</div>
                    <div class="system-stat-value">—</div>
                </div>
            </div>
        </div>

    </section>

    <div id="stacks"></div>

    <section class="card">

        <div class="card-header">
            <div class="card-title">Processes</div>
        </div>

        <div class="card-body">

            <div class="process-grid">

                <div>
                    <h3>Linux Processes</h3>
                    <table class="process-table">
                        <thead>
                            <tr>
                                <th>Process</th>
                                <th>PID</th>
                                <th>RAM</th>
                            </tr>
                        </thead>
                        <tbody id="processes">
                            <tr>
                                <td colspan="3">Loading...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div>
                    <h3>Activity</h3>
    <div id="log" class="log">Ready.</div>

</main>

<footer>
    RPI Server Control
</footer>

<script>

const stackNames = {
    download: "Download Stack",
    arr: "ARR Stack"
};

function esc(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function log(message) {
    const el = document.getElementById("log");
    const now = new Date().toLocaleTimeString();
    el.textContent = `[${now}] ${message}\n` + el.textContent;
}

function confirmAction(command, stack) {
    const label = stack === "all"
        ? "all stacks"
        : stackNames[stack];

    if (confirm(`${command.toUpperCase()} ${label}?`)) {
        action(command, stack);
    }
}

async function action(command, stack) {

    document.querySelectorAll("button").forEach(b => b.disabled = true);

    log(`${command} ${stack}...`);

    try {
        const response = await fetch(
            `/api/action?command=${encodeURIComponent(command)}&stack=${encodeURIComponent(stack)}`,
            { method: "POST" }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Action failed");
        }

        log(data.message || `${command} ${stack} completed`);

        await loadStatus();

    } catch (error) {
        log(`ERROR: ${error.message}`);
    }

    document.querySelectorAll("button").forEach(b => b.disabled = false);
}

function formatUptime(seconds) {
    if (seconds == null) return "—";

    const days = Math.floor(seconds / 86400);
    seconds %= 86400;

    const hours = Math.floor(seconds / 3600);
    seconds %= 3600;

    const minutes = Math.floor(seconds / 60);

    if (days > 0) {
        return `${days}d ${hours}h`;
    }

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }

    return `${minutes}m`;
}


function renderSystem(system) {

    if (!system) {
        return `
            <div class="system-stat">
                <div class="system-stat-label">System</div>
                <div class="system-stat-value">Unavailable</div>
            </div>
        `;
    }

    const memory = system.memory;
    const disk = system.disk;
    const load = system.load;

    return `
        <div class="system-stat">
            <div class="system-stat-label">CPU</div>
            <div class="system-stat-value">
                ${system.cpu_percent == null ? "—" : esc(system.cpu_percent) + "%"}
            </div>
            <div class="system-stat-detail">
                Load ${load ? esc(load.map(v => v.toFixed(2)).join(" / ")) : "—"}
            </div>
        </div>

        <div class="system-stat">
            <div class="system-stat-label">Temperature</div>
            <div class="system-stat-value">
                ${system.temperature_c == null ? "—" : esc(system.temperature_c) + "°C"}
            </div>
            <div class="system-stat-detail">
                CPU temperature
            </div>
        </div>

        <div class="system-stat">
            <div class="system-stat-label">Memory</div>
            <div class="system-stat-value">
                ${memory ? esc(memory.percent) + "%" : "—"}
            </div>
            <div class="system-stat-detail">
                ${memory
                    ? esc(memory.used_mb) + " / " + esc(memory.total_mb) + " MB"
                    : "Unavailable"}
            </div>

            ${memory ? `
                <div class="system-stat-detail">
                    Available: ${esc(memory.available_mb)} MB
                </div>

                <div class="system-stat-detail">
                    Cache: ${esc(memory.cached_mb)} MB
                </div>

                <div class="system-stat-detail">
                    Swap: ${esc(memory.swap.used_mb)} /
                    ${esc(memory.swap.total_mb)} MB
                    (${esc(memory.swap.percent)}%)
                </div>
            ` : ""}
        </div>

        <div class="system-stat">
            <div class="system-stat-label">Disk</div>
            <div class="system-stat-value">
                ${disk ? esc(disk.percent) + "%" : "—"}
            </div>
            <div class="system-stat-detail">
                ${disk
                    ? esc(disk.used_gb) + " / " + esc(disk.total_gb) + " GB"
                    : "Unavailable"}
            </div>
        </div>

        <div class="system-stat">
            <div class="system-stat-label">Uptime</div>
            <div class="system-stat-value">
                ${formatUptime(system.uptime_seconds)}
            </div>
            <div class="system-stat-detail">
                Since last boot
            </div>
        </div>
    `;
}


function renderProcesses(processes) {

    const el = document.getElementById("processes");

    if (!processes || processes.length === 0) {
        el.innerHTML = `
            <tr>
                <td colspan="3">No process information available.</td>
            </tr>
        `;
        return;
    }

    el.innerHTML = processes.map(process => `
        <tr>
            <td>${esc(process.name)}</td>
            <td>${esc(process.pid)}</td>
            <td>${esc(process.memory_mb)} MB</td>
        </tr>
    `).join("");
}




function renderStack(name, stack) {

    const running = stack.status === "running";
    const healthy = stack.healthy === true;

    let statusClass = "stopped";
    let statusText = "Stopped";

    if (running && healthy) {
        statusClass = "running";
        statusText = "Running";
    } else if (running) {
        statusClass = "warning";
        statusText = "Running / Attention";
    }

    let containers = "";

    for (const [containerName, container] of Object.entries(
        stack.containers || {}
    )) {

        let health = container.health || "none";

        containers += `
            <div class="container">
                <div class="container-name">
                    ${esc(containerName)}
                </div>

                <div class="container-info">
                    Status: ${esc(container.status)}<br>
                    Health: ${esc(health)}<br>
                    Image: ${esc(container.image || "")}
                </div>
            </div>
        `;
    }

    if (!containers) {
        containers = `
            <div class="container">
                <div class="container-info">
                    No containers running.
                </div>
            </div>
        `;
    }

    return `
        <section class="card">

            <div class="card-header">

                <div class="card-title">
                    ${esc(name)}
                </div>

                <div class="status">
                    <span class="dot ${statusClass}"></span>
                    ${statusText}
                </div>

            </div>

            <div class="card-body">

                <div class="actions">

                    <button class="start"
                        onclick="action('start','${esc(name === "Download Stack" ? "download" : "arr")}')">
                        ▶ Start
                    </button>

                    <button class="stop"
                        onclick="confirmAction('stop','${esc(name === "Download Stack" ? "download" : "arr")}')">
                        ■ Stop
                    </button>

                    <button class="restart"
                        onclick="confirmAction('restart','${esc(name === "Download Stack" ? "download" : "arr")}')">
                        ↻ Restart
                    </button>

                </div>

                <div class="containers">
                    ${containers}
                </div>

            </div>

        </section>
    `;
}

async function loadStatus() {

    try {

        const response = await fetch("/api/status", {
            cache: "no-store"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Status request failed");
        }

        document.getElementById("system").innerHTML =
            renderSystem(data.system);

        renderProcesses(data.processes);

        document.getElementById("stacks").innerHTML =
            renderStack(stackNames.download, data.download) +
            renderStack(stackNames.arr, data.arr);

        document.getElementById("updated").textContent =
            "Updated " + new Date().toLocaleTimeString();

    } catch (error) {

        document.getElementById("updated").textContent = "Status error";
        log(`ERROR: ${error.message}`);

    }
}

loadStatus();

setInterval(loadStatus, 5000);

</script>

</body>
</html>
'''


def run_control(command, stack):
    allowed_commands = {"start", "stop", "restart"}
    allowed_stacks = {"download", "arr", "all"}

    if command not in allowed_commands:
        raise ValueError("Invalid command")

    if stack not in allowed_stacks:
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

    # CPU temperature: kernel thermal zone, no subprocess required.
    temp_raw = _read_int("/sys/class/thermal/thermal_zone0/temp")
    stats["temperature_c"] = (
        round(temp_raw / 1000.0, 1)
        if temp_raw is not None
        else None
    )

    # CPU usage from /proc/stat.
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()

        values = list(map(int, line.split()[1:]))
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        total = sum(values)

        previous = getattr(get_system_stats, "_cpu_sample", None)
        get_system_stats._cpu_sample = (total, idle)

        if previous:
            prev_total, prev_idle = previous
            total_delta = total - prev_total
            idle_delta = idle - prev_idle

            if total_delta > 0:
                stats["cpu_percent"] = round(
                    100.0 * (total_delta - idle_delta) / total_delta,
                    1,
                )
            else:
                stats["cpu_percent"] = 0.0
        else:
            stats["cpu_percent"] = None

    except (OSError, ValueError, IndexError):
        stats["cpu_percent"] = None

    # Memory from /proc/meminfo.
    try:
        mem = {}

        with open("/proc/meminfo", "r") as f:
            for line in f:
                key, value = line.split(":", 1)
                mem[key] = int(value.strip().split()[0])

        total_kb = mem["MemTotal"]
        available_kb = mem["MemAvailable"]
        used_kb = total_kb - available_kb

        cached_kb = (
            mem.get("Cached", 0)
            + mem.get("SReclaimable", 0)
            - mem.get("Shmem", 0)
        )

        stats["memory"] = {
            "used_mb": round(used_kb / 1024, 1),
            "total_mb": round(total_kb / 1024, 1),
            "available_mb": round(available_kb / 1024, 1),
            "cached_mb": round(max(cached_kb, 0) / 1024, 1),
            "percent": round(100.0 * used_kb / total_kb, 1),
        }

        # Swap usage
        swap_total_kb = mem.get("SwapTotal", 0)
        swap_free_kb = mem.get("SwapFree", 0)
        swap_used_kb = swap_total_kb - swap_free_kb

        stats["memory"]["swap"] = {
            "used_mb": round(swap_used_kb / 1024, 1),
            "total_mb": round(swap_total_kb / 1024, 1),
            "percent": (
                round(100.0 * swap_used_kb / swap_total_kb, 1)
                if swap_total_kb
                else 0.0
            ),
        }

    except (OSError, ValueError, KeyError, ZeroDivisionError):
        stats["memory"] = None

    # Load average.
    try:
        with open("/proc/loadavg", "r") as f:
            load = f.read().split()

        stats["load"] = [
            float(load[0]),
            float(load[1]),
            float(load[2]),
        ]

    except (OSError, ValueError, IndexError):
        stats["load"] = None

    # Uptime.
    try:
        with open("/proc/uptime", "r") as f:
            uptime = float(f.read().split()[0])

        stats["uptime_seconds"] = int(uptime)

    except (OSError, ValueError, IndexError):
        stats["uptime_seconds"] = None

    # Root filesystem usage.
    try:
        usage = os.statvfs("/")

        total = usage.f_blocks * usage.f_frsize
        free = usage.f_bavail * usage.f_frsize
        used = total - free

        stats["disk"] = {
            "used_gb": round(used / 1024**3, 1),
            "total_gb": round(total / 1024**3, 1),
            "percent": round(100.0 * used / total, 1) if total else 0.0,
        }

    except OSError:
        stats["disk"] = None

    return stats


def get_process_stats(limit=15):
    """Return the top Linux processes by RSS memory."""

    processes = []

    try:
        page_size = os.sysconf("SC_PAGE_SIZE")

        for pid_name in os.listdir("/proc"):
            if not pid_name.isdigit():
                continue

            pid = int(pid_name)

            try:
                with open(f"/proc/{pid}/stat", "r") as f:
                    stat = f.read()

                # Process name is enclosed in parentheses and can contain spaces.
                close = stat.rfind(")")
                if close == -1:
                    continue

                name = stat[stat.find("(") + 1:close]
                fields = stat[close + 2:].split()

                # RSS is field 24 in /proc/<pid>/stat.
                rss_pages = int(fields[21])
                rss_mb = rss_pages * page_size / 1024 / 1024

                processes.append({
                    "pid": pid,
                    "name": name,
                    "memory_mb": round(rss_mb, 1),
                })

            except (OSError, ValueError, IndexError):
                continue

    except OSError:
        return []

    processes.sort(key=lambda x: x["memory_mb"], reverse=True)

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
            result.stderr.strip() or result.stdout.strip() or "Status failed"
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

    header = handler.headers.get("Authorization", "")

    if not header.startswith("Basic "):
        return False

    try:
        decoded = base64.b64decode(
            header[6:],
            validate=True
        ).decode("utf-8")
        supplied_user, supplied_password = decoded.split(":", 1)
    except Exception:
        return False

    return (
        supplied_user == username
        and supplied_password == password
    )


def require_auth(handler):
    if authorized(handler):
        return True

    handler.send_response(401)
    handler.send_header("WWW-Authenticate", 'Basic realm="RPI Server"')
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

    def do_GET(self):

        if not require_auth(self):
            return

        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/":
            payload = HTML.encode()

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()

            self.wfile.write(payload)
            return

        if parsed.path == "/api/status":
            try:
                self.send_json(get_status())
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        self.send_json({"error": "Not found"}, 404)

    def do_POST(self):

        if not require_auth(self):
            return

        parsed = urllib.parse.urlparse(self.path)

        if parsed.path != "/api/action":
            self.send_json({"error": "Not found"}, 404)
            return

        params = urllib.parse.parse_qs(parsed.query)

        command = params.get("command", [None])[0]
        stack = params.get("stack", [None])[0]

        try:
            output = run_control(command, stack)

            self.send_json({
                "ok": True,
                "message": output
            })

        except ValueError as e:
            self.send_json({"error": str(e)}, 400)

        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":

    if not os.path.exists(CONTROL):
        raise SystemExit(f"Control script not found: {CONTROL}")

    print(f"RPI Server UI listening on http://{HOST}:{PORT}")

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()

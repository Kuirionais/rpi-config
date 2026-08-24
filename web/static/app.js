const stackNames = {
    download: "Download Stack",
    arr: "ARR Stack",
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
    const element = document.getElementById("log");
    const time = new Date().toLocaleTimeString();
    element.textContent = `[${time}] ${message}\n` + element.textContent;
}

function setButtonsDisabled(disabled) {
    document.querySelectorAll("button").forEach(button => {
        button.disabled = disabled;
    });
}

function confirmAction(command, stack) {
    const label = stack === "all"
        ? "all stacks"
        : stack === "jdownloader"
            ? "JDownloader"
            : stackNames[stack];

    if (confirm(`${command.toUpperCase()} ${label}?`)) {
        action(command, stack);
    }
}

async function action(command, stack) {
    setButtonsDisabled(true);
    log(`${command} ${stack}...`);

    try {
        const response = await fetch(
            `/api/action?command=${encodeURIComponent(command)}&stack=${encodeURIComponent(stack)}`,
            { method: "POST" }
        );
        const data = await response.json();

        if (!response.ok) {
            throw Error(data.error || "Action failed");
        }

        log(data.message || `${command} ${stack} completed`);
        await loadStatus();
    } catch (error) {
        log(`ERROR: ${error.message}`);
    }

    setButtonsDisabled(false);
}

function uptime(seconds) {
    if (seconds == null) {
        return "—";
    }

    const days = Math.floor(seconds / 86400);
    seconds %= 86400;

    const hours = Math.floor(seconds / 3600);
    seconds %= 3600;

    const minutes = Math.floor(seconds / 60);

    return days
        ? `${days}d ${hours}h`
        : hours
            ? `${hours}h ${minutes}m`
            : `${minutes}m`;
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
                Load ${load ? esc(load.map(value => value.toFixed(2)).join(" / ")) : "—"}
            </div>
        </div>
        <div class="system-stat">
            <div class="system-stat-label">Temperature</div>
            <div class="system-stat-value">
                ${system.temperature_c == null ? "—" : esc(system.temperature_c) + "°C"}
            </div>
            <div class="system-stat-detail">CPU temperature</div>
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
                ${uptime(system.uptime_seconds)}
            </div>
            <div class="system-stat-detail">Since last boot</div>
        </div>
    `;
}

function renderProcesses(processes) {
    const element = document.getElementById("processes");

    if (!processes || !processes.length) {
        element.innerHTML = `
            <tr>
                <td colspan="3">No process information available.</td>
            </tr>
        `;
        return;
    }

    element.innerHTML = processes.map(process => `
        <tr>
            <td>${esc(process.name)}</td>
            <td>${esc(process.pid)}</td>
            <td>${esc(process.memory_mb)} MB</td>
        </tr>
    `).join("");
}

function statusInfo(stack) {
    const running = stack && stack.status === "running";
    const healthy = stack && stack.healthy === true;

    if (running && healthy) {
        return ["running", "Running"];
    }

    if (running) {
        return ["warning", "Running / Attention"];
    }

    return ["stopped", "Stopped"];
}

function renderContainer(name, container) {
    return `
        <div class="container">
            <div class="container-name">${esc(name)}</div>
            <div class="container-info">
                Status: ${esc(container.status)}<br>
                Health: ${esc(container.health || "none")}<br>
                Image: ${esc(container.image || "")}
            </div>
        </div>
    `;
}

function renderContainerList(containers) {
    let html = "";

    for (const [name, container] of Object.entries(containers || {})) {
        html += renderContainer(name, container);
    }

    return html || `
        <div class="container">
            <div class="container-info">No containers running.</div>
        </div>
    `;
}

function renderStack(name, stack) {
    const [statusClass, statusText] = statusInfo(stack);
    const key = name === "Download Stack" ? "download" : "arr";

    return `
        <section class="card">
            <div class="card-header">
                <div class="card-title">${esc(name)}</div>
                <div class="status">
                    <span class="dot ${statusClass}"></span>
                    ${statusText}
                </div>
            </div>
            <div class="card-body">
                <div class="actions">
                    <button class="start" onclick="action('start', '${key}')">
                        ▶ Start
                    </button>
                    <button class="stop" onclick="confirmAction('stop', '${key}')">
                        ■ Stop
                    </button>
                    <button class="restart" onclick="confirmAction('restart', '${key}')">
                        ↻ Restart
                    </button>
                </div>
                <div class="containers">
                    ${renderContainerList(stack && stack.containers)}
                </div>
            </div>
        </section>
    `;
}

function renderJDownloader(stack) {
    const container = stack && stack.containers && stack.containers.jdownloader;
    const running = container && container.status === "running";
    const statusClass = running ? "running" : "stopped";
    const statusText = running ? "Running" : "Stopped";

    return `
        <section class="card">
            <div class="card-header">
                <div class="card-title">JDownloader</div>
                <div class="status">
                    <span class="dot ${statusClass}"></span>
                    ${statusText}
                </div>
            </div>
            <div class="card-body">
                <div class="actions">
                    <button class="start" onclick="action('start', 'jdownloader')">
                        ▶ Start
                    </button>
                    <button class="stop" onclick="confirmAction('stop', 'jdownloader')">
                        ■ Stop
                    </button>
                    <button class="restart" onclick="confirmAction('restart', 'jdownloader')">
                        ↻ Restart
                    </button>
                </div>
                <div class="containers">
                    ${renderContainer(
                        "jdownloader",
                        container || {
                            status: "not created",
                            health: "none",
                            image: "jlesage/jdownloader-2:latest",
                        }
                    )}
                </div>
            </div>
        </section>
    `;
}

async function loadStatus() {
    try {
        const response = await fetch("/api/status", {
            cache: "no-store",
        });
        const data = await response.json();

        if (!response.ok) {
            throw Error(data.error || "Status request failed");
        }

        document.getElementById("system").innerHTML =
            renderSystem(data.system);
        renderProcesses(data.processes);
        document.getElementById("stacks").innerHTML =
            renderStack(stackNames.download, data.download) +
            renderJDownloader(data.jdownloader) +
            renderStack(stackNames.arr, data.arr);
        document.getElementById("updated").textContent =
            "Updated " + new Date().toLocaleTimeString();
    } catch (error) {
        document.getElementById("updated").textContent = "Status error";
        log(`ERROR: ${error.message}`);
    }
}

loadStatus();
setInterval(loadStatus, 15000);

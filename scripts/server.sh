#!/bin/bash

set -u

DOCKER_DIR="/srv/docker"

DOWNLOAD_PROJECT="docker"
DOWNLOAD_COMPOSE="$DOCKER_DIR/download.yaml"

ARR_PROJECT="arrstack"
ARR_COMPOSE="$DOCKER_DIR/arr.yaml"

usage() {
    cat <<EOF_USAGE
Usage: $0 <command> [stack] [--json]

Commands:
  start [stack]       Start a stack or JDownloader
  stop [stack]        Stop a stack or JDownloader
  restart [stack]     Restart a stack or JDownloader
  status [stack]      Show stack/container status

Stacks:
  download            VPN/download stack
  arr                 Sonarr/Radarr stack
  jdownloader         JDownloader container only
  all                 All active stacks

Options:
  --json              Output machine-readable JSON (status only)

Examples:
  $0 start
  $0 start download
  $0 start jdownloader
  $0 stop arr
  $0 stop jdownloader
  $0 restart all
  $0 status
  $0 status arr
  $0 status --json
  $0 status arr --json
EOF_USAGE
}

compose_cmd() {
    local project="$1"
    local compose_file="$2"
    shift 2

    docker compose \
        -p "$project" \
        -f "$compose_file" \
        "$@"
}

start_stack() {
    case "$1" in
        download)
            echo "==> Starting download stack..."
            compose_cmd "$DOWNLOAD_PROJECT" "$DOWNLOAD_COMPOSE" up -d
            ;;

        arr)
            echo "==> Starting ARR stack..."
            compose_cmd "$ARR_PROJECT" "$ARR_COMPOSE" up -d
            ;;

        *)
            echo "Unknown stack: $1" >&2
            return 1
            ;;
    esac
}

stop_stack() {
    case "$1" in
        download)
            echo "==> Stopping download stack..."
            compose_cmd "$DOWNLOAD_PROJECT" "$DOWNLOAD_COMPOSE" down
            ;;

        arr)
            echo "==> Stopping ARR stack..."
            compose_cmd "$ARR_PROJECT" "$ARR_COMPOSE" down
            ;;

        *)
            echo "Unknown stack: $1" >&2
            return 1
            ;;
    esac
}

restart_stack() {
    stop_stack "$1" && start_stack "$1"
}

jdownloader_action() {
    case "$1" in
        start)
            echo "==> Starting JDownloader..."
            compose_cmd "$DOWNLOAD_PROJECT" "$DOWNLOAD_COMPOSE" start jdownloader
            ;;

        stop)
            echo "==> Stopping JDownloader..."
            compose_cmd "$DOWNLOAD_PROJECT" "$DOWNLOAD_COMPOSE" stop jdownloader
            ;;

        restart)
            echo "==> Restarting JDownloader..."
            compose_cmd "$DOWNLOAD_PROJECT" "$DOWNLOAD_COMPOSE" restart jdownloader
            ;;

        *)
            echo "Unknown JDownloader action: $1" >&2
            return 1
            ;;
    esac
}

# Return JSON for one compose project.
#
# We use docker inspect rather than parsing the human-readable
# "docker compose ps" table, so the output is stable for the
# future web UI.
json_stack() {
    local stack="$1"
    local project
    local compose_file

    case "$stack" in
        download)
            project="$DOWNLOAD_PROJECT"
            compose_file="$DOWNLOAD_COMPOSE"
            ;;
        arr)
            project="$ARR_PROJECT"
            compose_file="$ARR_COMPOSE"
            ;;
        *)
            printf '{"error":"unknown stack"}'
            return 1
            ;;
    esac

    # Get all containers belonging to this Compose project directly
    # from Docker. This works for both running and stopped containers.
    local ids
    ids="$(docker ps -aq --filter "label=com.docker.compose.project=$project")"

    if [ -z "$ids" ]; then
        printf '{"status":"stopped","healthy":false,"containers":{}}'
        return 0
    fi

    local inspect_json

    if ! inspect_json="$(docker inspect $ids 2>/dev/null)"; then
        printf '{"error":"docker inspect failed"}'
        return 1
    fi

    python3 - "$stack" "$inspect_json" <<'PYJSON'
import json
import sys

stack = sys.argv[1]
containers_raw = sys.argv[2]

try:
    containers = json.loads(containers_raw)
except json.JSONDecodeError:
    print('{"error":"invalid docker inspect output"}')
    sys.exit(1)

result = {
    "status": "stopped",
    "healthy": False,
    "containers": {}
}

if not containers:
    print(json.dumps(result, separators=(",", ":")))
    sys.exit(0)

running = 0
has_unhealthy = False
has_starting = False

for c in containers:
    name = c.get("Name", "").lstrip("/")
    state = c.get("State", {})
    status = state.get("Status", "unknown")

    health_obj = state.get("Health")
    if health_obj:
        health = health_obj.get("Status", "unknown")
    else:
        health = "none"

    if status == "running":
        running += 1

    if health == "unhealthy":
        has_unhealthy = True
    elif health == "starting":
        has_starting = True

    result["containers"][name] = {
        "status": status,
        "health": health,
        "image": c.get("Config", {}).get("Image", ""),
        "started_at": state.get("StartedAt", "")
    }

total = len(containers)

if running == total and total > 0:
    result["status"] = "running"
    result["healthy"] = not (has_unhealthy or has_starting)
elif running > 0:
    result["status"] = "partial"
    result["healthy"] = False

print(json.dumps(result, separators=(",", ":")))
PYJSON
}

status_stack() {
    case "$1" in
        download)
            echo "===== DOWNLOAD STACK ====="
            compose_cmd "$DOWNLOAD_PROJECT" "$DOWNLOAD_COMPOSE" ps
            ;;

        arr)
            echo "===== ARR STACK ====="
            compose_cmd "$ARR_PROJECT" "$ARR_COMPOSE" ps
            ;;

        *)
            echo "Unknown stack: $1" >&2
            return 1
            ;;
    esac
}

status_json() {
    local stack="$1"

    case "$stack" in
        download|arr)
            printf '{"%s":' "$stack"
            json_stack "$stack"
            printf '}\n'
            ;;

        all)
            printf '{"download":'
            json_stack download
            printf ',"arr":'
            json_stack arr
            printf '}\n'
            ;;

        *)
            echo '{"error":"unknown stack"}'
            return 1
            ;;
    esac
}

# -------------------------
# Argument parsing
# -------------------------

COMMAND="${1:-}"
STACK="all"
JSON=false

if [ -z "$COMMAND" ]; then
    usage
    exit 1
fi

shift

for arg in "$@"; do
    case "$arg" in
        --json)
            JSON=true
            ;;

        download|arr|jdownloader|all)
            STACK="$arg"
            ;;

        *)
            echo "Unknown argument: $arg" >&2
            usage
            exit 1
            ;;
    esac
done

case "$COMMAND" in
    start|stop|restart)
        if [ "$JSON" = true ]; then
            echo "--json is only valid with status" >&2
            exit 1
        fi

        case "$STACK" in
            download|arr)
                case "$COMMAND" in
                    start)
                        start_stack "$STACK"
                        ;;

                    stop)
                        stop_stack "$STACK"
                        ;;

                    restart)
                        restart_stack "$STACK"
                        ;;
                esac
                ;;

            jdownloader)
                jdownloader_action "$COMMAND"
                ;;

            all)
                case "$COMMAND" in
                    start)
                        echo "===== STARTING ALL STACKS ====="
                        start_stack download &&
                        start_stack arr
                        ;;

                    stop)
                        echo "===== STOPPING ALL STACKS ====="
                        stop_stack arr &&
                        stop_stack download
                        ;;

                    restart)
                        echo "===== RESTARTING ALL STACKS ====="
                        stop_stack arr &&
                        stop_stack download &&
                        start_stack download &&
                        start_stack arr
                        ;;
                esac
                ;;

            *)
                echo "Unknown stack: $STACK" >&2
                exit 1
                ;;
        esac
        ;;

    status)
        if [ "$JSON" = true ]; then
            status_json "$STACK"
        else
            case "$STACK" in
                download|arr)
                    status_stack "$STACK"
                    ;;

                all)
                    status_stack download
                    echo
                    status_stack arr
                    ;;

                *)
                    echo "Unknown stack: $STACK" >&2
                    exit 1
                    ;;
            esac
        fi
        ;;

    *)
        usage
        exit 1
        ;;
esac
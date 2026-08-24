#!/bin/bash

set -u

DOCKER_DIR="/srv/docker"

DOWNLOAD_PROJECT="docker"
DOWNLOAD_COMPOSE="$DOCKER_DIR/compose.yaml"

ARR_PROJECT="arrstack"
ARR_COMPOSE="$DOCKER_DIR/Stack.yaml"

usage() {
    cat <<EOF_USAGE
Usage: $0 <command> [stack] [--json]

Commands:
  start [stack]       Start a stack
  stop [stack]        Stop a stack
  restart [stack]     Restart a stack
  status [stack]      Show stack/container status

Stacks:
  download            VPN/download stack
  arr                 Sonarr/Radarr stack
  all                 All active stacks

Options:
  --json              Output machine-readable JSON (status only)

Examples:
  $0 start
  $0 start download
  $0 stop arr
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
            echo '{"error":"unknown stack"}'
            return 1
            ;;
    esac

    local ids
    ids="$(compose_cmd "$project" "$compose_file" ps -aq 2>/dev/null || true)"

    if [ -z "$ids" ]; then
        printf '{"status":"stopped","healthy":false,"containers":{}}'
        return 0
    fi

    local first=1
    local running=0
    local total=0
    local containers=""

    while IFS= read -r id; do
        [ -z "$id" ] && continue

        total=$((total + 1))

        local name
        local state
        local health
        local image
        local started

        name="$(docker inspect --format '{{.Name}}' "$id" 2>/dev/null | sed 's#^/##')"
        state="$(docker inspect --format '{{.State.Status}}' "$id" 2>/dev/null)"
        health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id" 2>/dev/null)"
        image="$(docker inspect --format '{{.Config.Image}}' "$id" 2>/dev/null)"
        started="$(docker inspect --format '{{.State.StartedAt}}' "$id" 2>/dev/null)"

        [ "$state" = "running" ] && running=$((running + 1))

        # JSON escaping using Python if available.
        # Python is present on normal Raspberry Pi OS installations,
        # but fall back to basic escaping if it isn't.
        json_escape() {
            if command -v python3 >/dev/null 2>&1; then
                python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().rstrip("\n")))' <<< "$1"
            else
                printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"
            fi
        }

        local jname jstate jhealth jimage jstarted

        jname="$(json_escape "$name")"
        jstate="$(json_escape "$state")"
        jhealth="$(json_escape "$health")"
        jimage="$(json_escape "$image")"
        jstarted="$(json_escape "$started")"

        if [ "$first" -eq 0 ]; then
            containers+=","
        fi
        first=0

        containers+="
        $jname:{
            \"status\":$jstate,
            \"health\":$jhealth,
            \"image\":$jimage,
            \"started_at\":$jstarted
        }"
    done <<< "$ids"

    local stack_status="stopped"
    local healthy="false"

    if [ "$running" -eq "$total" ] && [ "$total" -gt 0 ]; then
        stack_status="running"
        healthy="true"

        # If a container has an explicit Docker health check and it
        # isn't healthy, the stack isn't considered healthy.
        while IFS= read -r id; do
            [ -z "$id" ] && continue

            local h
            h="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id" 2>/dev/null)"

            if [ "$h" = "unhealthy" ] || [ "$h" = "starting" ]; then
                healthy="false"
            fi
        done <<< "$ids"

    elif [ "$running" -gt 0 ]; then
        stack_status="partial"
    fi

    printf '{'
    printf '"status":"%s",' "$stack_status"
    printf '"healthy":%s,' "$healthy"
    printf '"containers":{%s}' "$containers"
    printf '}'
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

        download|arr|all)
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
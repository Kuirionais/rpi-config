#!/bin/bash

set -u

DOCKER_DIR="/srv/docker"

DOWNLOAD_PROJECT="docker"
DOWNLOAD_COMPOSE="$DOCKER_DIR/compose.yaml"

ARR_PROJECT="arrstack"
ARR_COMPOSE="$DOCKER_DIR/Stack.yaml"

GLUETUN_CONTAINER="gluetun"
GLUETUN_TIMEOUT=120
GLUETUN_INTERVAL=2

usage() {
    cat <<EOF
Usage: $0 <command> [stack]

Commands:
  start [stack]      Start a stack
  stop [stack]       Stop a stack
  restart [stack]    Restart a stack
  status [stack]     Show stack/container status

Stacks:
  download           VPN/download stack
  arr                Sonarr/Radarr stack
  all                All active stacks

Examples:
  $0 start
  $0 start download
  $0 stop arr
  $0 restart all
  $0 status
EOF
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
            echo "ERROR: Unknown stack: $1"
            return 1
            ;;
    esac
}

stop_stack() {
    case "$1" in
        download)
            echo "==> Stopping download stack..."
            compose_cmd "$DOWNLOAD_PROJECT" "$DOWNLOAD_COMPOSE" stop
            ;;

        arr)
            echo "==> Stopping ARR stack..."
            compose_cmd "$ARR_PROJECT" "$ARR_COMPOSE" stop
            ;;

        *)
            echo "ERROR: Unknown stack: $1"
            return 1
            ;;
    esac
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
            echo "ERROR: Unknown stack: $1"
            return 1
            ;;
    esac
}

wait_for_gluetun() {
    local elapsed=0
    local health

    echo
    echo "==> Waiting for Gluetun to become healthy..."

    while (( elapsed < GLUETUN_TIMEOUT )); do
        health="$(
            docker inspect \
                -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' \
                "$GLUETUN_CONTAINER" 2>/dev/null || true
        )"

        case "$health" in
            healthy)
				echo
                echo "==> Gluetun is healthy."
                return 0
                ;;

            unhealthy)
                echo
                echo "ERROR: Gluetun is unhealthy."
                return 1
                ;;

            starting)
                printf "\r    Gluetun: starting (%ss/%ss)" \
                    "$elapsed" "$GLUETUN_TIMEOUT"
                ;;

            no-healthcheck)
                echo
                echo "ERROR: Gluetun does not have a healthcheck."
                return 1
                ;;

            "")
                printf "\r    Gluetun: not running (%ss/%ss)" \
                    "$elapsed" "$GLUETUN_TIMEOUT"
                ;;

            *)
                printf "\r    Gluetun: %-12s (%ss/%ss)" \
                    "$health" "$elapsed" "$GLUETUN_TIMEOUT"
                ;;
        esac

        sleep "$GLUETUN_INTERVAL"
        ((elapsed += GLUETUN_INTERVAL))
    done

    echo
    echo "ERROR: Timed out waiting for Gluetun to become healthy."
    return 1
}

start_all() {
    echo "===== STARTING ALL STACKS ====="

    if ! start_stack download; then
        echo "ERROR: Failed to start download stack."
        return 1
    fi

    if ! wait_for_gluetun; then
        echo "ERROR: ARR stack will NOT be started."
        return 1
    fi

    if ! start_stack arr; then
        echo "ERROR: Failed to start ARR stack."
        return 1
    fi

    echo
    echo "==> All stacks started successfully."
}

stop_all() {
    echo "===== STOPPING ALL STACKS ====="

    # ARR depends on the download/VPN stack, so stop it first.
    if ! stop_stack arr; then
        echo "ERROR: Failed to stop ARR stack."
        return 1
    fi

    if ! stop_stack download; then
        echo "ERROR: Failed to stop download stack."
        return 1
    fi

    echo
    echo "==> All stacks stopped successfully."
}

restart_all() {
    echo "===== RESTARTING ALL STACKS ====="

    if ! stop_stack arr; then
        echo "ERROR: Failed to stop ARR stack."
        return 1
    fi

    if ! stop_stack download; then
        echo "ERROR: Failed to stop download stack."
        return 1
    fi

    if ! start_stack download; then
        echo "ERROR: Failed to start download stack."
        return 1
    fi

    if ! wait_for_gluetun; then
        echo "ERROR: ARR stack will NOT be restarted."
        return 1
    fi

    if ! start_stack arr; then
        echo "ERROR: Failed to start ARR stack."
        return 1
    fi

    echo
    echo "==> All stacks restarted successfully."
}

case "${1:-}" in
    start|stop|restart|status)
        COMMAND="$1"
        STACK="${2:-all}"
        ;;

    *)
        usage
        exit 1
        ;;
esac

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
                stop_stack "$STACK" &&
                start_stack "$STACK"
                ;;

            status)
                status_stack "$STACK"
                ;;
        esac
        ;;

    all)
        case "$COMMAND" in
            start)
                start_all
                ;;

            stop)
                stop_all
                ;;

            restart)
                restart_all
                ;;

            status)
                status_stack download
                echo
                status_stack arr
                ;;
        esac
        ;;

    *)
        echo "ERROR: Unknown stack: $STACK"
        usage
        exit 1
        ;;
esac
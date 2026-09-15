#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$PROJECT_DIR/.supportflow"
PID_FILE="$RUNTIME_DIR/run.pid"
API_PID_FILE="$RUNTIME_DIR/api.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
LOCK_FILE="$RUNTIME_DIR/run.lock"
BACKEND_HOST="${SUPPORTFLOW_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${SUPPORTFLOW_BACKEND_PORT:-8010}"
FRONTEND_HOST="${SUPPORTFLOW_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${SUPPORTFLOW_FRONTEND_PORT:-8510}"
API_PID=""
FRONTEND_PID=""

usage() {
    cat <<'EOF'
Uso: ./run.sh [start|stop|restart]

  start     Inicia FastAPI y Streamlit (opción predeterminada).
  stop      Detiene una ejecución iniciada por este script.
  restart   Detiene la ejecución actual y vuelve a iniciarla.
EOF
}

read_pid() {
    local file="$1"
    local pid=""
    [[ -f "$file" ]] && read -r pid <"$file"
    [[ "$pid" =~ ^[0-9]+$ ]] && printf '%s' "$pid"
}

is_project_supervisor() {
    local pid="$1"
    local process_dir
    [[ -d "/proc/$pid" ]] || return 1
    process_dir="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
    [[ "$process_dir" == "$PROJECT_DIR" ]] || return 1
    tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null | grep -Eq '(^| )([^ ]*/)?run\.sh( |$)'
}

remove_runtime_pids() {
    rm -f "$PID_FILE" "$API_PID_FILE" "$FRONTEND_PID_FILE"
}

stop_project() {
    local pid
    pid="$(read_pid "$PID_FILE" || true)"
    if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null || ! is_project_supervisor "$pid"; then
        remove_runtime_pids
        echo "SupportFlow no está en ejecución."
        return 0
    fi

    echo "Deteniendo SupportFlow (PID $pid)..."
    kill -TERM "$pid"
    for _ in {1..100}; do
        if ! kill -0 "$pid" 2>/dev/null; then
            remove_runtime_pids
            echo "SupportFlow detenido."
            return 0
        fi
        sleep 0.1
    done

    echo "El proceso no terminó a tiempo; forzando la detención." >&2
    local child_pid
    for child_file in "$FRONTEND_PID_FILE" "$API_PID_FILE"; do
        child_pid="$(read_pid "$child_file" || true)"
        if [[ -n "$child_pid" ]] && [[ -d "/proc/$child_pid" ]]; then
            if [[ "$(readlink -f "/proc/$child_pid/cwd" 2>/dev/null || true)" == "$PROJECT_DIR" ]]; then
                kill -TERM "$child_pid" 2>/dev/null || true
            fi
        fi
    done
    kill -KILL "$pid" 2>/dev/null || true
    remove_runtime_pids
}

validate_port() {
    local name="$1"
    local port="$2"
    if [[ ! "$port" =~ ^[0-9]+$ ]] || ((port < 1 || port > 65535)); then
        echo "Error: $name debe ser un puerto entre 1 y 65535." >&2
        exit 1
    fi
}

cleanup() {
    local pid
    for pid in "$FRONTEND_PID" "$API_PID"; do
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
    if [[ "$(read_pid "$PID_FILE" || true)" == "$$" ]]; then
        remove_runtime_pids
    fi
}

if (($# > 1)); then
    usage >&2
    exit 2
fi

COMMAND="${1:-start}"
case "$COMMAND" in
    stop)
        stop_project
        exit 0
        ;;
    restart)
        stop_project
        ;;
    start) ;;
    help | -h | --help)
        usage
        exit 0
        ;;
    *)
        echo "Error: opción desconocida: $COMMAND" >&2
        usage >&2
        exit 2
        ;;
esac

validate_port "SUPPORTFLOW_BACKEND_PORT" "$BACKEND_PORT"
validate_port "SUPPORTFLOW_FRONTEND_PORT" "$FRONTEND_PORT"

if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv no está instalado o no está disponible en PATH." >&2
    exit 1
fi
if ! command -v flock >/dev/null 2>&1; then
    echo "Error: flock no está instalado o no está disponible en PATH." >&2
    exit 1
fi

cd "$PROJECT_DIR"
mkdir -p "$RUNTIME_DIR"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    pid="$(read_pid "$PID_FILE" || true)"
    echo "Error: SupportFlow ya está en ejecución${pid:+ (PID $pid)}." >&2
    echo "Usa './run.sh restart' para reiniciarlo o './run.sh stop' para detenerlo." >&2
    exit 1
fi

printf '%s\n' "$$" >"$PID_FILE"
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

export SUPPORTFLOW_API_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"

echo "Preparando dependencias..."
uv sync --locked

echo "Iniciando FastAPI en ${SUPPORTFLOW_API_URL}..."
uv run uvicorn supportflow.main:app \
    --host "$BACKEND_HOST" \
    --port "$BACKEND_PORT" \
    --workers 1 \
    --no-proxy-headers \
    --no-access-log &
API_PID=$!
printf '%s\n' "$API_PID" >"$API_PID_FILE"

HEALTH_URL="${SUPPORTFLOW_API_URL}/health"
API_READY=false
for _ in {1..50}; do
    if ! kill -0 "$API_PID" 2>/dev/null; then
        echo "Error: FastAPI terminó durante el arranque. Revisa si el puerto está ocupado." >&2
        wait "$API_PID" || true
        exit 1
    fi
    if uv run python -c '
import sys
import urllib.request

try:
    with urllib.request.urlopen(sys.argv[1], timeout=0.3) as response:
        raise SystemExit(0 if response.status == 200 else 1)
except Exception:
    raise SystemExit(1) from None
' "$HEALTH_URL" 2>/dev/null; then
        API_READY=true
        break
    fi
    sleep 0.1
done

if [[ "$API_READY" != true ]]; then
    echo "Error: FastAPI no respondió en ${HEALTH_URL}." >&2
    exit 1
fi

echo "Iniciando Streamlit en http://${FRONTEND_HOST}:${FRONTEND_PORT}..."
uv run streamlit run streamlit_app.py \
    --server.address "$FRONTEND_HOST" \
    --server.port "$FRONTEND_PORT" \
    --server.headless true &
FRONTEND_PID=$!
printf '%s\n' "$FRONTEND_PID" >"$FRONTEND_PID_FILE"

echo
echo "SupportFlow está iniciando:"
echo "  Frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "  API:      ${SUPPORTFLOW_API_URL}"
echo "  Swagger:  ${SUPPORTFLOW_API_URL}/docs"
echo "Presiona Ctrl+C para detener ambos servicios."

wait "$FRONTEND_PID"

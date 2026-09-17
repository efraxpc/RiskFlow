#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
RUNTIME_DIR="$PROJECT_DIR/.riskflow"
PID_FILE="$RUNTIME_DIR/run.pid"
API_PID_FILE="$RUNTIME_DIR/api.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
LOCK_FILE="$RUNTIME_DIR/run.lock"

BACKEND_HOST="${RISKFLOW_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${RISKFLOW_BACKEND_PORT:-8000}"
FRONTEND_HOST="${RISKFLOW_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${RISKFLOW_FRONTEND_PORT:-5173}"

API_PID=""
FRONTEND_PID=""

usage() {
    cat <<'EOF'
Uso: ./run.sh [start|stop|restart]

  start     Instala dependencias e inicia FastAPI y Vite (predeterminado).
  stop      Detiene una ejecución iniciada por este script.
  restart   Detiene la ejecución actual y vuelve a iniciarla.

Variables opcionales:
  RISKFLOW_BACKEND_HOST       Host de FastAPI (127.0.0.1).
  RISKFLOW_BACKEND_PORT       Puerto de FastAPI (8000).
  RISKFLOW_FRONTEND_HOST      Host de Vite (127.0.0.1).
  RISKFLOW_FRONTEND_PORT      Puerto de Vite (5173).
EOF
}

read_pid() {
    local file="$1"
    local pid=""
    [[ -f "$file" ]] && read -r pid <"$file"
    [[ "$pid" =~ ^[0-9]+$ ]] && printf '%s' "$pid"
}

validate_port() {
    local name="$1"
    local port="$2"
    if [[ ! "$port" =~ ^[0-9]+$ ]] || ((port < 1 || port > 65535)); then
        echo "Error: $name debe ser un puerto entre 1 y 65535." >&2
        exit 1
    fi
}

process_uses_directory() {
    local pid="$1"
    local expected_directory="$2"
    [[ -d "/proc/$pid" ]] || return 1
    [[ "$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)" == "$expected_directory" ]]
}

is_project_supervisor() {
    local pid="$1"
    process_uses_directory "$pid" "$PROJECT_DIR" || return 1
    tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null | grep -Eq '(^|/| )run\.sh( |$)'
}

remove_runtime_pids() {
    rm -f "$PID_FILE" "$API_PID_FILE" "$FRONTEND_PID_FILE"
}

stop_recorded_child() {
    local pid_file="$1"
    local expected_directory="$2"
    local expected_command="$3"
    local pid
    pid="$(read_pid "$pid_file" || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        if process_uses_directory "$pid" "$expected_directory" && \
            tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null | grep -Eq "$expected_command"; then
            kill -TERM "$pid" 2>/dev/null || true
        fi
    fi
}

stop_project() {
    local pid
    pid="$(read_pid "$PID_FILE" || true)"

    if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null || ! is_project_supervisor "$pid"; then
        stop_recorded_child "$FRONTEND_PID_FILE" "$FRONTEND_DIR" '(^|/)vite( |$)'
        stop_recorded_child "$API_PID_FILE" "$BACKEND_DIR" '(^|/)uvicorn( |$)'
        remove_runtime_pids
        echo "RiskFlow no está en ejecución."
        return 0
    fi

    echo "Deteniendo RiskFlow (PID $pid)..."
    kill -TERM "$pid"
    for _ in {1..100}; do
        if ! kill -0 "$pid" 2>/dev/null; then
            remove_runtime_pids
            echo "RiskFlow detenido."
            return 0
        fi
        sleep 0.1
    done

    echo "El supervisor no terminó a tiempo; deteniendo sus procesos." >&2
    stop_recorded_child "$FRONTEND_PID_FILE" "$FRONTEND_DIR" '(^|/)vite( |$)'
    stop_recorded_child "$API_PID_FILE" "$BACKEND_DIR" '(^|/)uvicorn( |$)'
    kill -KILL "$pid" 2>/dev/null || true
    remove_runtime_pids
}

cleanup() {
    local pid
    for pid in "$FRONTEND_PID" "$API_PID"; do
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
    if [[ "$(read_pid "$PID_FILE" || true)" == "$$" ]]; then
        remove_runtime_pids
    fi
}

url_is_ready() {
    local url="$1"
    "$BACKEND_DIR/.venv/bin/python" - "$url" <<'PY' 2>/dev/null
import sys
import urllib.request

try:
    with urllib.request.urlopen(sys.argv[1], timeout=0.3) as response:
        raise SystemExit(0 if response.status == 200 else 1)
except Exception:
    raise SystemExit(1) from None
PY
}

wait_for_service() {
    local name="$1"
    local pid="$2"
    local url="$3"
    for _ in {1..100}; do
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "Error: $name terminó durante el arranque. Revisa si el puerto está ocupado." >&2
            return 1
        fi
        if url_is_ready "$url"; then
            return 0
        fi
        sleep 0.1
    done
    echo "Error: $name no respondió en $url." >&2
    return 1
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

validate_port "RISKFLOW_BACKEND_PORT" "$BACKEND_PORT"
validate_port "RISKFLOW_FRONTEND_PORT" "$FRONTEND_PORT"

if [[ "$BACKEND_HOST" == "$FRONTEND_HOST" && "$BACKEND_PORT" == "$FRONTEND_PORT" ]]; then
    echo "Error: backend y frontend no pueden usar el mismo host y puerto." >&2
    exit 1
fi

for required_command in uv npm flock; do
    if ! command -v "$required_command" >/dev/null 2>&1; then
        echo "Error: $required_command no está instalado o no está disponible en PATH." >&2
        exit 1
    fi
done

cd "$PROJECT_DIR"
mkdir -p "$RUNTIME_DIR"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    running_pid="$(read_pid "$PID_FILE" || true)"
    echo "Error: RiskFlow ya está en ejecución${running_pid:+ (PID $running_pid)}." >&2
    echo "Usa './run.sh restart' para reiniciarlo o './run.sh stop' para detenerlo." >&2
    exit 1
fi

printf '%s\n' "$$" >"$PID_FILE"
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "Preparando dependencias del backend..."
(cd "$BACKEND_DIR" && env -u VIRTUAL_ENV uv sync --locked --all-groups)

echo "Preparando dependencias del frontend..."
(cd "$FRONTEND_DIR" && npm ci --no-audit --no-fund)

API_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"
FRONTEND_URL="http://${FRONTEND_HOST}:${FRONTEND_PORT}"
export VITE_RISKFLOW_API_URL="$API_URL"

echo "Iniciando FastAPI en $API_URL..."
(cd "$BACKEND_DIR" && exec "$BACKEND_DIR/.venv/bin/uvicorn" app.main:app \
    --host "$BACKEND_HOST" \
    --port "$BACKEND_PORT" \
    --no-proxy-headers \
    --no-access-log) &
API_PID=$!
printf '%s\n' "$API_PID" >"$API_PID_FILE"

wait_for_service "FastAPI" "$API_PID" "$API_URL/health"

echo "Iniciando Vite en $FRONTEND_URL..."
(cd "$FRONTEND_DIR" && exec "$FRONTEND_DIR/node_modules/.bin/vite" \
    --host "$FRONTEND_HOST" \
    --port "$FRONTEND_PORT" \
    --strictPort) &
FRONTEND_PID=$!
printf '%s\n' "$FRONTEND_PID" >"$FRONTEND_PID_FILE"

wait_for_service "Vite" "$FRONTEND_PID" "$FRONTEND_URL/"

echo
echo "RiskFlow está en ejecución:"
echo "  Frontend: $FRONTEND_URL"
echo "  API:      $API_URL"
echo "  Swagger:  $API_URL/docs"
echo "Presiona Ctrl+C para detener ambos servicios."

wait -n "$API_PID" "$FRONTEND_PID"
echo "Uno de los servicios terminó; cerrando RiskFlow." >&2
exit 1

#!/usr/bin/env bash
# PMTscope 启动/停止脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
VENV_STREAMLIT="$SCRIPT_DIR/.venv/bin/streamlit"
PID_FILE="$SCRIPT_DIR/.pmtscope.pid"
LOG_FILE="$SCRIPT_DIR/pmtscope.log"
HOST="${PMTSCOPE_HOST:-0.0.0.0}"
PORT="${PMTSCOPE_PORT:-8501}"

start() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "PMTscope 已在运行中 (PID: $pid)"
            return 1
        else
            rm -f "$PID_FILE"
        fi
    fi

    echo "正在启动 PMTscope ..."
    nohup "$VENV_STREAMLIT" run "$SCRIPT_DIR/app.py" \
        --server.address "$HOST" \
        --server.port "$PORT" \
        --server.headless true \
        >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 2

    if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "PMTscope 已启动 (PID: $(cat "$PID_FILE"))"
        echo "访问地址: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost'):$PORT"
    else
        echo "启动失败，请查看日志: $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "正在停止 PMTscope (PID: $pid) ..."
            kill "$pid"
            sleep 1
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid"
            fi
            rm -f "$PID_FILE"
            echo "PMTscope 已停止"
        else
            rm -f "$PID_FILE"
            echo "PMTscope 未在运行"
        fi
    else
        echo "PMTscope 未在运行（找不到 PID 文件）"
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "PMTscope 正在运行 (PID: $pid)"
            echo "访问地址: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost'):$PORT"
        else
            echo "PMTscope 未在运行（PID 文件存在但进程不存在）"
            rm -f "$PID_FILE"
        fi
    else
        echo "PMTscope 未在运行"
    fi
}

restart() {
    stop
    sleep 1
    start
}

case "${1:-}" in
    start)   start ;;
    stop)    stop ;;
    restart) restart ;;
    status)  status ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

#!/bin/bash
set -euo pipefail

PROJECT_DIR="/Users/hexianji/Downloads/M20_audio"
PAGE_URL="https://jeffery-ho.github.io/AudioOnDeviceEditor/"
LOG_FILE="/tmp/m20_audio_server.log"
PID_FILE="/tmp/m20_audio_server.pid"
cd "$PROJECT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "错误：未找到 python3。"
  read -r -p "按回车键退出..."
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "错误：未找到 ffmpeg，请先安装（例如 brew install ffmpeg）。"
  read -r -p "按回车键退出..."
  exit 1
fi

echo "启动音频转码服务..."
echo "项目目录: $PROJECT_DIR"
echo "FFmpeg: $(command -v ffmpeg)"
echo ""

if curl -fsS --max-time 2 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
  echo "服务已经在运行。"
else
  if lsof -tiTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "端口 8000 已被其他进程占用，请先处理该进程。"
    exit 1
  fi
  nohup env HOST=127.0.0.1 PORT=8000 FFMPEG_BIN="$(command -v ffmpeg)" python3 server.py >"$LOG_FILE" 2>&1 &
  server_pid=$!
  printf '%s\n' "$server_pid" >"$PID_FILE"
  for _ in 1 2 3 4 5; do
    if curl -fsS --max-time 1 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
      echo "服务已启动，PID: $server_pid"
      break
    fi
    sleep 1
  done
  if ! curl -fsS --max-time 1 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    rm -f "$PID_FILE"
    echo "服务启动失败，请查看日志: $LOG_FILE"
    exit 1
  fi
fi

if command -v open >/dev/null 2>&1; then
  open "$PAGE_URL"
fi

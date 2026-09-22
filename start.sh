#!/usr/bin/env bash
# Token 消耗看板 —— macOS / Linux 启动脚本
set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  Token 消耗看板"
echo "============================================"
echo
echo "浏览器会自动打开，页面上有绿色「实时扫描中」标识即为实时版。"
echo "按 Ctrl+C 停止服务。"
echo

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python

exec "$PY" -m tokenboard "$@"

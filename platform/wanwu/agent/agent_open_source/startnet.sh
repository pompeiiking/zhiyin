#!/bin/bash

# 端口号（根据你服务运行端口修改）
PORT=1990

# 设置日志目录和固定日志文件名
LOG_DIR="./logs"
LOG_FILE="$LOG_DIR/net_search.log"

# 创建日志目录（如果不存在）
mkdir -p "$LOG_DIR"

# 检查端口是否被占用
PID_ON_PORT=$(lsof -t -i:$PORT)

if [ -n "$PID_ON_PORT" ]; then
  echo "端口 $PORT 被占用，尝试杀死进程 $PID_ON_PORT..."
  kill -9 $PID_ON_PORT
  echo "进程 $PID_ON_PORT 已被终止。"
fi

# 启动服务并将输出追加写入固定日志文件
echo "启动 Flask 服务..."
nohup python netsearch_server.py >> "$LOG_FILE" 2>&1 &

# 保存进程 ID 到 pid 文件（可选）
echo $! > net_search.pid

echo "服务已启动，日志写入：$LOG_FILE"
echo "PID: $(cat net_search.pid)"

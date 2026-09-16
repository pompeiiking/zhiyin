#!/bin/bash

# 基础配置
APP_NAME="server_open"               # Flask 应用的模块名（server1.py）
APP_VAR="app"                    # Flask 应用中创建的变量名，如 app = Flask(__name__)
PORT=7258                        # 监听端口
LOG_DIRECTORY="./logs"           # 日志目录
LOG_FILE="${LOG_DIRECTORY}/${APP_NAME}_console.log"
TIMEOUT=300 

# 检查日志目录是否存在
if [ ! -d "$LOG_DIRECTORY" ]; then
  echo "日志目录不存在，正在创建..."
  mkdir -p "$LOG_DIRECTORY"
  echo "日志目录已创建：$LOG_DIRECTORY"
fi

# 检查端口是否被占用
process_ids=$(lsof -ti:$PORT)
if [ -n "$process_ids" ]; then
  echo "端口 ${PORT} 已被占用，正在杀死相关进程..."
  kill $process_ids || kill -9 $process_ids
  sleep 3
  echo "已杀掉端口 ${PORT} 上的进程"
else
  echo "端口 ${PORT} 未被占用"
fi

# 启动 Flask 应用（使用 gunicorn）
echo "启动 Flask 服务..."
gunicorn ${APP_NAME}:${APP_VAR} --bind 0.0.0.0:$PORT --timeout $TIMEOUT --log-level info > "$LOG_FILE" 2>&1 &

# 检查 Flask 服务是否成功启动
sleep 3
if lsof -i:$PORT >/dev/null; then
  echo "Flask 服务成功启动，日志输出到 ${LOG_FILE}"
else
  echo "服务启动失败，端口 ${PORT} 上未找到进程，请检查日志 ${LOG_FILE} 获取更多信息"
fi

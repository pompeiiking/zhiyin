#!/bin/bash  
  
# 运行日志统一写入挂载目录，禁止污染受控的 PAMI 源码快照。
LOGFILE="./logs/minio.log"
  
# 使用nohup在后台运行Flask应用，并将输出重定向到日志文件  
# 注意：将下面的/path/to/your/app.py替换为你的Flask应用脚本的实际路径  

nohup python3 /agent/agent_open_source/minio/minio_open.py > "$LOGFILE" 2>&1 &  
  
echo "Flask app started in the background."

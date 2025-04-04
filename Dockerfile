# 基于Python 3.12官方镜像
FROM python:3.12-slim
# 设置工作目录
WORKDIR /app
# 复制项目文件
COPY . .
# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt
# 启动命令
CMD ["python", "main.py"]
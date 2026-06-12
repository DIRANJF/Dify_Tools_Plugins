FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# poppler-utils 为可选依赖（加密 PDF 降级用），跳过安装以加速构建
# 如需启用，在服务器上手动执行：docker exec -it dify-tools apt-get update && apt-get install -y poppler-utils

COPY requirements.txt .
# 先升级pip，同时关闭进度条
RUN pip3 install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com --progress-bar off
# 再安装业务依赖
RUN pip3 install --no-cache-dir --prefer-binary -r requirements.txt \
-i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com \
--progress-bar off

COPY . .

# 清理可能从宿主机带入的 Windows __pycache__
RUN find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8502/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8502", "--workers", "2"]

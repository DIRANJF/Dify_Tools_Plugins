FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 尝试安装 poppler-utils（加密 PDF 降级用，非必需，失败则跳过）
RUN apt-get update \
    && apt-get install -y poppler-utils || echo "poppler-utils 安装失败，跳过" \
    && rm -rf /var/lib/apt/lists/*

# pip 使用阿里云镜像加速
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt

COPY . .

# 清理可能从宿主机带入的 Windows __pycache__
RUN find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8502/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8502", "--workers", "2"]

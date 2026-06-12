FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 写入阿里云镜像源（直接覆盖，避免 sed 兼容性问题）
RUN echo "Types: deb\nURIs: http://mirrors.aliyun.com/debian\nSuites: trixie trixie-updates\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg" \
    > /etc/apt/sources.list.d/debian.sources \
    && echo "Types: deb\nURIs: http://mirrors.aliyun.com/debian-security\nSuites: trixie-security\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg" \
    >> /etc/apt/sources.list.d/debian.sources

# 安装系统依赖：poppler-utils（pdf2image 降级处理加密 PDF 时需要）
# 禁用 Post-Invoke 钩子避免清理脚本报错
RUN rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# pip 使用阿里云镜像
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt

COPY . .

# 清理可能从宿主机带入的 Windows __pycache__
RUN find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8502/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8502", "--workers", "2"]

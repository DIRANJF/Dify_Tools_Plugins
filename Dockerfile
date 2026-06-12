FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# poppler-utils 为可选依赖（加密 PDF 降级用），跳过安装以加速构建
# 如需启用，在服务器上手动执行：docker exec -it dify-tools apt-get update && apt-get install -y poppler-utils

# ---- 逐个安装依赖，降低单次 pip 的线程占用 ----
# 基础框架
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary fastapi uvicorn[standard] python-multipart pydantic requests \
 && pip install --no-cache-dir --prefer-binary openpyxl \
 && pip install --no-cache-dir --prefer-binary pypdf \
 && pip install --no-cache-dir --prefer-binary Pillow \
 && pip install --no-cache-dir --prefer-binary pdf2image

COPY . .

# 清理可能从宿主机带入的 Windows __pycache__
RUN find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8502/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8502", "--workers", "2"]

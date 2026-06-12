"""
PDF 合并工具 — 核心业务逻辑
从原始 pdfcom 项目迁移并适配，支持：
  - 多个 PDF 文件合并
  - 图片（PNG/JPG/BMP/TIFF/GIF/WebP）转 PDF 后合并
  - 加密/损坏 PDF 自动降级为图片后合并
"""

import io
import os
import tempfile
import shutil
import logging
from typing import Optional

import requests
from pypdf import PdfReader, PdfWriter
from PIL import Image

logger = logging.getLogger("pdf_merge.service")

# 支持的文件扩展名
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "bmp", "tiff", "tif", "gif", "webp"}


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def get_file_type(filename: str) -> str:
    """判断文件类型：'pdf'、'image' 或 'unknown'"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        return "pdf"
    if ext in {"png", "jpg", "jpeg", "bmp", "tiff", "tif", "gif", "webp"}:
        return "image"
    return "unknown"


def is_allowed_file(filename: str) -> bool:
    """检查文件扩展名是否被允许"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_EXTENSIONS


def download_file(url: str, dest_dir: str, filename: Optional[str] = None) -> str:
    """
    从 URL 下载文件到本地目录。
    返回: 本地文件路径
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=120, stream=True)
    resp.raise_for_status()

    # 推断文件名
    if not filename:
        # 从 URL 或 Content-Disposition 提取
        cd = resp.headers.get("Content-Disposition", "")
        if "filename=" in cd:
            filename = cd.split("filename=")[-1].strip('"\' ')
        else:
            filename = url.rsplit("/", 1)[-1].split("?")[0] or "downloaded_file"

    # 如果文件名没有扩展名，尝试从 Content-Type 推断
    if "." not in filename:
        ct = resp.headers.get("Content-Type", "").lower()
        ext_map = {
            "application/pdf": ".pdf",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
            "image/gif": ".gif",
            "image/webp": ".webp",
        }
        for mime, ext in ext_map.items():
            if mime in ct:
                filename += ext
                break

    filepath = os.path.join(dest_dir, filename)
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return filepath


# ---------------------------------------------------------------------------
# PDF 合并核心逻辑
# ---------------------------------------------------------------------------

def _merge_pdf(writer: PdfWriter, pdf_path: str) -> int:
    """将 PDF 文件的页面添加到 writer 中，返回添加的页数"""
    reader = PdfReader(pdf_path)
    for page in reader.pages:
        writer.add_page(page)
    return len(reader.pages)


def _image_to_pdf_page(image_path: str) -> PdfReader:
    """将图片转换为单页 PDF Reader 对象"""
    img = Image.open(image_path)
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="PDF", resolution=150)
    buf.seek(0)
    return PdfReader(buf)


def _pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 150) -> list[str]:
    """
    将 PDF 转为图片（降级方案，用于加密/损坏的 PDF）。
    需要安装 pdf2image 和 poppler。
    """
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(pdf_path, dpi=dpi)
        paths = []
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        for i, img in enumerate(images):
            p = os.path.join(output_dir, f"{base}_p{i+1}.jpg")
            img.convert("RGB").save(p, format="JPEG", quality=95)
            paths.append(p)
        return paths
    except ImportError:
        logger.warning("pdf2image 未安装，无法降级处理加密 PDF")
        raise
    except Exception as e:
        raise RuntimeError(f"PDF 转图片失败: {e}")


def merge_files(
    file_list: list[dict],
    output_path: str,
    temp_dir: Optional[str] = None,
    progress_callback=None,
) -> str:
    """
    合并 PDF 和图片文件。

    Args:
        file_list: [{"path": str, "type": "pdf"|"image"}]
        output_path: 输出 PDF 路径
        temp_dir: 临时目录（用于降级转换）
        progress_callback: fn(current, total, message)

    Returns:
        输出文件路径
    """
    writer = PdfWriter()
    total = len(file_list)

    for idx, info in enumerate(file_list):
        fpath = info["path"]
        ftype = info["type"]

        if progress_callback:
            progress_callback(idx + 1, total, f"处理文件 {idx+1}/{total}")

        try:
            if ftype == "pdf":
                _merge_pdf(writer, fpath)
            elif ftype == "image":
                reader = _image_to_pdf_page(fpath)
                writer.add_page(reader.pages[0])
            else:
                logger.warning(f"跳过不支持的文件: {fpath}")
        except Exception as e:
            # 降级：加密/损坏的 PDF 转图片后合并
            if ftype == "pdf":
                logger.warning(f"PDF 直接合并失败 ({fpath})，尝试降级处理: {e}")
                img_dir = os.path.join(temp_dir or tempfile.mkdtemp(), f"fallback_{idx}")
                os.makedirs(img_dir, exist_ok=True)
                image_paths = _pdf_to_images(fpath, img_dir)
                for ip in image_paths:
                    reader = _image_to_pdf_page(ip)
                    writer.add_page(reader.pages[0])
            else:
                raise

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


# ---------------------------------------------------------------------------
# 高层接口
# ---------------------------------------------------------------------------

def merge_from_urls(
    file_urls: list[str],
    output_dir: Optional[str] = None,
) -> bytes:
    """
    从 URL 列表下载文件并合并为一个 PDF。
    返回: PDF 文件的 bytes

    Args:
        file_urls: 文件下载 URL 列表
        output_dir: 工作目录（默认使用临时目录）
    """
    work_dir = output_dir or tempfile.mkdtemp(prefix="pdf_merge_")
    temp_dir = os.path.join(work_dir, "temp")
    download_dir = os.path.join(work_dir, "downloads")
    output_path = os.path.join(work_dir, "merged.pdf")

    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(download_dir, exist_ok=True)

    try:
        # 下载所有文件
        file_list = []
        for i, url in enumerate(file_urls):
            local_path = download_file(url, download_dir, filename=f"file_{i}")
            if not is_allowed_file(local_path):
                raise ValueError(f"不支持的文件类型: {os.path.basename(local_path)}")
            ftype = get_file_type(local_path)
            file_list.append({"path": local_path, "type": ftype})

        if not file_list:
            raise ValueError("没有有效的文件可合并")

        # 执行合并
        merge_files(file_list, output_path, temp_dir)

        # 读取结果
        with open(output_path, "rb") as f:
            return f.read()

    finally:
        # 清理临时目录
        if not output_dir and os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)


def merge_from_uploads(
    files: list[tuple[str, bytes]],
    output_dir: Optional[str] = None,
) -> bytes:
    """
    从已上传的文件内容合并为一个 PDF。
    返回: PDF 文件的 bytes

    Args:
        files: [(filename, content_bytes), ...]
        output_dir: 工作目录（默认使用临时目录）
    """
    work_dir = output_dir or tempfile.mkdtemp(prefix="pdf_merge_")
    temp_dir = os.path.join(work_dir, "temp")
    upload_dir = os.path.join(work_dir, "uploads")
    output_path = os.path.join(work_dir, "merged.pdf")

    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)

    try:
        file_list = []
        for filename, content in files:
            if not is_allowed_file(filename):
                raise ValueError(f"不支持的文件类型: {filename}")
            fpath = os.path.join(upload_dir, filename)
            with open(fpath, "wb") as f:
                f.write(content)
            ftype = get_file_type(filename)
            file_list.append({"path": fpath, "type": ftype})

        if not file_list:
            raise ValueError("没有有效的文件可合并")

        merge_files(file_list, output_path, temp_dir)

        with open(output_path, "rb") as f:
            return f.read()

    finally:
        if not output_dir and os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)

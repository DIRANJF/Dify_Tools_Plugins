"""
PDF 合并工具 — FastAPI 路由定义
支持两种模式：
  1. URL 模式：传入文件 URL 列表，服务端下载后合并
  2. 文件上传模式：直接上传文件合并
每种模式都有对应的 Base64 返回接口（适配 Dify JSON 工作流）
"""

import io
import base64
import logging
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .service import merge_from_urls, merge_from_uploads

logger = logging.getLogger("pdf_merge")

router = APIRouter()


# ---------------------------------------------------------------------------
# 请求 / 响应模型
# ---------------------------------------------------------------------------

class MergeByUrlRequest(BaseModel):
    file_urls: list[str] = Field(
        ...,
        description="文件下载 URL 列表，支持 PDF 和图片（PNG/JPG/BMP/TIFF/GIF/WebP）",
        min_length=1,
    )


class MergeBase64Response(BaseModel):
    filename: str = Field(default="merged.pdf", description="生成的文件名")
    file_base64: str = Field(..., description="合并后 PDF 文件的 Base64 编码")
    file_size: int = Field(..., description="文件大小（字节）")
    page_count: Optional[int] = Field(default=None, description="合并后的页数")
    message: str = Field(default="合并成功")


class MergeByUrlBase64Request(BaseModel):
    file_urls: list[str] = Field(
        ...,
        description="文件下载 URL 列表",
        min_length=1,
    )


# ---------------------------------------------------------------------------
# 路由：URL 模式
# ---------------------------------------------------------------------------

@router.post(
    "/by-url",
    summary="通过 URL 合并文件（返回文件下载）",
    description="传入多个文件的下载 URL，自动下载并合并为一个 PDF。支持 PDF 和图片混合输入。",
    response_class=StreamingResponse,
)
async def merge_by_url(req: MergeByUrlRequest):
    try:
        result_bytes = merge_from_urls(req.file_urls)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"合并失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"合并 PDF 时出错: {e}")

    return StreamingResponse(
        io.BytesIO(result_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=merged.pdf"},
    )


@router.post(
    "/by-url/base64",
    summary="通过 URL 合并文件（返回 Base64）",
    description="传入多个文件的下载 URL，自动下载并合并为一个 PDF，返回 Base64 编码结果。适用于 Dify 工作流。",
    response_model=MergeBase64Response,
)
async def merge_by_url_base64(req: MergeByUrlBase64Request):
    try:
        result_bytes = merge_from_urls(req.file_urls)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"合并失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"合并 PDF 时出错: {e}")

    # 计算页数
    page_count = None
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(result_bytes))
        page_count = len(reader.pages)
    except Exception:
        pass

    return MergeBase64Response(
        filename="merged.pdf",
        file_base64=base64.b64encode(result_bytes).decode("utf-8"),
        file_size=len(result_bytes),
        page_count=page_count,
        message="合并成功",
    )


# ---------------------------------------------------------------------------
# 路由：文件上传模式
# ---------------------------------------------------------------------------

@router.post(
    "/upload-and-merge",
    summary="上传文件并合并（返回文件下载）",
    description="直接上传多个文件，合并为一个 PDF。支持 PDF 和图片混合输入。",
    response_class=StreamingResponse,
)
async def upload_and_merge(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="没有上传文件")

    file_data = []
    for f in files:
        if not f.filename:
            continue
        content = await f.read()
        file_data.append((f.filename, content))

    if not file_data:
        raise HTTPException(status_code=400, detail="没有有效的文件")

    try:
        result_bytes = merge_from_uploads(file_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"合并失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"合并 PDF 时出错: {e}")

    return StreamingResponse(
        io.BytesIO(result_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=merged.pdf"},
    )


@router.post(
    "/upload-and-merge/base64",
    summary="上传文件并合并（返回 Base64）",
    description="直接上传多个文件，合并为一个 PDF，返回 Base64 编码结果。适用于 Dify 工作流。",
    response_model=MergeBase64Response,
)
async def upload_and_merge_base64(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="没有上传文件")

    file_data = []
    for f in files:
        if not f.filename:
            continue
        content = await f.read()
        file_data.append((f.filename, content))

    if not file_data:
        raise HTTPException(status_code=400, detail="没有有效的文件")

    try:
        result_bytes = merge_from_uploads(file_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"合并失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"合并 PDF 时出错: {e}")

    page_count = None
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(result_bytes))
        page_count = len(reader.pages)
    except Exception:
        pass

    return MergeBase64Response(
        filename="merged.pdf",
        file_base64=base64.b64encode(result_bytes).decode("utf-8"),
        file_size=len(result_bytes),
        page_count=page_count,
        message="合并成功",
    )

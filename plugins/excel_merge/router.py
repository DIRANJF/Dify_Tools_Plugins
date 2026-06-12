"""
Excel 合并工具 — FastAPI 路由定义
"""

import io
import base64
import logging

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .service import merge_excel_files

logger = logging.getLogger("excel_merge")

router = APIRouter()


# ---------------------------------------------------------------------------
# 请求 / 响应模型
# ---------------------------------------------------------------------------

class MergeRequest(BaseModel):
    file1_url: str = Field(..., description="模板 Excel 文件的下载 URL（前两行为表头）")
    file2_url: str = Field(..., description="数据源 Excel 文件的下载 URL（第一行为字段名）")


class MergeBase64Response(BaseModel):
    filename: str = Field(default="merged_output.xlsx", description="生成的文件名")
    file_base64: str = Field(..., description="合并后 Excel 文件的 Base64 编码")
    file_size: int = Field(..., description="文件大小（字节）")
    message: str = Field(default="合并成功")


class ErrorResponse(BaseModel):
    error: str
    code: int


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@router.post(
    "",
    summary="合并两个 Excel 文件（返回文件下载）",
    description="通过两个文件 URL 获取 Excel 文件，将文件2的数据按照字段映射关系填充到文件1的表头模板下，自动生成合计行，返回合并后的新 Excel 文件。",
    response_class=StreamingResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def merge_excel_file(req: MergeRequest):
    try:
        result_bytes = merge_excel_files(req.file1_url, req.file2_url)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"下载文件失败: {e}")
    except Exception as e:
        logger.error(f"合并失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理 Excel 文件时出错: {e}")

    return StreamingResponse(
        io.BytesIO(result_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=merged_output.xlsx"},
    )


@router.post(
    "/base64",
    summary="合并两个 Excel 文件（返回 Base64）",
    description="返回 Base64 编码的合并文件，适用于工作流中需要 JSON 格式输出的场景。",
    response_model=MergeBase64Response,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def merge_excel_file_base64(req: MergeRequest):
    try:
        result_bytes = merge_excel_files(req.file1_url, req.file2_url)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"下载文件失败: {e}")
    except Exception as e:
        logger.error(f"合并失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理 Excel 文件时出错: {e}")

    return MergeBase64Response(
        filename="merged_output.xlsx",
        file_base64=base64.b64encode(result_bytes).decode("utf-8"),
        file_size=len(result_bytes),
        message="合并成功",
    )

"""
示例插件 — FastAPI 路由定义

创建新插件步骤：
1. 复制 _example_plugin 目录，重命名为你的工具名（如 pdf_tool）
2. 修改 meta.json 中的 name、prefix 等信息
3. 在 router.py 中定义你的 API 路由
4. （可选）创建 schema.json 作为 Dify 的 OpenAPI Schema
5. 重启服务，新插件会被自动加载
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


class ExampleRequest(BaseModel):
    input_text: str = Field(..., description="输入文本")


class ExampleResponse(BaseModel):
    result: str = Field(..., description="处理结果")
    message: str = Field(default="处理成功")


@router.post(
    "",
    summary="示例接口",
    description="这是一个示例接口，替换为你的实际业务逻辑。",
    response_model=ExampleResponse,
)
async def process(req: ExampleRequest):
    # TODO: 替换为你的实际处理逻辑
    result = f"已处理: {req.input_text}"
    return ExampleResponse(result=result, message="处理成功")

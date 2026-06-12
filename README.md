# Dify 工具集 — 插件式服务

一个服务承载所有 Dify 自定义工具，新增工具只需往 `plugins/` 目录丢文件，主代码零改动。

## 项目结构

```
dify-tools/
├── main.py                          # 主入口，自动扫描并加载插件
├── plugins/
│   ├── excel_merge/                 # Excel 合并工具
│   │   ├── meta.json
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── schema.json
│   │   └── __init__.py
│   ├── pdf_merge/                   # PDF 合并工具
│   │   ├── meta.json
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── schema.json
│   │   └── __init__.py
│   └── _example_plugin/             # 插件模板（复制此目录创建新插件）
│       ├── meta.json
│       ├── router.py
│       └── __init__.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 已实现的工具

### 1. Excel 合并工具 (`excel_merge`)

根据模板表头将源数据填充生成新 Excel 文件，支持自动合计计算。

| 端点 | 说明 |
|------|------|
| `POST /api/v1/excel/merge` | 合并两个 Excel 文件（返回文件下载） |
| `POST /api/v1/excel/merge/base64` | 合并两个 Excel 文件（返回 Base64） |

### 2. PDF 合并工具 (`pdf_merge`)

将多个 PDF 和图片合并为一个 PDF 文件，支持 URL 模式和文件上传模式，加密 PDF 自动降级处理。

| 端点 | 说明 |
|------|------|
| `POST /api/v1/pdf/merge/by-url` | 通过 URL 合并文件（返回文件下载） |
| `POST /api/v1/pdf/merge/by-url/base64` | 通过 URL 合并文件（返回 Base64） |
| `POST /api/v1/pdf/merge/upload-and-merge` | 上传文件并合并（返回文件下载） |
| `POST /api/v1/pdf/merge/upload-and-merge/base64` | 上传文件并合并（返回 Base64） |

## 快速启动

### Docker（推荐）

```bash
cd dify-tools
docker compose up -d --build
```

### 本地运行

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

## 新增工具（3 步完成）

### 第 1 步：复制插件模板

```bash
cp -r plugins/_example_plugin plugins/your_tool_name
```

> 注意：目录名不要以 `_` 开头，否则会被跳过。

### 第 2 步：编辑三个文件

**meta.json** — 插件元数据：
```json
{
  "name": "你的工具名称",
  "version": "1.0.0",
  "description": "工具功能描述",
  "prefix": "/api/v1/your-tool-name"
}
```

**router.py** — 定义 API 路由：
```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class YourRequest(BaseModel):
    input_data: str

@router.post("", summary="你的接口")
async def your_endpoint(req: YourRequest):
    return {"result": "处理完成"}
```

**schema.json**（可选）— Dify 的 OpenAPI Schema，用于在 Dify 中创建自定义工具。

### 第 3 步：重启服务

```bash
docker compose restart
```

如果使用了 volume 挂载（docker-compose.yml 中已默认配置），只需重启容器即可，无需重新构建镜像。

## 管理接口

| 端点 | 说明 |
|------|------|
| `GET /health` | 健康检查，返回已加载插件数量 |
| `GET /api/v1/tools` | 列出所有已加载的工具 |
| `GET /api/v1/tools/{id}/schema` | 获取指定工具的 Dify Schema |
| `GET /docs` | FastAPI 自动生成的 Swagger 文档 |

## Dify 配置

1. 打开 Dify 的「创建自定义工具」
2. 将对应插件目录下的 `schema.json` 内容粘贴到 Schema 输入框
3. 替换 `servers.url` 为实际服务地址
4. 保存即可在工作流中使用

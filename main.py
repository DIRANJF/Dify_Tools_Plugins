"""
Dify 工具集 — 插件式服务主入口
自动扫描 plugins/ 目录，发现并注册所有工具插件。
新增工具只需在 plugins/ 下添加目录，无需修改本文件。
"""

import os
import sys
import json
import shutil
import importlib
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dify-tools")

# ---------------------------------------------------------------------------
# 清理残留的 __pycache__（防止 Windows 编译的 .pyc 在 Linux 容器中出错）
# ---------------------------------------------------------------------------
def _clean_pycache(root: Path):
    for pycache in root.rglob("__pycache__"):
        try:
            shutil.rmtree(pycache)
            logger.debug(f"已清理: {pycache}")
        except Exception:
            pass

_clean_pycache(Path(__file__).parent)

# ---------------------------------------------------------------------------
# 应用初始化
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Dify 工具集",
    description="统一工具服务 — 插件式架构，所有工具自动加载",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 插件注册表（运行时信息）
# ---------------------------------------------------------------------------
PLUGIN_REGISTRY: dict[str, dict] = {}
PLUGIN_ERRORS: dict[str, str] = {}  # 记录加载失败的插件及原因

PLUGINS_DIR = Path(__file__).parent / "plugins"


def load_plugins():
    """
    扫描 plugins/ 目录，自动加载所有插件。
    插件识别规则：
      1. 是一个目录（非 _ 开头）
      2. 包含 meta.json（插件元数据）
      3. 包含 router.py（FastAPI 路由模块）
    """
    if not PLUGINS_DIR.exists():
        logger.warning(f"插件目录不存在: {PLUGINS_DIR}")
        return

    # 清除 importlib 缓存，避免旧字节码干扰
    importlib.invalidate_caches()

    for item in sorted(PLUGINS_DIR.iterdir()):
        # 跳过非目录、隐藏目录、__pycache__
        if not item.is_dir() or item.name.startswith(("_", ".")):
            continue

        meta_file = item / "meta.json"
        router_file = item / "router.py"

        if not meta_file.exists():
            logger.debug(f"跳过 {item.name}: 缺少 meta.json")
            continue
        if not router_file.exists():
            logger.debug(f"跳过 {item.name}: 缺少 router.py")
            continue

        try:
            # 读取元数据
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            plugin_name = meta.get("name", item.name)
            plugin_prefix = meta.get("prefix", f"/api/v1/{item.name}")

            # 动态导入路由模块
            module_path = f"plugins.{item.name}.router"
            module = importlib.import_module(module_path)

            # 获取 router 对象
            if not hasattr(module, "router"):
                err = "router.py 缺少 'router' 变量"
                logger.error(f"插件 {plugin_name}: {err}")
                PLUGIN_ERRORS[item.name] = err
                continue

            router = module.router

            # 注册路由
            app.include_router(
                router,
                prefix=plugin_prefix,
                tags=[plugin_name],
            )

            # 记录注册信息
            PLUGIN_REGISTRY[item.name] = {
                "name": plugin_name,
                "version": meta.get("version", "0.1.0"),
                "description": meta.get("description", ""),
                "prefix": plugin_prefix,
                "meta": meta,
            }

            logger.info(f"[已加载] {plugin_name} v{meta.get('version', '?')} → {plugin_prefix}")

        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}"
            logger.error(f"[加载失败] {item.name}: {err_msg}", exc_info=True)
            PLUGIN_ERRORS[item.name] = err_msg

    logger.info(f"插件加载完成: 成功 {len(PLUGIN_REGISTRY)}, 失败 {len(PLUGIN_ERRORS)}")


# 启动时加载所有插件
load_plugins()


# ---------------------------------------------------------------------------
# 全局路由
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """健康检查"""
    result = {
        "status": "ok" if not PLUGIN_ERRORS else "degraded",
        "plugins_loaded": len(PLUGIN_REGISTRY),
        "plugins": list(PLUGIN_REGISTRY.keys()),
    }
    if PLUGIN_ERRORS:
        result["plugin_errors"] = PLUGIN_ERRORS
    return result


@app.get("/api/v1/tools")
async def list_tools():
    """列出所有已加载的工具"""
    return {
        "total": len(PLUGIN_REGISTRY),
        "tools": [
            {
                "id": pid,
                "name": info["name"],
                "version": info["version"],
                "description": info["description"],
                "prefix": info["prefix"],
            }
            for pid, info in PLUGIN_REGISTRY.items()
        ],
    }


@app.get("/api/v1/tools/{tool_id}/schema")
async def get_tool_schema(tool_id: str):
    """获取指定工具的 Dify OpenAPI Schema（如果存在）"""
    if tool_id not in PLUGIN_REGISTRY:
        return JSONResponse(status_code=404, content={"error": f"工具 {tool_id} 不存在"})

    schema_file = PLUGINS_DIR / tool_id / "schema.json"
    if not schema_file.exists():
        return JSONResponse(status_code=404, content={"error": "未找到该工具的 Schema 文件"})

    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    return schema

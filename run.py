import sys
import time
import signal
import socket
import logging
import traceback

logger = logging.getLogger("dify-tools-runner")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logger.addHandler(_handler)

SHUTDOWN_SIGNALS = {signal.SIGTERM, signal.SIGINT}
_received_signal = {"sig": None}


def _signal_handler(sig, frame):
    _received_signal["sig"] = sig
    logger.info(f"[信号] 收到信号 {sig} ({signal.Signals(sig).name if hasattr(signal, 'Signals') else sig}，正在优雅退出...")
    sys.exit(0)


for _sig in SHUTDOWN_SIGNALS:
    try:
        signal.signal(_sig, _signal_handler)
    except Exception:
        pass


def _check_port(host: str, port: int, timeout: float = 5.0) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Dify Tools 服务启动")
    logger.info(f"Python: %s", sys.version.split()[0])
    logger.info(f"PID: %d", __import__('os').getpid())
    logger.info("=" * 60)

    try:
        logger.info("[步骤 1/3] 导入应用（含插件加载...")
        from main import app
        logger.info("[步骤 1/3] ✓ 应用导入完成")

        logger.info("[步骤 2/3] 初始化 uvicorn...")
        import uvicorn
        logger.info(f"[步骤 2/3] ✓ uvicorn 版本: {getattr(uvicorn, '__version__', 'unknown')}")

        logger.info("[步骤 3/3] 启动服务器 (host=0.0.0.0, port=8502)...")

        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8502,
            log_level="info",
            access_log=False,
            limit_concurrency=100,
        )
        server = uvicorn.Server(config)

        logger.info("[启动] uvicorn.Server.run()")
        server.run()

        logger.info("[完成] 服务器正常退出")
        sys.exit(0)

    except SystemExit as e:
        logger.info(f"[退出] SystemExit: code={e.code}")
        sys.exit(e.code if isinstance(e.code, int) else 0)

    except Exception as e:
        logger.error(f"[崩溃] 未捕获异常: {type(e).__name__}: {e}")
        logger.error(f"[崩溃] 堆栈:\n{traceback.format_exc()}")
        sys.exit(1)

    finally:
        logger.info(f"[结束] run.py 执行完毕，退出进程")

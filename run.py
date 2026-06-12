import sys
import traceback
from main import app

try:
    import uvicorn

    if __name__ == "__main__":
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8502,
            limit_concurrency=100,
            access_log=False,
            log_level="info",
        )
        server = uvicorn.Server(config)
        server.run()
except Exception as e:
    print(f"[FATAL] Server crashed with exception: {type(e).__name__}: {e}", flush=True)
    print(f"[FATAL] Traceback:", flush=True)
    traceback.print_exc(file=sys.stdout)
    sys.exit(1)

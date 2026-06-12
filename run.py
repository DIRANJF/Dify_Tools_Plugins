import asyncio
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
        )
        server = uvicorn.Server(config)
        server.run()
except ImportError:
    print("uvicorn not installed, please install requirements.txt first")

import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8502,
        log_level="info",
        access_log=False,
        limit_concurrency=100,
    )

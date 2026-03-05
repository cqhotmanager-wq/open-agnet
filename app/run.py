# 使用配置文件中的 server.port / server.host 启动服务：python -m app

import uvicorn

from app.core.config import load_config

if __name__ == "__main__":
    config = load_config()
    uvicorn.run(
        "app.main:app",
        host=config.server.host,
        port=config.server.port,
        reload=True,
    )

from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# 优先在后端目录加载环境文件，确保路由依赖的设置已生效
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env", override=False)
load_dotenv(find_dotenv(), override=False)

from fastapi import FastAPI
from src.settings import APP_HOST, APP_PORT
from router.weaviate import router as weaviate_router
from router.rag import router as rag_router
from router.compare import router as compare_router
from src.storage import init_storage_and_db


app = FastAPI(
    title="一致性检查",
    description="一致性检查后端 API",
    version="1.0.0",
)

# 初始化SQLite数据库
@app.on_event("startup")
async def _startup_init():
    db_path = init_storage_and_db()
    print(f"[startup] storage initialized; sqlite db: {db_path}")

app.include_router(weaviate_router)
app.include_router(rag_router)
app.include_router(compare_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=APP_HOST,
        port=APP_PORT,
    )

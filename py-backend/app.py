from fastapi import FastAPI
from router.weaviate import router as weaviate_router
from router.rag import router as rag_router
from router.compare import router as compare_router
from src.storage import init_storage_and_db

DEFAULT_SILICONFLOW_API_TOKEN = "sk-dybroxxstjaxkyrnevsqdjikzardzzsppbvwbmimrflpoyfj"
DEFAULT_OUTPUT_DIR = "E:/MyProjects/policy-consistency-check/py-backend/output"

app = FastAPI(
    title="一致性检查",
    description="一致性检查后端 API",
    version="1.0.0",
)

# 应用启动时初始化存储目录与SQLite数据库
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
        host="0.0.0.0",
        port=10010,
    )

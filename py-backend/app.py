from typing import Any, Dict, Optional

import os
import shutil
import tempfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from api.difyApi import dify_get_file_content
from api.embeddingApi import DEFAULT_EMBEDDING_MODEL, get_embeddings_from_siliconflow
from router.weaviate import router as weaviate_router
from src.doc_structure_recognition import build_segments_struct, format_segments_output
from src.pydantic_models import *
from src.utils import build_toc, save_segments2csv
from src.storage import init_storage_and_db
from src.storage import persist_parsed_document

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


@app.post("/api/extract-segments", response_model=DocumentTOCResponse)
async def extract_document_segments(
    file: UploadFile = File(...),
    save: bool = Form(False),
    persist: bool = Form(False),
    collection_name: Optional[str] = Form(None),
):
    """上传文档并提取段落结构。"""
    temp_file_path: Optional[str] = None

    try:
        allowed_extensions = [".txt", ".pdf", ".docx", ".md"]
        file_extension = os.path.splitext(file.filename)[1].lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_extension}。支持的格式: {', '.join(allowed_extensions)}",
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        file_content, key_words = dify_get_file_content(temp_file_path)

        if not file_content:
            raise HTTPException(
                status_code=500,
                detail="文档内容提取失败，请检查文件格式或 Dify 服务状态。",
            )

        file_struct = build_segments_struct(
            file_content=file_content,
            file_name=file.filename,
        )
        segments = file_struct.get("segments", [])

        if not segments:
            raise HTTPException(
                status_code=422,
                detail="未能从文档中提取到有效的政策条款，请检查文档格式。",
            )

        toc_tree, counts = build_toc(segments)

        formatted_output = format_segments_output(
            file_name=os.path.splitext(file.filename)[0],
            segments=segments,
        )

        response_payload: Dict[str, Any] = {
            "success": True,
            "file": {"name": file.filename},
            "toc": toc_tree,
            "counts": counts,
        }

        if save:
            csv_file_path = save_segments2csv(
                formatted_output,
                file_name=os.path.splitext(file.filename)[0],
                output_dir=DEFAULT_OUTPUT_DIR,
            )
            response_payload["save_path"] = csv_file_path

        if key_words:
            response_payload["keywords"] = key_words

        # 持久化到 storage/docs/<collection>/<doc>/ 及数据库
        if persist:
            try:
                ingest_result = persist_parsed_document(
                    temp_file_path=temp_file_path,
                    filename=file.filename,
                    original_mime=None,
                    file_content=file_content,
                    segments=segments,
                    toc=toc_tree,
                    keywords=key_words,
                    collection_name=collection_name or "policy_documents",
                )
                response_payload.update({
                    "doc_id": ingest_result["doc_id"],
                    "collection_id": ingest_result["collection_id"],
                    "storage": ingest_result["paths"],
                    "chunk_count": ingest_result["chunk_count"],
                })
            except Exception as e:
                response_payload["persist_error"] = str(e)

        return response_payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass


@app.post("/api/embeddings")
async def generate_embeddings(payload: EmbeddingRequest):
    api_token = payload.api_token or DEFAULT_SILICONFLOW_API_TOKEN
    if not api_token:
        raise HTTPException(status_code=400, detail="缺少 SiliconFlow API token")

    model = payload.model or DEFAULT_EMBEDDING_MODEL
    timeout = payload.timeout or 10

    try:
        result = get_embeddings_from_siliconflow(
            inputs=payload.inputs,
            api_token=api_token,
            model=model,
            timeout=timeout,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:  # pragma: no cover - 网络异常等
        raise HTTPException(status_code=502, detail=str(error)) from error

    if not result:
        raise HTTPException(status_code=502, detail="Embedding 服务返回空结果")

    return {
        "success": True,
        "model": model,
        "data": result,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=10010,
    )

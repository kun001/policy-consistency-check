from __future__ import annotations

import json
import os
import shutil
import tempfile
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Query
from pydantic import BaseModel

from api.difyApi import dify_get_file_content
from api.weaivateApi import (
    DEFAULT_COLLECTION_NAME,
    DEFAULT_SILICONFLOW_API_TOKEN,
    DEFAULT_WEAVIATE_API_KEY,
    weaviate_search,
)
from src.doc_structure_recognition import build_segments_struct
from src.utils import build_toc
from src.storage import persist_parsed_document, index_document_chunks, rollback_document_vectors
from src.pydantic_models import WeaviateSearchRequest
from src.storage import CollectionsRepo, DocumentsRepo, ChunksRepo, connect
from pathlib import Path
from src.storage.db import get_storage_root

router = APIRouter(prefix="/api/rag", tags=["rag"])


class IndexDocRequest(BaseModel):
    doc_id: str
    collection_name: Optional[str] = None
    siliconflow_api_token: Optional[str] = None
    weaviate_api_key: Optional[str] = None
    client_params: Optional[Dict[str, Any]] = None
    batch_size: int = 50
    max_retries: int = 2


class RollbackDocRequest(BaseModel):
    doc_id: str
    collection_name: Optional[str] = None
    siliconflow_api_token: Optional[str] = None
    weaviate_api_key: Optional[str] = None
    client_params: Optional[Dict[str, Any]] = None


@router.post("/ingest-and-index")
async def ingest_and_index(
    file: UploadFile = File(...),
    collection_name: Optional[str] = Form(None),
    siliconflow_api_token: Optional[str] = Form(None),
    weaviate_api_key: Optional[str] = Form(None),
    client_params: Optional[str] = Form(None),  # JSON string for client params
    batch_size: int = Form(50),
    max_retries: int = Form(2),
):
    """上传文档→解析持久化→向量化索引，一次完成。

    返回：{
      success, doc_id, collection_id, storage, chunk_count,
      embedding_stats: {attempted, uploaded, failed}
    }
    """
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
            raise HTTPException(status_code=500, detail="文档内容提取失败，请检查文件格式或 Dify 服务状态。")

        file_struct = build_segments_struct(file_content=file_content, file_name=file.filename)
        segments = file_struct.get("segments", [])
        if not segments:
            raise HTTPException(status_code=422, detail="未能从文档中提取到有效的政策条款，请检查文档格式。")

        toc_tree, _counts = build_toc(segments)

        ingest_result = persist_parsed_document(
            temp_file_path=temp_file_path,
            filename=file.filename,
            original_mime=None,
            file_content=file_content,
            segments=segments,
            toc=toc_tree,
            keywords=key_words,
            collection_name=collection_name or DEFAULT_COLLECTION_NAME,
        )

        # 解析 client_params（如果存在）
        client_params_obj: Optional[Dict[str, Any]] = None
        if client_params:
            try:
                client_params_obj = json.loads(client_params)
            except Exception:
                raise HTTPException(status_code=400, detail="client_params 需为合法 JSON 字符串")

        stats = index_document_chunks(
            doc_id=ingest_result["doc_id"],
            collection_name=collection_name or DEFAULT_COLLECTION_NAME,
            siliconflow_api_token=siliconflow_api_token or DEFAULT_SILICONFLOW_API_TOKEN,
            weaviate_api_key=weaviate_api_key or DEFAULT_WEAVIATE_API_KEY,
            client_params=client_params_obj,
            batch_size=batch_size,
            max_retries=max_retries,
        )

        return {
            "success": True,
            "doc_id": ingest_result["doc_id"],
            "collection_id": ingest_result["collection_id"],
            "storage": ingest_result["paths"],
            "chunk_count": ingest_result["chunk_count"],
            "embedding_stats": stats,
        }
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


@router.post("/index-doc-chunks")
async def index_doc_chunks(payload: IndexDocRequest):
    stats = index_document_chunks(
        doc_id=payload.doc_id,
        collection_name=payload.collection_name or DEFAULT_COLLECTION_NAME,
        siliconflow_api_token=payload.siliconflow_api_token or DEFAULT_SILICONFLOW_API_TOKEN,
        weaviate_api_key=payload.weaviate_api_key or DEFAULT_WEAVIATE_API_KEY,
        client_params=payload.client_params,
        batch_size=payload.batch_size,
        max_retries=payload.max_retries,
    )

    return {"success": True, "stats": stats}


@router.post("/rollback-doc-chunks")
async def rollback_doc_chunks(payload: RollbackDocRequest):
    stats = rollback_document_vectors(
        doc_id=payload.doc_id,
        collection_name=payload.collection_name or DEFAULT_COLLECTION_NAME,
        siliconflow_api_token=payload.siliconflow_api_token or DEFAULT_SILICONFLOW_API_TOKEN,
        weaviate_api_key=payload.weaviate_api_key or DEFAULT_WEAVIATE_API_KEY,
        client_params=payload.client_params,
    )

    return {"success": True, "stats": stats}


@router.post("/search")
async def rag_search(payload: WeaviateSearchRequest):
    results = weaviate_search(
        payload.query,
        collection_name=payload.collection_name or DEFAULT_COLLECTION_NAME,
        siliconflow_api_token=payload.siliconflow_api_token or DEFAULT_SILICONFLOW_API_TOKEN,
        weaviate_api_key=payload.weaviate_api_key or DEFAULT_WEAVIATE_API_KEY,
        client_params=payload.client_params,
        limit=payload.limit,
        filter_conditions=payload.filter_conditions,
        filters=payload.filters,
    )

    return {
        "success": True,
        "query": payload.query,
        "count": len(results),
        "contexts": results,
    }


# 从SQLite列出文档与分段
@router.get("/documents")
async def list_documents(collection_name: Optional[str] = Query(None)):
    """列出指定集合的所有文档。默认集合为 DEFAULT_COLLECTION_NAME。"""
    target_name = collection_name or DEFAULT_COLLECTION_NAME
    conn = connect()
    c_repo = CollectionsRepo(conn)
    # 确保集集合存在，便于无数据时也能返回合元信息
    collection = c_repo.ensure(name=target_name, provider="weaviate", config=None, is_active=1)
    d_repo = DocumentsRepo(conn)
    documents = d_repo.list_by_collection(collection_id=collection["id"]) or []
    return {
        "success": True,
        "dataset": {"id": collection["id"], "name": collection["name"], "provider": collection.get("provider")},
        "documents": documents,
        "total": len(documents),
    }


@router.get("/documents/{doc_id}/chunks")
async def list_chunks_by_doc(doc_id: str):
    """按 doc_id 列出分段（chunks），映射为前端 PolicyDetail 所需字段。"""
    conn = connect()
    ch_repo = ChunksRepo(conn)
    chunks = ch_repo.list_by_doc(doc_id) or []

    def _status_map(embedding_status: Optional[str]) -> str:
        if embedding_status == "embedded":
            return "completed"
        if embedding_status == "failed":
            return "error"
        return "processing"

    segments = []
    for ch in chunks:
        content = ch.get("content") or ""
        segments.append({
            "id": ch.get("id"),
            "position": int(ch.get("chunk_index") or 0),
            "status": _status_map(ch.get("embedding_status")),
            "enabled": True,
            "content": content,
            "word_count": len(content),
            "tokens": ch.get("token_count") or 0,
            "created_at": ch.get("created_at"),
            "updated_at": ch.get("updated_at"),
        })

    return {
        "success": True,
        "doc_id": doc_id,
        "data": segments,
        "count": len(segments),
    }


@router.get("/documents/{doc_id}/parsed")
async def get_parsed_document(doc_id: str):
    """返回指定文档的解析产物：content、toc、counts、keywords。"""
    conn = connect()
    d_repo = DocumentsRepo(conn)
    doc = d_repo.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")

    try:
        storage_root = get_storage_root()
        # 通过 collection_id 组装路径
        parsed_dir = storage_root / "docs" / str(doc.get("collection_id")) / doc_id / "parsed"
        if not parsed_dir.exists():
            # 回退通过 storage_path 推导
            storage_path_rel = doc.get("storage_path") or ""
            if storage_path_rel:
                raw_file_path = storage_root / storage_path_rel
                doc_dir = raw_file_path.parent.parent if raw_file_path.exists() else None
                if doc_dir:
                    alt_parsed_dir = doc_dir / "parsed"
                    if alt_parsed_dir.exists():
                        parsed_dir = alt_parsed_dir
        if not parsed_dir.exists():
            raise HTTPException(status_code=404, detail="parsed artifacts not found")

        content_text = ""
        toc_tree = None
        keywords = doc.get("keywords")

        # 读取内容
        content_path = parsed_dir / "content.txt"
        if content_path.exists():
            try:
                content_text = content_path.read_text(encoding="utf-8")
            except Exception:
                content_text = content_path.read_text(errors="ignore")

        # 读取分段与 toc
        seg_path = parsed_dir / "segments.json"
        toc_path = parsed_dir / "toc.json"
        if seg_path.exists():
            import json as _json
            with open(seg_path, "r", encoding="utf-8") as f:
                segments_obj = _json.load(f)
            # 动态重建 toc 和计数，避免文件缺失造成问题
            from src.utils import build_toc
            toc_tree, counts = build_toc(segments_obj)
        elif toc_path.exists():
            import json as _json
            with open(toc_path, "r", encoding="utf-8") as f:
                toc_tree = _json.load(f)
            counts = {"chapters": 0, "sections": 0, "articles": 0}
        else:
            toc_tree = {"id": "doc-1", "type": "document", "children": []}
            counts = {"chapters": 0, "sections": 0, "articles": 0}

        return {
            "success": True,
            "doc_id": doc_id,
            "collection_id": doc.get("collection_id"),
            "file": {"name": doc.get("source_filename")},
            "paths": {
                "parsed": str(parsed_dir),
            },
            "content": content_text,
            "toc": toc_tree,
            "counts": counts,
            "keywords": keywords,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
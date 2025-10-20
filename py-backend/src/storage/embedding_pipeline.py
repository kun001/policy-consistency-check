from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID, NAMESPACE_DNS, uuid5

from .repositories import DocumentsRepo, ChunksRepo, CollectionsRepo
from .db import connect

# 通过 API 层的初始化方法获取引擎，避免包路径冲突
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
from api.weaivateApi import _init_engine


def _compute_weaviate_uuid(chunk_id: str, collection_name: str) -> str:
    try:
        return str(UUID(str(chunk_id)))
    except Exception:
        return str(uuid5(NAMESPACE_DNS, f"{collection_name}:{chunk_id}"))


def _build_docs_payload(
    doc_id: str,
    collection_id: str,
    chunks: Sequence[Dict[str, Any]],
    *,
    text_key: str = "content",
    title_key: str = "title",
    metadata_key: str = "metadata",
    collection_name: str,
) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for ch in chunks:
        chunk_id = ch.get("id")
        weav_uuid = _compute_weaviate_uuid(str(chunk_id), collection_name)
        payload: Dict[str, Any] = {
            "id": chunk_id,
            text_key: ch.get("content") or "",
            title_key: ch.get("title") or str(chunk_id),
            metadata_key: {
                "collection_id": collection_id,
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "chunk_index": int(ch.get("chunk_index") or 0),
                "section_path": ch.get("section_path") or [],
            },
            "_weaviate_uuid": weav_uuid,  # 便于回写 weaviate_id
        }
        docs.append(payload)
    return docs


def index_document_chunks(
    doc_id: str,
    *,
    collection_name: str,
    siliconflow_api_token: str,
    weaviate_api_key: Optional[str] = None,
    client_params: Optional[Dict[str, Any]] = None,
    batch_size: int = 50,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """将指定 doc 的 chunks 批量嵌入并写入 Weaviate，失败重试并更新数据库状态。

    返回：{"attempted": int, "uploaded": int, "failed": int}
    """
    conn = connect()
    c_repo = CollectionsRepo(conn)
    d_repo = DocumentsRepo(conn)
    ch_repo = ChunksRepo(conn)

    doc = d_repo.get(doc_id)
    if not doc:
        return {"attempted": 0, "uploaded": 0, "failed": 0, "error": f"Doc {doc_id} not found"}

    collection_id = doc.get("collection_id")
    chunks = ch_repo.list_by_doc(doc_id)
    # 过滤空内容分块
    chunks = [ch for ch in chunks if (ch.get("content") or "").strip()]
    attempted = len(chunks)

    if attempted == 0:
        d_repo.update(doc_id, status="succeeded", parsing_payload={"chunk_count": 0})
        return {"attempted": 0, "uploaded": 0, "failed": 0}

    engine = _init_engine(
        collection_name,
        siliconflow_api_token=siliconflow_api_token,
        client_params=client_params,
        weaviate_api_key=weaviate_api_key,
    )
    if not engine:
        for ch in chunks:
            ch_repo.update(str(ch.get("id")), embedding_status="failed", last_error="init engine failed")
        d_repo.update(doc_id, status="failed")
        return {"attempted": attempted, "uploaded": 0, "failed": attempted}

    uploaded = 0
    failed = 0

    # 构造文档 payload（带上 weaviate uuid 供回写）
    docs = _build_docs_payload(doc_id, collection_id, chunks, collection_name=collection_name)

    # 批次处理带重试
    for start in range(0, len(docs), batch_size):
        batch_docs = docs[start:start + batch_size]
        texts = [d.get("content", "") for d in batch_docs]
        # 嵌入重试
        vectors: Optional[List[List[float]]] = None
        last_error: Optional[str] = None
        for _ in range(max_retries + 1):
            try:
                vectors = engine._embed_texts(texts)
                break
            except Exception as e:
                last_error = str(e)
                time.sleep(0.5)
        if vectors is None:
            failed += len(batch_docs)
            # 标记失败状态
            for d in batch_docs:
                ch_repo.update(str(d["id"]), embedding_status="failed", last_error=last_error)
            continue

        # 上载重试
        ok = False
        for _ in range(max_retries + 1):
            try:
                engine._upsert_with_vectors(
                    vectors=vectors,
                    documents=batch_docs,
                    text_key="content",
                    title_key="title",
                    metadata_key="metadata",
                    batch_size=len(batch_docs),
                )
                ok = True
                break
            except Exception as e:
                last_error = str(e)
                time.sleep(0.5)
        if not ok:
            failed += len(batch_docs)
            for d in batch_docs:
                ch_repo.update(str(d["id"]), embedding_status="failed", last_error=last_error)
            continue

        # 成功：回写 weaviate_id 与状态
        for d in batch_docs:
            ch_repo.update(str(d["id"]), weaviate_id=d["_weaviate_uuid"], embedding_status="embedded", last_error=None)
        uploaded += len(batch_docs)

    # 更新文档状态
    if failed == 0 and uploaded == attempted:
        d_repo.update(doc_id, status="succeeded")
    elif uploaded > 0:
        d_repo.update(doc_id, status="processing")
    else:
        d_repo.update(doc_id, status="failed")

    try:
        engine.close()
    except Exception:
        pass

    return {"attempted": attempted, "uploaded": uploaded, "failed": failed}


def rollback_document_vectors(
    doc_id: str,
    *,
    collection_name: str,
    siliconflow_api_token: str,
    weaviate_api_key: Optional[str] = None,
    client_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """删除指定文档在 Weaviate 的所有向量，并将 chunks 状态回滚为 pending。远端删除失败时仍回滚本地状态。"""
    conn = connect()
    ch_repo = ChunksRepo(conn)
    d_repo = DocumentsRepo(conn)

    chunks = ch_repo.list_by_doc(doc_id)
    if not chunks:
        return {"deleted_remote": 0, "rolled_back": 0}

    engine = _init_engine(
        collection_name,
        siliconflow_api_token=siliconflow_api_token,
        client_params=client_params,
        weaviate_api_key=weaviate_api_key,
    )

    deleted_remote = 0
    for ch in chunks:
        # weaviate_id 可能为空；若为空则按约定计算
        chunk_id = str(ch.get("id"))
        uuid_value = ch.get("weaviate_id") or _compute_weaviate_uuid(chunk_id, collection_name)
        try:
            ok = engine.delete_document_by_id(uuid_value)
            if ok:
                deleted_remote += 1
        except Exception:
            # 忽略远端删除异常
            pass
        # 本地回滚状态
        ch_repo.update(chunk_id, embedding_status="pending", weaviate_id=None, last_error=None)

    d_repo.update(doc_id, status="uploaded")

    try:
        engine.close()
    except Exception:
        pass

    return {"deleted_remote": deleted_remote, "rolled_back": len(chunks)}
from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from tqdm import tqdm
from api.weaivateApi import (
    weaviate_search
)
from api.difyApi import get_diff_analysis_result
from src.storage import connect, DocumentsRepo, ChunksRepo
from src.storage.db import get_storage_root
from pathlib import Path

NATIONAL_DEFAULT_COLLECTION_NAME = "national_policy_documents"

router = APIRouter(prefix="/api/compare", tags=["compare"])


class CompareRequest(BaseModel):
    local_doc_id: str
    national_doc_ids: List[str]
    limit: int = 2  # 每个条款最多返回的国家匹配条款数量
    collection_name: Optional[str] = None


def _read_local_content(doc_id: str, doc: Dict[str, Any]) -> str:
    """读取地方政策全文内容（parsed/content.txt）。若不存在则返回空字符串。"""
    try:
        storage_root = get_storage_root()
        parsed_dir = storage_root / "docs" / str(doc.get("collection_id")) / doc_id / "parsed"
        content_path = parsed_dir / "content.txt"
        if content_path.exists():
            try:
                return content_path.read_text(encoding="utf-8")
            except Exception:
                return content_path.read_text(errors="ignore")
        # fallback 通过 storage_path 反推 parsed 目录
        storage_path_rel = doc.get("storage_path") or ""
        if storage_path_rel:
            raw_file_path = storage_root / storage_path_rel
            doc_dir = raw_file_path.parent.parent if raw_file_path.exists() else None
            if doc_dir:
                alt_content_path = doc_dir / "parsed" / "content.txt"
                if alt_content_path.exists():
                    try:
                        return alt_content_path.read_text(encoding="utf-8")
                    except Exception:
                        return alt_content_path.read_text(errors="ignore")
        return ""
    except Exception:
        return ""


@router.post("/analyze")
async def analyze(payload: CompareRequest):
    """
    针对每个地方条款（chunk），在 Weaviate 中检索相关国家条款，调用 Dify 工作流进行差异分析
    """
    if not payload.local_doc_id:
        raise HTTPException(status_code=400, detail="local_doc_id 为必填参数")
    if not payload.national_doc_ids:
        raise HTTPException(status_code=400, detail="national_doc_ids 为必填参数")

    conn = connect()
    d_repo = DocumentsRepo(conn)
    ch_repo = ChunksRepo(conn)

    local_doc = d_repo.get(payload.local_doc_id)
    if not local_doc:
        raise HTTPException(status_code=404, detail="地方政策文档不存在")

    local_file_name = local_doc.get("source_filename") or payload.local_doc_id
    local_file_content = _read_local_content(payload.local_doc_id, local_doc)

    # 列出地方条款（chunks）
    chunks = ch_repo.list_by_doc(payload.local_doc_id) or []
    if not chunks:
        raise HTTPException(status_code=422, detail="地方政策未找到条款分段")

    clauses: List[Dict[str, Any]] = []
    collection_name = payload.collection_name or NATIONAL_DEFAULT_COLLECTION_NAME

    for ch in tqdm(chunks, desc="处理条款"):
        local_clause_text = ch.get("content") or ""
        chunk_index = int(ch.get("chunk_index") or 0)
        clause_id = f"L-{chunk_index:03d}"

        # 1) 在 Weaviate 中检索相似国家条款
        search_results = weaviate_search(
            query=local_clause_text,
            collection_name=collection_name,
            limit=max(1, payload.limit),
        ) or []
        # 仅保留来自指定国家政策文档的条款
        filtered = [
            r for r in search_results
            if str(r.get("metadata", {}).get("doc_id")) in set(payload.national_doc_ids)
        ]
        # 取前 N 条
        filtered = filtered[: payload.limit]

        # 提供给 Dify 的国家条款原文列表（包含国家文件名与条款）
        nid_set = {str(r.get("metadata", {}).get("doc_id")) for r in filtered}
        nation_docs: Dict[str, str] = {}
        for nid in nid_set:
            doc_rec = d_repo.get(nid)
            nation_docs[nid] = (doc_rec.get("source_filename") if doc_rec else nid)

        nations_segments = [
            {
                "nation_name": nation_docs.get(str(r.get("metadata", {}).get("doc_id")), str(r.get("metadata", {}).get("doc_id"))),
                "clause": r.get("text") or "",
            }
            for r in filtered
        ]

        # 2) 调用 Dify 工作流进行差异分析
        diff_raw = get_diff_analysis_result(
            file_name=local_file_name,
            file_content=local_file_content,
            segment=local_clause_text,
            nations_segments=str(nations_segments),
        )

        # 3) 解析工作流返回（JSON 字符串 or dict）
        diff_type = "无法比较"
        diff_keywords = ""
        analysis_text = ""
        national_clauses: List[Dict[str, str]] = []

        parsed: Optional[Dict[str, Any]] = None
        if isinstance(diff_raw, dict):
            parsed = diff_raw
        elif isinstance(diff_raw, str):
            try:
                parsed = json.loads(diff_raw)
            except Exception:
                parsed = None

        if parsed:
            diff_type = parsed.get("差异类型") or diff_type
            diff_keywords = parsed.get("差异关键词") or diff_keywords
            analysis_text = parsed.get("差异描述") or analysis_text
            sim_list = parsed.get("相似国家条款") or []
            # 规范化为 { nation_name, clause }
            for item in sim_list:
                if isinstance(item, dict):
                    nation_name = item.get("国家政策文件") or ""
                    clause_text = item.get("国家政策条款") or ""
                    if nation_name or clause_text:
                        national_clauses.append({
                            "nation_name": nation_name,
                            "clause": clause_text,
                        })

        # 若工作流未返回国家条款，使用 weaviate 检索结果兜底
        if not national_clauses and filtered:
            for r in filtered:
                nid = str(r.get("metadata", {}).get("doc_id"))
                national_clauses.append({
                    "nation_name": nation_docs.get(nid, nid),
                    "clause": r.get("text") or "",
                })

        clauses.append({
            "id": clause_id,
            "local_clause": local_clause_text,
            "diff_type": diff_type,
            "diff_keywords": diff_keywords or ("无差异" if diff_type == "无差异" else ""),
            "analysis": analysis_text or ("与国家条款一致" if diff_type == "无差异" else ""),
            "national_clauses": national_clauses,
        })

    return {
        "success": True,
        "local_file": local_file_name,
        "clauses": clauses,
    }
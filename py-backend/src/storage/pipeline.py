from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db import ensure_storage_dirs, get_storage_root, connect
from .repositories import CollectionsRepo, DocumentsRepo, ChunksRepo

# MIME 推断（简单映射）
EXT_MIME = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def guess_mime(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return EXT_MIME.get(ext, "application/octet-stream")


def flatten_segments_to_chunks(segments: Any) -> List[Dict[str, Any]]:
    """根据分段结构生成 chunk 列表：title、content、section_path。
    复用 format_segments_output 输出的路径 + 条款文本，解析出章节路径与“第..条”。
    """
    from doc_structure_recognition import format_segments_output

    lines: List[str] = format_segments_output(segments)
    items: List[Dict[str, Any]] = []
    re_article = re.compile(r"^(?:(?P<prefix>.*?))?\s*(?P<title>第[一二三四五六七八九十百千零O0-9０-９]+条)\s*(?P<body>.*)$")

    for idx, line in enumerate(lines):
        text = (line or "").strip()
        m = re_article.match(text)
        if not m:
            # 无法匹配“第..条”的情况，作为纯文本条款处理
            items.append({
                "chunk_index": idx,
                "title": None,
                "content": text,
                "section_path": [],
            })
            continue
        prefix = (m.group("prefix") or "").strip()
        section_path = [p for p in prefix.split(" ") if p]
        title = m.group("title").strip()
        body = (m.group("body") or "").strip()
        items.append({
            "chunk_index": idx,
            "title": title,
            "content": body,
            "section_path": section_path,
        })
    return items


def persist_parsed_document(
    *,
    temp_file_path: str,
    filename: str,
    original_mime: Optional[str],
    file_content: str,
    segments: Any,
    toc: Dict[str, Any],
    keywords: Optional[Any],
    collection_name: str = "policy_documents",
) -> Dict[str, Any]:
    """将上传+解析产物接入存储：落盘 raw/ 与 parsed/，写入 documents/chunks。

    返回：{ collection_id, doc_id, paths: {...}, chunk_count }
    """
    # 准备目录与连接
    storage_root = ensure_storage_dirs(get_storage_root())
    conn = connect()

    # 确保 collection 存在
    c_repo = CollectionsRepo(conn)
    collection = c_repo.ensure(name=collection_name, provider="weaviate", config=None, is_active=1)
    collection_id = collection["id"]

    # 创建文档记录（先写入 uploaded/processing 状态）
    d_repo = DocumentsRepo(conn)

    # 预先计算指标
    word_count = len((file_content or "").split())
    mime = original_mime or guess_mime(filename)

    # 目标目录
    # storage/docs/<collection>/<doc>/raw/<file>
    # storage/docs/<collection>/<doc>/parsed/
    doc_id = uuid_hex()
    doc_dir = storage_root / "docs" / collection_id / doc_id
    raw_dir = doc_dir / "raw"
    parsed_dir = doc_dir / "parsed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    parsed_dir.mkdir(parents=True, exist_ok=True)

    raw_path = raw_dir / filename
    # 将临时文件拷贝为 raw 文件
    try:
        shutil.copyfile(temp_file_path, raw_path)
    except Exception:
        # 拷贝失败则写入文本内容作为原始文件
        with open(raw_path, "wb") as f:
            f.write((file_content or "").encode("utf-8"))

    storage_path_rel = str(Path("docs") / collection_id / doc_id / "raw" / filename)
    doc_pk = d_repo.create(
        collection_id=collection_id,
        source_filename=filename,
        storage_path=storage_path_rel,
        original_mime=mime,
        status="processing",
        page_count=None,
        word_count=word_count,
        summary=None,
        keywords=keywords,
        parsing_payload=None,
        last_error=None,
        version=1,
        id=doc_id,
    )

    # 写入解析产物
    with open(parsed_dir / "content.txt", "w", encoding="utf-8") as f:
        f.write(file_content or "")
    with open(parsed_dir / "toc.json", "w", encoding="utf-8") as f:
        json.dump(toc, f, ensure_ascii=False, indent=2)
    with open(parsed_dir / "segments.json", "w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)
    if keywords is not None:
        with open(parsed_dir / "keywords.json", "w", encoding="utf-8") as f:
            json.dump(keywords, f, ensure_ascii=False, indent=2)

    # 写入 chunks
    ch_repo = ChunksRepo(conn)
    chunks = flatten_segments_to_chunks(segments)
    for item in chunks:
        ch_repo.create(
            doc_id=doc_pk,
            collection_id=collection_id,
            chunk_index=item["chunk_index"],
            title=item.get("title"),
            content=item.get("content", ""),
            section_path=item.get("section_path"),
            token_count=None,
            metadata=None,
            weaviate_id=None,
            embedding_status="pending",
        )

    # 更新文档状态为 succeeded，并记录解析统计
    parsing_payload = {"chunk_count": len(chunks)}
    d_repo.update(doc_pk, status="succeeded", parsing_payload=parsing_payload)

    return {
        "collection_id": collection_id,
        "doc_id": doc_pk,
        "paths": {
            "raw": str(raw_path),
            "parsed": str(parsed_dir),
            "storage_path": storage_path_rel,
        },
        "chunk_count": len(chunks),
    }


def uuid_hex() -> str:
    from uuid import uuid4
    return uuid4().hex
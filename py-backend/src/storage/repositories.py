from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .db import connect


def _json_dump(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _json_load(value: Optional[str]) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


class CollectionsRepo:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or connect()

    def create(
        self,
        name: str,
        description: Optional[str] = None,
        provider: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        is_active: int | bool = 1,
        *,
        id: Optional[str] = None,
    ) -> str:
        cid = id or uuid4().hex
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO collections (id, name, description, provider, config, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                cid,
                name,
                description,
                provider,
                _json_dump(config),
                1 if bool(is_active) else 0,
            ),
        )
        self.conn.commit()
        return cid

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM collections WHERE id = ?", (id,))
        row = cur.fetchone()
        if not row:
            return None
        data = dict(row)
        data["config"] = _json_load(data.get("config"))
        data["is_active"] = int(data.get("is_active") or 0)
        return data

    # 新增：按名称查询与确保存在
    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM collections WHERE name = ? LIMIT 1", (name,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["config"] = _json_load(d.get("config"))
        d["is_active"] = int(d.get("is_active") or 0)
        return d

    def ensure(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        existing = self.get_by_name(name)
        if existing:
            return existing
        cid = self.create(name=name, **kwargs)
        return self.get(cid) or {"id": cid, "name": name}

    def list(self, active: Optional[bool] = None) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        if active is None:
            cur.execute("SELECT * FROM collections ORDER BY created_at DESC")
        else:
            cur.execute("SELECT * FROM collections WHERE is_active = ? ORDER BY created_at DESC", (1 if active else 0,))
        rows = cur.fetchall() or []
        results: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["config"] = _json_load(d.get("config"))
            d["is_active"] = int(d.get("is_active") or 0)
            results.append(d)
        return results

    def update(self, id: str, **fields: Any) -> bool:
        if not fields:
            return False
        mapping: Dict[str, Any] = {}
        for k, v in fields.items():
            if k == "config":
                mapping[k] = _json_dump(v)
            elif k == "is_active":
                mapping[k] = 1 if bool(v) else 0
            else:
                mapping[k] = v
        set_clause = ", ".join([f"{k} = ?" for k in mapping.keys()])
        sql = f"UPDATE collections SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, [*mapping.values(), id])
        self.conn.commit()
        return cur.rowcount > 0

    def delete(self, id: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM collections WHERE id = ?", (id,))
        self.conn.commit()
        return cur.rowcount > 0


class DocumentsRepo:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or connect()

    def create(
        self,
        collection_id: str,
        source_filename: str,
        storage_path: str,
        *,
        original_mime: Optional[str] = None,
        status: Optional[str] = "uploaded",
        page_count: Optional[int] = None,
        word_count: Optional[int] = None,
        summary: Optional[str] = None,
        keywords: Optional[Any] = None,
        parsing_payload: Optional[Any] = None,
        last_error: Optional[str] = None,
        version: int = 1,
        id: Optional[str] = None,
    ) -> str:
        did = id or uuid4().hex
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO documents (
              id, collection_id, source_filename, storage_path, original_mime, status,
              page_count, word_count, summary, keywords, parsing_payload, last_error, version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                did,
                collection_id,
                source_filename,
                storage_path,
                original_mime,
                status,
                page_count,
                word_count,
                summary,
                _json_dump(keywords),
                _json_dump(parsing_payload),
                last_error,
                version,
            ),
        )
        self.conn.commit()
        return did

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM documents WHERE id = ?", (id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["keywords"] = _json_load(d.get("keywords"))
        d["parsing_payload"] = _json_load(d.get("parsing_payload"))
        return d

    def list_by_collection(self, collection_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM documents WHERE collection_id = ? ORDER BY created_at DESC", (collection_id,))
        rows = cur.fetchall() or []
        results: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["keywords"] = _json_load(d.get("keywords"))
            d["parsing_payload"] = _json_load(d.get("parsing_payload"))
            results.append(d)
        return results

    def update(self, id: str, **fields: Any) -> bool:
        if not fields:
            return False
        mapping: Dict[str, Any] = {}
        for k, v in fields.items():
            if k in ("keywords", "parsing_payload"):
                mapping[k] = _json_dump(v)
            else:
                mapping[k] = v
        set_clause = ", ".join([f"{k} = ?" for k in mapping.keys()])
        sql = f"UPDATE documents SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, [*mapping.values(), id])
        self.conn.commit()
        return cur.rowcount > 0

    def delete(self, id: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM documents WHERE id = ?", (id,))
        self.conn.commit()
        return cur.rowcount > 0


class ChunksRepo:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self.conn = conn or connect()

    def create(
        self,
        doc_id: str,
        collection_id: str,
        chunk_index: int,
        title: Optional[str],
        content: str,
        *,
        section_path: Optional[Any] = None,
        token_count: Optional[int] = None,
        metadata: Optional[Any] = None,
        weaviate_id: Optional[str] = None,
        embedding_status: Optional[str] = None,
        last_error: Optional[str] = None,
        id: Optional[str] = None,
    ) -> str:
        cid = id or uuid4().hex
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO chunks (
              id, doc_id, collection_id, chunk_index, title, section_path,
              content, token_count, metadata, weaviate_id, embedding_status, last_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cid,
                doc_id,
                collection_id,
                chunk_index,
                title,
                _json_dump(section_path),
                content,
                token_count,
                _json_dump(metadata),
                weaviate_id,
                embedding_status,
                last_error,
            ),
        )
        self.conn.commit()
        return cid

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM chunks WHERE id = ?", (id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["section_path"] = _json_load(d.get("section_path"))
        d["metadata"] = _json_load(d.get("metadata"))
        return d

    def list_by_doc(self, doc_id: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM chunks WHERE doc_id = ? ORDER BY chunk_index ASC", (doc_id,))
        rows = cur.fetchall() or []
        results: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["section_path"] = _json_load(d.get("section_path"))
            d["metadata"] = _json_load(d.get("metadata"))
            results.append(d)
        return results

    def update(self, id: str, **fields: Any) -> bool:
        if not fields:
            return False
        mapping: Dict[str, Any] = {}
        for k, v in fields.items():
            if k in ("section_path", "metadata"):
                mapping[k] = _json_dump(v)
            else:
                mapping[k] = v
        set_clause = ", ".join([f"{k} = ?" for k in mapping.keys()])
        sql = f"UPDATE chunks SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cur = self.conn.cursor()
        cur.execute(sql, [*mapping.values(), id])
        self.conn.commit()
        return cur.rowcount > 0

    def delete(self, id: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM chunks WHERE id = ?", (id,))
        self.conn.commit()
        return cur.rowcount > 0

    def delete_by_doc(self, doc_id: str) -> int:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        self.conn.commit()
        return cur.rowcount or 0
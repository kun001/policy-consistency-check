from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

# Environment variables
ENV_STORAGE_ROOT = "STORAGE_ROOT"  # root directory for storage/, defaults to <py-backend>/storage
ENV_DB_FILE = "DB_FILE"            # optional absolute path to sqlite db file; defaults to storage/db.sqlite3

DEFAULT_STORAGE_DIRNAME = "storage"


def _backend_root() -> Path:
    """Return the py-backend directory path."""
    return Path(__file__).resolve().parent.parent.parent


def get_storage_root() -> Path:
    """Resolve storage root using ENV or default to <py-backend>/storage."""
    env = os.getenv(ENV_STORAGE_ROOT)
    if env:
        return Path(env).resolve()
    return _backend_root() / DEFAULT_STORAGE_DIRNAME


def ensure_storage_dirs(storage_root: Optional[Path] = None) -> Path:
    """Create required storage directories: storage/, storage/docs/, storage/tmp/."""
    root = storage_root or get_storage_root()
    (root).mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "tmp").mkdir(parents=True, exist_ok=True)
    return root


def get_db_path(storage_root: Optional[Path] = None) -> Path:
    """Return sqlite db path; ENV override via DB_FILE, else <storage>/db.sqlite3."""
    override = os.getenv(ENV_DB_FILE)
    if override:
        path = Path(override).resolve()
    else:
        root = storage_root or get_storage_root()
        path = root / "db.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open sqlite3 connection with row_factory configured."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Create tables and indices according to the storage design doc (idempotent)."""
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA foreign_keys = ON;

        -- 3.1 collections
        CREATE TABLE IF NOT EXISTS collections (
          id TEXT PRIMARY KEY,
          name TEXT,
          description TEXT,
          provider TEXT,
          config TEXT,
          is_active INTEGER DEFAULT 1,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- 3.2 documents
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY,
          collection_id TEXT,
          source_filename TEXT,
          storage_path TEXT,
          original_mime TEXT,
          status TEXT,
          page_count INTEGER,
          word_count INTEGER,
          summary TEXT,
          keywords TEXT,
          parsing_payload TEXT,
          last_error TEXT,
          version INTEGER DEFAULT 1,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection_id);

        -- 3.4 chunks
        CREATE TABLE IF NOT EXISTS chunks (
          id TEXT PRIMARY KEY,
          doc_id TEXT,
          collection_id TEXT,
          chunk_index INTEGER,
          title TEXT,
          section_path TEXT,
          content TEXT,
          token_count INTEGER,
          metadata TEXT,
          weaviate_id TEXT,
          embedding_status TEXT,
          last_error TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_weaviate ON chunks(weaviate_id);

        -- 3.5 keywords (optional)
        CREATE TABLE IF NOT EXISTS keywords (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          doc_id TEXT,
          term TEXT,
          weight REAL,
          source TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
        );

        -- 3.6 process_logs (optional)
        CREATE TABLE IF NOT EXISTS process_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          doc_id TEXT,
          stage TEXT,
          status TEXT,
          message TEXT,
          extra TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def init_storage_and_db() -> Path:
    """Ensure storage tree exists and initialize sqlite schema. Returns db file path."""
    root = ensure_storage_dirs()
    db_path = get_db_path(root)
    conn = connect(db_path)
    try:
        initialize_schema(conn)
    finally:
        conn.close()
    return db_path

# if __name__ == "__main__":
#     print(init_storage_and_db())
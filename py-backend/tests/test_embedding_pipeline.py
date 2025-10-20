import sys
from pathlib import Path
import tempfile

# add src to path
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from storage import (
    init_storage_and_db,
    persist_parsed_document,
    index_document_chunks,
    rollback_document_vectors,
    CollectionsRepo,
    DocumentsRepo,
    ChunksRepo,
)
from doc_structure_recognition import build_segments_struct
from utils import build_toc

DEFAULT_TOKEN = "sk-dybroxxstjaxkyrnevsqdjikzardzzsppbvwbmimrflpoyfj"
DEFAULT_COLLECTION_NAME = "unittest_embed_collection"


def main():
    print("init db:", init_storage_and_db())

    sample_content = (
        "第一章 总则\n"
        "第一条 本办法适用于...\n"
        "第二条 市场交易遵循...\n"
    )
    sample_filename = "unittest_embed_policy.md"

    # 写入临时原始文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as tmp:
        tmp.write(sample_content.encode("utf-8"))
        temp_path = tmp.name

    # 构造分段结构
    file_struct = build_segments_struct(file_content=sample_content, file_name=sample_filename)
    segments = file_struct.get("segments", [])
    toc_tree, counts = build_toc(segments)

    # 持久化
    result = persist_parsed_document(
        temp_file_path=temp_path,
        filename=sample_filename,
        original_mime="text/markdown",
        file_content=sample_content,
        segments=segments,
        toc=toc_tree,
        keywords=["市场", "交易"],
        collection_name=DEFAULT_COLLECTION_NAME,
    )
    print("persist result:", result)

    # 索引到 Weaviate
    idx_stats = index_document_chunks(
        result["doc_id"],
        collection_name=DEFAULT_COLLECTION_NAME,
        siliconflow_api_token=DEFAULT_TOKEN,
        weaviate_api_key="key_kunkun",
        client_params=None,
        batch_size=10,
        max_retries=1,
    )
    print("index stats:", idx_stats)

    # 校验数据库状态
    conn_repo = CollectionsRepo()
    doc_repo = DocumentsRepo(conn_repo.conn)
    chunk_repo = ChunksRepo(conn_repo.conn)

    doc = doc_repo.get(result["doc_id"]) or {}
    chunks = chunk_repo.list_by_doc(result["doc_id"]) or []
    assert len(chunks) == result["chunk_count"], "chunk count mismatch"

    embedded_count = sum(1 for ch in chunks if ch.get("embedding_status") == "embedded")
    failed_count = sum(1 for ch in chunks if ch.get("embedding_status") == "failed")
    assert embedded_count + failed_count == result["chunk_count"], "status mismatch after index"

    # 执行回滚
    rb_stats = rollback_document_vectors(
        result["doc_id"],
        collection_name=DEFAULT_COLLECTION_NAME,
        siliconflow_api_token=DEFAULT_TOKEN,
        weaviate_api_key="key_kunkun",
        client_params=None,
    )
    print("rollback stats:", rb_stats)

    chunks_after = chunk_repo.list_by_doc(result["doc_id"]) or []
    pending_count = sum(1 for ch in chunks_after if ch.get("embedding_status") == "pending")
    assert pending_count == result["chunk_count"], "rollback did not reset chunk statuses to pending"

    print("test_embedding_pipeline: OK")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        raise
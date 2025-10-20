import os
import sys
import tempfile
from pathlib import Path

# add src to path
BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from storage import init_storage_and_db, persist_parsed_document, CollectionsRepo, DocumentsRepo, ChunksRepo  # type: ignore
from doc_structure_recognition import build_segments_struct
from utils import build_toc


def main():
    print("init db:", init_storage_and_db())

    sample_content = (
        "第一章 总则\n"
        "第一条 本办法适用于...\n"
        "第二条 市场交易遵循...\n"
        "第二章 交易组织\n"
        "第一节 会员管理\n"
        "第三条 会员资格...\n"
        "第四条 会员权利与义务...\n"
    )
    sample_filename = "unittest_policy.md"

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
        collection_name="unittest_collection",
    )
    print("persist result:", result)

    # 校验数据库记录
    conn_repo = CollectionsRepo()
    doc_repo = DocumentsRepo(conn_repo.conn)
    chunk_repo = ChunksRepo(conn_repo.conn)

    doc = doc_repo.get(result["doc_id"]) or {}
    chunks = chunk_repo.list_by_doc(result["doc_id"]) or []
    assert doc.get("status") == "succeeded"
    assert len(chunks) == result["chunk_count"], "chunk count mismatch"

    # 校验落盘文件
    parsed_dir = Path(result["paths"]["parsed"]).resolve()
    assert (parsed_dir / "content.txt").exists()
    assert (parsed_dir / "toc.json").exists()
    assert (parsed_dir / "segments.json").exists()
    assert (parsed_dir / "keywords.json").exists()

    print("test_ingest_pipeline: OK")

    # 清理临时原始上传文件
    try:
        os.unlink(temp_path)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise
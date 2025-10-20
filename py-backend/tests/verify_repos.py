import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]  # py-backend
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from storage import init_storage_and_db, CollectionsRepo, DocumentsRepo, ChunksRepo


def main():
    db_path = init_storage_and_db()
    print('DB path:', db_path)

    c_repo = CollectionsRepo()
    col_id = c_repo.create(name='policy_docs', description='政策文档', provider='weaviate', config={'class': 'PolicyDoc'}, is_active=True)
    print('collection created:', col_id)
    print('collection get:', c_repo.get(col_id))

    d_repo = DocumentsRepo(c_repo.conn)
    doc_id = d_repo.create(
        collection_id=col_id,
        source_filename='example.md',
        storage_path=f'docs/{col_id}/doc1/raw/example.md',
        original_mime='text/markdown',
        status='uploaded',
        keywords=['市场','交易'],
        parsing_payload={'job_id': 'j123'},
    )
    print('document created:', doc_id)
    print('documents list:', len(d_repo.list_by_collection(col_id)))

    ch_repo = ChunksRepo(d_repo.conn)
    chunk_ids = []
    for i, text in enumerate(['第一条 内容A', '第二条 内容B']):
        cid = ch_repo.create(
            doc_id=doc_id,
            collection_id=col_id,
            chunk_index=i,
            title=f'第{i+1}条',
            content=text,
            section_path=['第一章'],
            metadata={'page': i+1},
            embedding_status='pending',
        )
        chunk_ids.append(cid)
    print('chunk ids:', chunk_ids)
    print('chunks by doc:', len(ch_repo.list_by_doc(doc_id)))

    assert c_repo.update(col_id, description='政策文档(更新)')
    assert d_repo.update(doc_id, status='processing')
    assert ch_repo.update(chunk_ids[0], embedding_status='embedded')
    print('updated ok')

    deleted_count = ch_repo.delete_by_doc(doc_id)
    print('chunks deleted:', deleted_count)
    assert d_repo.delete(doc_id)
    assert c_repo.delete(col_id)
    print('cleanup ok')


if __name__ == '__main__':
    main()
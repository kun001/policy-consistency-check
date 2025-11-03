"""Script to exercise all methods on WeaviateEngine."""

import os
import sys
import uuid
from pathlib import Path
from typing import Dict, List


CURRENT_DIR = Path(__file__).resolve().parent
WEAVIATE_DIR = CURRENT_DIR.parent / "api" / "weaviate"
if str(WEAVIATE_DIR) not in sys.path:
    sys.path.insert(0, str(WEAVIATE_DIR))

from weaviateEngine import WeaviateEngine  # type: ignore  # noqa: E402

def build_sample_documents(prefix: str) -> List[Dict[str, str]]:
    """Generate documents with predictable metadata for testing."""
    return [
        {
            "id": f"{prefix}-001",
            "title": "Policy Compliance Overview",
            "content": "Sample policy compliance document for integration testing.",
            "metadata": {"tag": "policy", "lang": "en"},
        },
        {
            "id": f"{prefix}-002",
            "title": "Industry Regulation Summary",
            "content": "Summary of industry regulations used to validate vector search.",
            "metadata": {"tag": "regulation", "lang": "en"},
        },
    ]


def main() -> None:
    siliconflow_api_token = "sk-dybroxxstjaxkyrnevsqdjikzardzzsppbvwbmimrflpoyfj"
    if not siliconflow_api_token:
        raise ValueError("Please set SILICONFLOW_API_TOKEN before running the test.")

    collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
    engine = WeaviateEngine(
        collection_name=collection_name,
        siliconflow_api_token=siliconflow_api_token,
    )

    try:
        print(f"collection name: {collection_name}")

        client_params = engine._build_client_params({}, None)
        print("client params:", client_params)

        exists = engine._collection_exists()
        print("collection exists after init:", exists)

        sample_texts = ["sample text A", "sample text B"]
        embeddings = engine._embed_texts(sample_texts)
        print("embedding count:", len(embeddings))

        collection = engine._get_collection()
        print("collection object type:", type(collection))

        documents = build_sample_documents(prefix=collection_name)
        inserted = engine.index_documents(documents)
        print("documents indexed:", inserted)

        new_docs = build_sample_documents(prefix=f"{collection_name}-extra")
        new_vectors = engine._embed_texts([doc["content"] for doc in new_docs])
        uploaded = engine._upsert_with_vectors(
            vectors=new_vectors,
            documents=new_docs,
            text_key="content",
            title_key="title",
            metadata_key="metadata",
            batch_size=10,
        )
        print("documents upserted via helper:", uploaded)

        search_results = engine.search("policy compliance", limit=3)
        print("search results count:", len(search_results))
        for idx, item in enumerate(search_results, start=1):
            print(f"result {idx} -> title: {item.get('title')}, distance: {item.get('_distance')}")
    finally:
        engine.close()
        print("client closed.")


if __name__ == "__main__":
    main()

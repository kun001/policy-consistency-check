import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
from uuid import UUID

API_DIR = Path(__file__).resolve().parent
SRC_DIR = API_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from src.weaviate.weaviateEngine import WeaviateEngine
from src.settings import (
    DEFAULT_COLLECTION_NAME,
    SILICONFLOW_API_TOKEN as DEFAULT_SILICONFLOW_API_TOKEN,
    WEAVIATE_API_KEY as DEFAULT_WEAVIATE_API_KEY,
)


def _init_engine(
    collection_name: Optional[str] = None,
    *,
    siliconflow_api_token: Optional[str] = None,
    client_params: Optional[Dict[str, Any]] = None,
    weaviate_api_key: Optional[str] = None,
) -> Optional[WeaviateEngine]:
    """
    创建 WeaviateEngine 实例，便于上层接口直接使用。
    """
    target_collection = collection_name or DEFAULT_COLLECTION_NAME
    token = siliconflow_api_token or DEFAULT_SILICONFLOW_API_TOKEN
    api_key = weaviate_api_key or DEFAULT_WEAVIATE_API_KEY

    if not target_collection:
        print("错误：未提供 collection_name，且默认值为空。")
        return None
    if not token:
        print("错误：未设置 SiliconFlow API Token。")
        return None

    try:
        return WeaviateEngine(
            collection_name=target_collection,
            siliconflow_api_token=token,
            client_params=client_params,
            weaviate_api_key=api_key,
        )
    except Exception as exc:  # pragma: no cover
        print(f"WeaviateEngine 初始化失败：{exc}")
        return None


def weaviate_index_documents(
    documents: Sequence[Dict[str, Any]],
    *,
    collection_name: Optional[str] = None,
    siliconflow_api_token: Optional[str] = None,
    weaviate_api_key: Optional[str] = None,
    client_params: Optional[Dict[str, Any]] = None,
    text_key: str = "content",
    title_key: str = "title",
    metadata_key: str = "metadata",
    batch_size: int = 50,
) -> int:
    """
    写入（或更新）文档到 Weaviate 向量库。
    """
    engine = _init_engine(
        collection_name,
        siliconflow_api_token=siliconflow_api_token,
        client_params=client_params,
        weaviate_api_key=weaviate_api_key,
    )
    if not engine:
        return 0

    try:
        uploaded = engine.index_documents(
            documents,
            text_key=text_key,
            title_key=title_key,
            metadata_key=metadata_key,
            batch_size=batch_size,
        )
        print(f"Weaviate：成功写入 {uploaded} 条文档。")
        return uploaded
    except Exception as exc:  # pragma: no cover
        print(f"Weaviate：写入文档失败，原因：{exc}")
        return 0
    finally:
        engine.close()


def weaviate_delete_document(
    uuid_value: Union[str, UUID],
    *,
    collection_name: Optional[str] = None,
    siliconflow_api_token: Optional[str] = None,
    weaviate_api_key: Optional[str] = None,
    client_params: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    根据 UUID 删除单条记录。
    """
    engine = _init_engine(
        collection_name,
        siliconflow_api_token=siliconflow_api_token,
        client_params=client_params,
        weaviate_api_key=weaviate_api_key,
    )
    if not engine:
        return False

    try:
        result = engine.delete_document_by_id(uuid_value)
        print(f"Weaviate：删除文档 {'成功' if result else '失败'}，UUID={uuid_value}")
        return result
    except Exception as exc:  # pragma: no cover
        print(f"Weaviate：删除文档时发生异常，原因：{exc}")
        return False
    finally:
        engine.close()


def weaviate_search(
    query: str,
    *,
    collection_name: Optional[str] = None,
    siliconflow_api_token: Optional[str] = None,
    weaviate_api_key: Optional[str] = None,
    client_params: Optional[Dict[str, Any]] = None,
    limit: int = 10,
    filter_conditions: Optional[Sequence[Dict[str, Any]]] = None,
    filters: Optional[Dict[str, Any]] = None,
    search_type: str = "hybrid",
    alpha: Optional[float] = None,
    fusion_type: Optional[str] = None,
    max_vector_distance: Optional[float] = None,
    bm25_properties: Optional[Sequence[str]] = None,
    bm25_search_operator: Optional[int] = None,
    vector: Optional[Sequence[float]] = None,
) -> List[Dict[str, Any]]:
    """
    在 Weaviate 中搜索内容，支持三种检索方式：关键词（BM25）、混合（Hybrid，默认）、向量（Near Vector）。
    """
    engine = _init_engine(
        collection_name,
        siliconflow_api_token=siliconflow_api_token,
        client_params=client_params,
        weaviate_api_key=weaviate_api_key,
    )
    if not engine:
        return []

    try:
        final_filters = filters
        if final_filters is None and filter_conditions:
            final_filters = engine.build_filter(filter_conditions)

        results = engine.search(
            query,
            limit=limit,
            filters=final_filters,
            search_type=search_type,
            alpha=alpha,
            fusion_type=fusion_type,
            max_vector_distance=max_vector_distance,
            bm25_properties=bm25_properties,
            bm25_search_operator=bm25_search_operator,
            vector=vector,
        )
        print(f"Weaviate：{(search_type or 'hybrid').lower()} 检索完成，共返回 {len(results)} 条结果。")
        return results
    except Exception as exc:  # pragma: no cover
        print(f"Weaviate：检索失败，原因：{exc}")
        return []
    finally:
        engine.close()


def weaviate_drop_collection(
    collection_name: Optional[str] = None,
    *,
    siliconflow_api_token: Optional[str] = None,
    weaviate_api_key: Optional[str] = None,
    client_params: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    删除集合及其所有内容。
    """
    engine = _init_engine(
        collection_name,
        siliconflow_api_token=siliconflow_api_token,
        client_params=client_params,
        weaviate_api_key=weaviate_api_key,
    )
    if not engine:
        return False

    try:
        result = engine.drop_collection()
        print(f"Weaviate：删除集合 {'成功' if result else '失败'}，collection={engine.collection_name}")
        return result
    except Exception as exc:  # pragma: no cover
        print(f"Weaviate：删除集合时发生异常，原因：{exc}")
        return False
    finally:
        engine.close()


__all__ = [
    "weaviate_index_documents",
    "weaviate_delete_document",
    "weaviate_search",
    "weaviate_drop_collection",
]

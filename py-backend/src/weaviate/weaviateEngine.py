"""Utility class for interacting with the Weaviate cluster."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
from uuid import UUID, NAMESPACE_DNS, uuid4, uuid5

import weaviate
import weaviate.classes.config as wc
from weaviate import WeaviateClient
from weaviate.auth import AuthApiKey
from weaviate.classes.query import MetadataQuery
import weaviate.classes.query as wq
from weaviate.collections import Collection

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
from api.embeddingApi import get_embeddings_from_siliconflow
from src.settings import (
    WEAVIATE_HTTP_HOST as DEFAULT_WEAVIATE_HTTP_HOST,
    WEAVIATE_HTTP_PORT as DEFAULT_WEAVIATE_HTTP_PORT,
    WEAVIATE_HTTP_SECURE as DEFAULT_WEAVIATE_HTTP_SECURE,
    WEAVIATE_GRPC_HOST as DEFAULT_WEAVIATE_GRPC_HOST,
    WEAVIATE_GRPC_PORT as DEFAULT_WEAVIATE_GRPC_PORT,
    WEAVIATE_GRPC_SECURE as DEFAULT_WEAVIATE_GRPC_SECURE,
    WEAVIATE_API_KEY as DEFAULT_WEAVIATE_API_KEY,
)


class WeaviateEngine:
    """High level helper that wraps common Weaviate workflows."""

    def __init__(
        self,
        collection_name: str,
        siliconflow_api_token: str,
        client_params: Optional[Dict[str, Any]] = None,
        weaviate_api_key: Optional[str] = None,
    ) -> None:
        if not collection_name:
            raise ValueError("collection_name is required")
        if not siliconflow_api_token:
            raise ValueError("siliconflow_api_token is required")

        self.collection_name = collection_name
        self._siliconflow_api_token = siliconflow_api_token

        params = self._build_client_params(client_params, weaviate_api_key)
        self.client: WeaviateClient = weaviate.connect_to_custom(
            skip_init_checks=False,
            **params,
        )

        if not self._collection_exists():
            self.create_collection()

    def _build_client_params(
        self,
        client_params: Optional[Dict[str, Any]],
        weaviate_api_key: Optional[str],
    ) -> Dict[str, Any]:
        base_params: Dict[str, Any] = {
            "http_host": DEFAULT_WEAVIATE_HTTP_HOST,
            "http_port": DEFAULT_WEAVIATE_HTTP_PORT,
            "http_secure": DEFAULT_WEAVIATE_HTTP_SECURE,
            "grpc_host": DEFAULT_WEAVIATE_GRPC_HOST,
            "grpc_port": DEFAULT_WEAVIATE_GRPC_PORT,
            "grpc_secure": DEFAULT_WEAVIATE_GRPC_SECURE,
        }
        if client_params:
            base_params.update(client_params)

        api_key = weaviate_api_key or base_params.pop("api_key", DEFAULT_WEAVIATE_API_KEY)
        if "auth_credentials" not in base_params:
            base_params["auth_credentials"] = AuthApiKey(api_key)

        return base_params

    def _collection_exists(self) -> bool:
        try:
            return self.client.collections.exists(self.collection_name)
        except Exception as error:  # pragma: no cover
            print(f"Failed to check collection existence: {error}")
            return False

    def create_collection(self) -> None:
        try:
            self.client.collections.create(
                name=self.collection_name,
                properties=[
                    wc.Property(name="content", data_type=wc.DataType.TEXT),
                    wc.Property(name="title", data_type=wc.DataType.TEXT, skip_vectorization=True),
                    wc.Property(name="metadata_json", data_type=wc.DataType.TEXT, skip_vectorization=True),
                    wc.Property(name="source_id", data_type=wc.DataType.TEXT, skip_vectorization=True),
                ],
            )
        except Exception as error:  # pragma: no cover
            print(f"Failed to create collection {self.collection_name}: {error}")
            raise

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:  # pragma: no cover
            pass

    def _embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            raise ValueError("texts collection must not be empty")

        payload = get_embeddings_from_siliconflow(inputs=list(texts), api_token=self._siliconflow_api_token)
        data = payload.get("data", []) if isinstance(payload, dict) else []
        if len(data) != len(texts):
            raise ValueError("Embedding response size mismatch")

        sorted_data = sorted(data, key=lambda item: item.get("index", 0))
        embeddings: List[List[float]] = []
        for item in sorted_data:
            embedding = item.get("embedding")
            if not isinstance(embedding, Iterable):
                raise ValueError("Invalid embedding format received from SiliconFlow")
            embeddings.append([float(value) for value in embedding])
        return embeddings

    def _get_collection(self) -> Collection:
        return self.client.collections.get(self.collection_name)

    def _ensure_uuid(self, doc: Dict[str, Any]) -> str:
        raw_id = doc.get("id")
        if raw_id:
            raw_str = str(raw_id)
            try:
                return str(UUID(raw_str))
            except ValueError:
                return str(uuid5(NAMESPACE_DNS, f"{self.collection_name}:{raw_str}"))
        return str(uuid4())

    def index_documents(
        self,
        documents: Sequence[Dict[str, Any]],
        *,
        text_key: str = "content",
        title_key: str = "title",
        metadata_key: str = "metadata",
        batch_size: int = 50,
    ) -> int:
        if not documents:
            return 0

        cleaned_docs: List[Dict[str, Any]] = []
        texts: List[str] = []
        for doc in documents:
            if not isinstance(doc, dict):
                raise TypeError("documents must be a sequence of dictionaries")
            text_value = doc.get(text_key)
            if not isinstance(text_value, str) or not text_value.strip():
                raise ValueError(f"document missing valid '{text_key}' content")
            texts.append(text_value)
            cleaned_docs.append(doc)

        vectors = self._embed_texts(texts)
        return self._upsert_with_vectors(
            vectors=vectors,
            documents=cleaned_docs,
            text_key=text_key,
            title_key=title_key,
            metadata_key=metadata_key,
            batch_size=batch_size,
        )

    def _upsert_with_vectors(
        self,
        *,
        vectors: Sequence[Sequence[float]],
        documents: Sequence[Dict[str, Any]],
        text_key: str,
        title_key: str,
        metadata_key: str,
        batch_size: int,
    ) -> int:
        if len(vectors) != len(documents):
            raise ValueError("vectors and documents sequences must be the same length")

        collection = self._get_collection()
        total_uploaded = 0
        for start in range(0, len(documents), batch_size):
            chunk_docs = documents[start:start + batch_size]
            chunk_vectors = vectors[start:start + batch_size]
            try:
                with collection.batch.dynamic() as batch:
                    for doc, vector in zip(chunk_docs, chunk_vectors):
                        properties: Dict[str, Any] = {
                            "content": doc.get(text_key, ""),
                            "title": doc.get(title_key, "") or doc.get("id", ""),
                            "metadata_json": json.dumps(doc.get(metadata_key, {}), ensure_ascii=False),
                            "source_id": str(doc.get("id") or ""),
                        }
                        uuid_value = self._ensure_uuid(doc)
                        batch.add_object(
                            properties=properties,
                            vector=list(vector),
                            uuid=uuid_value,
                        )
                        total_uploaded += 1
            except Exception as error:
                print(f"Failed to upload batch: {error}")
                raise
        return total_uploaded

    def delete_document_by_id(self, uuid_value: Union[str, UUID]) -> bool:
        """
        Delete a single object by UUID.
        """
        try:
            normalized_uuid = str(UUID(str(uuid_value)))
        except ValueError as error:
            print(f"Invalid UUID provided: {error}")
            return False

        collection = self._get_collection()
        try:
            result = collection.data.delete_by_id(normalized_uuid)
            return bool(result)
        except Exception as error:  # pragma: no cover
            print(f"Failed to delete object {normalized_uuid}: {error}")
            return False

    def delete_collection(self, collection_name: Optional[str] = None) -> bool:
        """
        Delete a collection by name; defaults to this engine's collection.
        """
        target_collection = collection_name or self.collection_name
        try:
            if not self.client.collections.exists(target_collection):
                return False
            self.client.collections.delete(target_collection)
            return True
        except Exception as error:  # pragma: no cover
            print(f"Failed to delete collection {target_collection}: {error}")
            return False

    def drop_collection(self) -> bool:
        """
        Delete the entire collection from Weaviate.
        """
        return self.delete_collection(self.collection_name)

    def build_filter(
        self,
        conditions: Sequence[Dict[str, Any]],
        *,
        operator: str = "And",
    ) -> Optional[Dict[str, Any]]:
        """
        Build a Weaviate filter payload from simplified condition dictionaries.
        # filter_obj =>
            # {
            #   "operator": "And",
            #   "operands": [
            #       {"path": ["metadata.tag"], "operator": "Equal", "valueString": "policy"},
            #       {"path": ["metadata.lang"], "operator": "Equal", "valueString": "en"},
            #   ],
            # }
        """
        if not conditions:
            return None

        filter_dict: Dict[str, Any] = {
            "operator": operator,
            "operands": [],
        }

        for condition in conditions:
            if not isinstance(condition, dict):
                continue

            path_key = condition.get("key")
            match_value = condition.get("match")
            comparison_operator = condition.get("operator", "Equal")

            if not path_key or match_value is None:
                continue

            if isinstance(path_key, str):
                path = path_key.split(".")
            elif isinstance(path_key, (list, tuple)):
                path = [str(part) for part in path_key]
            else:
                continue

            operand: Dict[str, Any] = {
                "path": path,
                "operator": comparison_operator,
            }

            if isinstance(match_value, bool):
                operand["valueBoolean"] = match_value
            elif isinstance(match_value, (int, float)):
                operand["valueNumber"] = match_value
            else:
                operand["valueString"] = str(match_value)

            filter_dict["operands"].append(operand)

        return filter_dict if filter_dict["operands"] else None

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        search_type: str = "hybrid",
        alpha: Optional[float] = None,
        fusion_type: Optional[str] = None,
        max_vector_distance: Optional[float] = None,
        bm25_properties: Optional[Sequence[str]] = None,
        bm25_search_operator: Optional[int] = None,
        vector: Optional[Sequence[float]] = None,
    ) -> List[Dict[str, Any]]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        collection = self._get_collection()
        st = (search_type or "hybrid").lower()
        payloads: List[Dict[str, Any]] = []

        if st == "keyword":
            meta = wq.MetadataQuery(score=True)
            kwargs: Dict[str, Any] = {
                "query": query,
                "limit": limit,
                "return_properties": ["content", "title", "metadata_json", "source_id"],
                "return_metadata": meta,
            }
            if filters:
                kwargs["filters"] = filters
            if bm25_properties:
                kwargs["query_properties"] = list(bm25_properties)
            if bm25_search_operator is not None:
                kwargs["bm25_search_operator"] = int(bm25_search_operator)
            results = collection.query.bm25(**kwargs)
            for obj in results.objects:
                metadata: Dict[str, Any] = {}
                metadata_raw = obj.properties.get("metadata_json") if obj.properties else None
                if isinstance(metadata_raw, str) and metadata_raw:
                    try:
                        metadata = json.loads(metadata_raw)
                    except json.JSONDecodeError:
                        metadata = {"raw": metadata_raw}
                payloads.append({
                    "uuid": str(obj.uuid),
                    "text": obj.properties.get("content", "") if obj.properties else "",
                    "title": obj.properties.get("title") if obj.properties else None,
                    "metadata": metadata,
                    "source_id": obj.properties.get("source_id") if obj.properties else None,
                    "_score": getattr(obj.metadata, "score", None),
                })
            return payloads

        if st == "vector":
            vec = list(vector) if vector is not None else self._embed_texts([query])[0]
            meta = MetadataQuery(distance=True)
            results = collection.query.near_vector(
                near_vector=vec,
                limit=limit,
                filters=filters,
                return_properties=["content", "title", "metadata_json", "source_id"],
                return_metadata=meta,
            )
            for obj in results.objects:
                metadata: Dict[str, Any] = {}
                metadata_raw = obj.properties.get("metadata_json") if obj.properties else None
                if isinstance(metadata_raw, str) and metadata_raw:
                    try:
                        metadata = json.loads(metadata_raw)
                    except json.JSONDecodeError:
                        metadata = {"raw": metadata_raw}
                payloads.append({
                    "uuid": str(obj.uuid),
                    "text": obj.properties.get("content", "") if obj.properties else "",
                    "title": obj.properties.get("title") if obj.properties else None,
                    "metadata": metadata,
                    "source_id": obj.properties.get("source_id") if obj.properties else None,
                    "_distance": obj.metadata.distance if obj.metadata else None,
                })
            return payloads

        # hybrid (default)
        vec = list(vector) if vector is not None else self._embed_texts([query])[0]
        meta = wq.MetadataQuery(score=True, distance=True)
        kwargs: Dict[str, Any] = {
            "query": query,
            "limit": limit,
            "vector": wq.HybridVector.near_vector(vector=vec),
            "return_properties": ["content", "title", "metadata_json", "source_id"],
            "return_metadata": meta,
        }
        if filters:
            kwargs["filters"] = filters
        if alpha is not None:
            kwargs["alpha"] = float(alpha)
        if fusion_type:
            kwargs["fusion_type"] = fusion_type
        if max_vector_distance is not None:
            kwargs["max_vector_distance"] = float(max_vector_distance)
        if bm25_properties:
            kwargs["query_properties"] = list(bm25_properties)
        results = collection.query.hybrid(**kwargs)
        for obj in results.objects:
            metadata: Dict[str, Any] = {}
            metadata_raw = obj.properties.get("metadata_json") if obj.properties else None
            if isinstance(metadata_raw, str) and metadata_raw:
                try:
                    metadata = json.loads(metadata_raw)
                except json.JSONDecodeError:
                    metadata = {"raw": metadata_raw}
            payloads.append({
                "uuid": str(obj.uuid),
                "text": obj.properties.get("content", "") if obj.properties else "",
                "title": obj.properties.get("title") if obj.properties else None,
                "metadata": metadata,
                "source_id": obj.properties.get("source_id") if obj.properties else None,
                "_distance": getattr(obj.metadata, "distance", None),
                "_score": getattr(obj.metadata, "score", None),
            })
        return payloads


__all__ = ["WeaviateEngine"]

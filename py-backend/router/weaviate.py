from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api.weaivateApi import (
    weaviate_delete_document,
    weaviate_drop_collection,
    weaviate_index_documents,
    weaviate_search,
)
from src.pydantic_models import WeaviateIndexRequest, WeaviateSearchRequest


router = APIRouter(prefix="/api/weaviate", tags=["weaviate"])


@router.post("/add-documents")
async def add_documents(payload: WeaviateIndexRequest):
    if not payload.documents:
        raise HTTPException(status_code=400, detail="documents policy")

    documents_payload = [document.dict(exclude_unset=True) for document in payload.documents]

    uploaded = weaviate_index_documents(
        documents_payload,
        collection_name=payload.collection_name,
        siliconflow_api_token=payload.siliconflow_api_token,
        weaviate_api_key=payload.weaviate_api_key,
        client_params=payload.client_params,
        text_key=payload.text_key,
        title_key=payload.title_key,
        metadata_key=payload.metadata_key,
        batch_size=payload.batch_size,
    )

    if payload.documents and uploaded <= 0:
        raise HTTPException(status_code=500, detail="Weaviate 文档索引失败")

    return {
        "success": True,
        "uploaded": uploaded,
    }


@router.post("/search")
async def search(payload: WeaviateSearchRequest):
    results = weaviate_search(
        payload.query,
        collection_name=payload.collection_name,
        siliconflow_api_token=payload.siliconflow_api_token,
        weaviate_api_key=payload.weaviate_api_key,
        client_params=payload.client_params,
        limit=payload.limit,
        filter_conditions=payload.filter_conditions,
        filters=payload.filters,
    )

    return {
        "success": True,
        "results": results,
        "count": len(results),
    }


@router.delete("/delete-documents")
async def delete_document(
    uuid_value: str,
    collection_name: Optional[str] = Query(None),
    siliconflow_api_token: Optional[str] = Query(None),
    weaviate_api_key: Optional[str] = Query(None),
):
    deleted = weaviate_delete_document(
        uuid_value,
        collection_name=collection_name,
        siliconflow_api_token=siliconflow_api_token,
        weaviate_api_key=weaviate_api_key,
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="document删除失败")

    return {"success": True, "uuid": uuid_value}


@router.delete("/delete-collection")
async def drop_collection(
    collection_name: Optional[str] = Query(None),
    siliconflow_api_token: Optional[str] = Query(None),
    weaviate_api_key: Optional[str] = Query(None),
):
    deleted = weaviate_drop_collection(
        collection_name=collection_name,
        siliconflow_api_token=siliconflow_api_token,
        weaviate_api_key=weaviate_api_key,
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="collection删除失败")

    return {"success": True, "collection_name": collection_name}


from pydantic import BaseModel
from typing import List, Any, Dict, Optional, Union, Literal

class DocumentSegmentResponse(BaseModel):
    success: bool
    message: str
    file_name: str
    segments: list
    segment_count: int
    save_path: Optional[str] = None

class ErrorResponse(BaseModel):
    success: bool
    message: str
    error_detail: Optional[str] = None

# ===== 层级目录（TOC）响应模型 =====
class FileInfo(BaseModel):
    name: str

class TocCounts(BaseModel):
    chapters: int
    sections: int
    articles: int

class TocNode(BaseModel):
    id: str
    type: Literal["document", "chapter", "section", "article"]
    label: Optional[str] = None
    index: Optional[int] = None
    text: Optional[str] = None
    children: Optional[List['TocNode']] = None

class DocumentTOCResponse(BaseModel):
    success: bool
    file: FileInfo
    toc: TocNode
    counts: TocCounts

class WeaviateDocument(BaseModel):
    id: Optional[str] = None
    content: str
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class WeaviateIndexRequest(BaseModel):
    documents: List[WeaviateDocument]
    collection_name: Optional[str] = None
    siliconflow_api_token: Optional[str] = None
    weaviate_api_key: Optional[str] = None
    client_params: Optional[Dict[str, Any]] = None
    text_key: str = "content"
    title_key: str = "title"
    metadata_key: str = "metadata"
    batch_size: int = 50


class WeaviateSearchRequest(BaseModel):
    query: str
    limit: int = 10
    collection_name: Optional[str] = None
    siliconflow_api_token: Optional[str] = None
    weaviate_api_key: Optional[str] = None
    client_params: Optional[Dict[str, Any]] = None
    filter_conditions: Optional[List[Dict[str, Any]]] = None
    filters: Optional[Dict[str, Any]] = None


class EmbeddingRequest(BaseModel):
    inputs: Union[str, List[str]]
    api_token: Optional[str] = None
    model: Optional[str] = None
    timeout: Optional[float] = None
from pydantic import BaseModel
from typing import List, Optional, Literal

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

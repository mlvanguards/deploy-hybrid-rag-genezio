from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ProcessingResponse(BaseModel):
    success: bool
    message: str
    document_count: Optional[int] = None


class SearchQuery(BaseModel):
    query: str
    metadata_filter: Optional[Dict[str, Any]] = None
    limit: int = 5


class SearchResponse(BaseModel):
    response: str
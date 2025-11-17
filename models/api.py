from models.models import (
    Document,
    DocumentMetadataFilter,
    DocumentMetadata,
    Query,
    QueryResult,
)
from pydantic import BaseModel
from typing import List, Optional


class UpsertRequest(BaseModel):
    documents: List[Document]


class UpsertResponse(BaseModel):
    ids: List[str]


class QueryRequest(BaseModel):
    queries: List[Query]


class QueryResponse(BaseModel):
    results: List[QueryResult]


class DeleteRequest(BaseModel):
    ids: Optional[List[str]] = None
    filter: Optional[DocumentMetadataFilter] = None
    delete_all: Optional[bool] = False


class DeleteResponse(BaseModel):
    success: bool


class DocumentInfo(BaseModel):
    """Information about a document (aggregated from chunks)"""
    document_id: str
    chunk_count: int
    metadata: DocumentMetadata
    sample_text: Optional[str] = None  # First chunk text as preview


class ListDocumentsRequest(BaseModel):
    limit: Optional[int] = 100
    offset: Optional[int] = 0
    filter: Optional[DocumentMetadataFilter] = None


class ListDocumentsResponse(BaseModel):
    documents: List[DocumentInfo]
    total: int

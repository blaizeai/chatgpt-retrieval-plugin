import os
from typing import Optional, List, Any
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Depends, Body, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from loguru import logger

from services.rerank import rerank  # ← BGE Reranker (FlagEmbedding)

from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
    ListDocumentsRequest,
    ListDocumentsResponse,
    DocumentInfo,
)
from datastore.factory import get_datastore
from services.file import get_document_from_file
from models.models import DocumentMetadata, Source

# --- Auth ---
bearer_scheme = HTTPBearer()
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
assert BEARER_TOKEN is not None


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer" or credentials.credentials != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials


# --- Rerank config ---
# ⚡ Optimisations: Réduit RERANK_K de 20 à 5 et RERANK_FINAL_N de 6 à 3
# Côté Rust on demande top_k=5, donc pas besoin de reranker 20 chunks
RERANK_ENABLE = os.getenv("RERANK_ENABLE", "true").lower() == "true"
RERANK_K = int(os.getenv("RERANK_K", "5"))             # ⚡ Réduit de 20 à 5
RERANK_FINAL_N = int(os.getenv("RERANK_FINAL_N", "3"))  # ⚡ Réduit de 6 à 3


def _get_attr(obj: Any, name: str, default=None):
    """Compat dict / objet pydantic."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _safe_text(x: Any) -> str:
    t = _get_attr(x, "text", "")
    return t or ""


def _maybe_rerank(blocks: List[Any]) -> List[Any]:
    """
    blocks: liste d'éléments {'query': str, 'results': [...]}
    Re-classe chaque bloc avec le reranker si activé, SANS modifier les objets Pydantic.
    """
    if not RERANK_ENABLE:
        return blocks

    try:
        for qr in blocks:
            user_query = _get_attr(qr, "query")
            items = _get_attr(qr, "results", []) or []
            if not user_query or not items:
                continue

            K = min(RERANK_K, len(items))
            cand = items[:K]  # ne pas modifier les objets

            # ⚡ FIX: Appel rerank() une seule fois au lieu de 2 (bug de duplication)
            scores = rerank(user_query, [_safe_text(x) for x in cand])  # List[float]

            # --- LOG DEBUG : id + score index + score rerank ---
            try:
                before = ", ".join(f"{_get_attr(x,'id','?')}:{_get_attr(x,'score',0):.3f}" for x in cand)
                after = ", ".join(f"{_get_attr(x,'id','?')}:{s:.3f}" for s, x in sorted(zip(scores, cand), key=lambda p: p[0], reverse=True))
                logger.debug(f"[RERANK] query={user_query!r} K={len(cand)} before=[{before}] after=[{after}]")
            except Exception:
                pass

            # Trie par score de rerank décroissant, sans modifier les objets
            ranked = [it for it, _ in sorted(zip(cand, scores), key=lambda p: p[0], reverse=True)]
            final = ranked[:max(1, min(RERANK_FINAL_N, len(ranked)))]

            if isinstance(qr, dict):
                qr["results"] = final
            else:
                setattr(qr, "results", final)

        return blocks
    except Exception as e:
        logger.warning(f"Rerank disabled due to error: {e}")
        return blocks


app = FastAPI(dependencies=[Depends(validate_token)])
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

# Sub-app pour exposer uniquement /sub/openapi.json
sub_app = FastAPI(
    title="Retrieval Plugin API",
    description="A retrieval API for querying and filtering documents based on natural language queries and metadata",
    version="1.0.0",
    servers=[{"url": "https://your-app-url.com"}],
    dependencies=[Depends(validate_token)],
)
app.mount("/sub", sub_app)


@app.post("/upsert-file", response_model=UpsertResponse)
async def upsert_file(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
):
    try:
        metadata_obj = (
            DocumentMetadata.parse_raw(metadata)
            if metadata
            else DocumentMetadata(source=Source.file)
        )
    except Exception:
        metadata_obj = DocumentMetadata(source=Source.file)

    document = await get_document_from_file(file, metadata_obj)

    try:
        ids = await datastore.upsert([document])
        return UpsertResponse(ids=ids)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=f"str({e})")


@app.post("/upsert", response_model=UpsertResponse)
async def upsert(request: UpsertRequest = Body(...)):
    try:
        ids = await datastore.upsert(request.documents)
        return UpsertResponse(ids=ids)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.post("/query", response_model=QueryResponse)
async def query_main(request: QueryRequest = Body(...)):
    try:
        results = await datastore.query(request.queries)
        results = _maybe_rerank(results)
        return QueryResponse(results=results)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@sub_app.post(
    "/query",
    response_model=QueryResponse,
    description="Accepts search query objects array each with query and optional filter. Break down complex questions into sub-questions. Refine by criteria (time, source) sparingly. Split queries if ResponseTooLargeError occurs.",
)
async def query(request: QueryRequest = Body(...)):
    try:
        results = await datastore.query(request.queries)
        results = _maybe_rerank(results)
        return QueryResponse(results=results)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.delete("/delete", response_model=DeleteResponse)
async def delete(request: DeleteRequest = Body(...)):
    if not (request.ids or request.filter or request.delete_all):
        raise HTTPException(
            status_code=400,
            detail="One of ids, filter, or delete_all is required",
        )
    try:
        success = await datastore.delete(
            ids=request.ids,
            filter=request.filter,
            delete_all=request.delete_all,
        )
        return DeleteResponse(success=success)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.post("/list", response_model=ListDocumentsResponse)
async def list_documents(request: ListDocumentsRequest = Body(...)):
    """
    List all documents with their metadata, chunk count, and sample text.
    Supports pagination and filtering.
    """
    try:
        documents_data, total = await datastore.list_documents(
            limit=request.limit or 100,
            offset=request.offset or 0,
            filter=request.filter,
        )

        # Convert to DocumentInfo objects
        documents = [
            DocumentInfo(
                document_id=doc["document_id"],
                chunk_count=doc["chunk_count"],
                metadata=DocumentMetadata(**doc["metadata"]),
                sample_text=doc["sample_text"],
            )
            for doc in documents_data
        ]

        return ListDocumentsResponse(documents=documents, total=total)
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()


def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)

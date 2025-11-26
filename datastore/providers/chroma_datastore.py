"""
Chroma datastore support for the ChatGPT retrieval plugin.

Consult the Chroma docs and GitHub repo for more information:
- https://docs.trychroma.com/usage-guide?lang=py
- https://github.com/chroma-core/chroma
- https://www.trychroma.com/
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

import chromadb

from datastore.datastore import DataStore
from models.models import (
    Document,
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentMetadataFilter,
    QueryResult,
    QueryWithEmbedding,
    Source,
)
from services.chunks import get_document_chunks

CHROMA_IN_MEMORY = os.environ.get("CHROMA_IN_MEMORY", "True")
CHROMA_PERSISTENCE_DIR = os.environ.get("CHROMA_PERSISTENCE_DIR", "openai")
CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://127.0.0.1")
CHROMA_PORT = os.environ.get("CHROMA_PORT", "8000")
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "openaiembeddings")


class ChromaDataStore(DataStore):
    def __init__(
        self,
        in_memory: bool = CHROMA_IN_MEMORY,  # type: ignore
        persistence_dir: Optional[str] = CHROMA_PERSISTENCE_DIR,
        collection_name: str = CHROMA_COLLECTION,
        host: str = CHROMA_HOST,
        port: str = CHROMA_PORT,
        client: Optional[chromadb.Client] = None,
    ):
        if client:
            self._client = client
        else:
            if in_memory:
                settings = (
                    chromadb.config.Settings(
                        chroma_db_impl="duckdb+parquet",
                        persist_directory=persistence_dir,
                    )
                    if persistence_dir
                    else chromadb.config.Settings()
                )

                self._client = chromadb.Client(settings=settings)
            else:
                self._client = chromadb.Client(
                    settings=chromadb.config.Settings(
                        chroma_api_impl="rest",
                        chroma_server_host=host,
                        chroma_server_http_port=port,
                    )
                )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=None,
        )

    async def upsert(
        self, documents: List[Document], chunk_token_size: Optional[int] = None
    ) -> List[str]:
        """
        Takes in a list of documents and inserts them into the database. If an id already exists, the document is updated.
        Return a list of document ids.
        """

        chunks = get_document_chunks(documents, chunk_token_size)

        # Chroma has a true upsert, so we don't need to delete first
        return await self._upsert(chunks)

    async def _upsert(self, chunks: Dict[str, List[DocumentChunk]]) -> List[str]:
        """
        Takes in a list of list of document chunks and inserts them into the database.
        Return a list of document ids.
        """

        self._collection.upsert(
            ids=[chunk.id for chunk_list in chunks.values() for chunk in chunk_list],
            embeddings=[
                chunk.embedding
                for chunk_list in chunks.values()
                for chunk in chunk_list
            ],
            documents=[
                chunk.text for chunk_list in chunks.values() for chunk in chunk_list
            ],
            metadatas=[
                self._process_metadata_for_storage(chunk.metadata)
                for chunk_list in chunks.values()
                for chunk in chunk_list
            ],
        )
        return list(chunks.keys())

    def _where_from_query_filter(self, query_filter: DocumentMetadataFilter) -> Dict:
        output = {
            k: v
            for (k, v) in query_filter.dict().items()
            if v is not None and k != "start_date" and k != "end_date" and k != "source"
        }
        if query_filter.source:
            output["source"] = query_filter.source.value
        if query_filter.start_date and query_filter.end_date:
            # Handle 'Z' suffix (UTC timezone) which fromisoformat doesn't support before Python 3.11
            start_date_str = query_filter.start_date.replace('Z', '+00:00')
            end_date_str = query_filter.end_date.replace('Z', '+00:00')
            output["$and"] = [
                {
                    "created_at": {
                        "$gte": int(
                            datetime.fromisoformat(start_date_str).timestamp()
                        )
                    }
                },
                {
                    "created_at": {
                        "$lte": int(
                            datetime.fromisoformat(end_date_str).timestamp()
                        )
                    }
                },
            ]
        elif query_filter.start_date:
            start_date_str = query_filter.start_date.replace('Z', '+00:00')
            output["created_at"] = {
                "$gte": int(datetime.fromisoformat(start_date_str).timestamp())
            }
        elif query_filter.end_date:
            end_date_str = query_filter.end_date.replace('Z', '+00:00')
            output["created_at"] = {
                "$lte": int(datetime.fromisoformat(end_date_str).timestamp())
            }

        return output

    def _process_metadata_for_storage(self, metadata: DocumentChunkMetadata) -> Dict:
        stored_metadata = {}
        if metadata.source:
            stored_metadata["source"] = metadata.source.value
        if metadata.source_id:
            stored_metadata["source_id"] = metadata.source_id
        if metadata.url:
            stored_metadata["url"] = metadata.url
        if metadata.created_at:
            # Handle 'Z' suffix (UTC timezone) which fromisoformat doesn't support before Python 3.11
            created_at_str = metadata.created_at.replace('Z', '+00:00')
            stored_metadata["created_at"] = int(
                datetime.fromisoformat(created_at_str).timestamp()
            )
        if metadata.author:
            stored_metadata["author"] = metadata.author
        if metadata.document_id:
            stored_metadata["document_id"] = metadata.document_id
        if metadata.filename:
            stored_metadata["filename"] = metadata.filename
        if metadata.filesize:
            stored_metadata["filesize"] = metadata.filesize

        return stored_metadata

    def _process_metadata_from_storage(self, metadata: Dict) -> DocumentChunkMetadata:
        return DocumentChunkMetadata(
            source=Source(metadata["source"]) if "source" in metadata else None,
            source_id=metadata.get("source_id", None),
            url=metadata.get("url", None),
            created_at=datetime.fromtimestamp(metadata["created_at"]).isoformat()
            if "created_at" in metadata
            else None,
            author=metadata.get("author", None),
            document_id=metadata.get("document_id", None),
            filename=metadata.get("filename", None),
            filesize=metadata.get("filesize", None),
        )

    async def _query(self, queries: List[QueryWithEmbedding]) -> List[QueryResult]:
        """
        Takes in a list of queries with embeddings and filters and returns a list of query results with matching document chunks and scores.
        """
        results = [
            self._collection.query(
                query_embeddings=[query.embedding],
                include=["documents", "distances", "metadatas"],  # embeddings
                n_results=min(query.top_k, self._collection.count()),  # type: ignore
                where=(
                    self._where_from_query_filter(query.filter) if query.filter else {}
                ),
            )
            for query in queries
        ]

        output = []
        for query, result in zip(queries, results):
            inner_results = []
            (ids,) = result["ids"]
            # (embeddings,) = result["embeddings"]
            (documents,) = result["documents"]
            (metadatas,) = result["metadatas"]
            (distances,) = result["distances"]
            for id_, text, metadata, distance in zip(
                ids,
                documents,
                metadatas,
                distances,  # embeddings (https://github.com/openai/chatgpt-retrieval-plugin/pull/59#discussion_r1154985153)
            ):
                inner_results.append(
                    DocumentChunkWithScore(
                        id=id_,
                        text=text,
                        metadata=self._process_metadata_from_storage(metadata),
                        # embedding=embedding,
                        score=distance,
                    )
                )
            output.append(QueryResult(query=query.query, results=inner_results))

        return output

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[DocumentMetadataFilter] = None,
        delete_all: Optional[bool] = None,
    ) -> bool:
        """
        Removes vectors by ids, filter, or everything in the datastore.
        Multiple parameters can be used at once.
        Returns whether the operation was successful.
        """
        if delete_all:
            self._collection.delete()
            return True

        if ids and len(ids) > 0:
            if len(ids) > 1:
                where_clause = {"$or": [{"document_id": id_} for id_ in ids]}
            else:
                (id_,) = ids
                where_clause = {"document_id": id_}

            if filter:
                where_clause = {
                    "$and": [self._where_from_query_filter(filter), where_clause]
                }
        elif filter:
            where_clause = self._where_from_query_filter(filter)

        self._collection.delete(where=where_clause)
        return True

    async def list_documents(
        self,
        limit: int = 100,
        offset: int = 0,
        filter: Optional[DocumentMetadataFilter] = None,
    ) -> tuple[List[Dict], int]:
        """
        Lists all documents in the datastore with metadata.
        Returns a tuple of (list of document info dicts, total count).
        """
        from collections import defaultdict
        from typing import Dict, Any

        # Get all documents from the collection
        # Chroma get() returns all documents if no filters
        where_clause = self._where_from_query_filter(filter) if filter else {}

        try:
            result = self._collection.get(
                where=where_clause if where_clause else None,
                include=["documents", "metadatas"],
            )
        except Exception:
            # If collection is empty or error, return empty list
            return [], 0

        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])

        # Group chunks by document_id
        documents_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "chunks": [],
            "metadata": None,
        })

        for id_, text, metadata in zip(ids, documents, metadatas):
            doc_id = metadata.get("document_id") if metadata else None

            if not doc_id:
                continue

            documents_map[doc_id]["chunks"].append({
                "id": id_,
                "text": text or "",
            })

            # Store metadata (same for all chunks of a document)
            if documents_map[doc_id]["metadata"] is None:
                documents_map[doc_id]["metadata"] = metadata

        # Convert to list and sort by document_id for consistent ordering
        documents_list = []
        for doc_id, doc_data in sorted(documents_map.items()):
            chunks = doc_data["chunks"]
            metadata = doc_data["metadata"] or {}

            # Convert stored metadata back to original format
            processed_metadata = {}
            if "source" in metadata:
                processed_metadata["source"] = metadata["source"]
            if "source_id" in metadata:
                processed_metadata["source_id"] = metadata["source_id"]
            if "url" in metadata:
                processed_metadata["url"] = metadata["url"]
            if "created_at" in metadata:
                # Convert timestamp back to ISO format
                try:
                    processed_metadata["created_at"] = datetime.fromtimestamp(
                        metadata["created_at"]
                    ).isoformat() + "Z"
                except (ValueError, TypeError):
                    processed_metadata["created_at"] = None
            if "author" in metadata:
                processed_metadata["author"] = metadata["author"]
            if "document_id" in metadata:
                processed_metadata["document_id"] = metadata["document_id"]
            if "filename" in metadata:
                processed_metadata["filename"] = metadata["filename"]
            if "filesize" in metadata:
                processed_metadata["filesize"] = metadata["filesize"]

            documents_list.append({
                "document_id": doc_id,
                "chunk_count": len(chunks),
                "metadata": processed_metadata,
                "sample_text": chunks[0]["text"][:200] if chunks else None,
            })

        total = len(documents_list)

        # Apply offset and limit for pagination
        paginated_documents = documents_list[offset:offset + limit]

        return paginated_documents, total

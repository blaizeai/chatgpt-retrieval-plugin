# New Route: POST /list - List Documents

## Summary

Added a new API endpoint to list all uploaded documents with their metadata, chunk count, and preview text.

## Changes Made

### 1. New Models (`models/api.py`)

Added three new Pydantic models:

- **`DocumentInfo`**: Contains information about a single document
  - `document_id`: UUID of the document
  - `chunk_count`: Number of chunks the document was split into
  - `metadata`: Document metadata (source, author, etc.)
  - `sample_text`: Preview of first chunk (max 200 chars)

- **`ListDocumentsRequest`**: Request body for `/list` endpoint
  - `limit`: Max results per page (default: 100)
  - `offset`: Pagination offset (default: 0)
  - `filter`: Optional metadata filter

- **`ListDocumentsResponse`**: Response from `/list` endpoint
  - `documents`: List of `DocumentInfo` objects
  - `total`: Total count of documents matching filter

### 2. DataStore Interface (`datastore/datastore.py`)

Added abstract method to base `DataStore` class:

```python
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
```

### 3. Qdrant Implementation (`datastore/providers/qdrant_datastore.py`)

Implemented `list_documents()` for Qdrant:

- Uses `client.scroll()` to retrieve all chunks
- Groups chunks by `document_id`
- Aggregates metadata and counts chunks per document
- Supports pagination (offset/limit)
- Supports metadata filtering

**Algorithm:**
1. Scroll through all points in Qdrant (in batches of 1000)
2. Group chunks by `document_id` using a dictionary
3. Count chunks and extract metadata for each document
4. Sort by `document_id` for consistent ordering
5. Apply pagination (offset/limit)
6. Return paginated results + total count

### 4. API Route (`server/main.py`)

Added new POST endpoint:

```python
@app.post("/list", response_model=ListDocumentsResponse)
async def list_documents(request: ListDocumentsRequest = Body(...)):
    """
    List all documents with their metadata, chunk count, and sample text.
    Supports pagination and filtering.
    """
```

### 5. Documentation

Updated:
- **`help.txt`**: Added detailed documentation with curl examples
- **`CLAUDE.md`**: Updated routes overview and common workflows

### 6. Test Script

Created `test_list_route.py` for quick validation:
- Tests listing all documents
- Tests filtering by metadata
- Tests pagination

## Usage Examples

### Basic listing

```bash
curl -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"limit":10,"offset":0}' | jq .
```

### With filter

```bash
curl -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 50,
    "filter": {
      "source": "file",
      "author": "Alice"
    }
  }' | jq .
```

### Pagination

```bash
# Page 1
curl -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"limit":100,"offset":0}' | jq .

# Page 2
curl -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"limit":100,"offset":100}' | jq .
```

## Response Format

```json
{
  "documents": [
    {
      "document_id": "uuid-1",
      "chunk_count": 5,
      "metadata": {
        "source": "file",
        "author": "Alice",
        "created_at": "2025-01-15T10:30:00Z",
        "source_id": null,
        "url": null
      },
      "sample_text": "This is a preview of the first chunk..."
    }
  ],
  "total": 42
}
```

## Testing

```bash
# Make sure server is running
poetry run dev

# Run test script
python test_list_route.py
```

## Notes

- **Qdrant-specific**: Currently only implemented for Qdrant provider
- **Other providers**: Need to implement `list_documents()` method
- **Performance**: For large datasets, uses scroll API in batches of 1000
- **Ordering**: Documents are sorted by `document_id` for consistency
- **Filtering**: Supports same filters as `/query` endpoint

## Future Improvements

For other vector database providers, implement `list_documents()` in:
- `datastore/providers/pinecone_datastore.py`
- `datastore/providers/weaviate_datastore.py`
- `datastore/providers/chroma_datastore.py`
- etc.

Each implementation should follow the same contract:
- Accept limit, offset, and optional filter
- Return tuple of (documents_list, total_count)
- Group chunks by document_id
- Include metadata and sample text

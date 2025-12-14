# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **RAG (Retrieval-Augmented Generation) service** forked from OpenAI's ChatGPT Retrieval Plugin. It provides semantic search and document retrieval capabilities for the Blaise AI system using vector embeddings.

**Key Features:**
- FastAPI-based REST API for document upsert, query, and deletion
- Hybrid search using BGE-M3 embeddings + BGE reranker
- Support for 15+ vector databases (Qdrant, Pinecone, Weaviate, etc.)
- Automatic GPU acceleration (MPS for Mac Silicon, CUDA for NVIDIA, CPU fallback)
- Document chunking and metadata extraction
- Bearer token authentication

## Development Commands

### Environment Setup

```bash
# Install dependencies (requires Python 3.10)
pip install poetry
poetry env use python3.10
poetry shell
poetry install

# After adding dependencies to pyproject.toml
poetry lock
poetry install
```

### Running the Service

```bash
# Development server (localhost)
poetry run dev

# Production server
poetry run start

# Direct uvicorn (alternative)
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Run all tests
pytest

# Run specific provider tests
pytest tests/datastore/providers/qdrant/

# Run with coverage
pytest --cov=. --cov-report=html

# Quick validation test (~30 seconds)
python quick_test.py

# Performance benchmark (~3-5 minutes)
python benchmark_embeddings.py
```

### Optimization

```bash
# Auto-detect platform and generate optimized config
python optimize_platform.py

# Apply optimizations (creates .env.optimized)
cp .env.optimized .env

# Verify GPU acceleration is active
python quick_test.py
# Should show: "✅ Mac Silicon MPS acceleration ACTIVE" or similar
```

## Architecture

### Request Flow

```
Client (Rust backend)
    ↓ HTTP POST /query with Bearer token
FastAPI Server (server/main.py)
    ↓ Extract query text
Embedding Service (services/bge.py or services/openai.py)
    ↓ Generate embeddings (BGE-M3 local or OpenAI API)
Vector Database (datastore/providers/{provider}_datastore.py)
    ↓ Retrieve top-k chunks
Reranker (services/rerank.py)
    ↓ Re-score with BGE cross-encoder
    ↓ Return top-N results
Response with ranked document chunks
```

### Core Components

#### 1. FastAPI Server (`server/main.py`)

Main endpoints:
- `POST /upsert`: Upload documents (JSON)
- `POST /upsert-file`: Upload files (PDF, DOCX, TXT, PPTX, MD)
- `POST /query`: Semantic search with optional reranking
- `POST /list`: List all uploaded documents with metadata and chunk info
- `DELETE /delete`: Remove documents by ID, filter, or delete all

Authentication: Bearer token via `Authorization: Bearer <token>` header

Reranking is controlled by environment variables:
- `RERANK_ENABLE=true`: Enable BGE reranker (default: true)
- `RERANK_K=5`: Number of candidates to rerank (default: 5)
- `RERANK_FINAL_N=3`: Final results to return (default: 3)

#### 2. Embedding Services

**BGE-M3 Local (`services/bge.py`)** - Recommended for production:
- Uses `BAAI/bge-m3` model from HuggingFace
- Automatic device detection (MPS/CUDA/CPU)
- LRU cache for repeated queries (2000 entries)
- Model warmup on startup
- Batch processing with memory management

**OpenAI API (`services/openai.py`)** - Alternative:
- Uses `text-embedding-3-large` (256 dimensions by default)
- Supports Azure OpenAI deployments
- Configurable via `OPENAI_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`

To switch between them, set `EMBEDDING_SERVICE` in `.env`:
- `EMBEDDING_SERVICE=bge` (local BGE, default)
- `EMBEDDING_SERVICE=openai` (OpenAI API)

#### 3. Vector Database Abstraction

**Factory Pattern** (`datastore/factory.py`):
- Single `get_datastore()` function returns appropriate provider
- Provider selected via `DATASTORE` environment variable

**Base Class** (`datastore/datastore.py`):
```python
class DataStore(ABC):
    async def upsert(documents: List[Document]) -> List[str]
    async def query(queries: List[Query]) -> List[QueryResult]
    async def delete(ids, filter, delete_all) -> bool
```

**Providers** (`datastore/providers/`):
Each provider implements the `DataStore` interface:
- `qdrant_datastore.py`: Qdrant (recommended, default config)
- `pinecone_datastore.py`: Pinecone
- `weaviate_datastore.py`: Weaviate
- `chroma_datastore.py`: Chroma
- `redis_datastore.py`: Redis
- And 10+ more...

#### 4. Document Processing

**Chunking** (`services/chunks.py`):
- Splits documents into ~200 token chunks
- Uses `tiktoken` for accurate tokenization
- Preserves metadata across chunks

**File Parsing** (`services/file.py`):
- PDF: pdfplumber (better UTF-8 and accent support than PyPDF2)
- DOCX: docx2txt
- PPTX: python-pptx
- TXT/MD: Direct text extraction

**Metadata Extraction** (`services/extract_metadata.py`):
- Optional LLM-based metadata extraction
- Extracts: title, author, date, keywords

**PII Detection** (`services/pii_detection.py`):
- Optional PII screening before upload
- Uses OpenAI API to detect sensitive info

#### 5. Reranking (`services/rerank.py`)

**BGE Reranker**:
- Uses `BAAI/bge-reranker-v2-m3` cross-encoder
- Re-scores query-document pairs for relevance
- Automatic device detection (MPS/CUDA/CPU)
- Applied after initial vector search

**Flow**:
1. Vector search returns top-k candidates (e.g., k=20)
2. Reranker scores each candidate against query
3. Return top-N best scored results (e.g., N=3)

## Environment Variables

### Required

```bash
DATASTORE=qdrant                    # Vector DB provider
BEARER_TOKEN=your-secret-token      # API authentication
OPENAI_API_KEY=sk-...              # For OpenAI embeddings (if using)
```

### Embeddings (BGE Local - Recommended)

```bash
EMBEDDING_SERVICE=bge               # Use local BGE (default)
EMBEDDING_MODEL=BAAI/bge-m3         # HuggingFace model
EMBEDDING_DEVICE=mps                # mps, cuda:0, or cpu (auto-detected)
EMBEDDING_BATCH=32                  # Batch size (32 for MPS, 64 for CUDA)
EMBEDDING_MAX_LEN=8192              # Max sequence length
EMBEDDING_CACHE_SIZE=2000           # LRU cache size
EMBEDDING_FP16=false                # Use FP16 (only for CUDA, MPS has bugs)
```

### Embeddings (OpenAI API - Alternative)

```bash
EMBEDDING_SERVICE=openai            # Use OpenAI API
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSION=256             # 256, 512, 1024, or 1536

# Optional: Azure OpenAI
OPENAI_API_BASE=https://your-instance.openai.azure.com/
OPENAI_API_TYPE=azure
OPENAI_EMBEDDINGMODEL_DEPLOYMENTID=your-deployment-name
```

### Reranking

```bash
RERANK_ENABLE=true                  # Enable BGE reranker
RERANK_K=5                          # Candidates to rerank
RERANK_FINAL_N=3                    # Final results
RERANK_DEVICE=mps                   # mps, cuda:0, or cpu (auto-detected)
```

### Vector Database (Qdrant Example)

```bash
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=document_chunks
QDRANT_API_KEY=                     # Optional for local instance
```

See `.env.example` for all provider-specific variables.

## GPU Acceleration

### Automatic Platform Detection

Both BGE embedding and reranker services automatically detect the best available device:

1. **Mac Silicon (M1/M2/M3/M4)**: Uses MPS (Metal Performance Shaders)
   - Expected speedup: 5-10x vs CPU
   - Optimal batch size: 32
   - FP16 disabled (stability issues)

2. **NVIDIA GPU**: Uses CUDA
   - Expected speedup: 10-50x vs CPU
   - Optimal batch size: 64
   - FP16 enabled for faster inference

3. **CPU Fallback**: No GPU detected
   - Baseline performance
   - Batch size: 16

### Platform Optimization

```bash
# Generate optimized config for your platform
python optimize_platform.py

# Review generated config
cat .env.optimized

# Apply optimizations
cp .env .env.backup
cp .env.optimized .env

# Verify acceleration is active
poetry run start
# Look for: "🚀 [BGE] Auto-detected Mac Silicon - using MPS acceleration"
```

### Memory Management

**MPS-specific optimizations** (`services/bge.py:97-103`):
- GPU cache cleared after each batch: `torch.mps.empty_cache()`
- High watermark ratio: `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0`
- Fallback enabled: `PYTORCH_ENABLE_MPS_FALLBACK=1`

**LRU Cache** for repeated queries:
- Default: 2000 entries
- Configurable: `EMBEDDING_CACHE_SIZE=2000`
- Cache key: hash of query text

## Adding a New Vector Database Provider

1. Create provider file: `datastore/providers/your_db_datastore.py`
2. Implement `DataStore` interface:
   ```python
   from datastore.datastore import DataStore

   class YourDBDataStore(DataStore):
       async def _upsert(self, chunks) -> List[str]:
           # Insert chunks into your DB
           pass

       async def _query(self, queries) -> List[QueryResult]:
           # Search your DB and return results
           pass

       async def delete(self, ids, filter, delete_all) -> bool:
           # Delete from your DB
           pass
   ```
3. Add to factory: `datastore/factory.py`
   ```python
   case "yourdb":
       from datastore.providers.your_db_datastore import YourDBDataStore
       return YourDBDataStore()
   ```
4. Document setup: `docs/providers/yourdb/setup.md`
5. Add integration test: `tests/datastore/providers/yourdb/test_yourdb_datastore.py`
6. Update `.env.example` with required variables

## Common Workflows

### Testing a Query Locally

```bash
# Start Qdrant (if using Qdrant)
docker run -p 6333:6333 qdrant/qdrant

# Set environment
export DATASTORE=qdrant
export BEARER_TOKEN=dev-secret
export OPENAI_API_KEY=sk-...  # or use BGE local

# Start server
poetry run dev

# Upload documents
curl -X POST "http://localhost:8000/upsert" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"text": "Paris is the capital of France.", "metadata": {"source": "file"}},
      {"text": "Berlin is the capital of Germany.", "metadata": {"source": "file"}}
    ]
  }'

# List all documents
curl -X POST "http://localhost:8000/list" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}' | jq .

# Query
curl -X POST "http://localhost:8000/query" \
  -H "Authorization: Bearer dev-secret" \
  -H "Content-Type: application/json" \
  -d '{"queries": [{"query": "What is the capital of France?", "top_k": 5}]}'
```

### Switching Vector Databases

```bash
# From Qdrant to Pinecone
export DATASTORE=pinecone
export PINECONE_API_KEY=your-key
export PINECONE_ENVIRONMENT=your-env
export PINECONE_INDEX=your-index

# Restart server
poetry run start
```

### Enabling/Disabling Reranking

```bash
# Disable for faster but less accurate results
export RERANK_ENABLE=false

# Enable with custom settings
export RERANK_ENABLE=true
export RERANK_K=10        # Rerank top 10 candidates
export RERANK_FINAL_N=5   # Return top 5 after reranking
```

## Integration with Blaise Backend

The retrieval-plugin is called by the Rust backend (`backend-rust/agent-server`) via the RAG agent:

**Rust → RAG Service Flow**:
1. Rust backend receives chat request with `tools_allowed=["rag"]`
2. RAG agent (`backend-rust/agent-server/src/rag/`) processes request:
   - Rewrites query using LLM for better retrieval
   - Calls RAG service `POST /query` with bearer token
   - Receives top-k chunks with BM25 + dense + rerank
   - Selects top 2 unique contexts
   - Injects contexts into system message
   - Calls llama-server with augmented context
3. Response returned with citations

**Configuration** (in `backend-rust/agent-server/.env`):
```bash
RAG_API_BASE=http://127.0.0.1:8000
RAG_API_TOKEN=your-bearer-token
RAG_TOP_K=20
```

## Performance Optimization Notes

### Recent Optimizations (see `OPTIMIZATIONS_SUMMARY.md`)

1. **GPU Acceleration**: Auto-detection and platform-specific tuning
2. **Reduced Reranking**: `RERANK_K=5` (was 20), `RERANK_FINAL_N=3` (was 6)
3. **Model Warmup**: First query is fast (no cold start)
4. **Memory Management**: GPU cache cleared between batches
5. **LRU Cache**: Increased from 1000 to 2000 entries

### Benchmarking

```bash
# Quick test (30 seconds)
python quick_test.py

# Full benchmark (3-5 minutes)
python benchmark_embeddings.py
```

Expected results on Mac Silicon (M1/M2/M3):
- Single query: ~50ms (was ~250ms on CPU)
- Batch of 10 queries: ~450ms (was ~2500ms)
- 20 document embeddings: ~150ms (was ~800ms)
- Rerank 5 passages: ~80ms (was ~300ms)

## File Structure

```
retrieval-plugin/
├── server/
│   └── main.py              # FastAPI app, endpoints, reranking logic
├── services/
│   ├── bge.py               # BGE-M3 local embeddings (GPU accelerated)
│   ├── rerank.py            # BGE reranker (cross-encoder)
│   ├── openai.py            # OpenAI API embeddings (alternative)
│   ├── chunks.py            # Document chunking
│   └── file.py              # File parsing (PDF, DOCX, etc.)
├── datastore/
│   ├── datastore.py         # Abstract base class
│   ├── factory.py           # Provider factory
│   └── providers/           # 15+ vector DB implementations
│       ├── qdrant_datastore.py
│       ├── pinecone_datastore.py
│       └── ...
├── models/
│   ├── api.py               # Request/response models
│   └── models.py            # Document and metadata models
├── tests/                   # Integration tests per provider
├── scripts/                 # Batch upload scripts (JSON, JSONL, ZIP)
├── docs/providers/          # Setup guides per vector DB
├── pyproject.toml           # Poetry dependencies
├── optimize_platform.py     # Auto-generate optimized config
├── quick_test.py            # Quick validation test
├── benchmark_embeddings.py  # Performance benchmark
└── help.txt                 # Quick reference for API usage
```

## Troubleshooting

### GPU Acceleration Not Working

```bash
# Check if MPS/CUDA is available
python -c "import torch; print(f'MPS: {torch.backends.mps.is_available()}, CUDA: {torch.cuda.is_available()}')"

# Verify device in logs
poetry run start
# Should see: "🚀 [BGE] Auto-detected Mac Silicon - using MPS acceleration"

# Force CPU for testing
export EMBEDDING_DEVICE=cpu
export RERANK_DEVICE=cpu
```

### Memory Issues

```bash
# Reduce batch size
export EMBEDDING_BATCH=16  # Instead of 32

# Reduce cache size
export EMBEDDING_CACHE_SIZE=1000  # Instead of 2000
```

### Slow Query Performance

```bash
# Check if reranking is enabled (adds latency but improves accuracy)
echo $RERANK_ENABLE

# Benchmark to identify bottleneck
python benchmark_embeddings.py

# Enable debug logging
export PYTORCH_MPS_LOG_LEVEL=DEBUG  # For MPS
poetry run start
```

### Authentication Errors

```bash
# Verify bearer token matches
echo $BEARER_TOKEN

# Test with curl
curl -X POST "http://localhost:8000/query" \
  -H "Authorization: Bearer $BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"queries": [{"query": "test", "top_k": 1}]}'
```

## Important Implementation Details

### Embedding Dimension Consistency

When using BGE-M3, the embedding dimension is fixed at 1024. When using OpenAI embeddings, ensure `EMBEDDING_DIMENSION` matches your vector database configuration.

**Mismatch example** (causes errors):
- `.env`: `EMBEDDING_DIMENSION=256`
- Qdrant collection: 1024 dimensions
- **Fix**: Recreate collection or change embedding model

### Document Chunking

Default chunk size: ~200 tokens (configurable in `services/chunks.py`)
- Overlap: None (chunks are sequential)
- Tokenizer: `tiktoken` (cl100k_base encoding)
- Each chunk gets a unique ID and inherits parent document metadata

### Metadata Filtering

Supported filter fields (see `models/models.py`):
- `source`: str (e.g., "file", "web")
- `source_id`: str
- `document_id`: str (UUID)
- `url`: str
- `created_at`: str (ISO 8601)
- `author`: str

Custom fields can be added by editing `DocumentMetadata` and `DocumentMetadataFilter` classes.

### Reranking Logic

The reranker is applied **after** vector search in `server/main.py`:
1. Vector DB returns top-k results (e.g., k=20)
2. Reranker scores only top `RERANK_K` candidates (e.g., 5)
3. Results sorted by rerank score (not original vector score)
4. Top `RERANK_FINAL_N` returned (e.g., 3)

**Note**: Original vector scores are replaced by rerank scores in the response.

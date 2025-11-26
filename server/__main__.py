#!/usr/bin/env python3
"""
Entry point for RAG service binary (PyInstaller)
"""
import os
import sys
import platform
from pathlib import Path

def get_config_dir():
    """Get the application config directory based on OS"""
    system = platform.system()

    if system == 'Windows':
        base = Path(os.getenv('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    elif system == 'Darwin':  # macOS
        base = Path.home() / 'Library' / 'Application Support'
    else:  # Linux and others
        base = Path(os.getenv('XDG_CONFIG_HOME', Path.home() / '.config'))

    config_dir = base / 'Blaise'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def setup_config():
    """Setup configuration file with defaults"""
    config_dir = get_config_dir()
    env_file = config_dir / 'rag.env'

    # Create default config if it doesn't exist
    if not env_file.exists():
        # Set Chroma data directory in Application Support
        chroma_dir = config_dir / 'chroma_data'

        default_config = f"""# Blaise RAG Service Configuration
# This file is created automatically on first run
# You can modify these values without recompiling the application

# Vector Database Provider - Using Chroma embedded (no separate server needed)
DATASTORE=chroma

# Authentication - CHANGE THIS TOKEN!
# You can add multiple tokens separated by commas: token1,token2,token3
BEARER_TOKEN=change-me-after-install

# Embedding Service (bge for local, openai for API)
EMBEDDING_SERVICE=bge

# Server Configuration
RAG_HOST=127.0.0.1
RAG_PORT=8000

# Reranking Configuration
RERANK_ENABLE=true
RERANK_K=5
RERANK_FINAL_N=3

# Chroma Configuration (embedded mode - no server required)
CHROMA_COLLECTION=blaise_documents
CHROMA_PERSISTENT_DIR={chroma_dir}

# Alternative: Qdrant (requires separate Qdrant server)
# DATASTORE=qdrant
# QDRANT_URL=http://localhost:6333
# QDRANT_COLLECTION=blaise_documents

# Alternative: OpenAI Embeddings (requires API key)
# EMBEDDING_SERVICE=openai
# OPENAI_API_KEY=sk-...
# EMBEDDING_MODEL=text-embedding-3-large
# EMBEDDING_DIMENSION=256
"""
        env_file.write_text(default_config)
        print(f"✅ [RAG Config] Created at: {env_file}")
        print(f"⚠️  [RAG Config] IMPORTANT: Edit this file and change BEARER_TOKEN!")
    else:
        print(f"✅ [RAG Config] Loaded from: {env_file}")

    return env_file

def load_config(env_file):
    """Load environment variables from config file"""
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file, override=True)
        print(f"✅ [RAG Config] Configuration loaded successfully")
    except Exception as e:
        print(f"⚠️  [RAG Config] Warning: Could not load config file: {e}")
        print(f"⚠️  [RAG Config] Using default values")

def main():
    """Main entry point"""
    print("=" * 60)
    print("Blaise RAG Service")
    print("=" * 60)

    # Setup and load configuration
    env_file = setup_config()
    load_config(env_file)

    # Get configuration values
    host = os.getenv("RAG_HOST", "127.0.0.1")
    port = int(os.getenv("RAG_PORT", "8000"))
    datastore = os.getenv("DATASTORE", "chroma")
    embedding_service = os.getenv("EMBEDDING_SERVICE", "bge")

    print(f"📍 [RAG Config] Host: {host}:{port}")
    print(f"📦 [RAG Config] Datastore: {datastore}")
    print(f"🧠 [RAG Config] Embeddings: {embedding_service}")
    print(f"📝 [RAG Config] Config file: {env_file}")
    print("=" * 60)

    # Import and run the FastAPI server
    try:
        import uvicorn
        from server.main import app

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        print(f"❌ [RAG Service] Failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

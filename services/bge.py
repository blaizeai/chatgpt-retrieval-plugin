# services/bge.py
import os
import platform
from typing import List
import numpy as np
from functools import lru_cache
import hashlib
import torch

try:
    from FlagEmbedding import BGEM3FlagModel
except Exception as e:
    raise RuntimeError(
        "FlagEmbedding introuvable. Installe d'abord: pip install FlagEmbedding torch"
    ) from e

# ⚡ Auto-detect optimal device
def _detect_device():
    """Auto-detect best available device"""
    env_device = os.getenv("EMBEDDING_DEVICE")
    if env_device:
        return env_device

    # Mac Silicon (M1/M2/M3)
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        if torch.backends.mps.is_available():
            print("🚀 [BGE] Auto-detected Mac Silicon - using MPS acceleration")
            return "mps"

    # CUDA
    if torch.cuda.is_available():
        print(f"🚀 [BGE] Auto-detected CUDA - using GPU {torch.cuda.get_device_name(0)}")
        return "cuda:0"

    print("⚠️  [BGE] No GPU detected - using CPU (slower)")
    return "cpu"

DEFAULT_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
DEFAULT_DEVICE = _detect_device()
DEFAULT_BATCH = int(os.getenv("EMBEDDING_BATCH", "32" if DEFAULT_DEVICE == "mps" else "64"))
DEFAULT_MAX_LEN = int(os.getenv("EMBEDDING_MAX_LEN", "8192"))
# ⚡ Cache LRU pour les queries (souvent répétées)
CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "2000"))

_model = None

def _load_model():
    global _model
    if _model is not None:
        return _model

    # ⚡ FP16 uniquement pour CUDA (MPS a des bugs avec FP16)
    use_fp16 = DEFAULT_DEVICE.startswith("cuda") and os.getenv("EMBEDDING_FP16", "true").lower() == "true"

    print(f"📦 [BGE] Loading model {DEFAULT_MODEL} on {DEFAULT_DEVICE} (fp16={use_fp16})")
    _model = BGEM3FlagModel(DEFAULT_MODEL, devices=[DEFAULT_DEVICE], use_fp16=use_fp16)

    # ⚡ Warmup: Premier passage pour compiler/optimiser
    print("🔥 [BGE] Warming up model...")
    try:
        _ = _model.encode(["warmup text"], return_dense=True, return_sparse=False, return_colbert_vecs=False)
        print("✅ [BGE] Model ready!")
    except Exception as e:
        print(f"⚠️  [BGE] Warmup failed (non-critical): {e}")

    return _model

def _l2_normalize(mat: np.ndarray) -> np.ndarray:
    # évite division par zéro
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return mat / norms

def _encode(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    m = _load_model()
    out = []

    # ⚡ Optimisation: Process en batches avec gestion mémoire MPS
    for i in range(0, len(texts), DEFAULT_BATCH):
        chunk = texts[i:i+DEFAULT_BATCH]

        # ⚠️ ne PAS passer normalize_embeddings ici (signature varie selon versions)
        res = m.encode(
            chunk,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
            max_length=DEFAULT_MAX_LEN,
        )
        vecs = np.asarray(res["dense_vecs"], dtype=np.float32, order="C")
        vecs = _l2_normalize(vecs)  # normalisation L2 pour Cosine/IP
        out.extend(v.tolist() for v in vecs)

        # ⚡ Libère la mémoire GPU après chaque batch (important pour MPS)
        if DEFAULT_DEVICE == "mps":
            try:
                torch.mps.empty_cache()
            except:
                pass
        elif DEFAULT_DEVICE.startswith("cuda"):
            torch.cuda.empty_cache()

    return out

def embed_documents(texts: List[str]) -> List[List[float]]:
    return _encode(texts)

# ⚡ Cache LRU pour les queries (hashé car lru_cache nécessite des args hashable)
@lru_cache(maxsize=CACHE_SIZE)
def _cached_embed_query(text_hash: str, text: str) -> tuple:
    """Helper cacheable qui retourne un tuple (pour être hashable)"""
    vec = _encode([text])[0]
    return tuple(vec)  # tuple est hashable pour lru_cache

def embed_query(text: str) -> List[float]:
    """Embed une query avec cache LRU"""
    text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]  # Hash court
    cached_tuple = _cached_embed_query(text_hash, text)
    return list(cached_tuple)  # Convertir tuple -> list pour compatibilité

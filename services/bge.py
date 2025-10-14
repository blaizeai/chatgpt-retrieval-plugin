# services/bge.py
import os
from typing import List
import numpy as np

try:
    from FlagEmbedding import BGEM3FlagModel
except Exception as e:
    raise RuntimeError(
        "FlagEmbedding introuvable. Installe d'abord: pip install FlagEmbedding torch"
    ) from e

DEFAULT_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
DEFAULT_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")  # "cpu" | "cuda:0"
DEFAULT_BATCH = int(os.getenv("EMBEDDING_BATCH", "64"))
DEFAULT_MAX_LEN = int(os.getenv("EMBEDDING_MAX_LEN", "8192"))

_model = None

def _load_model():
    global _model
    if _model is not None:
        return _model
    use_fp16 = DEFAULT_DEVICE.startswith("cuda") and os.getenv("EMBEDDING_FP16", "true").lower() == "true"
    _model = BGEM3FlagModel(DEFAULT_MODEL, devices=[DEFAULT_DEVICE], use_fp16=use_fp16)
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
    return out

def embed_documents(texts: List[str]) -> List[List[float]]:
    return _encode(texts)

def embed_query(text: str) -> List[float]:
    return _encode([text])[0]

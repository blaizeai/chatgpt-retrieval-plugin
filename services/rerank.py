# services/rerank.py
import os
from typing import List
from FlagEmbedding import FlagReranker

_R = None
def _get():
    global _R
    if _R is None:
        model = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
        device = os.getenv("RERANK_DEVICE", "cpu")   # "cpu" | "cuda:0"
        use_fp16 = device.startswith("cuda")
        _R = FlagReranker(model, use_fp16=use_fp16, devices=[device])
    return _R

def rerank(query: str, passages: List[str]) -> List[float]:
    pairs = [[query, p] for p in passages]
    return _get().compute_score(pairs, normalize=True)

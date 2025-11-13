# services/rerank.py
import os
import platform
from typing import List
import torch
from FlagEmbedding import FlagReranker

# ⚡ Auto-detect optimal device
def _detect_rerank_device():
    """Auto-detect best available device for reranker"""
    env_device = os.getenv("RERANK_DEVICE")
    if env_device:
        return env_device

    # Mac Silicon (M1/M2/M3)
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        if torch.backends.mps.is_available():
            print("🚀 [RERANK] Auto-detected Mac Silicon - using MPS acceleration")
            return "mps"

    # CUDA
    if torch.cuda.is_available():
        print(f"🚀 [RERANK] Auto-detected CUDA - using GPU")
        return "cuda:0"

    print("⚠️  [RERANK] No GPU detected - using CPU")
    return "cpu"

_R = None
_DEVICE = _detect_rerank_device()

def _get():
    global _R
    if _R is None:
        model = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
        # ⚡ FP16 uniquement pour CUDA (MPS a des bugs avec FP16)
        use_fp16 = _DEVICE.startswith("cuda")

        print(f"📦 [RERANK] Loading model {model} on {_DEVICE} (fp16={use_fp16})")
        _R = FlagReranker(model, use_fp16=use_fp16, devices=[_DEVICE])

        # ⚡ Warmup
        print("🔥 [RERANK] Warming up model...")
        try:
            _ = _R.compute_score([["test", "warmup"]], normalize=True)
            print("✅ [RERANK] Model ready!")
        except Exception as e:
            print(f"⚠️  [RERANK] Warmup failed (non-critical): {e}")

    return _R

def rerank(query: str, passages: List[str]) -> List[float]:
    """Rerank passages given a query"""
    if not passages:
        return []

    pairs = [[query, p] for p in passages]
    scores = _get().compute_score(pairs, normalize=True)

    # ⚡ Libère la mémoire GPU après reranking (important pour MPS)
    if _DEVICE == "mps":
        try:
            torch.mps.empty_cache()
        except:
            pass
    elif _DEVICE.startswith("cuda"):
        torch.cuda.empty_cache()

    return scores

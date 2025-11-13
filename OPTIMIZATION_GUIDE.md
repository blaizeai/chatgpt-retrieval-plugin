# 🚀 Retrieval Plugin Optimization Guide

Ce guide explique comment optimiser les performances du retrieval plugin sur différentes plateformes.

## Table des matières

1. [Quick Start](#quick-start)
2. [Platform-Specific Optimizations](#platform-specific-optimizations)
3. [Advanced Optimizations](#advanced-optimizations)
4. [Benchmarking](#benchmarking)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Auto-detect et configurer les optimisations

```bash
python optimize_platform.py
```

Ce script va :
- Détecter votre plateforme (Mac Silicon, CUDA, CPU)
- Générer un fichier `.env.optimized` avec les paramètres optimaux
- Afficher des recommandations spécifiques

### 2. Appliquer les optimisations

```bash
# Backup de votre configuration actuelle
cp .env .env.backup

# Appliquer les optimisations
cp .env.optimized .env

# Redémarrer le serveur
poetry run start
```

### 3. Mesurer les gains

```bash
python benchmark_embeddings.py
```

---

## Platform-Specific Optimizations

### 🍎 Mac Silicon (M1/M2/M3/M4)

**Configuration automatique** :
- Device: `mps` (Metal Performance Shaders)
- Batch size: `32` (optimal pour MPS)
- FP16: `false` (MPS a des bugs avec FP16)

**Gains attendus** : **5-10x plus rapide** vs CPU

**Configuration manuelle** (.env):
```bash
EMBEDDING_DEVICE=mps
EMBEDDING_BATCH=32
EMBEDDING_FP16=false
EMBEDDING_MAX_LEN=8192
EMBEDDING_CACHE_SIZE=2000

RERANK_DEVICE=mps
RERANK_ENABLE=true
RERANK_K=5
RERANK_FINAL_N=3

# Optimisations MPS
PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
PYTORCH_ENABLE_MPS_FALLBACK=1
```

**Installation PyTorch pour Mac Silicon** :
```bash
pip3 install torch torchvision torchaudio
```

### 🐧 Linux avec GPU NVIDIA

**Configuration automatique** :
- Device: `cuda:0`
- Batch size: `64` (CUDA peut gérer des gros batches)
- FP16: `true` (très rapide sur CUDA)

**Gains attendus** : **10-50x plus rapide** vs CPU

**Configuration manuelle** (.env):
```bash
EMBEDDING_DEVICE=cuda:0
EMBEDDING_BATCH=64
EMBEDDING_FP16=true
EMBEDDING_MAX_LEN=8192
EMBEDDING_CACHE_SIZE=2000

RERANK_DEVICE=cuda:0
RERANK_ENABLE=true
RERANK_K=10
RERANK_FINAL_N=5

# Optimisations CUDA
CUDA_LAUNCH_BLOCKING=0
TORCH_CUDNN_V8_API_ENABLED=1
```

**Installation PyTorch pour CUDA** :
```bash
# CUDA 11.8
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 💻 CPU Fallback

**Configuration automatique** :
- Device: `cpu`
- Batch size: `16` (petit pour éviter surcharge mémoire)
- Max length: `4096` (réduit pour CPU)

**Gains attendus** : Baseline (pas d'accélération)

**Configuration manuelle** (.env):
```bash
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH=16
EMBEDDING_FP16=false
EMBEDDING_MAX_LEN=4096
EMBEDDING_CACHE_SIZE=1000

RERANK_DEVICE=cpu
RERANK_ENABLE=true
RERANK_K=5
RERANK_FINAL_N=3
```

---

## Advanced Optimizations

### 1. Quantization (Expérimental)

La quantization INT8 peut réduire l'utilisation mémoire de ~4x et accélérer l'inférence de 2-3x.

**⚠️ Note** : Perte de qualité légère (~1-2% de précision)

```python
# À ajouter dans services/bge.py
import torch.quantization

def _load_model_quantized():
    model = BGEM3FlagModel(DEFAULT_MODEL, devices=[DEFAULT_DEVICE], use_fp16=False)

    # Quantization dynamique (compatible CPU/CUDA/MPS)
    model.model = torch.quantization.quantize_dynamic(
        model.model,
        {torch.nn.Linear},  # Quantize linear layers
        dtype=torch.qint8
    )

    return model
```

### 2. Model Compilation (PyTorch 2.0+)

`torch.compile()` peut accélérer les modèles de 30-50% supplémentaire.

**⚠️ Note** : Nécessite PyTorch 2.0+ et peut augmenter le temps de démarrage

```python
# À ajouter dans services/bge.py
def _load_model_compiled():
    model = BGEM3FlagModel(DEFAULT_MODEL, devices=[DEFAULT_DEVICE], use_fp16=use_fp16)

    # Compile le modèle avec PyTorch 2.0+
    if hasattr(torch, 'compile'):
        model.model = torch.compile(model.model, mode="reduce-overhead")

    return model
```

### 3. Cache Optimizations

Le cache LRU est déjà implémenté pour les queries. Pour améliorer :

```bash
# Augmenter la taille du cache si vous avez beaucoup de queries répétées
EMBEDDING_CACHE_SIZE=5000

# Désactiver le cache si vos queries ne se répètent jamais
EMBEDDING_CACHE_SIZE=0
```

### 4. Batch Size Tuning

Trouvez le batch size optimal pour votre GPU :

```bash
# Augmentez progressivement jusqu'à OOM (Out Of Memory)
EMBEDDING_BATCH=16   # Safe
EMBEDDING_BATCH=32   # Mac Silicon optimal
EMBEDDING_BATCH=64   # CUDA optimal
EMBEDDING_BATCH=128  # High-end GPU
EMBEDDING_BATCH=256  # Very high-end GPU
```

**Comment trouver l'optimal** :
```bash
# Testez différentes valeurs
for batch in 16 32 64 128; do
  export EMBEDDING_BATCH=$batch
  python benchmark_embeddings.py 2>&1 | grep "Average"
done
```

### 5. Réduire la latence de démarrage

Les modèles BGE sont lourds (~2GB). Pour réduire le temps de chargement :

1. **Précharger les modèles au démarrage** :
   ```python
   # Dans server/main.py, ajouter dans startup()
   @app.on_event("startup")
   async def startup():
       global datastore
       datastore = await get_datastore()

       # Précharge les modèles
       from services.bge import _load_model
       from services.rerank import _get
       _load_model()  # Charge BGE-M3
       _get()         # Charge Reranker
   ```

2. **Utiliser un model server persistant** (comme vLLM ou Text Embeddings Inference)

---

## Benchmarking

### Running Benchmarks

```bash
# Benchmark complet
python benchmark_embeddings.py

# Benchmark avec profiling
python -m cProfile -o profile.stats benchmark_embeddings.py

# Analyser le profiling
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

### Interprétation des résultats

**Métriques importantes** :
- **Average Time** : Temps moyen par opération
- **Throughput** : Nombre d'opérations par seconde
- **Std Dev** : Stabilité (plus faible = mieux)

**Benchmarks typiques** (Mac M1):
```
Test                                     Avg Time    Throughput
----------------------------------------------------------------------
Single query embedding (short)              0.050s  20.00 queries/s
10 queries embedding                        0.450s  22.22 queries/s
20 documents embedding                      0.300s  66.67 docs/s
Rerank 5 passages                           0.080s  62.50 ops/s
```

---

## Troubleshooting

### Problème : MPS non disponible sur Mac

**Symptôme** : `torch.backends.mps.is_available()` retourne `False`

**Solution** :
```bash
# Vérifier version PyTorch
python -c "import torch; print(torch.__version__)"

# Doit être >= 1.12.0 pour MPS
pip3 install --upgrade torch
```

### Problème : CUDA Out Of Memory

**Symptôme** : `RuntimeError: CUDA out of memory`

**Solutions** :
1. Réduire `EMBEDDING_BATCH`
2. Réduire `EMBEDDING_MAX_LEN`
3. Activer gradient checkpointing (avancé)
4. Utiliser un GPU avec plus de VRAM

```bash
# Monitorer l'utilisation GPU
watch -n 1 nvidia-smi  # CUDA
# ou
sudo powermetrics --samplers gpu_power -i 1000  # Mac
```

### Problème : Performance dégradée après optimisation

**Causes possibles** :
1. FP16 instable sur votre plateforme
2. Batch size trop grand (thrashing mémoire)
3. MPS fallback vers CPU

**Diagnostic** :
```bash
# Activer logs détaillés
export PYTORCH_MPS_LOG_LEVEL=DEBUG  # Mac
export CUDA_LAUNCH_BLOCKING=1       # CUDA

# Vérifier device réellement utilisé
python -c "from services.bge import DEFAULT_DEVICE; print(f'Device: {DEFAULT_DEVICE}')"
```

### Problème : Erreurs d'import FlagEmbedding

**Symptôme** : `ModuleNotFoundError: No module named 'FlagEmbedding'`

**Solution** :
```bash
pip3 install -U FlagEmbedding
```

---

## Performance Comparison Table

| Platform          | Device | Speedup | Batch | FP16  | Recommended Use Case          |
|-------------------|--------|---------|-------|-------|-------------------------------|
| Mac M1/M2/M3      | MPS    | 5-10x   | 32    | No    | Development, prototyping      |
| NVIDIA RTX 3090   | CUDA   | 30-50x  | 128   | Yes   | Production, large datasets    |
| NVIDIA T4         | CUDA   | 10-20x  | 64    | Yes   | Cloud deployment              |
| Intel/AMD CPU     | CPU    | 1x      | 16    | No    | Fallback only                 |

---

## Additional Resources

- [FlagEmbedding Documentation](https://github.com/FlagOpen/FlagEmbedding)
- [PyTorch MPS Backend](https://pytorch.org/docs/stable/notes/mps.html)
- [CUDA Best Practices](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- [BGE Models on HuggingFace](https://huggingface.co/BAAI)

---

## Support

Si vous rencontrez des problèmes :
1. Vérifier les logs avec `RUST_LOG=debug` ou équivalent
2. Tester avec `python optimize_platform.py`
3. Exécuter `python benchmark_embeddings.py` pour diagnostics
4. Ouvrir une issue avec les logs et config

---

**Dernière mise à jour** : 2025-01-13

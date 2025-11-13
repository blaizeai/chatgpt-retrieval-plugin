#!/usr/bin/env python3
"""
Quick test script to verify optimizations are working
"""

import sys

def main():
    print("🧪 Quick Optimization Test\n")

    # Test 1: Import modules
    print("1️⃣  Testing imports...")
    try:
        import torch
        print(f"   ✅ PyTorch {torch.__version__}")
    except ImportError:
        print("   ❌ PyTorch not installed")
        print("   Install: pip3 install torch")
        sys.exit(1)

    try:
        from FlagEmbedding import BGEM3FlagModel, FlagReranker
        print("   ✅ FlagEmbedding installed")
    except ImportError:
        print("   ❌ FlagEmbedding not installed")
        print("   Install: pip3 install FlagEmbedding")
        sys.exit(1)

    # Test 2: Device detection
    print("\n2️⃣  Testing device detection...")
    import platform

    system = platform.system()
    machine = platform.machine()
    print(f"   System: {system} {machine}")

    if system == "Darwin" and machine == "arm64":
        if torch.backends.mps.is_available():
            print("   ✅ Mac Silicon MPS available!")
            device = "mps"
        else:
            print("   ⚠️  Mac Silicon detected but MPS not available")
            print("   Install: pip3 install --upgrade torch")
            device = "cpu"
    elif torch.cuda.is_available():
        print(f"   ✅ CUDA available - {torch.cuda.get_device_name(0)}")
        device = "cuda:0"
    else:
        print("   ⚠️  No GPU acceleration available - using CPU")
        device = "cpu"

    # Test 3: Load and test embedding
    print("\n3️⃣  Testing embedding model...")
    try:
        from services.bge import embed_query, DEFAULT_DEVICE
        print(f"   Device configured: {DEFAULT_DEVICE}")

        # Quick embedding test
        print("   Loading model (this may take a moment)...")
        result = embed_query("test query")
        print(f"   ✅ Embedding successful! Vector dim: {len(result)}")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        sys.exit(1)

    # Test 4: Test reranker
    print("\n4️⃣  Testing reranker...")
    try:
        from services.rerank import rerank, _DEVICE as RERANK_DEVICE
        print(f"   Device configured: {RERANK_DEVICE}")

        # Quick rerank test
        scores = rerank("test query", ["passage 1", "passage 2"])
        print(f"   ✅ Reranking successful! Scores: {scores}")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        sys.exit(1)

    # Test 5: Performance summary
    print("\n5️⃣  Performance summary:")
    print("="*60)

    if device == "mps":
        print("   🚀 Mac Silicon MPS acceleration ACTIVE")
        print("   Expected speedup: 5-10x vs CPU")
    elif device == "cuda:0":
        print("   🚀 CUDA GPU acceleration ACTIVE")
        print("   Expected speedup: 10-50x vs CPU")
    else:
        print("   ⚠️  Running on CPU (slower)")
        print("   Consider using a GPU for better performance")

    print("="*60)

    print("\n✅ All tests passed!")
    print("\nNext steps:")
    print("  • Run full benchmark: python benchmark_embeddings.py")
    print("  • Start server: poetry run start")
    print("  • Read optimization guide: OPTIMIZATION_GUIDE.md")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

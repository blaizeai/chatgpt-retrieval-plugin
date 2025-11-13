#!/usr/bin/env python3
"""
Compare performance before (CPU) and after (GPU) optimization
"""

import os
import time
import statistics


def benchmark_device(device_name, device_value, iterations=5):
    """Benchmark with specific device"""
    print(f"\n{'='*70}")
    print(f"🧪 Testing device: {device_name.upper()}")
    print(f"{'='*70}")

    # Set device
    os.environ["EMBEDDING_DEVICE"] = device_value
    os.environ["RERANK_DEVICE"] = device_value

    # Reload modules to apply new device
    import sys
    modules_to_reload = [k for k in sys.modules.keys() if 'services' in k]
    for mod in modules_to_reload:
        del sys.modules[mod]

    from services.bge import embed_query, embed_documents
    from services.rerank import rerank

    results = {}

    # Test 1: Single query
    print("\n1️⃣  Single query embedding...")
    times = []
    for i in range(iterations):
        start = time.perf_counter()
        _ = embed_query("What is machine learning?")
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        print(f"   Iteration {i+1}: {elapsed:.3f}s")

    avg = statistics.mean(times)
    results['single_query'] = avg
    print(f"   Average: {avg:.3f}s")

    # Test 2: Batch documents
    print("\n2️⃣  Batch document embedding (20 docs)...")
    docs = ["Machine learning document"] * 20
    times = []
    for i in range(iterations):
        start = time.perf_counter()
        _ = embed_documents(docs)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        print(f"   Iteration {i+1}: {elapsed:.3f}s")

    avg = statistics.mean(times)
    results['batch_docs'] = avg
    print(f"   Average: {avg:.3f}s")

    # Test 3: Reranking
    print("\n3️⃣  Reranking (5 passages)...")
    passages = ["passage " + str(i) for i in range(5)]
    times = []
    for i in range(iterations):
        start = time.perf_counter()
        _ = rerank("test query", passages)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        print(f"   Iteration {i+1}: {elapsed:.3f}s")

    avg = statistics.mean(times)
    results['rerank'] = avg
    print(f"   Average: {avg:.3f}s")

    return results


def print_comparison(cpu_results, gpu_results, gpu_name):
    """Print comparison table"""
    print("\n" + "="*70)
    print("📊 PERFORMANCE COMPARISON")
    print("="*70)
    print()
    print(f"{'Test':<30} {'CPU':<12} {gpu_name.upper():<12} {'Speedup':<12}")
    print("-"*70)

    tests = [
        ('single_query', 'Single Query'),
        ('batch_docs', '20 Documents'),
        ('rerank', 'Rerank 5 passages'),
    ]

    speedups = []
    for key, name in tests:
        cpu_time = cpu_results[key]
        gpu_time = gpu_results[key]
        speedup = cpu_time / gpu_time

        speedups.append(speedup)

        print(f"{name:<30} {cpu_time:>10.3f}s  {gpu_time:>10.3f}s  {speedup:>10.2f}x")

    print("-"*70)
    avg_speedup = statistics.mean(speedups)
    print(f"{'Average Speedup':<30} {'':>10}  {'':>10}  {avg_speedup:>10.2f}x")
    print("="*70)

    # Performance assessment
    print("\n📈 Performance Assessment:")
    if avg_speedup >= 10:
        print("   🚀 EXCELLENT! 10x+ faster - optimal GPU acceleration")
    elif avg_speedup >= 5:
        print("   ✅ GREAT! 5-10x faster - good GPU acceleration")
    elif avg_speedup >= 2:
        print("   👍 GOOD! 2-5x faster - moderate acceleration")
    elif avg_speedup >= 1.5:
        print("   ⚠️  MODEST: 1.5-2x faster - check GPU configuration")
    else:
        print("   ❌ POOR: <1.5x faster - GPU not working properly?")

    print()
    print(f"   Time saved per 100 queries: {(cpu_results['single_query'] - gpu_results['single_query']) * 100:.1f}s")
    print(f"   Time saved per 1000 docs: {(cpu_results['batch_docs'] - gpu_results['batch_docs']) * 50:.1f}s")


def main():
    import sys
    import platform

    print("🔬 Performance Comparison Tool")
    print("="*70)

    # Detect available devices
    system = platform.system()
    machine = platform.machine()

    print(f"Platform: {system} {machine}")

    try:
        import torch
        print(f"PyTorch: {torch.__version__}")

        has_mps = system == "Darwin" and machine == "arm64" and torch.backends.mps.is_available()
        has_cuda = torch.cuda.is_available()

        if has_mps:
            print("GPU: Mac Silicon MPS available ✅")
            gpu_device = "mps"
            gpu_name = "MPS"
        elif has_cuda:
            gpu_name_str = torch.cuda.get_device_name(0)
            print(f"GPU: CUDA available - {gpu_name_str} ✅")
            gpu_device = "cuda:0"
            gpu_name = "CUDA"
        else:
            print("GPU: None available ❌")
            print("\n⚠️  No GPU acceleration available.")
            print("This comparison requires GPU support (MPS or CUDA).")
            sys.exit(1)

    except ImportError:
        print("❌ PyTorch not installed")
        sys.exit(1)

    print()
    print("⏱️  This will take ~2-3 minutes...")
    print()

    # Benchmark CPU
    print("\n" + "="*70)
    print("PHASE 1: Benchmarking CPU (baseline)")
    print("="*70)
    cpu_results = benchmark_device("cpu", "cpu", iterations=3)

    # Benchmark GPU
    print("\n" + "="*70)
    print(f"PHASE 2: Benchmarking {gpu_name} (optimized)")
    print("="*70)
    gpu_results = benchmark_device(gpu_name, gpu_device, iterations=3)

    # Print comparison
    print_comparison(cpu_results, gpu_results, gpu_name)

    # Recommendations
    print("\n💡 Recommendations:")
    print("="*70)

    avg_speedup = statistics.mean([
        cpu_results[k] / gpu_results[k]
        for k in ['single_query', 'batch_docs', 'rerank']
    ])

    if avg_speedup >= 3:
        print("✅ Your optimizations are working well!")
        print()
        print("To use these optimizations:")
        print("  1. Ensure .env has: EMBEDDING_DEVICE=" + gpu_device)
        print("  2. Restart your server: poetry run start")
        print("  3. Monitor logs for device confirmation")
    else:
        print("⚠️  Performance gain is lower than expected.")
        print()
        print("Troubleshooting steps:")
        print("  1. Check PyTorch installation: pip3 install --upgrade torch")
        print("  2. Verify device availability:")
        if gpu_device == "mps":
            print("     python3 -c 'import torch; print(torch.backends.mps.is_available())'")
        else:
            print("     python3 -c 'import torch; print(torch.cuda.is_available())'")
        print("  3. Check .env configuration")
        print("  4. Review PYTORCH logs with DEBUG level")

    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Comparison interrupted")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

#!/usr/bin/env python3
"""
Benchmark script pour mesurer les performances du retrieval plugin
Compare les performances CPU vs GPU (MPS/CUDA)
"""

import time
import sys
from typing import List, Dict
import statistics

# Import des services
try:
    from services.bge import embed_query, embed_documents, DEFAULT_DEVICE
    from services.rerank import rerank, _DEVICE as RERANK_DEVICE
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're in the chatgpt-retrieval-plugin directory")
    sys.exit(1)


class Benchmark:
    def __init__(self):
        self.results: List[Dict] = []

    def run_test(self, name: str, func, *args, warmup=1, iterations=5):
        """Run a benchmark test"""
        print(f"\n{'='*70}")
        print(f"🧪 Test: {name}")
        print(f"{'='*70}")

        # Warmup
        print(f"🔥 Warming up ({warmup} iterations)...")
        for _ in range(warmup):
            func(*args)

        # Actual benchmark
        print(f"⏱️  Running benchmark ({iterations} iterations)...")
        times = []
        for i in range(iterations):
            start = time.perf_counter()
            func(*args)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            print(f"   Iteration {i+1}/{iterations}: {elapsed:.3f}s")

        # Statistics
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0

        result = {
            "name": name,
            "avg_time": avg_time,
            "median_time": median_time,
            "std_dev": std_dev,
            "min_time": min(times),
            "max_time": max(times),
        }

        self.results.append(result)

        print(f"\n📊 Results:")
        print(f"   Average: {avg_time:.3f}s")
        print(f"   Median:  {median_time:.3f}s")
        print(f"   Std Dev: {std_dev:.3f}s")
        print(f"   Min:     {result['min_time']:.3f}s")
        print(f"   Max:     {result['max_time']:.3f}s")

        return result

    def print_summary(self):
        """Print summary of all benchmarks"""
        print("\n" + "="*70)
        print("📈 BENCHMARK SUMMARY")
        print("="*70)
        print(f"Embedding Device: {DEFAULT_DEVICE}")
        print(f"Reranking Device: {RERANK_DEVICE}")
        print()

        if not self.results:
            print("No results to display")
            return

        print(f"{'Test':<40} {'Avg Time':<12} {'Throughput'}")
        print("-"*70)

        for result in self.results:
            name = result['name']
            avg = result['avg_time']
            throughput = ""

            # Calculate throughput for relevant tests
            if "Single query" in name:
                throughput = f"{1/avg:.2f} queries/s"
            elif "10 queries" in name:
                throughput = f"{10/avg:.2f} queries/s"
            elif "documents" in name.lower():
                # Extract doc count from name if possible
                try:
                    doc_count = int(name.split()[0])
                    throughput = f"{doc_count/avg:.2f} docs/s"
                except:
                    pass

            print(f"{name:<40} {avg:>10.3f}s  {throughput}")

        print("="*70)

    def compare_with_baseline(self, cpu_avg: float, gpu_avg: float):
        """Compare GPU vs CPU performance"""
        speedup = cpu_avg / gpu_avg
        print(f"\n🚀 Speedup: {speedup:.2f}x faster on {DEFAULT_DEVICE.upper()} vs CPU")
        print(f"   Time reduction: {(1 - gpu_avg/cpu_avg)*100:.1f}%")


def main():
    print("🚀 Retrieval Plugin Benchmark Suite")
    print("="*70)

    benchmark = Benchmark()

    # Sample data
    short_query = "What is machine learning?"
    long_query = "Explain in detail how transformer models work in natural language processing"

    short_docs = [
        "Machine learning is a subset of AI",
        "Deep learning uses neural networks",
        "NLP processes natural language",
    ]

    medium_docs = [
        "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
        "Deep learning is a type of machine learning based on artificial neural networks.",
        "Natural language processing enables computers to understand human language.",
        "Computer vision allows machines to interpret and analyze visual information.",
        "Reinforcement learning trains agents through rewards and penalties.",
    ] * 4  # 20 documents

    long_docs = [
        "Transformers revolutionized NLP by introducing self-attention mechanisms that allow models to weigh the importance of different words in a sentence.",
        "BERT (Bidirectional Encoder Representations from Transformers) uses masked language modeling to learn contextualized word representations.",
        "GPT models use autoregressive language modeling to generate coherent text by predicting the next word in a sequence.",
        "Fine-tuning pre-trained language models on specific tasks has become a standard approach in NLP applications.",
        "The attention mechanism allows neural networks to focus on relevant parts of the input when making predictions.",
    ] * 10  # 50 documents

    # Test 1: Single query embedding
    benchmark.run_test(
        "Single query embedding (short)",
        embed_query,
        short_query,
        warmup=2,
        iterations=10
    )

    # Test 2: Single query embedding (long)
    benchmark.run_test(
        "Single query embedding (long)",
        embed_query,
        long_query,
        warmup=2,
        iterations=10
    )

    # Test 3: Multiple queries
    queries = [short_query, long_query] * 5  # 10 queries
    benchmark.run_test(
        "10 queries embedding",
        lambda: [embed_query(q) for q in queries],
        warmup=1,
        iterations=5
    )

    # Test 4: Small document batch
    benchmark.run_test(
        "3 documents embedding",
        embed_documents,
        short_docs,
        warmup=2,
        iterations=10
    )

    # Test 5: Medium document batch
    benchmark.run_test(
        "20 documents embedding",
        embed_documents,
        medium_docs,
        warmup=2,
        iterations=5
    )

    # Test 6: Large document batch
    benchmark.run_test(
        "50 documents embedding",
        embed_documents,
        long_docs,
        warmup=1,
        iterations=3
    )

    # Test 7: Reranking (small)
    benchmark.run_test(
        "Rerank 5 passages",
        rerank,
        short_query,
        short_docs[:5],
        warmup=2,
        iterations=10
    )

    # Test 8: Reranking (medium)
    benchmark.run_test(
        "Rerank 20 passages",
        rerank,
        long_query,
        medium_docs[:20],
        warmup=2,
        iterations=5
    )

    # Print final summary
    benchmark.print_summary()

    # Performance recommendations
    print("\n📝 Performance Recommendations:")
    print("="*70)

    if DEFAULT_DEVICE == "cpu":
        print("⚠️  You're running on CPU. For better performance:")
        print("   1. On Mac Silicon: Ensure PyTorch with MPS support is installed")
        print("   2. On Linux/Windows: Install CUDA-enabled PyTorch if you have NVIDIA GPU")
        print("   3. Run: python optimize_platform.py to auto-configure")
    elif DEFAULT_DEVICE == "mps":
        print("✅ You're using Mac Silicon MPS acceleration - Good!")
        print("   Expected speedup: 5-10x vs CPU")
    elif DEFAULT_DEVICE.startswith("cuda"):
        print("✅ You're using CUDA GPU acceleration - Excellent!")
        print("   Expected speedup: 10-50x vs CPU")

    print()
    print("For further optimization:")
    print("   • Increase EMBEDDING_BATCH if you have more GPU memory")
    print("   • Enable EMBEDDING_CACHE_SIZE for repeated queries")
    print("   • Consider quantization for even faster inference (experimental)")
    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during benchmark: {e}")
        import traceback
        traceback.print_exc()

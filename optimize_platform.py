#!/usr/bin/env python3
"""
Script d'optimisation automatique du retrieval plugin
Détecte la plateforme (Mac Silicon, CUDA, CPU) et applique les optimisations appropriées
"""

import platform
import subprocess
import sys
import os
from pathlib import Path


class PlatformOptimizer:
    def __init__(self):
        self.system = platform.system()  # Darwin, Linux, Windows
        self.machine = platform.machine()  # arm64, x86_64, AMD64
        self.device = self._detect_best_device()

    def _detect_best_device(self):
        """Détecte le meilleur device disponible"""
        # Mac Silicon (M1/M2/M3)
        if self.system == "Darwin" and self.machine == "arm64":
            try:
                import torch
                if torch.backends.mps.is_available():
                    return "mps"
            except ImportError:
                pass
            return "cpu"

        # CUDA (Linux/Windows avec GPU NVIDIA)
        elif self.system in ["Linux", "Windows"]:
            try:
                import torch
                if torch.cuda.is_available():
                    return f"cuda:0"
            except ImportError:
                pass
            return "cpu"

        return "cpu"

    def get_optimal_settings(self):
        """Retourne les paramètres optimaux selon la plateforme"""
        settings = {
            "EMBEDDING_DEVICE": self.device,
            "RERANK_DEVICE": self.device,
            "EMBEDDING_MODEL": "BAAI/bge-m3",
            "RERANK_MODEL": "BAAI/bge-reranker-v2-m3",
        }

        # Mac Silicon optimizations
        if self.device == "mps":
            settings.update({
                "EMBEDDING_BATCH": "32",  # MPS optimal batch size
                "EMBEDDING_FP16": "false",  # MPS a parfois des bugs avec FP16
                "EMBEDDING_MAX_LEN": "8192",
                "EMBEDDING_CACHE_SIZE": "2000",
                "RERANK_ENABLE": "true",
                "RERANK_K": "5",
                "RERANK_FINAL_N": "3",
                # Optimisations MPS spécifiques
                "PYTORCH_MPS_HIGH_WATERMARK_RATIO": "0.0",  # Meilleure gestion mémoire
                "PYTORCH_ENABLE_MPS_FALLBACK": "1",  # Fallback CPU si nécessaire
            })

        # CUDA optimizations
        elif self.device.startswith("cuda"):
            settings.update({
                "EMBEDDING_BATCH": "64",  # CUDA peut gérer des batches plus gros
                "EMBEDDING_FP16": "true",  # FP16 très rapide sur CUDA
                "EMBEDDING_MAX_LEN": "8192",
                "EMBEDDING_CACHE_SIZE": "2000",
                "RERANK_ENABLE": "true",
                "RERANK_K": "10",
                "RERANK_FINAL_N": "5",
                # Optimisations CUDA
                "CUDA_LAUNCH_BLOCKING": "0",
                "TORCH_CUDNN_V8_API_ENABLED": "1",
            })

        # CPU fallback (pas optimal mais fonctionnel)
        else:
            settings.update({
                "EMBEDDING_BATCH": "16",  # Petit batch pour CPU
                "EMBEDDING_FP16": "false",
                "EMBEDDING_MAX_LEN": "4096",  # Réduit pour CPU
                "EMBEDDING_CACHE_SIZE": "1000",
                "RERANK_ENABLE": "true",
                "RERANK_K": "5",
                "RERANK_FINAL_N": "3",
            })

        return settings

    def print_report(self):
        """Affiche un rapport de la configuration détectée"""
        print("=" * 70)
        print("🚀 PLATFORM OPTIMIZATION REPORT")
        print("=" * 70)
        print(f"System: {self.system}")
        print(f"Architecture: {self.machine}")
        print(f"Optimal Device: {self.device}")
        print()

        if self.device == "mps":
            print("✅ Mac Silicon detected! Using Metal Performance Shaders (MPS)")
            print("   Expected speedup: 5-10x vs CPU")
        elif self.device.startswith("cuda"):
            print("✅ NVIDIA GPU detected! Using CUDA acceleration")
            print("   Expected speedup: 10-50x vs CPU")
        else:
            print("⚠️  No GPU acceleration available. Using CPU.")
            print("   Consider using a machine with GPU for better performance.")

        print()
        print("Recommended settings:")
        print("-" * 70)
        for key, value in self.get_optimal_settings().items():
            print(f"{key}={value}")
        print("=" * 70)

    def write_env_file(self, output_path=".env.optimized"):
        """Écrit un fichier .env optimisé"""
        settings = self.get_optimal_settings()

        with open(output_path, "w") as f:
            f.write("# Auto-generated optimized configuration\n")
            f.write(f"# Platform: {self.system} {self.machine}\n")
            f.write(f"# Device: {self.device}\n\n")

            for key, value in settings.items():
                f.write(f"{key}={value}\n")

        print(f"\n✅ Configuration written to: {output_path}")
        print(f"   To use: cp {output_path} .env (backup your current .env first!)")

    def check_dependencies(self):
        """Vérifie que les dépendances nécessaires sont installées"""
        print("\n🔍 Checking dependencies...")

        required = ["torch", "FlagEmbedding", "fastapi", "uvicorn"]
        missing = []

        for pkg in required:
            try:
                __import__(pkg.lower().replace("-", "_"))
                print(f"   ✅ {pkg}")
            except ImportError:
                print(f"   ❌ {pkg} (missing)")
                missing.append(pkg)

        if missing:
            print(f"\n⚠️  Missing packages: {', '.join(missing)}")
            print("   Install with: pip install " + " ".join(missing))
            return False

        print("   All dependencies OK!")
        return True

    def install_optimized_torch(self):
        """Installe la version optimale de PyTorch selon la plateforme"""
        print("\n📦 PyTorch installation recommendation:")

        if self.device == "mps":
            print("   For Mac Silicon, ensure you have PyTorch with MPS support:")
            print("   pip3 install torch torchvision torchaudio")
        elif self.device.startswith("cuda"):
            print("   For CUDA, install PyTorch with CUDA support:")
            print("   pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
        else:
            print("   For CPU:")
            print("   pip3 install torch torchvision torchaudio")


def main():
    print("🔧 Retrieval Plugin Platform Optimizer\n")

    optimizer = PlatformOptimizer()
    optimizer.print_report()
    optimizer.check_dependencies()
    optimizer.install_optimized_torch()
    optimizer.write_env_file()

    print("\n" + "=" * 70)
    print("📝 Next steps:")
    print("=" * 70)
    print("1. Review .env.optimized file")
    print("2. Backup current .env: cp .env .env.backup")
    print("3. Apply optimizations: cp .env.optimized .env")
    print("4. Restart your server")
    print("5. Run benchmark: python benchmark_embeddings.py")
    print("=" * 70)


if __name__ == "__main__":
    main()

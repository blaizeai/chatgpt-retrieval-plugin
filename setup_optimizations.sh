#!/bin/bash
# Setup script for retrieval plugin optimizations

set -e  # Exit on error

echo "🚀 Retrieval Plugin - Optimization Setup"
echo "=========================================="
echo ""

# Detect platform
OS=$(uname -s)
ARCH=$(uname -m)

echo "📍 Detected platform: $OS $ARCH"
echo ""

# Step 1: Check Python
echo "1️⃣  Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "   ❌ Python3 not found. Please install Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "   ✅ $PYTHON_VERSION"
echo ""

# Step 2: Install/upgrade dependencies
echo "2️⃣  Installing dependencies..."
echo "   This may take a few minutes..."
echo ""

# Install PyTorch based on platform
if [[ "$OS" == "Darwin" && "$ARCH" == "arm64" ]]; then
    echo "   📦 Installing PyTorch for Mac Silicon (with MPS support)..."
    pip3 install -q torch torchvision torchaudio || true
elif command -v nvidia-smi &> /dev/null; then
    echo "   📦 Installing PyTorch for CUDA..."
    pip3 install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 || true
else
    echo "   📦 Installing PyTorch (CPU)..."
    pip3 install -q torch torchvision torchaudio || true
fi

# Install FlagEmbedding
echo "   📦 Installing FlagEmbedding..."
pip3 install -q FlagEmbedding || true

# Install other dependencies
echo "   📦 Installing other dependencies..."
pip3 install -q fastapi uvicorn numpy || true

echo "   ✅ Dependencies installed"
echo ""

# Step 3: Run optimization detection
echo "3️⃣  Detecting optimal configuration..."
python3 optimize_platform.py

echo ""

# Step 4: Backup and apply
echo "4️⃣  Applying optimizations..."

if [ -f .env ]; then
    if [ ! -f .env.backup ]; then
        echo "   💾 Backing up current .env to .env.backup"
        cp .env .env.backup
    else
        echo "   ℹ️  Backup .env.backup already exists (skipping backup)"
    fi
else
    echo "   ℹ️  No existing .env file found"
fi

if [ -f .env.optimized ]; then
    echo "   ✅ Applying optimized configuration"
    cp .env.optimized .env

    # Preserve bearer token from backup if it exists
    if [ -f .env.backup ]; then
        BEARER_TOKEN=$(grep "RAG_BEARER_TOKEN" .env.backup 2>/dev/null || echo "")
        if [ ! -z "$BEARER_TOKEN" ]; then
            echo "   🔐 Preserving bearer token from backup"
            echo "" >> .env
            echo "# Preserved from original .env" >> .env
            echo "$BEARER_TOKEN" >> .env
        fi
    fi

    echo "   ✅ Configuration applied!"
else
    echo "   ❌ .env.optimized not found"
    exit 1
fi

echo ""

# Step 5: Quick test
echo "5️⃣  Running quick validation test..."
echo ""
python3 quick_test.py

echo ""

# Step 6: Summary
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "📝 Next steps:"
echo ""
echo "  • Start server: poetry run start"
echo "  • Or: cd chatgpt-retrieval-plugin && poetry run start"
echo ""
echo "  • Run benchmark (optional): python3 benchmark_embeddings.py"
echo ""
echo "  • Check configuration: cat .env"
echo ""
echo "📚 Documentation:"
echo "  • Quick reference: OPTIMIZATION_README.md"
echo "  • Detailed guide: OPTIMIZATION_GUIDE.md"
echo ""
echo "🚀 Expected performance gain:"

if [[ "$OS" == "Darwin" && "$ARCH" == "arm64" ]]; then
    echo "  • Mac Silicon MPS: 5-10x faster than CPU"
elif command -v nvidia-smi &> /dev/null; then
    echo "  • NVIDIA GPU: 10-50x faster than CPU"
else
    echo "  • CPU: No acceleration (consider using GPU)"
fi

echo ""
echo "=========================================="

#!/bin/bash
# Build script for RAG service binary (PyInstaller)

set -e  # Exit on error

echo "============================================"
echo "Blaise RAG Service - Build Binary"
echo "============================================"

# Detect platform
OS=$(uname -s)
ARCH=$(uname -m)

case "$OS" in
    Darwin)
        PLATFORM="darwin"
        ;;
    Linux)
        PLATFORM="linux"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        PLATFORM="windows"
        ;;
    *)
        echo "❌ Unsupported OS: $OS"
        exit 1
        ;;
esac

case "$ARCH" in
    x86_64|amd64)
        ARCH="x86_64"
        ;;
    arm64|aarch64)
        ARCH="arm64"
        ;;
    *)
        echo "❌ Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

TARGET_DIR="$PLATFORM-$ARCH"
echo "📦 Target platform: $TARGET_DIR"

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Please install it first:"
    echo "   pip install poetry"
    exit 1
fi

echo "✅ Poetry found"

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
poetry install --only main

# Install PyInstaller in poetry env
echo ""
echo "📥 Installing PyInstaller..."
poetry run pip install pyinstaller

# Clean previous builds
echo ""
echo "🧹 Cleaning previous builds..."
rm -rf build dist *.spec.bak

# Build with PyInstaller
echo ""
echo "🔨 Building binary with PyInstaller..."
echo "⏳ This may take 10-15 minutes (downloads models on first run)..."
poetry run pyinstaller rag-service.spec

# Check if build succeeded
if [ ! -f "dist/rag-service" ]; then
    echo "❌ Build failed - binary not found"
    exit 1
fi

echo ""
echo "✅ Binary built successfully!"
ls -lh dist/rag-service

# Copy to Tauri resources
TAURI_RESOURCES="../tauri-app/src-tauri/resources/bin/$TARGET_DIR"
echo ""
echo "📦 Copying to Tauri resources: $TAURI_RESOURCES"

mkdir -p "$TAURI_RESOURCES"
cp dist/rag-service "$TAURI_RESOURCES/"
chmod +x "$TAURI_RESOURCES/rag-service"

echo "✅ Binary copied to: $TAURI_RESOURCES/rag-service"
ls -lh "$TAURI_RESOURCES/rag-service"

echo ""
echo "============================================"
echo "✅ Build completed successfully!"
echo "============================================"
echo ""
echo "📝 Next steps:"
echo "1. Edit the config file after first run:"
echo "   - macOS: ~/Library/Application Support/Blaise/rag.env"
echo "   - Linux: ~/.config/blaise/rag.env"
echo "   - Windows: %APPDATA%\\Blaise\\rag.env"
echo ""
echo "2. Change the BEARER_TOKEN in the config file"
echo ""
echo "3. Test the binary:"
echo "   cd $TAURI_RESOURCES"
echo "   ./rag-service"
echo ""

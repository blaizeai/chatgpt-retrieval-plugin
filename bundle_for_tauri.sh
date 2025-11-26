#!/bin/bash
# Bundle RAG service code into Tauri resources

set -e  # Exit on error

echo "============================================"
echo "Blaise RAG Service - Bundle for Tauri"
echo "============================================"

SOURCE_DIR="$(pwd)"
TARGET_DIR="../tauri-app/src-tauri/resources/rag-service"

echo "📦 Source: $SOURCE_DIR"
echo "📦 Target: $TARGET_DIR"

# Clean target directory
echo ""
echo "🧹 Cleaning target directory..."
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

# Copy Python source code
echo ""
echo "📥 Copying Python source code..."
cp -r server "$TARGET_DIR/"
cp -r services "$TARGET_DIR/"
cp -r datastore "$TARGET_DIR/"
cp -r models "$TARGET_DIR/"

# Copy configuration files
echo "📥 Copying configuration files..."
cp pyproject.toml "$TARGET_DIR/"
cp poetry.lock "$TARGET_DIR/"
cp README.md "$TARGET_DIR/"

# Copy .well-known if it exists
if [ -d ".well-known" ]; then
    echo "📥 Copying .well-known..."
    cp -r .well-known "$TARGET_DIR/"
fi

# Create __init__.py if it doesn't exist in server/
if [ ! -f "$TARGET_DIR/server/__init__.py" ]; then
    touch "$TARGET_DIR/server/__init__.py"
fi

# Remove unnecessary files
echo ""
echo "🧹 Removing unnecessary files..."
find "$TARGET_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$TARGET_DIR" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find "$TARGET_DIR" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find "$TARGET_DIR" -type f -name "*.pyc" -delete
find "$TARGET_DIR" -type f -name "*.pyo" -delete
find "$TARGET_DIR" -type f -name ".DS_Store" -delete

# Remove tests and docs if they exist
rm -rf "$TARGET_DIR/tests" 2>/dev/null || true
rm -rf "$TARGET_DIR/docs" 2>/dev/null || true

# Create a startup script
echo ""
echo "📝 Creating startup script..."
cat > "$TARGET_DIR/start.sh" << 'EOF'
#!/bin/bash
# Startup script for RAG service

cd "$(dirname "$0")"

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Please install it:"
    echo "   curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Check if Python 3.10 is available
if ! command -v python3.10 &> /dev/null; then
    echo "❌ Python 3.10 not found. Please install it first."
    exit 1
fi

echo "✅ Poetry and Python 3.10 found"
echo "📥 Installing dependencies (first run only)..."

# Install dependencies if not already installed
poetry env use python3.10
poetry install --only main --no-interaction

# Start the service
echo "🚀 Starting RAG service..."
poetry run python -m server
EOF

chmod +x "$TARGET_DIR/start.sh"

# Calculate size
SIZE=$(du -sh "$TARGET_DIR" | cut -f1)

echo ""
echo "============================================"
echo "✅ Bundle completed successfully!"
echo "============================================"
echo ""
echo "📦 Bundle size: $SIZE"
echo "📍 Location: $TARGET_DIR"
echo ""
echo "📝 Next steps:"
echo "1. Modify main.rs to launch start.sh"
echo "2. Test with: cd $TARGET_DIR && ./start.sh"
echo ""

#!/bin/bash

# Tweet Extraction Tool - Quick Setup Script
# This script helps you get started quickly with UV

set -e

echo "🐦 Tweet Extraction Tool - Quick Setup"
echo "======================================"

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "UV not found. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add UV to PATH for current session
    export PATH="$HOME/.cargo/bin:$PATH"
    
    # Verify installation
    if ! command -v uv &> /dev/null; then
        echo "❌ UV installation failed. Please install manually:"
        echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    
    echo "✅ UV installed successfully!"
else
    echo "✅ UV is already installed: $(uv --version)"
fi

echo ""
echo "📦 Installing dependencies..."
echo "UV will automatically find a compatible Python version (3.11+)..."
uv sync

echo ""
echo "⚙️  Setting up configuration..."
if [ ! -f "config.yaml" ]; then
    cp config.yaml.template config.yaml
    echo "✅ Created config.yaml from template"
    echo "📝 Please edit config.yaml with your X.com credentials"
else
    echo "✅ config.yaml already exists"
fi

echo ""
echo "🧪 Running setup tests..."
uv run python test_setup.py

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config.yaml with your X.com username, email, and password"
echo "2. Run your first extraction:"
echo "   uv run python pull_tweets.py @username -o tweets.parquet"
echo ""
echo "For help: uv run python pull_tweets.py --help"
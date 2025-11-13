#!/bin/bash

# Quick Start Script for Local Testing

echo "=========================================="
echo "🚀 Binance Bot - Local Testing Setup"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "📝 Please edit .env with your credentials:"
    echo "   nano .env"
    echo ""
    echo "Then run this script again."
    exit 1
fi

echo "✅ Found .env file"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q -e .

echo "✅ Dependencies installed"
echo ""

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "🐳 Docker detected"

    # Check if containers are running
    if docker-compose ps | grep -q "Up"; then
        echo "✅ Docker containers already running"
    else
        echo "🚀 Starting Docker containers (PostgreSQL + Redis)..."
        docker-compose up -d postgres redis
        echo "⏳ Waiting for services to be ready..."
        sleep 10
        echo "✅ Docker containers started"
    fi
else
    echo "⚠️  Docker not detected"
    echo "Please ensure PostgreSQL and Redis are running locally"
fi

echo ""
echo "=========================================="
echo "🧪 Running Validation Tests"
echo "=========================================="
echo ""

python scripts/validate_setup.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "🎉 Setup complete! Ready to test."
    echo "=========================================="
    echo ""
    echo "Available commands:"
    echo ""
    echo "1. Quick health check:"
    echo "   python scripts/health_check.py"
    echo ""
    echo "2. Test Binance API:"
    echo "   python scripts/test_binance_api.py"
    echo ""
    echo "3. Run 5-minute dry run:"
    echo "   python scripts/dry_run.py"
    echo ""
    echo "4. Run 30-minute dry run:"
    echo "   python scripts/dry_run.py --duration 1800"
    echo ""
    echo "5. Start the bot:"
    echo "   python -m src.main"
    echo ""
    echo "=========================================="
else
    echo ""
    echo "❌ Setup validation failed"
    echo "Please fix the issues above and try again"
    exit 1
fi

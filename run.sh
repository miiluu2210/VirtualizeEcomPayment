#!/bin/bash

# TechStore Vietnam API Simulator - Startup Script

echo "🚀 TechStore Vietnam API Simulator"
echo "=================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Create necessary directories
echo "📁 Creating data directories..."
mkdir -p shared_data
mkdir -p shared_data/customers
mkdir -p shared_data/shopify_orders
mkdir -p shared_data/sapo_orders
mkdir -p shared_data/odoo_orders
mkdir -p shared_data/paypal_transactions
mkdir -p shared_data/mercury_transactions
echo "✓ Directories created"

# Check if data exists
echo ""
echo "📊 Checking existing data..."
if [ -f "shared_data/products.json.gz" ]; then
    echo "  ✓ Products data found"
else
    echo "  ⚠ Products not generated"
fi

if [ -f "shared_data/staff.json.gz" ]; then
    echo "  ✓ Staff data found"
else
    echo "  ⚠ Staff not generated"
fi

if [ -d "shared_data/customers" ] && [ "$(ls -A shared_data/customers)" ]; then
    echo "  ✓ Customer data found"
else
    echo "  ⚠ Customers not generated"
fi

echo ""
echo "=================================="
echo "🎉 Starting API Server..."
echo "=================================="
echo ""
echo "📡 API will be available at: http://localhost:8000"
echo "📚 Documentation at: http://localhost:8000/docs"
echo "📖 ReDoc at: http://localhost:8000/redoc"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the application
python3 main.py
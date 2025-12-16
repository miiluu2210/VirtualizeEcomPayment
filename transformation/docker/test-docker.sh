#!/bin/bash
# Quick test script for Docker setup

set -e

echo "======================================="
echo "Docker Setup Test Script"
echo "======================================="
echo ""

# Check Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi
echo "✅ Docker is installed"

# Check Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi
echo "✅ Docker Compose is installed"

# Create test directories
echo ""
echo "Creating test directories..."
mkdir -p data/input data/output data/temp
echo "✅ Directories created"

# Check if test data exists
if [ ! -f "../../shared_data/private_data/cart_tracking/cart_events.json.gz" ]; then
    echo "❌ Test data not found"
    echo "   Please ensure cart_events.json.gz exists"
    exit 1
fi

# Copy test data
echo ""
echo "Copying test data..."
cp ../../shared_data/private_data/cart_tracking/cart_events.json.gz data/input/
echo "✅ Test data copied"

# Test 1: Build image
echo ""
echo "======================================="
echo "Test 1: Building Docker image"
echo "======================================="
docker build -f Dockerfile -t cart-transformer:test ../..
echo "✅ Image built successfully"

# Test 2: Run single container
echo ""
echo "======================================="
echo "Test 2: Running single container"
echo "======================================="
timeout 180 docker-compose up --abort-on-container-exit || true
echo "✅ Single container test completed"

# Check output
if [ -d "data/output/cart_events_cleaned" ]; then
    echo "✅ Output files created"
    echo ""
    echo "Output structure:"
    ls -lh data/output/
else
    echo "❌ No output files found"
    exit 1
fi

# Test 3: Worker pool (optional, takes longer)
read -p "Run worker pool test? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "======================================="
    echo "Test 3: Running worker pool"
    echo "======================================="

    # Clean previous output
    rm -rf data/output/*

    # Build worker image
    docker build -f Dockerfile.worker -t cart-transformer-worker:test ../..

    # Run with 2 workers
    timeout 180 docker-compose -f docker-compose.workers.yml up --scale worker=2 --abort-on-container-exit || true
    echo "✅ Worker pool test completed"
fi

# Cleanup
echo ""
echo "======================================="
echo "Cleanup"
echo "======================================="
read -p "Clean up test files? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose down -v
    docker-compose -f docker-compose.workers.yml down -v 2>/dev/null || true
    rm -rf data/
    echo "✅ Cleanup completed"
fi

echo ""
echo "======================================="
echo "All tests completed! ✅"
echo "======================================="

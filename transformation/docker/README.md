# Docker Setup for Cart Events Transformation

Complete Docker setup with 3 deployment options: Single Container, Worker Pool, and Production Pipeline.

## 🚀 Quick Start

### Option 1: Single Container (Simplest)
For one-time processing or simple deployments.

```bash
# 1. Create data directories
mkdir -p data/input data/output

# 2. Copy your data file
cp /path/to/cart_events.json.gz data/input/

# 3. Run transformation
docker-compose up

# 4. Check output
ls -lh data/output/
```

**Processing time for 2M events:** ~3-5 minutes

---

### Option 2: Worker Pool (Recommended) ⭐
For faster processing with parallel workers.

```bash
# 1. Prepare data
mkdir -p data/input data/output data/temp
cp /path/to/cart_events.json.gz data/input/

# 2. Start with 4 workers (default)
docker-compose -f docker-compose.workers.yml up

# 3. Or scale to 8 workers for faster processing
docker-compose -f docker-compose.workers.yml up --scale worker=8

# 4. Monitor progress
docker-compose -f docker-compose.workers.yml logs -f scheduler
```

**Processing time for 2M events:**
- 4 workers: ~1-2 minutes
- 8 workers: ~45-60 seconds

---

### Option 3: Build Custom Image

```bash
# Build the image
docker build -f docker/Dockerfile -t cart-transformer:latest ../..

# Run with custom parameters
docker run -v $(pwd)/data:/data cart-transformer:latest \
  python transform_cart_events_extreme.py \
  --input /data/input/cart_events.json.gz \
  --output /data/output \
  --chunk-size 100000
```

---

## 📊 Comparison

| Option | Setup Time | Processing Speed | Best For |
|--------|-----------|------------------|----------|
| **Single Container** | 2 min | 3-5 min | Simple deployments |
| **Worker Pool (4)** | 3 min | 1-2 min | Production (balanced) |
| **Worker Pool (8)** | 3 min | 45-60s | Production (fast) |

---

## 🏗️ Architecture

### Single Container
```
┌─────────────────────────────────┐
│  Docker Container               │
│  ┌──────────────────────────┐   │
│  │  Transformation Script   │   │
│  └──────────────────────────┘   │
│                                 │
│  /data/input  →  /data/output   │
└─────────────────────────────────┘
```

### Worker Pool
```
                 ┌─────────┐
                 │  Redis  │
                 └────┬────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
┌───▼────┐      ┌─────▼─────┐    ┌─────▼─────┐
│Worker 1│      │  Worker 2 │    │  Worker N │
└───┬────┘      └─────┬─────┘    └─────┬─────┘
    │                 │                 │
    └─────────────────┼─────────────────┘
                      │
                ┌─────▼──────┐
                │   Output   │
                └────────────┘
```

---

## 🔧 Configuration

### Environment Variables

**Single Container (docker-compose.yml):**
```yaml
environment:
  - CHUNK_SIZE=100000  # Batch size for processing
```

**Worker Pool (docker-compose.workers.yml):**
```yaml
environment:
  - REDIS_HOST=redis
  - REDIS_PORT=6379
  - WORKERS=4          # Number of workers
  - INPUT_FILE=/data/input/cart_events.json.gz
```

### Resource Limits

Adjust in docker-compose files:
```yaml
mem_limit: 1g    # Maximum memory per container
cpus: 2          # CPU cores per container
```

---

## 📈 Scaling Guide

### For Different Dataset Sizes:

**10K events:**
```bash
docker-compose up
# 1 worker sufficient
```

**100K events:**
```bash
docker-compose -f docker-compose.workers.yml up --scale worker=2
# 2 workers recommended
```

**500K events:**
```bash
docker-compose -f docker-compose.workers.yml up --scale worker=4
# 4 workers recommended
```

**2M events:**
```bash
docker-compose -f docker-compose.workers.yml up --scale worker=4
# 4-8 workers recommended
```

**10M+ events:**
```bash
docker-compose -f docker-compose.workers.yml up --scale worker=8
# 8-16 workers recommended
```

---

## 🎯 Use Cases

### Use Case 1: Scheduled Batch Processing
Run transformation every night at 2 AM:

```bash
# Add to crontab
0 2 * * * cd /path/to/project && docker-compose up
```

### Use Case 2: CI/CD Pipeline
In your GitHub Actions or Jenkins:

```yaml
- name: Transform cart events
  run: |
    docker-compose -f transformation/docker/docker-compose.yml up --exit-code-from transformation
```

### Use Case 3: Cloud Deployment

**AWS ECS:**
```bash
# Build and push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t cart-transformer -f docker/Dockerfile ../..
docker tag cart-transformer:latest <account>.dkr.ecr.us-east-1.amazonaws.com/cart-transformer:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/cart-transformer:latest

# Deploy to ECS
ecs-cli compose -f docker-compose.yml up
```

**Google Cloud Run:**
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT-ID/cart-transformer
gcloud run deploy cart-transformer --image gcr.io/PROJECT-ID/cart-transformer
```

---

## 🐛 Troubleshooting

### Issue: Container runs out of memory
```
Error: Container killed (OOM)
```

**Solution:**
```yaml
# Increase memory limit
mem_limit: 2g  # or higher

# Or reduce chunk size
environment:
  - CHUNK_SIZE=50000
```

### Issue: Redis connection failed
```
Error: Could not connect to Redis
```

**Solution:**
```bash
# Check Redis is running
docker-compose -f docker-compose.workers.yml ps

# View Redis logs
docker-compose -f docker-compose.workers.yml logs redis

# Restart Redis
docker-compose -f docker-compose.workers.yml restart redis
```

### Issue: Workers not processing
```
Workers started but no progress
```

**Solution:**
```bash
# Check queue status
docker-compose -f docker-compose.workers.yml exec redis redis-cli LLEN transformation

# View worker logs
docker-compose -f docker-compose.workers.yml logs -f worker

# Restart workers
docker-compose -f docker-compose.workers.yml restart worker
```

---

## 📊 Monitoring

### View Logs

```bash
# All services
docker-compose -f docker-compose.workers.yml logs -f

# Specific service
docker-compose -f docker-compose.workers.yml logs -f worker

# Scheduler only
docker-compose -f docker-compose.workers.yml logs -f scheduler
```

### Check Resource Usage

```bash
# All containers
docker stats

# Specific container
docker stats cart-worker-1
```

### Redis Monitoring (Optional)

```bash
# Start with monitoring
docker-compose -f docker-compose.workers.yml --profile monitoring up

# Access Redis Insight at http://localhost:8001
```

---

## 🧹 Cleanup

```bash
# Stop containers
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Remove images
docker rmi cart-transformer
```

---

## 📝 File Structure

```
transformation/docker/
├── Dockerfile                      # Single worker image
├── Dockerfile.worker               # Multi-worker image
├── docker-compose.yml              # Single container setup
├── docker-compose.workers.yml      # Worker pool setup
├── worker.py                       # Worker process script
├── scheduler.py                    # Job scheduler script
└── README.md                       # This file

data/
├── input/                          # Place input files here
│   └── cart_events.json.gz
├── output/                         # Processed output
│   ├── cart_events_cleaned/
│   └── session_metrics.parquet
└── temp/                           # Temporary worker files
```

---

## 🚀 Performance Tips

1. **Memory Optimization:**
   - Use extreme version for datasets > 500K events
   - Adjust chunk size based on available memory
   - Limit worker count to available CPU cores

2. **Speed Optimization:**
   - Use SSD for output directory
   - Scale workers to match CPU cores
   - Process during off-peak hours

3. **Cost Optimization:**
   - Use spot instances on cloud
   - Auto-scale workers based on queue size
   - Schedule processing during off-peak pricing

---

## 📚 Additional Resources

- [Main README](../README.md) - Pipeline overview
- [PERFORMANCE.md](../PERFORMANCE.md) - Performance comparison
- [DOCKER_GUIDE.md](../DOCKER_GUIDE.md) - Docker use cases

---

## 💡 Next Steps

1. **Test locally:**
   ```bash
   docker-compose up
   ```

2. **Deploy to cloud:**
   - AWS ECS, GKE, or Azure Container Instances
   - Set up auto-scaling
   - Configure monitoring

3. **Integrate with CI/CD:**
   - Automate on new data uploads
   - Schedule regular processing
   - Alert on failures

Happy transforming! 🎉

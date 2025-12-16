"""
Task Scheduler for Distributed Transformation
Splits large dataset into chunks and enqueues jobs to Redis
"""

import os
import json
import gzip
import logging
from pathlib import Path
from redis import Redis
from rq import Queue

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def split_work(input_file: str, num_workers: int) -> list:
    """
    Split the input file work into chunks for workers.

    Args:
        input_file: Path to cart_events.json.gz
        num_workers: Number of workers available

    Returns:
        List of chunk info dictionaries
    """
    logger.info(f"Analyzing {input_file} to split work...")

    # Count total events
    with gzip.open(input_file, 'rt', encoding='utf-8') as f:
        data = json.load(f)
        total_events = len(data)

    logger.info(f"Total events: {total_events:,}")
    logger.info(f"Workers: {num_workers}")

    # Calculate chunk size
    chunk_size = total_events // num_workers

    # Create chunk info
    chunks = []
    for i in range(num_workers):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size if i < num_workers - 1 else total_events

        chunks.append({
            'input_file': input_file,
            'output_dir': '/data/output',
            'start_idx': start_idx,
            'end_idx': end_idx,
            'chunk_num': i,
            'total_chunks': num_workers
        })

    logger.info(f"Created {len(chunks)} chunks, ~{chunk_size:,} events each")
    return chunks


def enqueue_jobs(redis_conn: Redis, chunks: list) -> list:
    """
    Enqueue transformation jobs to Redis queue.

    Args:
        redis_conn: Redis connection
        chunks: List of chunk info dictionaries

    Returns:
        List of job IDs
    """
    from worker import process_chunk

    queue = Queue('transformation', connection=redis_conn)
    job_ids = []

    logger.info(f"Enqueueing {len(chunks)} jobs...")

    for chunk in chunks:
        job = queue.enqueue(
            process_chunk,
            chunk,
            job_timeout='30m',
            result_ttl=3600,
            failure_ttl=3600
        )
        job_ids.append(job.id)
        logger.info(f"Enqueued job {job.id} for chunk {chunk['chunk_num']}")

    return job_ids


def monitor_jobs(redis_conn: Redis, job_ids: list):
    """
    Monitor job progress and report statistics.

    Args:
        redis_conn: Redis connection
        job_ids: List of job IDs to monitor
    """
    from rq.job import Job
    import time

    logger.info("Monitoring job progress...")

    while True:
        # Check job statuses
        statuses = {
            'queued': 0,
            'started': 0,
            'finished': 0,
            'failed': 0
        }

        for job_id in job_ids:
            job = Job.fetch(job_id, connection=redis_conn)
            status = job.get_status()
            statuses[status] = statuses.get(status, 0) + 1

        # Log progress
        logger.info(f"Progress: {statuses['finished']}/{len(job_ids)} completed, "
                   f"{statuses['started']} running, "
                   f"{statuses['queued']} queued, "
                   f"{statuses['failed']} failed")

        # Check if all done
        if statuses['finished'] + statuses['failed'] == len(job_ids):
            logger.info("All jobs completed!")

            # Print results
            for job_id in job_ids:
                job = Job.fetch(job_id, connection=redis_conn)
                if job.result:
                    logger.info(f"Job {job_id}: {job.result}")

            break

        time.sleep(5)


def main():
    """Main scheduler execution."""
    # Get configuration from environment
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    num_workers = int(os.getenv('WORKERS', 4))
    input_file = os.getenv('INPUT_FILE', '/data/input/cart_events.json.gz')

    logger.info("=" * 80)
    logger.info("Cart Events Transformation Scheduler")
    logger.info("=" * 80)
    logger.info(f"Redis: {redis_host}:{redis_port}")
    logger.info(f"Workers: {num_workers}")
    logger.info(f"Input: {input_file}")
    logger.info("=" * 80)

    # Connect to Redis
    redis_conn = Redis(host=redis_host, port=redis_port)

    # Wait for Redis to be ready
    import time
    for i in range(30):
        try:
            redis_conn.ping()
            logger.info("Connected to Redis")
            break
        except Exception as e:
            logger.warning(f"Waiting for Redis... ({i+1}/30)")
            time.sleep(2)
    else:
        logger.error("Could not connect to Redis")
        return

    # Check if input file exists
    if not Path(input_file).exists():
        logger.error(f"Input file not found: {input_file}")
        return

    # Split work into chunks
    chunks = split_work(input_file, num_workers)

    # Enqueue jobs
    job_ids = enqueue_jobs(redis_conn, chunks)

    # Monitor progress
    monitor_jobs(redis_conn, job_ids)

    logger.info("=" * 80)
    logger.info("Transformation pipeline completed!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

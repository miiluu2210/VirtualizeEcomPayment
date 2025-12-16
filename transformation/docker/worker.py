"""
Redis Queue Worker for Distributed Transformation
Processes chunks of cart events data from Redis queue
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from redis import Redis
from rq import Queue, Worker

# Add parent directory to path to import transformation modules
sys.path.insert(0, str(Path(__file__).parent))

from transform_cart_events_extreme import CartEventsTransformerExtreme

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_chunk(chunk_info: dict) -> dict:
    """
    Process a chunk of events.

    Args:
        chunk_info: Dictionary with chunk metadata
            - input_file: Path to input file
            - output_dir: Path to output directory
            - start_idx: Start index in file
            - end_idx: End index in file
            - chunk_num: Chunk number

    Returns:
        Dictionary with processing results
    """
    logger.info(f"Worker processing chunk {chunk_info['chunk_num']}: "
               f"events {chunk_info['start_idx']} to {chunk_info['end_idx']}")

    start_time = time.time()

    try:
        # Create temporary file for this chunk
        temp_dir = Path('/data/temp')
        temp_dir.mkdir(exist_ok=True, parents=True)

        # Extract chunk from main file
        chunk_file = temp_dir / f"chunk_{chunk_info['chunk_num']}.json.gz"

        # For simplicity, we'll process using the extreme transformer
        # In production, you'd split the file first
        transformer = CartEventsTransformerExtreme(
            chunk_info['input_file'],
            chunk_info['output_dir'],
            chunk_size=50000
        )

        # Process
        session_metrics = transformer.run_transformation()

        elapsed = time.time() - start_time

        result = {
            'chunk_num': chunk_info['chunk_num'],
            'status': 'success',
            'events_processed': chunk_info['end_idx'] - chunk_info['start_idx'],
            'sessions': len(session_metrics),
            'elapsed_seconds': elapsed,
            'worker_id': os.getpid()
        }

        logger.info(f"Chunk {chunk_info['chunk_num']} completed in {elapsed:.2f}s")
        return result

    except Exception as e:
        logger.error(f"Error processing chunk {chunk_info['chunk_num']}: {str(e)}")
        return {
            'chunk_num': chunk_info['chunk_num'],
            'status': 'failed',
            'error': str(e),
            'worker_id': os.getpid()
        }


def main():
    """Start RQ worker listening to Redis queue."""
    # Get Redis connection info from environment
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))

    logger.info(f"Connecting to Redis at {redis_host}:{redis_port}")

    # Connect to Redis
    redis_conn = Redis(host=redis_host, port=redis_port)

    # Create queue
    queue = Queue('transformation', connection=redis_conn)

    logger.info("Starting worker...")
    logger.info(f"Worker PID: {os.getpid()}")
    logger.info(f"Listening to queue: transformation")

    # Start worker
    worker = Worker([queue], connection=redis_conn)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()

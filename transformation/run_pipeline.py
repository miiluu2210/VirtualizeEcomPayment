"""
Main Pipeline Runner
Execute the complete data transformation and aggregation pipeline.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from transform_cart_events import CartEventsTransformer
from aggregate_metrics import SessionMetricsAggregator
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Execute the complete pipeline."""
    try:
        logger.info("=" * 80)
        logger.info("CART EVENTS DATA PIPELINE")
        logger.info("=" * 80)
        logger.info("")

        # Configuration
        INPUT_FILE = "../shared_data/private_data/cart_tracking/cart_events.json.gz"
        OUTPUT_DIR = "output"

        # Step 1: Transformation
        logger.info("STEP 1: Data Transformation")
        logger.info("-" * 80)
        transformer = CartEventsTransformer(INPUT_FILE, OUTPUT_DIR)
        df, session_metrics = transformer.run_transformation()
        logger.info("")

        # Step 2: Aggregation
        logger.info("STEP 2: Metrics Aggregation")
        logger.info("-" * 80)
        aggregator = SessionMetricsAggregator(OUTPUT_DIR)
        metrics = aggregator.run_aggregation()
        logger.info("")

        logger.info("=" * 80)
        logger.info("PIPELINE EXECUTION COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"Transformed data: {OUTPUT_DIR}/cart_events_cleaned/")
        logger.info(f"Session metrics: {OUTPUT_DIR}/session_metrics.parquet")
        logger.info(f"Aggregation report: {OUTPUT_DIR}/aggregation_report.txt")
        logger.info(f"Aggregation metrics: {OUTPUT_DIR}/aggregation_metrics.json")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Pipeline failed with error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

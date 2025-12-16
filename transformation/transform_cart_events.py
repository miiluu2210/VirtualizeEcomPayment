"""
Data Transformation Pipeline for Cart Events
This script processes cart_events.json, performs data cleaning, deduplication,
creates user journeys, and exports to partitioned parquet files.
"""

import json
import gzip
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CartEventsTransformer:
    """Transform cart events data with cleaning, deduplication, and user journey creation."""

    def __init__(self, input_file: str, output_dir: str):
        """
        Initialize the transformer.

        Args:
            input_file: Path to the cart_events.json.gz file
            output_dir: Directory to save the transformed parquet files
        """
        self.input_file = input_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_data(self) -> pd.DataFrame:
        """Load cart events data from gzipped JSON file."""
        logger.info(f"Loading data from {self.input_file}")

        with gzip.open(self.input_file, 'rt', encoding='utf-8') as f:
            data = json.load(f)

        df = pd.DataFrame(data)
        logger.info(f"Loaded {len(df)} events")
        return df

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Perform data cleaning operations.

        - Convert timestamp to datetime
        - Handle missing values
        - Standardize data types
        - Remove invalid records
        """
        logger.info("Starting data cleaning...")
        initial_count = len(df)

        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour

        # Remove records with missing critical fields
        critical_fields = ['event_id', 'session_id', 'customer_id', 'event_type']
        df = df.dropna(subset=critical_fields)

        # Handle missing utm fields (fill with 'unknown' or 'direct')
        utm_fields = ['utm_source', 'utm_medium', 'utm_campaign']
        for field in utm_fields:
            df[field] = df[field].fillna('unknown')

        # Handle missing referrer
        df['referrer'] = df['referrer'].fillna('direct')

        # Ensure numeric fields are correct type
        numeric_fields = ['product_price_vnd', 'product_price_usd',
                         'quantity', 'line_total_vnd', 'line_total_usd']
        for field in numeric_fields:
            df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0)

        # Remove invalid events (negative quantities or prices)
        df = df[df['product_price_vnd'] >= 0]
        df = df[df['quantity'] >= 0]

        cleaned_count = len(df)
        logger.info(f"Data cleaning complete. Removed {initial_count - cleaned_count} invalid records")

        return df

    def deduplicate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate events based on event_id.
        Keep the first occurrence of each event.
        """
        logger.info("Starting deduplication...")
        initial_count = len(df)

        # Remove duplicates based on event_id
        df = df.drop_duplicates(subset=['event_id'], keep='first')

        duplicates_removed = initial_count - len(df)
        logger.info(f"Deduplication complete. Removed {duplicates_removed} duplicate events")

        return df

    def create_user_journeys(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create user journey information for each session.

        For each session:
        - Create a sequence of events ordered by timestamp
        - Calculate session duration
        - Count number of events
        - Track event types
        """
        logger.info("Creating user journeys...")

        # Sort by session and timestamp
        df = df.sort_values(['session_id', 'timestamp'])

        # Create journey sequence number within each session
        df['event_sequence_num'] = df.groupby('session_id').cumcount() + 1

        # Calculate session-level metrics
        session_metrics = df.groupby('session_id').agg({
            'timestamp': ['min', 'max', 'count'],
            'event_type': lambda x: ','.join(x),
            'customer_id': 'first',
            'source': 'first',
            'device': 'first'
        }).reset_index()

        # Flatten column names
        session_metrics.columns = [
            'session_id', 'session_start', 'session_end', 'total_events',
            'event_journey', 'customer_id', 'source', 'device'
        ]

        # Calculate session duration in seconds
        session_metrics['session_duration_seconds'] = (
            session_metrics['session_end'] - session_metrics['session_start']
        ).dt.total_seconds()

        # Check if session has purchase (for now, we mark sessions with multiple events as potential purchases)
        session_metrics['has_purchase'] = False  # We don't have purchase events in the data

        # Merge session metrics back to main dataframe
        df = df.merge(
            session_metrics[['session_id', 'session_start', 'session_end',
                            'session_duration_seconds', 'total_events', 'event_journey']],
            on='session_id',
            how='left'
        )

        logger.info(f"Created user journeys for {len(session_metrics)} unique sessions")

        return df, session_metrics

    def save_to_parquet(self, df: pd.DataFrame, partition_by: str = 'date'):
        """
        Save the transformed data to parquet format with partitioning.

        Args:
            df: Transformed dataframe
            partition_by: Column to partition by (default: 'date')
        """
        logger.info(f"Saving data to parquet with partitioning by {partition_by}...")

        # Create output path
        output_path = self.output_dir / "cart_events_cleaned"

        # Save with partitioning
        df.to_parquet(
            output_path,
            engine='pyarrow',
            partition_cols=[partition_by],
            compression='snappy',
            index=False
        )

        logger.info(f"Data saved to {output_path}")

        # Also save a summary CSV for easy inspection
        summary_path = self.output_dir / "transformation_summary.csv"
        summary_df = df.groupby('date').agg({
            'event_id': 'count',
            'session_id': 'nunique',
            'customer_id': 'nunique',
            'event_type': lambda x: x.value_counts().to_dict()
        }).reset_index()
        summary_df.columns = ['date', 'total_events', 'unique_sessions',
                             'unique_customers', 'event_type_distribution']
        summary_df.to_csv(summary_path, index=False)
        logger.info(f"Summary saved to {summary_path}")

    def run_transformation(self):
        """Execute the full transformation pipeline."""
        logger.info("=" * 80)
        logger.info("Starting Cart Events Transformation Pipeline")
        logger.info("=" * 80)

        # Load data
        df = self.load_data()

        # Clean data
        df = self.clean_data(df)

        # Deduplicate
        df = self.deduplicate_data(df)

        # Create user journeys
        df, session_metrics = self.create_user_journeys(df)

        # Save to parquet
        self.save_to_parquet(df)

        # Save session metrics separately
        session_output_path = self.output_dir / "session_metrics.parquet"
        session_metrics.to_parquet(session_output_path, index=False)
        logger.info(f"Session metrics saved to {session_output_path}")

        # Print statistics
        logger.info("=" * 80)
        logger.info("Transformation Complete!")
        logger.info("=" * 80)
        logger.info(f"Total events processed: {len(df)}")
        logger.info(f"Unique sessions: {df['session_id'].nunique()}")
        logger.info(f"Unique customers: {df['customer_id'].nunique()}")
        logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
        logger.info(f"Event types distribution:")
        for event_type, count in df['event_type'].value_counts().items():
            logger.info(f"  - {event_type}: {count}")
        logger.info("=" * 80)

        return df, session_metrics


def main():
    """Main execution function."""
    # Configuration
    INPUT_FILE = "../shared_data/private_data/cart_tracking/cart_events.json.gz"
    OUTPUT_DIR = "output"

    # Create transformer and run
    transformer = CartEventsTransformer(INPUT_FILE, OUTPUT_DIR)
    df, session_metrics = transformer.run_transformation()

    return df, session_metrics


if __name__ == "__main__":
    main()

"""
Data Transformation Pipeline for Cart Events - EXTREME BIG DATA VERSION
Handles millions of events with streaming JSON parsing and minimal memory footprint.
Uses ijson for incremental JSON parsing without loading entire file into memory.
"""

import gzip
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Iterator
import logging
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CartEventsTransformerExtreme:
    """
    Transform cart events data with streaming for extremely large datasets.
    Can handle 2M+ events with minimal memory usage.
    """

    def __init__(self, input_file: str, output_dir: str, chunk_size: int = 100000):
        """
        Initialize the transformer.

        Args:
            input_file: Path to the cart_events.json.gz file
            output_dir: Directory to save the transformed parquet files
            chunk_size: Number of events to accumulate before writing (default: 100,000)
        """
        self.input_file = input_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size

        # Statistics
        self.stats = {
            'total_processed': 0,
            'total_cleaned': 0,
            'duplicates_removed': 0,
            'invalid_removed': 0
        }

        # Track seen IDs and session data incrementally
        self.seen_event_ids = set()
        self.session_data = defaultdict(lambda: {
            'events': [],
            'timestamps': [],
            'customer_id': None,
            'source': None,
            'device': None
        })

    def load_events_streaming(self) -> Iterator[dict]:
        """
        Stream events from gzipped JSON file one at a time.
        This avoids loading the entire file into memory.
        """
        try:
            import ijson
            logger.info("Using ijson for streaming JSON parsing (memory efficient)")

            with gzip.open(self.input_file, 'rb') as f:
                # Parse JSON array incrementally
                parser = ijson.items(f, 'item')
                for event in parser:
                    yield event

        except ImportError:
            logger.warning("ijson not installed, falling back to standard JSON loading")
            logger.warning("For 2M+ events, install ijson: pip install ijson")

            # Fallback: load entire file (not recommended for large files)
            import json
            with gzip.open(self.input_file, 'rt', encoding='utf-8') as f:
                data = json.load(f)
                for event in data:
                    yield event

    def process_events_in_batches(self) -> Iterator[pd.DataFrame]:
        """
        Process events in batches, yielding DataFrames for writing.
        """
        batch = []
        batch_num = 0

        logger.info(f"Starting streaming processing with batch size {self.chunk_size:,}")

        for event in self.load_events_streaming():
            self.stats['total_processed'] += 1

            # Log progress
            if self.stats['total_processed'] % 100000 == 0:
                logger.info(f"Processed {self.stats['total_processed']:,} events...")

            # Clean and validate event
            if not self._is_valid_event(event):
                self.stats['invalid_removed'] += 1
                continue

            # Check for duplicates
            if event['event_id'] in self.seen_event_ids:
                self.stats['duplicates_removed'] += 1
                continue

            self.seen_event_ids.add(event['event_id'])

            # Update session tracking
            self._update_session_data(event)

            # Add to batch
            batch.append(event)

            # When batch is full, process and yield
            if len(batch) >= self.chunk_size:
                df = self._process_batch(batch, batch_num)
                yield df
                batch = []
                batch_num += 1

        # Process remaining events
        if batch:
            df = self._process_batch(batch, batch_num)
            yield df

    def _is_valid_event(self, event: dict) -> bool:
        """Validate event has required fields and valid data."""
        # Check required fields
        required_fields = ['event_id', 'session_id', 'customer_id', 'event_type']
        for field in required_fields:
            if field not in event or event[field] is None:
                return False

        # Check numeric fields are valid
        if event.get('product_price_vnd', 0) < 0:
            return False
        if event.get('quantity', 0) < 0:
            return False

        return True

    def _update_session_data(self, event: dict):
        """Update session tracking data incrementally."""
        session_id = event['session_id']
        session = self.session_data[session_id]

        session['events'].append(event['event_type'])
        session['timestamps'].append(pd.to_datetime(event['timestamp']))

        if session['customer_id'] is None:
            session['customer_id'] = event['customer_id']
            session['source'] = event.get('source', 'unknown')
            session['device'] = event.get('device', 'unknown')

    def _process_batch(self, batch: list, batch_num: int) -> pd.DataFrame:
        """Process a batch of events into a cleaned DataFrame."""
        df = pd.DataFrame(batch)

        # Clean data
        df = self._clean_dataframe(df)

        # Add journey information
        df = self._add_journey_info(df)

        self.stats['total_cleaned'] += len(df)

        logger.info(f"Batch {batch_num + 1} processed: {len(df):,} events "
                   f"(Total: {self.stats['total_cleaned']:,})")

        return df

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and enrich DataFrame."""
        # Convert timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour

        # Handle missing values
        utm_fields = ['utm_source', 'utm_medium', 'utm_campaign']
        for field in utm_fields:
            if field in df.columns:
                df[field] = df[field].fillna('unknown')

        if 'referrer' in df.columns:
            df['referrer'] = df['referrer'].fillna('direct')

        # Ensure numeric types
        numeric_fields = ['product_price_vnd', 'product_price_usd',
                         'quantity', 'line_total_vnd', 'line_total_usd']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0)

        return df

    def _add_journey_info(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add session journey information to events."""
        # Sort by session and timestamp
        df = df.sort_values(['session_id', 'timestamp'])

        # Add sequence number
        df['event_sequence_num'] = df.groupby('session_id').cumcount() + 1

        # Add session metrics
        session_info = []
        for _, row in df.iterrows():
            session_id = row['session_id']
            session = self.session_data[session_id]

            timestamps = session['timestamps']
            if timestamps:
                duration = (max(timestamps) - min(timestamps)).total_seconds()
                session_info.append({
                    'session_start': min(timestamps),
                    'session_end': max(timestamps),
                    'session_duration_seconds': duration,
                    'total_events': len(session['events']),
                    'event_journey': ','.join(session['events'])
                })
            else:
                session_info.append({
                    'session_start': row['timestamp'],
                    'session_end': row['timestamp'],
                    'session_duration_seconds': 0,
                    'total_events': 1,
                    'event_journey': row['event_type']
                })

        info_df = pd.DataFrame(session_info)
        df = pd.concat([df.reset_index(drop=True), info_df], axis=1)

        return df

    def save_batch_to_parquet(self, df: pd.DataFrame, is_first: bool):
        """Save batch to partitioned parquet files."""
        if len(df) == 0:
            return

        output_path = self.output_dir / "cart_events_cleaned"

        # Determine write mode
        if is_first:
            # First batch: create new dataset
            df.to_parquet(
                output_path,
                engine='pyarrow',
                partition_cols=['date'],
                compression='snappy',
                index=False
            )
        else:
            # Subsequent batches: append
            # Write to temporary location then merge
            temp_path = self.output_dir / f"temp_{datetime.now().timestamp()}"
            df.to_parquet(
                temp_path,
                engine='pyarrow',
                partition_cols=['date'],
                compression='snappy',
                index=False
            )

            # Merge with existing data
            import pyarrow.parquet as pq
            import pyarrow as pa

            # Read both datasets
            existing = pq.ParquetDataset(output_path, use_legacy_dataset=False)
            new_data = pq.ParquetDataset(temp_path, use_legacy_dataset=False)

            # Combine and write
            combined_table = pa.concat_tables([
                existing.read(),
                new_data.read()
            ])

            pq.write_to_dataset(
                combined_table,
                root_path=output_path,
                partition_cols=['date'],
                compression='snappy'
            )

            # Clean up temp
            import shutil
            shutil.rmtree(temp_path)

    def generate_session_metrics(self) -> pd.DataFrame:
        """Generate final session metrics from tracked data."""
        logger.info(f"Generating session metrics for {len(self.session_data):,} sessions")

        session_list = []
        for session_id, data in self.session_data.items():
            timestamps = data['timestamps']
            if timestamps:
                session_list.append({
                    'session_id': session_id,
                    'customer_id': data['customer_id'],
                    'source': data['source'],
                    'device': data['device'],
                    'session_start': min(timestamps),
                    'session_end': max(timestamps),
                    'total_events': len(data['events']),
                    'event_journey': ','.join(data['events']),
                    'session_duration_seconds': (max(timestamps) - min(timestamps)).total_seconds(),
                    'has_purchase': False
                })

        return pd.DataFrame(session_list)

    def run_transformation(self):
        """Execute the full transformation pipeline with streaming."""
        logger.info("=" * 80)
        logger.info("Starting Cart Events Transformation Pipeline (EXTREME MODE)")
        logger.info("=" * 80)
        logger.info(f"Batch size: {self.chunk_size:,} events")
        logger.info("Memory-efficient streaming processing enabled")
        logger.info("=" * 80)

        is_first_batch = True

        # Process in streaming batches
        for batch_df in self.process_events_in_batches():
            # Save batch
            self.save_batch_to_parquet(batch_df, is_first_batch)
            is_first_batch = False

            # Clear memory
            del batch_df

        # Generate session metrics
        session_metrics = self.generate_session_metrics()
        session_output_path = self.output_dir / "session_metrics.parquet"
        session_metrics.to_parquet(session_output_path, index=False)

        # Print final statistics
        self._print_statistics(session_metrics)

        logger.info("=" * 80)
        logger.info("Transformation Complete!")
        logger.info("=" * 80)

        return session_metrics

    def _print_statistics(self, session_metrics: pd.DataFrame):
        """Print final processing statistics."""
        logger.info("=" * 80)
        logger.info("PROCESSING STATISTICS")
        logger.info("=" * 80)
        logger.info(f"Total events processed: {self.stats['total_processed']:,}")
        logger.info(f"Events after cleaning: {self.stats['total_cleaned']:,}")
        logger.info(f"Duplicates removed: {self.stats['duplicates_removed']:,}")
        logger.info(f"Invalid events removed: {self.stats['invalid_removed']:,}")
        logger.info(f"Unique sessions: {len(session_metrics):,}")
        logger.info(f"Unique customers: {session_metrics['customer_id'].nunique():,}")

        # Memory usage
        import psutil
        import os
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        logger.info(f"Peak memory usage: ~{memory_mb:.0f} MB")


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description='Transform cart events (Extreme Big Data version)')
    parser.add_argument('--input', default='../shared_data/private_data/cart_tracking/cart_events.json.gz',
                       help='Input file path')
    parser.add_argument('--output', default='output_extreme',
                       help='Output directory')
    parser.add_argument('--chunk-size', type=int, default=100000,
                       help='Batch size for processing (default: 100,000)')

    args = parser.parse_args()

    logger.info(f"Input: {args.input}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Batch size: {args.chunk_size:,}")

    # Create transformer and run
    transformer = CartEventsTransformerExtreme(args.input, args.output, args.chunk_size)
    session_metrics = transformer.run_transformation()

    return session_metrics


if __name__ == "__main__":
    main()

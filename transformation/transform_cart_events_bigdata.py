"""
Data Transformation Pipeline for Cart Events - BIG DATA VERSION
Optimized for processing millions of events with chunked processing and memory efficiency.
"""

import json
import gzip
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Iterator, Dict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CartEventsTransformerBigData:
    """Transform cart events data with chunked processing for large datasets."""

    def __init__(self, input_file: str, output_dir: str, chunk_size: int = 50000):
        """
        Initialize the transformer.

        Args:
            input_file: Path to the cart_events.json.gz file
            output_dir: Directory to save the transformed parquet files
            chunk_size: Number of events to process at once (default: 50,000)
        """
        self.input_file = input_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size

        # Temporary storage for session aggregation
        self.session_data = {}

    def load_data_in_chunks(self) -> Iterator[pd.DataFrame]:
        """Load cart events data in chunks from gzipped JSON file."""
        logger.info(f"Loading data in chunks of {self.chunk_size:,} from {self.input_file}")

        with gzip.open(self.input_file, 'rt', encoding='utf-8') as f:
            data = json.load(f)
            total_events = len(data)
            logger.info(f"Total events to process: {total_events:,}")

            # Process in chunks
            for i in range(0, total_events, self.chunk_size):
                chunk = data[i:i + self.chunk_size]
                df_chunk = pd.DataFrame(chunk)
                logger.info(f"Processing chunk {i//self.chunk_size + 1}: events {i+1:,} to {min(i+self.chunk_size, total_events):,}")
                yield df_chunk

    def clean_data_chunk(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean a chunk of data."""
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour

        # Remove records with missing critical fields
        critical_fields = ['event_id', 'session_id', 'customer_id', 'event_type']
        df = df.dropna(subset=critical_fields)

        # Handle missing utm fields
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

        # Remove invalid events
        df = df[df['product_price_vnd'] >= 0]
        df = df[df['quantity'] >= 0]

        return df

    def deduplicate_chunk(self, df: pd.DataFrame, seen_ids: set) -> tuple[pd.DataFrame, set]:
        """
        Remove duplicates within chunk and track across chunks.

        Returns:
            Tuple of (deduplicated dataframe, updated seen_ids set)
        """
        # Filter out events we've already seen
        mask = ~df['event_id'].isin(seen_ids)
        df_deduped = df[mask].copy()

        # Remove duplicates within this chunk
        df_deduped = df_deduped.drop_duplicates(subset=['event_id'], keep='first')

        # Update seen IDs
        seen_ids.update(df_deduped['event_id'].tolist())

        return df_deduped, seen_ids

    def update_session_metrics(self, df: pd.DataFrame):
        """Update session-level metrics incrementally."""
        for _, row in df.iterrows():
            session_id = row['session_id']

            if session_id not in self.session_data:
                self.session_data[session_id] = {
                    'events': [],
                    'timestamps': [],
                    'customer_id': row['customer_id'],
                    'source': row['source'],
                    'device': row['device']
                }

            self.session_data[session_id]['events'].append(row['event_type'])
            self.session_data[session_id]['timestamps'].append(row['timestamp'])

    def add_journey_info(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add journey information to events based on accumulated session data."""
        # Sort by session and timestamp
        df = df.sort_values(['session_id', 'timestamp'])

        # Add sequence number
        df['event_sequence_num'] = df.groupby('session_id').cumcount() + 1

        # Add session metrics from accumulated data
        session_metrics = []
        for _, row in df.iterrows():
            session_id = row['session_id']
            if session_id in self.session_data:
                session = self.session_data[session_id]
                timestamps = session['timestamps']

                metrics = {
                    'session_start': min(timestamps),
                    'session_end': max(timestamps),
                    'total_events': len(session['events']),
                    'event_journey': ','.join(session['events'])
                }

                # Calculate duration
                duration = (max(timestamps) - min(timestamps)).total_seconds()
                metrics['session_duration_seconds'] = duration

                session_metrics.append(metrics)
            else:
                # Should not happen, but handle gracefully
                session_metrics.append({
                    'session_start': row['timestamp'],
                    'session_end': row['timestamp'],
                    'total_events': 1,
                    'event_journey': row['event_type'],
                    'session_duration_seconds': 0
                })

        # Add metrics to dataframe
        metrics_df = pd.DataFrame(session_metrics)
        df = pd.concat([df.reset_index(drop=True), metrics_df], axis=1)

        return df

    def save_chunk_to_parquet(self, df: pd.DataFrame, chunk_num: int):
        """Save a processed chunk to parquet."""
        if len(df) == 0:
            return

        output_path = self.output_dir / "cart_events_cleaned"

        # For first chunk, create new parquet dataset
        # For subsequent chunks, append to existing
        mode = 'overwrite' if chunk_num == 0 else 'append'

        df.to_parquet(
            output_path,
            engine='pyarrow',
            partition_cols=['date'],
            compression='snappy',
            index=False,
            mode=mode,
            existing_data_behavior='overwrite_or_ignore'
        )

        logger.info(f"Saved chunk {chunk_num + 1} with {len(df):,} events to parquet")

    def generate_session_metrics(self) -> pd.DataFrame:
        """Generate final session metrics from accumulated data."""
        logger.info(f"Generating session metrics for {len(self.session_data):,} sessions")

        session_list = []
        for session_id, data in self.session_data.items():
            timestamps = data['timestamps']
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
                'has_purchase': False  # Placeholder
            })

        return pd.DataFrame(session_list)

    def run_transformation(self):
        """Execute the full transformation pipeline with chunked processing."""
        logger.info("=" * 80)
        logger.info("Starting Cart Events Transformation Pipeline (BIG DATA MODE)")
        logger.info("=" * 80)

        seen_event_ids = set()
        total_processed = 0
        total_cleaned = 0
        chunk_num = 0

        # Process data in chunks
        for chunk_df in self.load_data_in_chunks():
            initial_chunk_size = len(chunk_df)

            # Clean chunk
            chunk_df = self.clean_data_chunk(chunk_df)

            # Deduplicate
            chunk_df, seen_event_ids = self.deduplicate_chunk(chunk_df, seen_event_ids)

            # Update session metrics incrementally
            self.update_session_metrics(chunk_df)

            # Add journey info
            chunk_df = self.add_journey_info(chunk_df)

            # Save chunk
            self.save_chunk_to_parquet(chunk_df, chunk_num)

            total_processed += initial_chunk_size
            total_cleaned += len(chunk_df)
            chunk_num += 1

            logger.info(f"Progress: {total_processed:,} events processed, {total_cleaned:,} events kept")

        # Generate and save session metrics
        session_metrics = self.generate_session_metrics()
        session_output_path = self.output_dir / "session_metrics.parquet"
        session_metrics.to_parquet(session_output_path, index=False)
        logger.info(f"Session metrics saved to {session_output_path}")

        # Generate summary
        self._generate_summary(total_processed, total_cleaned, session_metrics)

        logger.info("=" * 80)
        logger.info("Transformation Complete!")
        logger.info("=" * 80)

        return session_metrics

    def _generate_summary(self, total_processed: int, total_cleaned: int, session_metrics: pd.DataFrame):
        """Generate and save transformation summary."""
        logger.info(f"Total events processed: {total_processed:,}")
        logger.info(f"Total events after cleaning/dedup: {total_cleaned:,}")
        logger.info(f"Unique sessions: {len(session_metrics):,}")
        logger.info(f"Unique customers: {session_metrics['customer_id'].nunique():,}")

        # Read back the data to get event type distribution
        output_path = self.output_dir / "cart_events_cleaned"
        if output_path.exists():
            df_sample = pd.read_parquet(output_path)
            logger.info(f"Event types distribution:")
            for event_type, count in df_sample['event_type'].value_counts().items():
                logger.info(f"  - {event_type}: {count:,}")


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description='Transform cart events data (Big Data version)')
    parser.add_argument('--input', default='../shared_data/private_data/cart_tracking/cart_events.json.gz',
                       help='Input file path')
    parser.add_argument('--output', default='output_bigdata',
                       help='Output directory')
    parser.add_argument('--chunk-size', type=int, default=50000,
                       help='Chunk size for processing (default: 50000)')

    args = parser.parse_args()

    # Create transformer and run
    transformer = CartEventsTransformerBigData(args.input, args.output, args.chunk_size)
    session_metrics = transformer.run_transformation()

    return session_metrics


if __name__ == "__main__":
    main()

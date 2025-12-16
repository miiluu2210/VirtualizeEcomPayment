"""
Aggregation Script for Cart Events Metrics
This script reads the transformed parquet files and calculates various session-level metrics.
"""

import pandas as pd
from pathlib import Path
import logging
from typing import Dict, List
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SessionMetricsAggregator:
    """Aggregate and analyze session-level metrics from transformed cart events."""

    def __init__(self, input_dir: str):
        """
        Initialize the aggregator.

        Args:
            input_dir: Directory containing the transformed parquet files
        """
        self.input_dir = Path(input_dir)
        self.session_metrics_file = self.input_dir / "session_metrics.parquet"
        self.cart_events_dir = self.input_dir / "cart_events_cleaned"

    def load_session_metrics(self) -> pd.DataFrame:
        """Load session metrics from parquet file."""
        logger.info(f"Loading session metrics from {self.session_metrics_file}")

        if not self.session_metrics_file.exists():
            raise FileNotFoundError(f"Session metrics file not found: {self.session_metrics_file}")

        df = pd.read_parquet(self.session_metrics_file)
        logger.info(f"Loaded {len(df)} session records")

        return df

    def load_cart_events(self) -> pd.DataFrame:
        """Load all cart events from partitioned parquet files."""
        logger.info(f"Loading cart events from {self.cart_events_dir}")

        if not self.cart_events_dir.exists():
            raise FileNotFoundError(f"Cart events directory not found: {self.cart_events_dir}")

        df = pd.read_parquet(self.cart_events_dir)
        logger.info(f"Loaded {len(df)} cart event records")

        return df

    def calculate_average_session_duration(self, session_df: pd.DataFrame) -> Dict:
        """
        Calculate average session duration statistics.

        Returns:
            Dictionary with duration statistics
        """
        logger.info("Calculating average session duration...")

        stats = {
            'average_duration_seconds': session_df['session_duration_seconds'].mean(),
            'median_duration_seconds': session_df['session_duration_seconds'].median(),
            'min_duration_seconds': session_df['session_duration_seconds'].min(),
            'max_duration_seconds': session_df['session_duration_seconds'].max(),
            'std_duration_seconds': session_df['session_duration_seconds'].std(),
            'total_sessions': len(session_df)
        }

        # Convert to minutes for readability
        stats['average_duration_minutes'] = stats['average_duration_seconds'] / 60
        stats['median_duration_minutes'] = stats['median_duration_seconds'] / 60

        logger.info(f"Average session duration: {stats['average_duration_minutes']:.2f} minutes")
        logger.info(f"Median session duration: {stats['median_duration_minutes']:.2f} minutes")

        return stats

    def calculate_purchase_sessions(self, events_df: pd.DataFrame) -> Dict:
        """
        Calculate number of sessions with purchase actions.

        Note: Since we don't have explicit 'purchase' events in the data,
        we'll use a heuristic: sessions that end with 'add_to_cart' or have
        significant cart activity might indicate purchase intent.

        Returns:
            Dictionary with purchase statistics
        """
        logger.info("Calculating purchase session statistics...")

        # Get the last event for each session
        last_events = events_df.sort_values('timestamp').groupby('session_id').last()

        # Heuristic: Consider sessions with multiple add_to_cart events as potential purchases
        session_event_summary = events_df.groupby('session_id').agg({
            'event_type': lambda x: list(x),
            'event_id': 'count'
        }).reset_index()

        session_event_summary.columns = ['session_id', 'event_types', 'event_count']

        # Count sessions with purchase indicators
        # Heuristic: Sessions with at least 2 events and ending with add_to_cart
        session_event_summary['has_purchase_intent'] = session_event_summary.apply(
            lambda row: (
                row['event_count'] >= 2 and
                'add_to_cart' in row['event_types'] and
                row['event_types'][-1] == 'add_to_cart'
            ),
            axis=1
        )

        purchase_stats = {
            'total_sessions': len(session_event_summary),
            'sessions_with_purchase_intent': session_event_summary['has_purchase_intent'].sum(),
            'purchase_intent_rate': (
                session_event_summary['has_purchase_intent'].sum() / len(session_event_summary) * 100
            )
        }

        logger.info(f"Sessions with purchase intent: {purchase_stats['sessions_with_purchase_intent']} "
                   f"({purchase_stats['purchase_intent_rate']:.2f}%)")

        return purchase_stats, session_event_summary

    def calculate_event_statistics(self, events_df: pd.DataFrame) -> Dict:
        """Calculate various event-level statistics."""
        logger.info("Calculating event statistics...")

        stats = {
            'total_events': len(events_df),
            'event_type_distribution': events_df['event_type'].value_counts().to_dict(),
            'unique_sessions': events_df['session_id'].nunique(),
            'unique_customers': events_df['customer_id'].nunique(),
            'unique_products': events_df['product_id'].nunique(),
            'average_events_per_session': len(events_df) / events_df['session_id'].nunique(),
        }

        # Source and device statistics
        stats['source_distribution'] = events_df['source'].value_counts().to_dict()
        stats['device_distribution'] = events_df['device'].value_counts().to_dict()

        return stats

    def calculate_customer_journey_metrics(self, events_df: pd.DataFrame) -> Dict:
        """Analyze customer journey patterns."""
        logger.info("Calculating customer journey metrics...")

        # Get journey patterns (sequence of event types)
        journey_patterns = events_df.groupby('session_id')['event_type'].apply(
            lambda x: ' -> '.join(x)
        ).value_counts().head(20)

        metrics = {
            'top_journey_patterns': journey_patterns.to_dict(),
            'average_journey_length': events_df.groupby('session_id').size().mean(),
            'max_journey_length': events_df.groupby('session_id').size().max(),
            'min_journey_length': events_df.groupby('session_id').size().min()
        }

        logger.info(f"Average journey length: {metrics['average_journey_length']:.2f} events")
        logger.info(f"Top journey pattern: {list(journey_patterns.index)[0]} "
                   f"({list(journey_patterns.values)[0]} sessions)")

        return metrics

    def calculate_time_based_metrics(self, events_df: pd.DataFrame) -> Dict:
        """Calculate time-based metrics (daily, hourly patterns)."""
        logger.info("Calculating time-based metrics...")

        # Ensure timestamp is datetime
        events_df['timestamp'] = pd.to_datetime(events_df['timestamp'])
        events_df['date'] = events_df['timestamp'].dt.date
        events_df['hour'] = events_df['timestamp'].dt.hour
        events_df['day_of_week'] = events_df['timestamp'].dt.day_name()

        metrics = {
            'events_by_date': events_df.groupby('date').size().to_dict(),
            'events_by_hour': events_df.groupby('hour').size().to_dict(),
            'events_by_day_of_week': events_df.groupby('day_of_week').size().to_dict(),
            'sessions_by_date': events_df.groupby('date')['session_id'].nunique().to_dict()
        }

        return metrics

    def generate_summary_report(self, all_metrics: Dict) -> str:
        """Generate a human-readable summary report."""
        report = []
        report.append("=" * 80)
        report.append("CART EVENTS AGGREGATION SUMMARY REPORT")
        report.append("=" * 80)
        report.append("")

        # Session Duration Statistics
        report.append("SESSION DURATION STATISTICS")
        report.append("-" * 80)
        duration_stats = all_metrics['session_duration_stats']
        report.append(f"Total Sessions: {duration_stats['total_sessions']:,}")
        report.append(f"Average Duration: {duration_stats['average_duration_minutes']:.2f} minutes")
        report.append(f"Median Duration: {duration_stats['median_duration_minutes']:.2f} minutes")
        report.append(f"Min Duration: {duration_stats['min_duration_seconds']:.2f} seconds")
        report.append(f"Max Duration: {duration_stats['max_duration_seconds']:.2f} seconds")
        report.append("")

        # Purchase Intent Statistics
        report.append("PURCHASE INTENT STATISTICS")
        report.append("-" * 80)
        purchase_stats = all_metrics['purchase_stats']
        report.append(f"Total Sessions: {purchase_stats['total_sessions']:,}")
        report.append(f"Sessions with Purchase Intent: {purchase_stats['sessions_with_purchase_intent']:,}")
        report.append(f"Purchase Intent Rate: {purchase_stats['purchase_intent_rate']:.2f}%")
        report.append("")

        # Event Statistics
        report.append("EVENT STATISTICS")
        report.append("-" * 80)
        event_stats = all_metrics['event_stats']
        report.append(f"Total Events: {event_stats['total_events']:,}")
        report.append(f"Unique Sessions: {event_stats['unique_sessions']:,}")
        report.append(f"Unique Customers: {event_stats['unique_customers']:,}")
        report.append(f"Unique Products: {event_stats['unique_products']:,}")
        report.append(f"Average Events per Session: {event_stats['average_events_per_session']:.2f}")
        report.append("")
        report.append("Event Type Distribution:")
        for event_type, count in event_stats['event_type_distribution'].items():
            report.append(f"  - {event_type}: {count:,}")
        report.append("")

        # Customer Journey Metrics
        report.append("CUSTOMER JOURNEY METRICS")
        report.append("-" * 80)
        journey_metrics = all_metrics['journey_metrics']
        report.append(f"Average Journey Length: {journey_metrics['average_journey_length']:.2f} events")
        report.append(f"Max Journey Length: {journey_metrics['max_journey_length']} events")
        report.append(f"Min Journey Length: {journey_metrics['min_journey_length']} events")
        report.append("")
        report.append("Top 10 Journey Patterns:")
        for i, (pattern, count) in enumerate(list(journey_metrics['top_journey_patterns'].items())[:10], 1):
            report.append(f"  {i}. {pattern}: {count} sessions")
        report.append("")

        # Device and Source Distribution
        report.append("DEVICE DISTRIBUTION")
        report.append("-" * 80)
        for device, count in event_stats['device_distribution'].items():
            percentage = (count / event_stats['total_events']) * 100
            report.append(f"  - {device}: {count:,} ({percentage:.2f}%)")
        report.append("")

        report.append("SOURCE DISTRIBUTION")
        report.append("-" * 80)
        for source, count in event_stats['source_distribution'].items():
            percentage = (count / event_stats['total_events']) * 100
            report.append(f"  - {source}: {count:,} ({percentage:.2f}%)")
        report.append("")

        report.append("=" * 80)

        return "\n".join(report)

    def run_aggregation(self):
        """Execute the full aggregation pipeline."""
        logger.info("=" * 80)
        logger.info("Starting Cart Events Aggregation Pipeline")
        logger.info("=" * 80)

        # Load data
        session_df = self.load_session_metrics()
        events_df = self.load_cart_events()

        # Calculate all metrics
        all_metrics = {
            'session_duration_stats': self.calculate_average_session_duration(session_df),
            'purchase_stats': self.calculate_purchase_sessions(events_df)[0],
            'event_stats': self.calculate_event_statistics(events_df),
            'journey_metrics': self.calculate_customer_journey_metrics(events_df),
            'time_metrics': self.calculate_time_based_metrics(events_df)
        }

        # Generate and save report
        report = self.generate_summary_report(all_metrics)
        print("\n" + report)

        # Save metrics to JSON
        output_file = self.input_dir / "aggregation_metrics.json"
        with open(output_file, 'w') as f:
            # Convert non-serializable objects to strings
            serializable_metrics = {}
            for key, value in all_metrics.items():
                if isinstance(value, dict):
                    serializable_metrics[key] = {
                        str(k): (int(v) if isinstance(v, (pd.Int64Dtype, int)) else
                                float(v) if isinstance(v, float) else str(v))
                        for k, v in value.items()
                    }
                else:
                    serializable_metrics[key] = str(value)

            json.dump(serializable_metrics, f, indent=2, default=str)

        logger.info(f"Aggregation metrics saved to {output_file}")

        # Save report to text file
        report_file = self.input_dir / "aggregation_report.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        logger.info(f"Aggregation report saved to {report_file}")

        logger.info("=" * 80)
        logger.info("Aggregation Complete!")
        logger.info("=" * 80)

        return all_metrics


def main():
    """Main execution function."""
    # Configuration
    INPUT_DIR = "output"

    # Create aggregator and run
    aggregator = SessionMetricsAggregator(INPUT_DIR)
    metrics = aggregator.run_aggregation()

    return metrics


if __name__ == "__main__":
    main()

# Cart Events Data Transformation Pipeline

This folder contains the data transformation and aggregation pipeline for processing cart events data.

## Overview

The pipeline consists of three main scripts:

1. **`transform_cart_events.py`** - Data transformation with cleaning, deduplication, and user journey creation
2. **`aggregate_metrics.py`** - Metrics aggregation and analysis
3. **`run_pipeline.py`** - Main runner that executes the complete pipeline

## Features

### Data Transformation (`transform_cart_events.py`)

- **Data Loading**: Loads cart events from gzipped JSON file
- **Data Cleaning**:
  - Converts timestamps to datetime format
  - Handles missing values in UTM fields and referrer
  - Validates and cleans numeric fields
  - Removes invalid records (negative prices/quantities)
- **Deduplication**: Removes duplicate events based on `event_id`
- **User Journey Creation**:
  - Creates event sequence numbers within each session
  - Tracks the complete journey of user actions per session
  - Calculates session duration
  - Generates session-level metrics
- **Parquet Export**:
  - Saves data partitioned by date
  - Uses Snappy compression for efficiency
  - Creates separate session metrics file

### Metrics Aggregation (`aggregate_metrics.py`)

Calculates comprehensive metrics including:

- **Session Duration Statistics**:
  - Average, median, min, max session duration
  - Standard deviation
- **Purchase Intent Analysis**:
  - Identifies sessions with purchase intent
  - Calculates purchase intent rate
- **Event Statistics**:
  - Event type distribution
  - Source and device distribution
  - Average events per session
- **Customer Journey Metrics**:
  - Top journey patterns
  - Average journey length
  - Journey pattern analysis
- **Time-based Metrics**:
  - Events by date, hour, day of week
  - Sessions by date

## Installation

Install required dependencies:

```bash
pip install pandas pyarrow
```

Or install from the project requirements:

```bash
pip install -r requirements.txt
```

## Usage

### Run Complete Pipeline

The easiest way to run the entire pipeline:

```bash
python transformation/run_pipeline.py
```

This will:
1. Transform and clean the cart events data
2. Generate user journeys
3. Save partitioned parquet files
4. Calculate and display aggregation metrics
5. Generate summary reports

### Run Individual Scripts

You can also run each script separately:

#### Transform Data Only

```bash
python transformation/transform_cart_events.py
```

#### Aggregate Metrics Only

```bash
python transformation/aggregate_metrics.py
```

## Output Files

The pipeline generates the following output files in `transformation/output/`:

### Transformed Data

- **`cart_events_cleaned/`** - Partitioned parquet files by date
  - Contains cleaned and deduplicated events
  - Includes user journey information
  - Each event has session-level metrics attached

- **`session_metrics.parquet`** - Session-level summary data
  - One record per session
  - Contains session duration, event counts, journey sequences
  - Useful for session-level analysis

- **`transformation_summary.csv`** - Daily summary statistics
  - Events, sessions, and customers per day
  - Event type distribution per day

### Aggregation Results

- **`aggregation_report.txt`** - Human-readable summary report
  - Session duration statistics
  - Purchase intent analysis
  - Event statistics and distributions
  - Top journey patterns
  - Device and source breakdown

- **`aggregation_metrics.json`** - Machine-readable metrics
  - All calculated metrics in JSON format
  - Can be consumed by other systems or dashboards

## Data Schema

### Input Schema (cart_events.json)

```json
{
  "event_id": "evt_371ec2543769",
  "event_type": "add_to_cart",
  "timestamp": "2025-08-25T23:04:11.545981",
  "timestamp_unix": 1756137851545,
  "session_id": "sess_16d4694fbdb14807",
  "customer_id": 445412,
  "product_id": 90,
  "product_name": "...",
  "product_sku": "...",
  "product_category": "...",
  "product_brand": "...",
  "product_price_vnd": 3500000,
  "product_price_usd": 145.83,
  "quantity": 2,
  "old_quantity": null,
  "line_total_vnd": 7000000,
  "line_total_usd": 291.66,
  "source": "mobile_app",
  "device": "tablet",
  "browser": "Chrome",
  ...
}
```

### Output Schema (Enhanced)

The transformed data includes all original fields plus:

- `date` - Date extracted from timestamp
- `hour` - Hour extracted from timestamp
- `event_sequence_num` - Sequence number within session
- `session_start` - First event timestamp in session
- `session_end` - Last event timestamp in session
- `session_duration_seconds` - Duration of the session
- `total_events` - Total number of events in the session
- `event_journey` - Comma-separated sequence of event types

## User Journey Tracking

The pipeline creates detailed user journeys by:

1. **Sequencing Events**: Orders all events within a session by timestamp
2. **Numbering Events**: Assigns a sequence number to each event
3. **Journey String**: Creates a readable journey path (e.g., "add_to_cart -> update_quantity -> remove_from_cart")
4. **Session Metrics**: Calculates duration and event counts per session

Example user journey:
```
Session: sess_abc123
Journey: add_to_cart -> update_quantity -> add_to_cart -> remove_from_cart
Duration: 245 seconds
Total Events: 4
```

## Metrics Explained

### Session Duration
- **Average**: Mean time users spend in a session
- **Median**: Middle value, less affected by outliers
- Helps understand typical user engagement time

### Purchase Intent
Since the dataset doesn't have explicit "purchase" events, we use a heuristic:
- Sessions with 2+ events
- Ending with "add_to_cart"
- This indicates users who added items and didn't remove them

### Journey Patterns
Most common sequences of user actions, helping understand:
- Typical user behavior flows
- Where users drop off
- Which patterns lead to purchases

## Performance Considerations

- **Partitioning**: Data is partitioned by date for efficient querying
- **Compression**: Snappy compression reduces storage size
- **Parquet Format**: Column-oriented format enables fast analytics
- **Memory Efficient**: Processes data in chunks where applicable

## Extending the Pipeline

### Adding New Metrics

To add new metrics, modify `aggregate_metrics.py`:

```python
def calculate_custom_metric(self, df: pd.DataFrame) -> Dict:
    """Your custom metric calculation."""
    # Your logic here
    return metrics
```

Then add to the `run_aggregation` method:

```python
all_metrics['custom_metric'] = self.calculate_custom_metric(events_df)
```

### Adding New Transformations

Modify `transform_cart_events.py`:

```python
def custom_transformation(self, df: pd.DataFrame) -> pd.DataFrame:
    """Your custom transformation."""
    # Your logic here
    return df
```

Then add to the `run_transformation` pipeline.

## Troubleshooting

### Issue: Out of Memory
- Process data in chunks
- Reduce partition size
- Use more efficient data types

### Issue: Slow Performance
- Check partition sizes
- Verify compression settings
- Consider using Dask for large datasets

### Issue: Missing Data
- Check input file path
- Verify file permissions
- Review data cleaning logs

## Example Analysis Queries

After running the pipeline, you can analyze the data:

```python
import pandas as pd

# Load transformed data
df = pd.read_parquet('transformation/output/cart_events_cleaned')

# Find sessions with longest duration
long_sessions = df.groupby('session_id').first().nlargest(10, 'session_duration_seconds')

# Analyze conversion by source
conversion = df.groupby('source').agg({
    'session_id': 'nunique',
    'event_type': lambda x: (x == 'add_to_cart').sum()
})

# Time-of-day analysis
hourly = df.groupby('hour').size()
```

## Future Enhancements

Potential improvements:

1. **Real Purchase Events**: Integrate actual purchase data
2. **Funnel Analysis**: Track conversion funnel stages
3. **Cohort Analysis**: Analyze user cohorts over time
4. **Anomaly Detection**: Identify unusual patterns
5. **Predictive Models**: Predict purchase likelihood
6. **Real-time Processing**: Stream processing for live data

## Contact & Support

For questions or issues with the pipeline, please refer to the main project documentation.

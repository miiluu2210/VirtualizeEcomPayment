# README2: Cart Events API & Transformation Pipeline - Flow & Logic

> Chi tiết về luồng xử lý, logic và thứ tự chạy của Cart Events API và Transformation Pipeline

---

## 📋 MỤC LỤC

1. [Tổng Quan Kiến Trúc](#tổng-quan-kiến-trúc)
2. [API Events - Luồng & Logic](#api-events---luồng--logic)
3. [Transformation Pipeline - Logic](#transformation-pipeline---logic)
4. [Docker Integration Flow](#docker-integration-flow)
5. [Luồng Hoàn Chỉnh End-to-End](#luồng-hoàn-chỉnh-end-to-end)

---

## 🏗️ TỔNG QUAN KIẾN TRÚC

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CART EVENTS SYSTEM                            │
└─────────────────────────────────────────────────────────────────────┘

PHASE 1: DATA GENERATION (API)
┌──────────────────────────┐
│   FastAPI Server         │
│   routers/               │
│   cart_tracking_router.py│
└──────────┬───────────────┘
           │
           ├─→ Generate Events (POST /cart/generate/events)
           │   └─→ Save: shared_data/private_data/cart_tracking/cart_events.json.gz
           │
           ├─→ Query Events (GET /cart/events)
           ├─→ Filter by Customer/Product/Session
           ├─→ Statistics (GET /cart/statistics)
           └─→ Abandoned Carts (GET /cart/abandoned)

           ↓

PHASE 2: TRANSFORMATION (Python Scripts)
┌──────────────────────────┐
│   transformation/        │
│   ├─ transform_*.py      │
│   └─ aggregate_*.py      │
└──────────┬───────────────┘
           │
           ├─→ Load: cart_events.json.gz
           ├─→ Clean & Deduplicate
           ├─→ Create User Journeys
           ├─→ Save: Partitioned Parquet Files
           └─→ Aggregate: Session Metrics

           ↓

PHASE 3: DOCKER ORCHESTRATION (Optional)
┌──────────────────────────┐
│   Docker Containers      │
│   docker/                │
└──────────┬───────────────┘
           │
           ├─→ Single Worker: Process entire file
           │
           └─→ Worker Pool: Parallel processing
               ├─ Redis Queue
               ├─ Scheduler splits work
               └─ 4-8 Workers process chunks
```

---

## 📡 API EVENTS - LUỒNG & LOGIC

### **Nhóm API Endpoints**

#### **1. Information Endpoint**
```
GET /cart/
```
**Mục đích:** Xem thông tin tổng quan API
**Response:** Danh sách endpoints và số lượng events hiện có

---

#### **2. Query Endpoints** (Đọc dữ liệu)

##### **2.1. Get All Events**
```
GET /cart/events?limit=100&offset=0&event_type=add_to_cart
```

**Logic:**
1. Load file `cart_events.json.gz`
2. Apply filters (nếu có):
   - `event_type`: add_to_cart, remove_from_cart, update_quantity, etc.
   - `source`: website, mobile_app, mobile_web
   - `device`: desktop, mobile, tablet
   - `start_date`, `end_date`: Filter theo thời gian
3. Sort by timestamp (descending)
4. Pagination: offset → offset + limit
5. Return: events + count + total

**Use case:** Lấy danh sách events với filter

---

##### **2.2. Get Events by Customer**
```
GET /cart/events/customer/{customer_id}?limit=100
```

**Logic:**
1. Load events
2. Filter: `customer_id == {customer_id}`
3. Sort by timestamp desc
4. Limit results
5. Return customer's journey

**Use case:** Xem lịch sử mua sắm của 1 khách hàng

---

##### **2.3. Get Events by Product**
```
GET /cart/events/product/{product_id}?limit=100
```

**Logic:**
1. Load events
2. Filter: `product_id == {product_id}`
3. Sort by timestamp desc
4. Return product interaction history

**Use case:** Phân tích sản phẩm nào được add/remove nhiều

---

##### **2.4. Get Events by Session**
```
GET /cart/events/session/{session_id}?limit=100
```

**Logic:**
1. Load events
2. Filter: `session_id == {session_id}`
3. Sort by timestamp asc (chronological order)
4. Return complete user journey trong 1 session

**Use case:** Tracking user behavior trong 1 phiên

---

#### **3. Analytics Endpoints**

##### **3.1. Statistics**
```
GET /cart/statistics
```

**Logic:**
1. Load tất cả events
2. Aggregate:
   ```python
   - Count by event_type
   - Count by source (website/mobile/app)
   - Count by device (desktop/mobile/tablet)
   - Count unique customers
   - Count unique sessions
   - Calculate add/remove ratio
   - Top 10 products added to cart
   ```
3. Return summary statistics

**Output:**
```json
{
  "total_events": 10000,
  "by_event_type": {
    "add_to_cart": 3387,
    "update_quantity": 3350,
    "remove_from_cart": 3263
  },
  "unique_customers": 1000,
  "unique_sessions": 1000,
  "add_remove_ratio": 1.04,
  "top_products_added": [...]
}
```

---

##### **3.2. Abandoned Carts**
```
GET /cart/abandoned?limit=50&hours_threshold=24
```

**Logic:**
1. Load events
2. Group by `session_id`
3. For each session:
   ```python
   cart = {}
   for event in session_events:
       if event_type == "add_to_cart":
           cart[product_id].quantity += quantity
       elif event_type == "remove_from_cart":
           cart[product_id].quantity -= quantity
       elif event_type == "update_quantity":
           cart[product_id].quantity = quantity
   ```
4. Filter sessions where:
   - `cart` has items (not empty)
   - `last_activity` > `hours_threshold`
5. Calculate `cart_value_vnd`
6. Sort by cart value descending
7. Return top abandoned carts

**Use case:** Recovery campaigns cho abandoned carts

---

#### **4. Generation Endpoints**

##### **4.1. Generate Events**
```
POST /cart/generate/events?count=10000&method=new
```

**Logic:**
1. **Check existing data:**
   - If exists và `method != "new"` → Warning (để tránh ghi đè nhầm)
   - If exists và `method == "new"` → Append mode
   - If not exists → Replace mode

2. **Start background generation:**
   ```python
   generation_status = {
       "is_generating": True,
       "cart_events": {
           "target": count,
           "generated": 0,
           "completed": False
       }
   }
   ```

3. **Generate in batches:**
   ```python
   batch_size = 50000
   num_batches = count / batch_size

   for batch in num_batches:
       # Generate batch
       events = generate_cart_events_batch(batch_size)

       # Update progress
       progress_percentage = (generated / target) * 100

       # Calculate ETA
       elapsed_time = now - start_time
       avg_time_per_event = elapsed_time / generated
       remaining_time = avg_time_per_event * remaining_events
   ```

4. **Generate logic per event:**
   ```python
   # Create sessions (~1000 sessions for 10K events)
   num_sessions = count // 10

   for session in sessions:
       # 30% guest users (customer_id = null)
       is_guest = random() < 0.3

       # Session context
       session = {
           "session_id": generate_session_id(),
           "customer_id": random_customer() if not is_guest else null,
           "source": random_choice([website, mobile_app, mobile_web]),
           "device": random_choice([desktop, mobile, tablet]),
           "browser": random_choice([Chrome, Safari, Firefox, Edge])
       }

   for i in range(count):
       # Pick random session
       session = random_choice(sessions)

       # Generate event
       event = {
           "event_id": generate_uuid(),
           "event_type": random_choice(event_types),
           "timestamp": now - random_timedelta(0-90 days),
           "session_id": session.session_id,
           "customer_id": session.customer_id,
           ...
       }

       # Add event-specific data
       if event_type == "add_to_cart":
           event.update({
               "product_id": random_product(),
               "quantity": random(1-5),
               "price_vnd": product.price,
               "line_total_vnd": price * quantity
           })
       elif event_type == "remove_from_cart":
           # 30% remove all
           quantity = 0 if random() > 0.7 else random(1-5)
           ...
   ```

5. **Sort and save:**
   ```python
   events.sort(key=lambda x: x["timestamp"])
   save_compressed(events, "cart_events.json.gz")
   ```

6. **Update status:**
   ```python
   generation_status["completed"] = True
   generation_status["is_generating"] = False
   ```

**Parameters:**
- `count`: 100 - 1,000,000 events
- `method=new`: Append to existing data

**Event Types Generated:**
```
- add_to_cart          → Cart modification events
- remove_from_cart
- update_quantity
- view_item            → Browse events
- purchase             → Transaction events
- scroll, exit_page    → Engagement events
- search               → Search events
- add_to_wish_list     → Interest events
- begin_checkout       → Funnel events
- add_shipping_info
- add_payment_info
- payment_failed       → Error events
- order_cancelled
```

---

##### **4.2. Generation Status**
```
GET /cart/generate/status
```

**Logic:**
1. Check `generation_status["is_generating"]`
2. If generating:
   ```python
   return {
       "progress_percentage": 45.2,
       "events_generated": 4520,
       "target_events": 10000,
       "elapsed_time_minutes": 1.5,
       "estimated_time_remaining": "1.8 minutes",
       "events_per_second": 50.22
   }
   ```
3. If completed:
   ```python
   return {
       "generation_status": "completed",
       "total_events": 10000
   }
   ```
4. If idle:
   ```python
   return {
       "generation_status": "idle",
       "instructions": "Call POST /cart/generate/events"
   }
   ```

**Use case:** Monitor generation progress

---

### **Data Flow Diagram - API**

```
┌─────────────────────────────────────────────────────────────────┐
│                    API DATA FLOW                                 │
└─────────────────────────────────────────────────────────────────┘

1. GENERATION FLOW
═══════════════════

User Request
   │
   ├─→ POST /cart/generate/events?count=10000
   │
   ├─→ Check existing data
   │   ├─ Exists? → Warning (unless method=new)
   │   └─ Not exists? → Proceed
   │
   ├─→ Start background task
   │   └─→ generation_status["is_generating"] = True
   │
   ├─→ Generate in batches (50K per batch)
   │   │
   │   ├─→ Create sessions (10% of events)
   │   │   └─→ 30% guest users (customer_id = null)
   │   │
   │   ├─→ For each event:
   │   │   ├─ Pick random session
   │   │   ├─ Pick random product
   │   │   ├─ Generate timestamp (0-90 days ago)
   │   │   ├─ Pick event_type
   │   │   └─ Add event-specific data
   │   │
   │   ├─→ Update progress
   │   │   ├─ Calculate: progress_percentage
   │   │   ├─ Calculate: ETA
   │   │   └─ Log progress
   │   │
   │   └─→ Sort by timestamp
   │
   ├─→ Save to file
   │   └─→ shared_data/private_data/cart_tracking/cart_events.json.gz
   │
   └─→ Update status: completed = True

Monitor Progress
   │
   └─→ GET /cart/generate/status
       └─→ Real-time progress updates


2. QUERY FLOW
═════════════

User Query
   │
   ├─→ GET /cart/events?filters
   │
   ├─→ Load cart_events.json.gz
   │   └─→ Decompress gzip
   │       └─→ Parse JSON
   │
   ├─→ Apply filters
   │   ├─ event_type
   │   ├─ source
   │   ├─ device
   │   ├─ date range
   │   └─ customer/product/session
   │
   ├─→ Sort by timestamp
   │
   ├─→ Pagination (offset, limit)
   │
   └─→ Return {data, count, total}


3. ANALYTICS FLOW
═════════════════

Statistics Request
   │
   ├─→ GET /cart/statistics
   │
   ├─→ Load all events
   │
   ├─→ Aggregate
   │   ├─ Count by event_type
   │   ├─ Count by source
   │   ├─ Count by device
   │   ├─ Count unique customers
   │   ├─ Count unique sessions
   │   ├─ Calculate add/remove ratio
   │   └─ Top 10 products
   │
   └─→ Return statistics JSON

Abandoned Carts Request
   │
   ├─→ GET /cart/abandoned?hours_threshold=24
   │
   ├─→ Load all events
   │
   ├─→ Group by session_id
   │
   ├─→ For each session:
   │   ├─ Calculate current cart state
   │   │   ├─ Process add_to_cart events
   │   │   ├─ Process remove_from_cart events
   │   │   └─ Process update_quantity events
   │   │
   │   ├─ Check last_activity
   │   │   └─ If > hours_threshold → Abandoned
   │   │
   │   └─ Calculate cart_value_vnd
   │
   ├─→ Sort by cart_value descending
   │
   └─→ Return top abandoned carts
```

---

## 🔄 TRANSFORMATION PIPELINE - LOGIC

### **Thứ Tự Chạy Transformation**

```
INPUT: cart_events.json.gz (10K-2M+ events)
   │
   ├─→ STEP 1: Load Data
   ├─→ STEP 2: Clean Data
   ├─→ STEP 3: Deduplicate
   ├─→ STEP 4: Create User Journeys
   ├─→ STEP 5: Save Parquet (Partitioned)
   ├─→ STEP 6: Generate Session Metrics
   └─→ STEP 7: Aggregate Metrics

OUTPUT:
   ├─ cart_events_cleaned/ (Parquet, partitioned by date)
   ├─ session_metrics.parquet
   └─ aggregation_report.txt
```

---

### **STEP 1: Load Data**

**File:** `transform_cart_events.py`, `transform_cart_events_extreme.py`

**Standard Version:**
```python
def load_data():
    with gzip.open('cart_events.json.gz', 'rt') as f:
        data = json.load(f)  # Load toàn bộ vào memory
    df = pd.DataFrame(data)
    return df

# Memory: ~3-5x data size
# 10K events: ~30MB
# 2M events: ~6-12GB ❌ Out of Memory
```

**Extreme Version (Streaming):**
```python
def load_events_streaming():
    import ijson  # Streaming JSON parser

    with gzip.open('cart_events.json.gz', 'rb') as f:
        # Parse từng event một, không load hết vào memory
        parser = ijson.items(f, 'item')
        for event in parser:
            yield event  # Generator, chỉ giữ 1 event tại 1 thời điểm

# Memory: Constant ~500MB
# 10K events: ~300MB
# 2M events: ~500MB ✅ Success
```

**Logic:**
1. Mở file gzip
2. Parse JSON array
3. Extreme version: Stream từng item
4. Standard version: Load toàn bộ

---

### **STEP 2: Clean Data**

```python
def clean_data(df):
    # 1. Convert timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour

    # 2. Remove missing critical fields
    critical = ['event_id', 'session_id', 'customer_id', 'event_type']
    df = df.dropna(subset=critical)

    # 3. Handle missing UTM fields
    utm_fields = ['utm_source', 'utm_medium', 'utm_campaign']
    for field in utm_fields:
        df[field] = df[field].fillna('unknown')

    # 4. Handle missing referrer
    df['referrer'] = df['referrer'].fillna('direct')

    # 5. Ensure numeric types
    numeric_fields = ['product_price_vnd', 'quantity', 'line_total_vnd']
    for field in numeric_fields:
        df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0)

    # 6. Remove invalid records
    df = df[df['product_price_vnd'] >= 0]
    df = df[df['quantity'] >= 0]

    return df
```

**Output:** Clean DataFrame

---

### **STEP 3: Deduplicate**

**Standard Version:**
```python
def deduplicate(df):
    initial_count = len(df)

    # Remove duplicates based on event_id
    df = df.drop_duplicates(subset=['event_id'], keep='first')

    duplicates_removed = initial_count - len(df)
    return df
```

**Extreme Version (Incremental):**
```python
seen_event_ids = set()  # Track across batches

def deduplicate_batch(df, seen_ids):
    # Filter already seen
    mask = ~df['event_id'].isin(seen_ids)
    df = df[mask]

    # Remove duplicates within batch
    df = df.drop_duplicates(subset=['event_id'], keep='first')

    # Update seen set
    seen_ids.update(df['event_id'].tolist())

    return df, seen_ids
```

**Logic:**
1. Track `event_id` đã thấy
2. Remove events với `event_id` trùng
3. Keep first occurrence

---

### **STEP 4: Create User Journeys**

```python
def create_user_journeys(df):
    # 1. Sort by session and timestamp
    df = df.sort_values(['session_id', 'timestamp'])

    # 2. Add sequence number within session
    df['event_sequence_num'] = df.groupby('session_id').cumcount() + 1

    # 3. Calculate session-level metrics
    session_metrics = df.groupby('session_id').agg({
        'timestamp': ['min', 'max', 'count'],
        'event_type': lambda x: ','.join(x),
        'customer_id': 'first',
        'source': 'first',
        'device': 'first'
    })

    # 4. Flatten columns
    session_metrics.columns = [
        'session_id', 'session_start', 'session_end',
        'total_events', 'event_journey', 'customer_id',
        'source', 'device'
    ]

    # 5. Calculate session duration
    session_metrics['session_duration_seconds'] = (
        session_metrics['session_end'] - session_metrics['session_start']
    ).dt.total_seconds()

    # 6. Merge back to main dataframe
    df = df.merge(session_metrics, on='session_id', how='left')

    return df, session_metrics
```

**Output:**
```python
# Each event có thêm:
df['event_sequence_num']        # 1, 2, 3, ...
df['session_start']             # First event timestamp
df['session_end']               # Last event timestamp
df['session_duration_seconds']  # Duration
df['total_events']              # Number of events in session
df['event_journey']             # "add_to_cart,update_quantity,remove_from_cart"
```

**Example Journey:**
```json
{
  "session_id": "sess_abc123",
  "customer_id": 445412,
  "event_journey": "add_to_cart → update_quantity → add_to_cart → remove_from_cart",
  "total_events": 4,
  "session_duration_seconds": 245,
  "events": [
    {"event_sequence_num": 1, "event_type": "add_to_cart", "product_id": 90},
    {"event_sequence_num": 2, "event_type": "update_quantity", "product_id": 90},
    {"event_sequence_num": 3, "event_type": "add_to_cart", "product_id": 73},
    {"event_sequence_num": 4, "event_type": "remove_from_cart", "product_id": 90}
  ]
}
```

---

### **STEP 5: Save Parquet (Partitioned)**

```python
def save_to_parquet(df, partition_by='date'):
    output_path = "output/cart_events_cleaned"

    df.to_parquet(
        output_path,
        engine='pyarrow',
        partition_cols=['date'],      # Partition by date
        compression='snappy',          # Fast compression
        index=False
    )
```

**Output Structure:**
```
output/cart_events_cleaned/
├── date=2025-08-25/
│   └── xxx.parquet
├── date=2025-08-26/
│   └── xxx.parquet
├── date=2025-08-27/
│   └── xxx.parquet
...
└── date=2025-11-24/
    └── xxx.parquet

Total: 92 date partitions (3 months of data)
```

**Benefits:**
- Query by date: `SELECT * WHERE date='2025-08-25'` → Chỉ đọc 1 partition
- Columnar storage: Đọc nhanh, compression tốt
- Snappy: Fast compression (~2x smaller)

---

### **STEP 6: Generate Session Metrics**

```python
def generate_session_metrics():
    session_list = []

    for session_id, data in session_data.items():
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
            'session_duration_seconds': (max - min).total_seconds(),
            'has_purchase': False  # Placeholder
        })

    df = pd.DataFrame(session_list)
    df.to_parquet('session_metrics.parquet', index=False)

    return df
```

**Output:** `session_metrics.parquet`
- 1 row per session
- Summary của tất cả events trong session
- Use for session-level analysis

---

### **STEP 7: Aggregate Metrics**

**File:** `aggregate_metrics.py`

```python
def aggregate_all_metrics():
    # Load transformed data
    events_df = pd.read_parquet('cart_events_cleaned/')
    session_df = pd.read_parquet('session_metrics.parquet')

    # 1. Session Duration Statistics
    session_stats = {
        'average_duration_seconds': session_df['session_duration_seconds'].mean(),
        'median_duration_seconds': session_df['session_duration_seconds'].median(),
        'min_duration': session_df['session_duration_seconds'].min(),
        'max_duration': session_df['session_duration_seconds'].max()
    }

    # 2. Purchase Intent Analysis
    last_events = events_df.groupby('session_id').last()
    purchase_intent = (
        (last_events['event_type'] == 'add_to_cart') &
        (events_df.groupby('session_id').size() >= 2)
    )
    purchase_stats = {
        'sessions_with_purchase_intent': purchase_intent.sum(),
        'purchase_intent_rate': purchase_intent.mean() * 100
    }

    # 3. Event Statistics
    event_stats = {
        'total_events': len(events_df),
        'unique_sessions': events_df['session_id'].nunique(),
        'unique_customers': events_df['customer_id'].nunique(),
        'unique_products': events_df['product_id'].nunique(),
        'event_type_distribution': events_df['event_type'].value_counts().to_dict(),
        'source_distribution': events_df['source'].value_counts().to_dict(),
        'device_distribution': events_df['device'].value_counts().to_dict()
    }

    # 4. Journey Patterns
    journey_patterns = events_df.groupby('session_id')['event_type'].apply(
        lambda x: ' -> '.join(x)
    ).value_counts().head(20)

    # 5. Time-based Metrics
    time_metrics = {
        'events_by_hour': events_df.groupby('hour').size().to_dict(),
        'events_by_date': events_df.groupby('date').size().to_dict()
    }

    # Save all metrics
    save_metrics({
        'session_duration': session_stats,
        'purchase_intent': purchase_stats,
        'events': event_stats,
        'journeys': journey_patterns,
        'time': time_metrics
    })
```

**Output:**
```
aggregation_report.txt:
═══════════════════════════════════════
SESSION DURATION STATISTICS
───────────────────────────────────────
Total Sessions: 1,000
Average Duration: 105,220.91 minutes
Median Duration: 109,144.69 minutes

PURCHASE INTENT STATISTICS
───────────────────────────────────────
Sessions with Purchase Intent: 330
Purchase Intent Rate: 33.00%

EVENT STATISTICS
───────────────────────────────────────
Total Events: 10,000
Unique Sessions: 1,000
Unique Customers: 1,000
Event Type Distribution:
  - add_to_cart: 3,387
  - update_quantity: 3,350
  - remove_from_cart: 3,263

TOP JOURNEY PATTERNS
───────────────────────────────────────
1. update_quantity → remove_from_cart → update_quantity: 2 sessions
2. update_quantity → add_to_cart → add_to_cart: 2 sessions
...
```

---

## 🐳 DOCKER INTEGRATION FLOW

### **Architecture Options**

#### **Option 1: Single Container**

```
┌─────────────────────────────────────────────┐
│         Docker Container                     │
│  ┌────────────────────────────────────┐     │
│  │  Python Environment                │     │
│  │  ├─ pandas, pyarrow, ijson        │     │
│  │  └─ transformation scripts         │     │
│  └────────────────────────────────────┘     │
│                                              │
│  Volume Mounts:                              │
│  /data/input  → ./data/input                │
│  /data/output → ./data/output               │
└─────────────────────────────────────────────┘

COMMAND:
docker-compose up

PROCESSING FLOW:
1. Container starts
2. Loads ../shared_data/private_data/cart_tracking/cart_events.json.gz
3. Runs transform_cart_events_extreme.py
4. Saves output to /data/output
5. Container stops
```

---

#### **Option 2: Worker Pool** (Recommended)

```
┌──────────────────────────────────────────────────────────────────┐
│                      WORKER POOL ARCHITECTURE                     │
└──────────────────────────────────────────────────────────────────┘

                    ┌─────────────┐
                    │   Redis     │ ← Task Queue
                    │  Container  │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼────────┐ ┌───────▼────────┐ ┌──────▼─────────┐
│   Scheduler    │ │   Worker 1     │ │   Worker N     │
│   Container    │ │   Container    │ │   Container    │
│                │ │                │ │                │
│ scheduler.py   │ │  worker.py     │ │  worker.py     │
│  ├─ Split work │ │  ├─ Process    │ │  ├─ Process    │
│  ├─ Enqueue    │ │  │   chunk 1   │ │  │   chunk N   │
│  └─ Monitor    │ │  └─ Save       │ │  └─ Save       │
└────────────────┘ └────────────────┘ └────────────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Storage   │
                    │  /data/     │
                    └─────────────┘
```

**FLOW:**

**Step 1: Start Services**
```bash
docker-compose -f docker-compose.workers.yml up --scale worker=4
```

**Step 2: Services Start**
```
1. Redis container starts
   └─→ Task queue ready

2. Scheduler container starts
   ├─→ Connects to Redis
   ├─→ Analyzes input file
   ├─→ Splits work into chunks
   └─→ Enqueues jobs to Redis

3. Worker containers start (x4)
   ├─→ Connect to Redis
   └─→ Listen for jobs
```

**Step 3: Job Distribution**
```python
# Scheduler (scheduler.py)
def split_work(file, num_workers=4):
    total_events = count_events(file)  # 2M events
    chunk_size = total_events // num_workers  # 500K each

    chunks = [
        {"start": 0, "end": 500000, "chunk_num": 0},
        {"start": 500000, "end": 1000000, "chunk_num": 1},
        {"start": 1000000, "end": 1500000, "chunk_num": 2},
        {"start": 1500000, "end": 2000000, "chunk_num": 3}
    ]

    # Enqueue to Redis
    for chunk in chunks:
        queue.enqueue(process_chunk, chunk)
```

**Step 4: Worker Processing**
```python
# Worker (worker.py)
def process_chunk(chunk_info):
    # Load chunk
    events = load_events(
        file=chunk_info['input_file'],
        start=chunk_info['start'],
        end=chunk_info['end']
    )

    # Transform
    transformer = CartEventsTransformerExtreme(...)
    transformer.process_batch(events)

    # Save
    save_to_parquet(events, chunk_num=chunk_info['chunk_num'])

    return {
        'status': 'success',
        'events_processed': len(events),
        'chunk_num': chunk_info['chunk_num']
    }
```

**Step 5: Monitoring**
```python
# Scheduler monitors Redis queue
while True:
    jobs = get_all_jobs()

    completed = count(jobs, status='finished')
    failed = count(jobs, status='failed')
    running = count(jobs, status='started')

    if completed + failed == total_jobs:
        break  # All done

    sleep(5)
```

**Step 6: Completion**
```
All workers finish
   └─→ Scheduler detects completion
       └─→ Merges results (if needed)
           └─→ Generates final report
               └─→ Containers stop
```

---

### **Docker Commands Workflow**

**Single Container:**
```bash
# 1. Build image
docker build -f docker/Dockerfile -t cart-transformer .

# 2. Run transformation
docker run -v $(pwd)/data:/data cart-transformer

# 3. Check output
ls -la data/output/
```

**Worker Pool:**
```bash
# 1. Start all services with 4 workers
docker-compose -f docker/docker-compose.workers.yml up --scale worker=4

# 2. Monitor logs
docker-compose -f docker/docker-compose.workers.yml logs -f scheduler
docker-compose -f docker/docker-compose.workers.yml logs -f worker

# 3. Check Redis queue
docker-compose -f docker/docker-compose.workers.yml exec redis redis-cli LLEN transformation

# 4. Stop all services
docker-compose -f docker/docker-compose.workers.yml down

# 5. Cleanup
docker-compose -f docker/docker-compose.workers.yml down -v
```

---

## 🔗 LUỒNG HOÀN CHỈNH END-TO-END

### **Scenario: Process 2 Million Events**

```
PHASE 1: GENERATE DATA (API)
════════════════════════════
Time: ~5 minutes

1. Start API Server
   $ python main.py
   └─→ FastAPI server listening on :8000

2. Generate Events
   $ curl -X POST "http://localhost:8000/cart/generate/events?count=2000000"
   └─→ Background task starts
       ├─→ Creates 200K sessions (~30% guest)
       ├─→ Generates 2M events in batches (50K/batch)
       ├─→ Progress: 0% → 100% (real-time tracking)
       └─→ Saves: shared_data/private_data/cart_tracking/cart_events.json.gz

3. Check Progress
   $ curl "http://localhost:8000/cart/generate/status"
   {
       "progress_percentage": 75.5,
       "events_generated": 1510000,
       "estimated_time_remaining": "1.2 minutes"
   }

4. Verify Data
   $ curl "http://localhost:8000/cart/statistics"
   {
       "total_events": 2000000,
       "unique_sessions": 200000,
       "unique_customers": 140000  # 30% guest
   }

OUTPUT: cart_events.json.gz (~500MB compressed, ~2GB uncompressed)

════════════════════════════════════════════════════════════════

PHASE 2A: TRANSFORM (Python - Single Process)
══════════════════════════════════════════════
Time: ~3-5 minutes
Memory: ~500MB

1. Run Extreme Version
   $ cd transformation
   $ python transform_cart_events_extreme.py \
       --input ../shared_data/private_data/cart_tracking/cart_events.json.gz \
       --output output_extreme \
       --chunk-size 100000

2. Processing Steps (Automated)
   ├─→ Load: Streaming JSON parse (ijson)
   ├─→ Process batches: 100K events at a time
   ├─→ Clean: Remove invalid, fill missing
   ├─→ Deduplicate: Track event_ids across batches
   ├─→ Create Journeys: Session tracking
   ├─→ Save: Partitioned parquet by date
   └─→ Generate: session_metrics.parquet

3. Monitor Progress
   [2025-12-16 10:00:00] Processed 100,000 events...
   [2025-12-16 10:00:30] Processed 200,000 events...
   ...
   [2025-12-16 10:04:30] Processed 2,000,000 events
   [2025-12-16 10:04:45] Peak memory usage: ~527 MB

OUTPUT:
├─ output_extreme/cart_events_cleaned/ (300 partitions, ~800MB)
├─ output_extreme/session_metrics.parquet (~50MB)
└─ output_extreme/transformation_summary.csv

════════════════════════════════════════════════════════════════

PHASE 2B: TRANSFORM (Docker - Worker Pool)
═══════════════════════════════════════════
Time: ~1-2 minutes (4 workers)
Memory: ~2.4GB total (600MB x 4)

1. Start Worker Pool
   $ cd transformation/docker
   $ docker-compose -f docker-compose.workers.yml up --scale worker=4

2. Automated Flow
   ├─→ Redis starts
   ├─→ Scheduler analyzes file (2M events)
   ├─→ Splits into 4 chunks (500K each)
   ├─→ Enqueues 4 jobs to Redis
   ├─→ 4 Workers pick up jobs
   │   ├─ Worker 1: Events 0-500K
   │   ├─ Worker 2: Events 500K-1M
   │   ├─ Worker 3: Events 1M-1.5M
   │   └─ Worker 4: Events 1.5M-2M
   ├─→ Each worker processes independently
   └─→ All workers save to shared output

3. Monitor Logs
   $ docker-compose -f docker-compose.workers.yml logs -f scheduler

   [scheduler] Splitting 2,000,000 events into 4 chunks
   [scheduler] Enqueued 4 jobs
   [scheduler] Progress: 4/4 completed
   [scheduler] All jobs completed in 1.8 minutes

OUTPUT: Same as Phase 2A but 3x faster

════════════════════════════════════════════════════════════════

PHASE 3: AGGREGATE METRICS
═══════════════════════════
Time: ~30 seconds

1. Run Aggregation
   $ python transformation/aggregate_metrics.py

2. Processing
   ├─→ Load: cart_events_cleaned/ (all partitions)
   ├─→ Load: session_metrics.parquet
   ├─→ Calculate:
   │   ├─ Session duration stats
   │   ├─ Purchase intent (33%)
   │   ├─ Event distributions
   │   ├─ Top journey patterns
   │   └─ Time-based metrics
   └─→ Generate reports

OUTPUT:
├─ aggregation_report.txt (human-readable)
└─ aggregation_metrics.json (machine-readable)

════════════════════════════════════════════════════════════════

PHASE 4: QUERY & ANALYZE (API)
═══════════════════════════════

Now you can query transformed data:

1. Session Analysis
   $ curl "http://localhost:8000/cart/events/session/sess_abc123"
   → See complete user journey

2. Customer Behavior
   $ curl "http://localhost:8000/cart/events/customer/445412"
   → All customer interactions

3. Product Performance
   $ curl "http://localhost:8000/cart/events/product/90"
   → Product add/remove history

4. Abandoned Carts
   $ curl "http://localhost:8000/cart/abandoned?hours_threshold=24"
   → Recovery targets

5. Statistics
   $ curl "http://localhost:8000/cart/statistics"
   → Overall metrics
```

---

## 📊 PERFORMANCE SUMMARY

### **2 Million Events**

| Phase | Method | Time | Memory | Output |
|-------|--------|------|--------|--------|
| **Generate** | API | 5 min | 1GB | 500MB .gz |
| **Transform** | Python Single | 3-5 min | 500MB | 800MB parquet |
| **Transform** | Docker 4 Workers | 1-2 min | 2.4GB | 800MB parquet |
| **Aggregate** | Python | 30s | 1GB | Reports |
| **TOTAL (Single)** | - | **8-10 min** | **500MB** | - |
| **TOTAL (Docker)** | - | **6-8 min** | **2.4GB** | - |

### **Scaling to 10M Events**

| Phase | Method | Time | Memory |
|-------|--------|------|--------|
| **Generate** | API | 25 min | 2GB |
| **Transform** | Python Single | 15-20 min | 600MB |
| **Transform** | Docker 8 Workers | 4-5 min | 4.8GB |
| **Aggregate** | Python | 2 min | 2GB |
| **TOTAL (Single)** | - | **42-47 min** | **600MB** |
| **TOTAL (Docker 8)** | - | **31-32 min** | **4.8GB** |

---

## 🎯 DECISION TREE

```
Bạn có bao nhiêu events?
    │
    ├─ < 100K events
    │   └─→ Python Script (Standard)
    │       $ python transform_cart_events.py
    │
    ├─ 100K - 500K events
    │   └─→ Python Script (Extreme)
    │       $ python transform_cart_events_extreme.py
    │
    ├─ 500K - 2M events
    │   ├─→ Python (nếu không cần nhanh)
    │   │   $ python transform_cart_events_extreme.py
    │   │
    │   └─→ Docker Workers (nếu cần nhanh)
    │       $ docker-compose -f docker-compose.workers.yml up --scale worker=4
    │
    └─ > 2M events
        └─→ Docker Workers Pool (8+ workers)
            $ docker-compose -f docker-compose.workers.yml up --scale worker=8
```

---

## 📚 FILES REFERENCE

```
PROJECT STRUCTURE
═════════════════

routers/
└── cart_tracking_router.py     # API endpoints (generate, query, stats)

transformation/
├── transform_cart_events.py           # Standard (< 100K)
├── transform_cart_events_bigdata.py   # BigData (100K-500K)
├── transform_cart_events_extreme.py   # Extreme (2M+) ⭐
├── aggregate_metrics.py               # Metrics aggregation
├── run_pipeline.py                    # Main runner
└── docker/
    ├── Dockerfile                     # Single container
    ├── Dockerfile.worker              # Worker image
    ├── docker-compose.yml             # Single setup
    ├── docker-compose.workers.yml     # Worker pool ⭐
    ├── worker.py                      # RQ worker
    └── scheduler.py                   # Job scheduler

shared_data/
└── private_data/
    └── cart_tracking/
        └── cart_events.json.gz        # Generated events
```

---

## 🔄 QUICK REFERENCE

### **Generate Events**
```bash
curl -X POST "http://localhost:8000/cart/generate/events?count=2000000"
```

### **Check Status**
```bash
curl "http://localhost:8000/cart/generate/status"
```

### **Transform (Python)**
```bash
python transformation/transform_cart_events_extreme.py
```

### **Transform (Docker Single)**
```bash
cd transformation/docker
docker-compose up
```

### **Transform (Docker Workers)**
```bash
cd transformation/docker
docker-compose -f docker-compose.workers.yml up --scale worker=4
```

### **Aggregate**
```bash
python transformation/aggregate_metrics.py
```

### **Query Events**
```bash
curl "http://localhost:8000/cart/events?limit=10&event_type=add_to_cart"
```

### **Statistics**
```bash
curl "http://localhost:8000/cart/statistics"
```

---

**END OF README2.md** 🎉

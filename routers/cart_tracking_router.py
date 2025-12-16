"""
Cart Tracking API Router
Track add to cart and remove from cart history for users
"""

from fastapi import APIRouter, Query, BackgroundTasks, Path
from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime, timedelta
import random
import uuid
from pathlib import Path as FilePath
import gzip
import json

from shared.data_generator import (
    get_random_customer, get_random_product,
    get_private_data_path, fake_vi, fake_en,
    SHARED_PRODUCTS, ensure_products_loaded
)

router = APIRouter()

# Configuration
TRACKING_DIR = get_private_data_path("cart_tracking", "")
TRACKING_DIR.mkdir(exist_ok=True)

generation_status = {
    "cart_events": {"generated": 0, "target": 10000, "completed": False},
    "is_generating": False,
    "start_time": None,
    "estimated_completion_time": None,
    "progress_percentage": 0
}

# Standard Response Model
class StandardResponse(BaseModel):
    status: str = Field(..., example="success")
    msg: str = Field(..., example="Operation completed successfully")
    data: Any = Field(None)
    count: Optional[int] = Field(None)
    total: Optional[int] = Field(None)

# Helper functions
def save_compressed(data, filepath):
    with gzip.open(filepath, 'wt', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def load_compressed(filepath):
    if not filepath.exists():
        return None
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        return json.load(f)

def generate_session_id():
    """Generate user session ID"""
    return f"sess_{uuid.uuid4().hex[:16]}"

def generate_cart_events_batch(count):
    """Generate cart tracking events with extended event types"""
    events = []

    # Extended event types list
    event_types = [
        "add_to_cart", "remove_from_cart", "update_quantity", "view_item",
        "purchase", "scroll", "exit_page", "search", "add_to_wish_list",
        "begin_checkout", "add_shipping_info", "add_payment_info",
        "payment_failed", "order_cancelled"
    ]
    sources = ["website", "mobile_app", "mobile_web"]
    devices = ["desktop", "mobile", "tablet"]
    browsers = ["Chrome", "Safari", "Firefox", "Edge", "Mobile App"]

    # Generate user sessions (group events by session)
    # ~30% of sessions are guest users (no customer_id)
    num_sessions = count // 10  # Average 10 events per session
    sessions = {}

    for _ in range(num_sessions):
        session_id = generate_session_id()
        is_guest = random.random() < 0.3  # 30% guest users

        if is_guest:
            customer_id = None
        else:
            customer = get_random_customer()
            customer_id = customer["id"]

        sessions[session_id] = {
            "customer_id": customer_id,
            "is_guest": is_guest,
            "source": random.choice(sources),
            "device": random.choice(devices),
            "browser": random.choice(browsers),
            "ip_address": f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
            "user_agent": f"Mozilla/5.0 ({random.choice(['Windows NT 10.0', 'Macintosh', 'Linux', 'iPhone', 'Android'])})"
        }

    session_ids = list(sessions.keys())

    for i in range(count):
        session_id = random.choice(session_ids)
        session = sessions[session_id]
        product = get_random_product()

        if not product:
            continue

        event_time = datetime.now() - timedelta(
            days=random.randint(0, 90),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )

        event_type = random.choice(event_types)

        # Base event structure
        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "event_type": event_type,
            "timestamp": event_time.isoformat(),
            "timestamp_unix": int(event_time.timestamp() * 1000),

            # Session info
            "session_id": session_id,
            "customer_id": session["customer_id"],  # Can be None for guest users
            "is_guest": session["is_guest"],

            # Context info
            "source": session["source"],
            "device": session["device"],
            "browser": session["browser"],
            "ip_address": session["ip_address"],
            "user_agent": session["user_agent"],

            # Page context
            "page_url": f"https://techstore.vn/product/{product['id']}",
            "referrer": random.choice([
                "https://google.com",
                "https://facebook.com",
                "https://techstore.vn/category/laptop",
                "https://techstore.vn/",
                None
            ]),

            # UTM tracking
            "utm_source": random.choice(["google", "facebook", "direct", "email", None]),
            "utm_medium": random.choice(["cpc", "organic", "social", "email", None]),
            "utm_campaign": random.choice(["summer_sale", "black_friday", "new_arrival", None]),
        }

        # Add event-specific data
        if event_type in ["add_to_cart", "remove_from_cart", "update_quantity"]:
            quantity = random.randint(1, 5)

            # For remove events, sometimes remove all
            if event_type == "remove_from_cart" and random.random() > 0.7:
                quantity = 0

            # For update events, set new quantity
            old_quantity = None
            if event_type == "update_quantity":
                old_quantity = random.randint(1, 5)
                quantity = random.randint(0, 10)

            event.update({
                "product_id": product["id"],
                "product_name": product["name"],
                "product_sku": product["sku"],
                "product_category": product["category"],
                "product_brand": product["brand"],
                "product_price_vnd": product["price_vnd"],
                "product_price_usd": product["price_usd"],
                "quantity": quantity,
                "old_quantity": old_quantity,
                "line_total_vnd": product["price_vnd"] * quantity,
                "line_total_usd": round(product["price_usd"] * quantity, 2),
            })

        elif event_type == "view_item":
            event.update({
                "product_id": product["id"],
                "product_name": product["name"],
                "product_sku": product["sku"],
                "product_category": product["category"],
                "product_brand": product["brand"],
                "product_price_vnd": product["price_vnd"],
                "product_price_usd": product["price_usd"],
                "view_duration_seconds": random.randint(5, 300),
            })

        elif event_type == "purchase":
            num_items = random.randint(1, 5)
            total_vnd = random.randint(500000, 50000000)
            event.update({
                "order_id": f"ORD_{uuid.uuid4().hex[:10].upper()}",
                "total_amount_vnd": total_vnd,
                "total_amount_usd": round(total_vnd / 24000, 2),
                "item_count": num_items,
                "payment_method": random.choice(["credit_card", "paypal", "momo", "zalopay", "cod"]),
                "shipping_method": random.choice(["standard", "express", "same_day"]),
            })

        elif event_type == "scroll":
            event.update({
                "scroll_depth_percent": random.randint(10, 100),
                "page_height": random.randint(1000, 5000),
                "scroll_position": random.randint(100, 5000),
            })

        elif event_type == "exit_page":
            event.update({
                "time_on_page_seconds": random.randint(5, 600),
                "exit_type": random.choice(["close_tab", "back_button", "navigate_away"]),
            })

        elif event_type == "search":
            search_terms = [
                "laptop", "phone", "headphones", "keyboard", "mouse",
                "monitor", "tablet", "camera", "smartwatch", "speaker"
            ]
            event.update({
                "search_query": random.choice(search_terms),
                "results_count": random.randint(0, 100),
                "search_type": random.choice(["keyword", "category", "brand"]),
            })

        elif event_type == "add_to_wish_list":
            event.update({
                "product_id": product["id"],
                "product_name": product["name"],
                "product_sku": product["sku"],
                "product_category": product["category"],
                "product_brand": product["brand"],
                "product_price_vnd": product["price_vnd"],
                "product_price_usd": product["price_usd"],
            })

        elif event_type == "begin_checkout":
            num_items = random.randint(1, 5)
            cart_value = random.randint(500000, 20000000)
            event.update({
                "cart_value_vnd": cart_value,
                "cart_value_usd": round(cart_value / 24000, 2),
                "item_count": num_items,
            })

        elif event_type == "add_shipping_info":
            event.update({
                "shipping_method": random.choice(["standard", "express", "same_day"]),
                "shipping_cost_vnd": random.randint(0, 100000),
                "estimated_delivery_days": random.randint(1, 7),
            })

        elif event_type == "add_payment_info":
            event.update({
                "payment_method": random.choice(["credit_card", "paypal", "momo", "zalopay", "cod"]),
                "save_payment_info": random.choice([True, False]),
            })

        elif event_type == "payment_failed":
            event.update({
                "order_id": f"ORD_{uuid.uuid4().hex[:10].upper()}",
                "payment_method": random.choice(["credit_card", "paypal", "momo", "zalopay"]),
                "failure_reason": random.choice([
                    "insufficient_funds", "card_declined", "expired_card",
                    "network_error", "timeout", "invalid_cvv"
                ]),
                "attempted_amount_vnd": random.randint(500000, 50000000),
            })

        elif event_type == "order_cancelled":
            event.update({
                "order_id": f"ORD_{uuid.uuid4().hex[:10].upper()}",
                "cancelled_by": random.choice(["customer", "system", "admin"]),
                "cancellation_reason": random.choice([
                    "changed_mind", "found_better_price", "delivery_too_slow",
                    "payment_issue", "out_of_stock", "duplicate_order"
                ]),
                "order_value_vnd": random.randint(500000, 50000000),
            })

        events.append(event)

    # Sort by timestamp
    events.sort(key=lambda x: x["timestamp"])
    return events

def generate_all_events(count=10000, mode="replace"):
    """Generate all cart events with batch processing and progress tracking"""
    import time

    print(f"Starting cart event generation: {count:,} events (mode: {mode})")

    # Initialize generation status
    generation_status["cart_events"]["target"] = count
    generation_status["cart_events"]["generated"] = 0
    generation_status["cart_events"]["completed"] = False
    generation_status["start_time"] = datetime.now()
    generation_status["progress_percentage"] = 0

    batch_file = TRACKING_DIR / "cart_events.json.gz"

    # Load existing events if appending
    all_events = []
    if mode == "append":
        existing = load_compressed(batch_file)
        if existing:
            all_events = existing
            print(f"Appending to {len(existing):,} existing events")

    # Generate in batches of 50,000 to avoid memory issues and allow progress tracking
    batch_size = 50000
    num_batches = (count + batch_size - 1) // batch_size

    for batch_num in range(num_batches):
        batch_start = time.time()
        current_batch_size = min(batch_size, count - len(all_events) + (len(existing) if mode == "append" and existing else 0))

        if current_batch_size <= 0:
            break

        print(f"Generating batch {batch_num + 1}/{num_batches} ({current_batch_size:,} events)...")

        # Generate batch
        new_events = generate_cart_events_batch(current_batch_size)
        all_events.extend(new_events)

        # Update progress
        if mode == "append" and existing:
            generation_status["cart_events"]["generated"] = len(all_events) - len(existing)
        else:
            generation_status["cart_events"]["generated"] = len(all_events)

        generation_status["progress_percentage"] = round(
            (generation_status["cart_events"]["generated"] / count) * 100, 2
        )

        # Calculate ETA
        elapsed_time = (datetime.now() - generation_status["start_time"]).total_seconds()
        if generation_status["cart_events"]["generated"] > 0:
            avg_time_per_event = elapsed_time / generation_status["cart_events"]["generated"]
            remaining_events = count - generation_status["cart_events"]["generated"]
            eta_seconds = avg_time_per_event * remaining_events
            generation_status["estimated_completion_time"] = (
                datetime.now() + timedelta(seconds=eta_seconds)
            ).isoformat()
            eta_minutes = eta_seconds / 60
            print(f"Progress: {generation_status['progress_percentage']}% - ETA: {eta_minutes:.1f} minutes")

        batch_end = time.time()
        print(f"Batch {batch_num + 1} completed in {batch_end - batch_start:.2f}s")

    # Sort all events by timestamp
    print("Sorting events by timestamp...")
    all_events.sort(key=lambda x: x["timestamp"])

    # Save to file
    print("Saving events to file...")
    save_compressed(all_events, batch_file)

    # Update final status
    generation_status["cart_events"]["generated"] = len(all_events) if mode == "replace" else len(all_events) - (len(existing) if existing else 0)
    generation_status["cart_events"]["target"] = count
    generation_status["cart_events"]["completed"] = True
    generation_status["progress_percentage"] = 100
    generation_status["estimated_completion_time"] = None

    total_time = (datetime.now() - generation_status["start_time"]).total_seconds()
    print(f"Cart event generation completed! Total: {len(all_events):,} events in {total_time:.2f}s")

    return all_events

# API Endpoints
@router.get("/", response_model=StandardResponse)
async def cart_tracking_info():
    """Cart Tracking API information"""
    return {
        "status": "success",
        "msg": "Cart Tracking API",
        "data": {
            "service": "Cart Tracking API",
            "description": "Track add/remove from cart events",
            "events": f"{generation_status['cart_events']['generated']:,}",
            "endpoints": [
                "/cart/events - List all cart events",
                "/cart/events/customer/{customer_id} - Events by customer",
                "/cart/events/product/{product_id} - Events by product",
                "/cart/events/session/{session_id} - Events by session",
                "/cart/statistics - Cart statistics",
                "/cart/abandoned - Abandoned carts",
                "/cart/generate/*"
            ]
        }
    }

@router.get("/events", response_model=StandardResponse)
async def get_cart_events(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = Query(None, description="Filter: add_to_cart, remove_from_cart, update_quantity"),
    source: Optional[str] = Query(None, description="Filter: website, mobile_app, mobile_web"),
    device: Optional[str] = Query(None, description="Filter: desktop, mobile, tablet"),
    start_date: Optional[str] = Query(None, description="Start date (ISO)"),
    end_date: Optional[str] = Query(None, description="End date (ISO)")
):
    """Get cart tracking events with filters"""
    batch_file = TRACKING_DIR / "cart_events.json.gz"
    events = load_compressed(batch_file)

    if not events:
        return {
            "status": "error",
            "msg": "No events data. Generate via /cart/generate/events",
            "data": [],
            "count": 0
        }

    filtered = events

    if event_type:
        filtered = [e for e in filtered if e.get("event_type") == event_type]
    if source:
        filtered = [e for e in filtered if e.get("source") == source]
    if device:
        filtered = [e for e in filtered if e.get("device") == device]
    if start_date:
        filtered = [e for e in filtered if e.get("timestamp", "") >= start_date]
    if end_date:
        filtered = [e for e in filtered if e.get("timestamp", "") <= end_date]

    # Sort by timestamp descending
    filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    result = filtered[offset:offset + limit]

    return {
        "status": "success",
        "msg": "Events retrieved successfully",
        "data": result,
        "count": len(result),
        "total": len(filtered)
    }

@router.get("/events/customer/{customer_id}", response_model=StandardResponse)
async def get_customer_cart_events(
    customer_id: int = Path(..., ge=1),
    limit: int = Query(100, ge=1, le=500)
):
    """Get cart events for a specific customer"""
    batch_file = TRACKING_DIR / "cart_events.json.gz"
    events = load_compressed(batch_file)

    if not events:
        return {
            "status": "error",
            "msg": "No events data",
            "data": [],
            "count": 0
        }

    filtered = [e for e in events if e.get("customer_id") == customer_id]
    filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    result = filtered[:limit]

    return {
        "status": "success",
        "msg": f"Events for customer {customer_id}",
        "data": result,
        "count": len(result),
        "total": len(filtered)
    }

@router.get("/events/product/{product_id}", response_model=StandardResponse)
async def get_product_cart_events(
    product_id: int = Path(..., ge=1),
    limit: int = Query(100, ge=1, le=500)
):
    """Get cart events for a specific product"""
    batch_file = TRACKING_DIR / "cart_events.json.gz"
    events = load_compressed(batch_file)

    if not events:
        return {
            "status": "error",
            "msg": "No events data",
            "data": [],
            "count": 0
        }

    filtered = [e for e in events if e.get("product_id") == product_id]
    filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    result = filtered[:limit]

    return {
        "status": "success",
        "msg": f"Events for product {product_id}",
        "data": result,
        "count": len(result),
        "total": len(filtered)
    }

@router.get("/events/session/{session_id}", response_model=StandardResponse)
async def get_session_cart_events(
    session_id: str = Path(...),
    limit: int = Query(100, ge=1, le=500)
):
    """Get cart events for a specific session"""
    batch_file = TRACKING_DIR / "cart_events.json.gz"
    events = load_compressed(batch_file)

    if not events:
        return {
            "status": "error",
            "msg": "No events data",
            "data": [],
            "count": 0
        }

    filtered = [e for e in events if e.get("session_id") == session_id]
    filtered.sort(key=lambda x: x.get("timestamp", ""))
    result = filtered[:limit]

    return {
        "status": "success",
        "msg": f"Events for session {session_id}",
        "data": result,
        "count": len(result)
    }

@router.get("/statistics", response_model=StandardResponse)
async def get_cart_statistics():
    """Get cart tracking statistics"""

    # Check if generation is in progress
    if generation_status["is_generating"]:
        elapsed = (datetime.now() - generation_status["start_time"]).total_seconds() / 60 if generation_status["start_time"] else 0
        eta_str = "calculating..."

        if generation_status["estimated_completion_time"]:
            try:
                eta_time = datetime.fromisoformat(generation_status["estimated_completion_time"])
                remaining_minutes = (eta_time - datetime.now()).total_seconds() / 60
                eta_str = f"{remaining_minutes:.1f} minutes"
            except:
                pass

        return {
            "status": "warning",
            "msg": f"Event generation in progress. Statistics will be available after completion. Please try again in approximately {eta_str}.",
            "data": {
                "generation_status": "in_progress",
                "progress": f"{generation_status['progress_percentage']}%",
                "events_generated": generation_status["cart_events"]["generated"],
                "target_events": generation_status["cart_events"]["target"],
                "elapsed_time_minutes": round(elapsed, 2),
                "estimated_completion": eta_str,
                "message": "Final statistics cannot be calculated until generation is complete. Please check back later."
            }
        }

    batch_file = TRACKING_DIR / "cart_events.json.gz"
    events = load_compressed(batch_file)

    if not events:
        return {
            "status": "error",
            "msg": "No events data. Please generate events first using /cart/generate/events",
            "data": None
        }

    # Count by event type
    event_type_counts = {}
    for e in events:
        et = e.get("event_type", "unknown")
        event_type_counts[et] = event_type_counts.get(et, 0) + 1

    # Count by source
    source_counts = {}
    for e in events:
        src = e.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    # Count by device
    device_counts = {}
    for e in events:
        dev = e.get("device", "unknown")
        device_counts[dev] = device_counts.get(dev, 0) + 1

    # Top products added to cart
    add_events = [e for e in events if e.get("event_type") == "add_to_cart"]
    product_adds = {}
    for e in add_events:
        pid = e.get("product_id")
        if pid:
            if pid not in product_adds:
                product_adds[pid] = {"count": 0, "name": e.get("product_name", ""), "total_value_vnd": 0}
            product_adds[pid]["count"] += 1
            product_adds[pid]["total_value_vnd"] += e.get("line_total_vnd", 0)

    top_products = sorted(product_adds.items(), key=lambda x: x[1]["count"], reverse=True)[:10]

    # Unique customers and sessions
    unique_customers = len(set(e.get("customer_id") for e in events if e.get("customer_id")))
    unique_sessions = len(set(e.get("session_id") for e in events if e.get("session_id")))

    # Calculate add/remove ratio
    add_count = event_type_counts.get("add_to_cart", 0)
    remove_count = event_type_counts.get("remove_from_cart", 0)

    return {
        "status": "success",
        "msg": "Statistics retrieved",
        "data": {
            "total_events": len(events),
            "by_event_type": event_type_counts,
            "by_source": source_counts,
            "by_device": device_counts,
            "unique_customers": unique_customers,
            "unique_sessions": unique_sessions,
            "add_remove_ratio": round(add_count / remove_count, 2) if remove_count > 0 else add_count,
            "top_products_added": [
                {"product_id": pid, "name": data["name"], "add_count": data["count"], "total_value_vnd": data["total_value_vnd"]}
                for pid, data in top_products
            ]
        }
    }

@router.get("/abandoned", response_model=StandardResponse)
async def get_abandoned_carts(
    limit: int = Query(50, ge=1, le=200),
    hours_threshold: int = Query(24, ge=1, le=168, description="Hours since last activity to consider abandoned")
):
    """Get abandoned cart sessions (added items but didn't purchase)"""
    batch_file = TRACKING_DIR / "cart_events.json.gz"
    events = load_compressed(batch_file)

    if not events:
        return {
            "status": "error",
            "msg": "No events data",
            "data": [],
            "count": 0
        }

    # Group events by session
    sessions = {}
    for e in events:
        sid = e.get("session_id")
        if sid:
            if sid not in sessions:
                sessions[sid] = {
                    "session_id": sid,
                    "customer_id": e.get("customer_id"),
                    "events": [],
                    "cart_items": {},
                    "last_activity": ""
                }
            sessions[sid]["events"].append(e)
            if e.get("timestamp", "") > sessions[sid]["last_activity"]:
                sessions[sid]["last_activity"] = e["timestamp"]

    # Calculate current cart state for each session
    threshold = datetime.now() - timedelta(hours=hours_threshold)
    abandoned = []

    for sid, session in sessions.items():
        # Calculate cart items
        cart = {}
        for e in session["events"]:
            pid = e.get("product_id")
            if not pid:
                continue

            if e.get("event_type") == "add_to_cart":
                if pid not in cart:
                    cart[pid] = {"product": e.get("product_name"), "quantity": 0, "price": e.get("product_price_vnd", 0)}
                cart[pid]["quantity"] += e.get("quantity", 1)
            elif e.get("event_type") == "remove_from_cart":
                if pid in cart:
                    cart[pid]["quantity"] -= e.get("quantity", 1)
                    if cart[pid]["quantity"] <= 0:
                        del cart[pid]
            elif e.get("event_type") == "update_quantity":
                if pid in cart:
                    cart[pid]["quantity"] = e.get("quantity", 0)
                    if cart[pid]["quantity"] <= 0:
                        del cart[pid]

        # Check if abandoned (has items and last activity older than threshold)
        if cart and session["last_activity"]:
            try:
                last_time = datetime.fromisoformat(session["last_activity"].replace("Z", "+00:00").replace("+00:00", ""))
                if last_time < threshold:
                    total_value = sum(item["price"] * item["quantity"] for item in cart.values())
                    abandoned.append({
                        "session_id": sid,
                        "customer_id": session["customer_id"],
                        "last_activity": session["last_activity"],
                        "hours_since_activity": int((datetime.now() - last_time).total_seconds() / 3600),
                        "cart_items": list(cart.values()),
                        "cart_value_vnd": total_value,
                        "item_count": len(cart)
                    })
            except:
                pass

    # Sort by cart value descending
    abandoned.sort(key=lambda x: x.get("cart_value_vnd", 0), reverse=True)
    result = abandoned[:limit]

    return {
        "status": "success",
        "msg": f"Abandoned carts (inactive > {hours_threshold}h)",
        "data": result,
        "count": len(result),
        "total": len(abandoned)
    }

# Generation Endpoints
@router.post("/generate/events", response_model=StandardResponse)
@router.get("/generate/events", response_model=StandardResponse)
async def generate_events_endpoint(
    background_tasks: BackgroundTasks,
    count: int = Query(10000, ge=100, le=1000000, description="Number of events to generate (100 - 1,000,000)"),
    method: Optional[str] = Query(None, description="Use 'new' to append to existing events, otherwise will replace")
):
    """
    Generate cart tracking events with extended event types

    Supports up to 1,000,000 events with the following event types:
    - add_to_cart, remove_from_cart, update_quantity
    - view_item, purchase, scroll, exit_page, search
    - add_to_wish_list, begin_checkout, add_shipping_info
    - add_payment_info, payment_failed, order_cancelled

    Guest users (user_id=null) are included (~30% of sessions)
    """
    try:
        # Ensure products are loaded
        await ensure_products_loaded()

        batch_file = TRACKING_DIR / "cart_events.json.gz"
        existing = load_compressed(batch_file)

        if existing and method != "new":
            return {
                "status": "warning",
                "msg": f"Events already exist ({len(existing):,} events). Use 'method=new' to append or call without method parameter to replace.",
                "data": {
                    "existing_events": len(existing),
                    "action_required": "Add '?method=new' to append, or call again to replace existing data"
                },
                "count": len(existing)
            }

        if generation_status["is_generating"]:
            elapsed = (datetime.now() - generation_status["start_time"]).total_seconds() / 60 if generation_status["start_time"] else 0
            eta_str = "calculating..."

            if generation_status["estimated_completion_time"]:
                try:
                    eta_time = datetime.fromisoformat(generation_status["estimated_completion_time"])
                    remaining_minutes = (eta_time - datetime.now()).total_seconds() / 60
                    eta_str = f"{remaining_minutes:.1f} minutes"
                except:
                    pass

            return {
                "status": "warning",
                "msg": f"Event generation already in progress. Please wait for completion (ETA: {eta_str})",
                "data": {
                    "progress": f"{generation_status['progress_percentage']}%",
                    "events_generated": generation_status["cart_events"]["generated"],
                    "target_events": generation_status["cart_events"]["target"],
                    "elapsed_time_minutes": round(elapsed, 2),
                    "estimated_completion": eta_str
                }
            }

        def generate():
            generation_status["is_generating"] = True
            try:
                mode = "append" if method == "new" else "replace"
                generate_all_events(count, mode)
            finally:
                generation_status["is_generating"] = False

        background_tasks.add_task(generate)

        # Estimate time (rough estimate: ~10,000 events per second)
        estimated_minutes = count / 10000 / 60
        estimated_time_msg = f"approximately {estimated_minutes:.1f} minutes" if estimated_minutes > 1 else f"approximately {estimated_minutes * 60:.0f} seconds"

        return {
            "status": "success",
            "msg": f"Event generation started. Generating {count:,} events ({estimated_time_msg}). Check /cart/generate/status for progress.",
            "data": {
                "target_events": count,
                "mode": "append" if method == "new" else "replace",
                "estimated_duration": estimated_time_msg,
                "status_endpoint": "/cart/generate/status",
                "statistics_endpoint": "/cart/statistics (available after completion)"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Failed to start generation: {str(e)}",
            "data": None
        }

@router.get("/generate/status", response_model=StandardResponse)
async def get_generation_status():
    """Get detailed generation status with progress and ETA"""

    if not generation_status["is_generating"]:
        if generation_status["cart_events"]["completed"]:
            return {
                "status": "success",
                "msg": "No active generation. Last generation completed successfully.",
                "data": {
                    "generation_status": "completed",
                    "total_events": generation_status["cart_events"]["generated"],
                    "last_target": generation_status["cart_events"]["target"],
                    "is_generating": False
                }
            }
        else:
            return {
                "status": "success",
                "msg": "No active generation. Ready to start new generation.",
                "data": {
                    "generation_status": "idle",
                    "is_generating": False,
                    "instructions": "Call POST /cart/generate/events?count=X to start generation"
                }
            }

    # Generation in progress
    elapsed = (datetime.now() - generation_status["start_time"]).total_seconds() if generation_status["start_time"] else 0
    elapsed_minutes = elapsed / 60

    eta_str = "calculating..."
    eta_minutes = None

    if generation_status["estimated_completion_time"]:
        try:
            eta_time = datetime.fromisoformat(generation_status["estimated_completion_time"])
            remaining_seconds = (eta_time - datetime.now()).total_seconds()
            eta_minutes = remaining_seconds / 60
            eta_str = f"{eta_minutes:.1f} minutes" if eta_minutes > 1 else f"{remaining_seconds:.0f} seconds"
        except:
            pass

    events_per_second = generation_status["cart_events"]["generated"] / elapsed if elapsed > 0 else 0

    return {
        "status": "success",
        "msg": f"Event generation in progress: {generation_status['progress_percentage']}% complete",
        "data": {
            "generation_status": "in_progress",
            "is_generating": True,
            "progress_percentage": generation_status["progress_percentage"],
            "events_generated": generation_status["cart_events"]["generated"],
            "target_events": generation_status["cart_events"]["target"],
            "remaining_events": generation_status["cart_events"]["target"] - generation_status["cart_events"]["generated"],
            "elapsed_time_seconds": round(elapsed, 2),
            "elapsed_time_minutes": round(elapsed_minutes, 2),
            "estimated_completion_time": generation_status["estimated_completion_time"],
            "estimated_time_remaining": eta_str,
            "events_per_second": round(events_per_second, 2),
            "message": f"Generation in progress. Estimated completion in {eta_str}. Statistics will be available after completion."
        }
    }

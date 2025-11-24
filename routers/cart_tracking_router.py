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
    "is_generating": False
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
    """Generate cart tracking events"""
    events = []

    event_types = ["add_to_cart", "remove_from_cart", "update_quantity"]
    sources = ["website", "mobile_app", "mobile_web"]
    devices = ["desktop", "mobile", "tablet"]
    browsers = ["Chrome", "Safari", "Firefox", "Edge", "Mobile App"]

    # Generate user sessions (group events by session)
    num_sessions = count // 10  # Average 10 events per session
    sessions = {}

    for _ in range(num_sessions):
        session_id = generate_session_id()
        customer = get_random_customer()
        sessions[session_id] = {
            "customer_id": customer["id"],
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
        quantity = random.randint(1, 5)

        # For remove events, sometimes remove all
        if event_type == "remove_from_cart" and random.random() > 0.7:
            quantity = 0

        # For update events, set new quantity
        if event_type == "update_quantity":
            old_quantity = random.randint(1, 5)
            quantity = random.randint(0, 10)
        else:
            old_quantity = None

        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "event_type": event_type,
            "timestamp": event_time.isoformat(),
            "timestamp_unix": int(event_time.timestamp() * 1000),

            # Session info
            "session_id": session_id,
            "customer_id": session["customer_id"],

            # Product info
            "product_id": product["id"],
            "product_name": product["name"],
            "product_sku": product["sku"],
            "product_category": product["category"],
            "product_brand": product["brand"],
            "product_price_vnd": product["price_vnd"],
            "product_price_usd": product["price_usd"],

            # Quantity info
            "quantity": quantity,
            "old_quantity": old_quantity,
            "line_total_vnd": product["price_vnd"] * quantity,
            "line_total_usd": round(product["price_usd"] * quantity, 2),

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
        events.append(event)

    # Sort by timestamp
    events.sort(key=lambda x: x["timestamp"])
    return events

def generate_all_events(count=10000, mode="replace"):
    """Generate all cart events"""
    print(f"Starting cart event generation: {count:,} events (mode: {mode})")

    new_events = generate_cart_events_batch(count)
    batch_file = TRACKING_DIR / "cart_events.json.gz"

    if mode == "append":
        existing = load_compressed(batch_file)
        if existing:
            all_events = existing + new_events
            all_events.sort(key=lambda x: x["timestamp"])
            print(f"Appending {count} new events to {len(existing)} existing")
        else:
            all_events = new_events
    else:
        all_events = new_events

    save_compressed(all_events, batch_file)

    generation_status["cart_events"]["generated"] = len(all_events)
    generation_status["cart_events"]["target"] = len(all_events)
    generation_status["cart_events"]["completed"] = True
    print(f"Cart event generation completed! Total: {len(all_events)}")

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
    batch_file = TRACKING_DIR / "cart_events.json.gz"
    events = load_compressed(batch_file)

    if not events:
        return {
            "status": "error",
            "msg": "No events data",
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
    count: int = Query(10000, ge=100, le=100000),
    method: Optional[str] = Query(None, description="'new' to append")
):
    """Generate cart tracking events"""
    try:
        # Ensure products are loaded
        await ensure_products_loaded()

        batch_file = TRACKING_DIR / "cart_events.json.gz"
        existing = load_compressed(batch_file)

        if existing and method != "new":
            return {
                "status": "warning",
                "msg": "Events exist. Use 'method=new' to append.",
                "data": {"count": len(existing)},
                "count": len(existing)
            }

        if generation_status["is_generating"]:
            return {
                "status": "warning",
                "msg": "Generation in progress",
                "data": {"current": generation_status["cart_events"]["generated"]}
            }

        def generate():
            generation_status["is_generating"] = True
            try:
                mode = "append" if method == "new" else "replace"
                generate_all_events(count, mode)
            finally:
                generation_status["is_generating"] = False

        background_tasks.add_task(generate)

        return {
            "status": "success",
            "msg": f"Cart event generation started ({count} events)",
            "data": {"target": count, "mode": "append" if method == "new" else "replace"}
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Failed: {str(e)}",
            "data": None
        }

@router.get("/generate/status", response_model=StandardResponse)
async def get_generation_status():
    """Get generation status"""
    return {
        "status": "success",
        "msg": "Generation status",
        "data": generation_status
    }

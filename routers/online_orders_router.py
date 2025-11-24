"""
Online Orders Tracking API Router
Track online orders from multiple channels: Shopify, web store, mobile app
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
    get_random_customer, get_random_product, generate_transaction_id,
    get_private_data_path, fake_vi, fake_en,
    SHARED_PRODUCTS, ensure_products_loaded
)

router = APIRouter()

# Configuration
ORDERS_DIR = get_private_data_path("online_orders", "")
ORDERS_DIR.mkdir(exist_ok=True)

generation_status = {
    "orders": {"generated": 0, "target": 50000, "completed": False},
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

def generate_online_orders_batch(count):
    """Generate online orders from multiple channels"""
    orders = []

    # Online channels
    channels = [
        {"id": "shopify", "name": "Shopify", "weight": 0.4},
        {"id": "website", "name": "TechStore Website", "weight": 0.3},
        {"id": "mobile_app", "name": "TechStore Mobile App", "weight": 0.2},
        {"id": "lazada", "name": "Lazada", "weight": 0.05},
        {"id": "shopee", "name": "Shopee", "weight": 0.05},
    ]

    # Order statuses
    order_statuses = [
        ("pending", "Cho xac nhan"),
        ("confirmed", "Da xac nhan"),
        ("processing", "Dang xu ly"),
        ("shipping", "Dang giao hang"),
        ("delivered", "Da giao hang"),
        ("completed", "Hoan thanh"),
        ("cancelled", "Da huy"),
        ("refunded", "Da hoan tien"),
    ]

    # Payment methods
    payment_methods = [
        {"id": "cod", "name": "Thanh toan khi nhan hang (COD)"},
        {"id": "bank_transfer", "name": "Chuyen khoan ngan hang"},
        {"id": "momo", "name": "Vi MoMo"},
        {"id": "zalopay", "name": "ZaloPay"},
        {"id": "vnpay", "name": "VNPay"},
        {"id": "credit_card", "name": "The tin dung/ghi no"},
        {"id": "paypal", "name": "PayPal"},
    ]

    # Shipping methods
    shipping_methods = [
        {"id": "standard", "name": "Giao hang tieu chuan", "fee_range": (20000, 40000)},
        {"id": "express", "name": "Giao hang nhanh", "fee_range": (40000, 80000)},
        {"id": "same_day", "name": "Giao trong ngay", "fee_range": (80000, 150000)},
        {"id": "free", "name": "Mien phi van chuyen", "fee_range": (0, 0)},
    ]

    # Shipping carriers
    carriers = ["GHN", "GHTK", "Viettel Post", "J&T Express", "Ninja Van", "Kerry Express"]

    for i in range(count):
        customer = get_random_customer()
        transaction_id = generate_transaction_id()

        # Select channel based on weight
        rand = random.random()
        cumulative = 0
        selected_channel = channels[0]
        for ch in channels:
            cumulative += ch["weight"]
            if rand < cumulative:
                selected_channel = ch
                break

        # Generate order items
        num_items = random.randint(1, 5)
        line_items = []
        subtotal = 0

        for j in range(num_items):
            product = get_random_product()
            if not product:
                continue

            quantity = random.randint(1, 3)
            price = product["price_vnd"]
            discount_percent = random.choice([0, 0, 0, 5, 10, 15, 20])
            discount_amount = int(price * quantity * discount_percent / 100)
            line_total = price * quantity - discount_amount
            subtotal += line_total

            line_items.append({
                "line_id": f"LI{i}_{j}",
                "product_id": product["id"],
                "product_name": product["name"],
                "product_sku": product["sku"],
                "product_category": product["category"],
                "quantity": quantity,
                "unit_price": price,
                "discount_percent": discount_percent,
                "discount_amount": discount_amount,
                "line_total": line_total,
                "weight_kg": product.get("weight_kg", 0.5) * quantity
            })

        # Calculate totals
        shipping = random.choice(shipping_methods)
        shipping_fee = random.randint(*shipping["fee_range"]) if shipping["fee_range"][1] > 0 else 0

        # Free shipping for orders > 2M VND
        if subtotal >= 2000000 and random.random() > 0.3:
            shipping_fee = 0

        tax = int(subtotal * 0.1)  # 10% VAT
        total = subtotal + tax + shipping_fee

        # Order timestamp
        order_time = datetime.now() - timedelta(
            days=random.randint(0, 180),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        # Select status based on age
        days_old = (datetime.now() - order_time).days
        if days_old > 7:
            status_weights = [0, 0, 0, 0.05, 0.1, 0.7, 0.1, 0.05]  # Mostly completed
        elif days_old > 3:
            status_weights = [0, 0.05, 0.1, 0.3, 0.2, 0.25, 0.05, 0.05]
        else:
            status_weights = [0.2, 0.25, 0.2, 0.15, 0.1, 0.05, 0.03, 0.02]

        status_idx = random.choices(range(len(order_statuses)), weights=status_weights)[0]
        status_code, status_name = order_statuses[status_idx]

        # Generate tracking info for shipped orders
        tracking_info = None
        if status_code in ["shipping", "delivered", "completed"]:
            carrier = random.choice(carriers)
            tracking_info = {
                "carrier": carrier,
                "tracking_number": f"{carrier[:3].upper()}{random.randint(100000000, 999999999)}",
                "shipped_at": (order_time + timedelta(days=random.randint(0, 2))).isoformat(),
                "estimated_delivery": (order_time + timedelta(days=random.randint(2, 7))).isoformat(),
                "tracking_url": f"https://tracking.{carrier.lower().replace(' ', '')}.vn/track"
            }

        # Customer address
        is_vietnamese = random.random() < 0.95
        cities = ["Ha Noi", "TP Ho Chi Minh", "Da Nang", "Hai Phong", "Can Tho", "Nha Trang", "Hue", "Bien Hoa"]

        order = {
            "order_id": f"ORD{order_time.strftime('%Y%m%d')}{str(i).zfill(6)}",
            "transaction_id": transaction_id,
            "customer_id": customer["id"],

            # Channel info
            "channel": selected_channel["id"],
            "channel_name": selected_channel["name"],
            "channel_order_id": f"{selected_channel['id'].upper()}{random.randint(10000000, 99999999)}",

            # Timestamps
            "created_at": order_time.isoformat(),
            "updated_at": datetime.now().isoformat(),
            "confirmed_at": (order_time + timedelta(hours=random.randint(0, 4))).isoformat() if status_code not in ["pending", "cancelled"] else None,

            # Status
            "status": status_code,
            "status_name": status_name,
            "status_history": [
                {"status": "pending", "timestamp": order_time.isoformat(), "note": "Don hang moi tao"}
            ],

            # Customer info
            "customer_name": fake_vi.name() if is_vietnamese else fake_en.name(),
            "customer_email": f"customer{customer['id']}@gmail.com",
            "customer_phone": fake_vi.phone_number(),

            # Shipping address
            "shipping_address": {
                "full_name": fake_vi.name() if is_vietnamese else fake_en.name(),
                "phone": fake_vi.phone_number(),
                "address": fake_vi.street_address(),
                "ward": f"Phuong {random.randint(1, 20)}",
                "district": f"Quan {random.randint(1, 12)}",
                "city": random.choice(cities),
                "country": "Vietnam",
                "postal_code": fake_vi.postcode() if hasattr(fake_vi, 'postcode') else "100000"
            },

            # Items
            "line_items": line_items,
            "item_count": len(line_items),
            "total_quantity": sum(item["quantity"] for item in line_items),

            # Pricing
            "subtotal": subtotal,
            "tax_amount": tax,
            "shipping_fee": shipping_fee,
            "discount_total": sum(item["discount_amount"] for item in line_items),
            "total": total,
            "currency": "VND",

            # Payment
            "payment_method": random.choice(payment_methods)["id"],
            "payment_method_name": random.choice(payment_methods)["name"],
            "payment_status": "paid" if status_code in ["completed", "delivered", "shipping"] else ("pending" if status_code != "cancelled" else "cancelled"),

            # Shipping
            "shipping_method": shipping["id"],
            "shipping_method_name": shipping["name"],
            "tracking": tracking_info,
            "total_weight_kg": round(sum(item.get("weight_kg", 0) for item in line_items), 2),

            # Notes
            "customer_note": random.choice([
                None, None, None,
                "Giao gio hanh chinh",
                "Goi truoc khi giao",
                "De truoc cong",
                "Ship nhanh giup em"
            ]),
            "internal_note": None,

            # Source tracking
            "source": "online",
            "utm_source": random.choice(["google", "facebook", "direct", "tiktok", None]),
            "utm_medium": random.choice(["cpc", "organic", "social", None]),
            "utm_campaign": random.choice(["summer_sale", "black_friday", None]),
        }
        orders.append(order)

    return orders

def generate_all_orders(count=50000, mode="replace"):
    """Generate all online orders"""
    print(f"Starting online orders generation: {count:,} orders (mode: {mode})")

    new_orders = generate_online_orders_batch(count)
    batch_file = ORDERS_DIR / "online_orders.json.gz"

    if mode == "append":
        existing = load_compressed(batch_file)
        if existing:
            all_orders = existing + new_orders
            print(f"Appending {count} new orders to {len(existing)} existing")
        else:
            all_orders = new_orders
    else:
        all_orders = new_orders

    # Sort by created_at
    all_orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    save_compressed(all_orders, batch_file)

    generation_status["orders"]["generated"] = len(all_orders)
    generation_status["orders"]["target"] = len(all_orders)
    generation_status["orders"]["completed"] = True
    print(f"Online orders generation completed! Total: {len(all_orders)}")

    return all_orders

# API Endpoints
@router.get("/", response_model=StandardResponse)
async def online_orders_info():
    """Online Orders API information"""
    return {
        "status": "success",
        "msg": "Online Orders Tracking API",
        "data": {
            "service": "Online Orders Tracking API",
            "description": "Track online orders from Shopify, website, mobile app, marketplaces",
            "orders": f"{generation_status['orders']['generated']:,}",
            "channels": ["shopify", "website", "mobile_app", "lazada", "shopee"],
            "endpoints": [
                "/online/orders - List all online orders",
                "/online/orders/{order_id} - Get order details",
                "/online/orders/customer/{customer_id} - Orders by customer",
                "/online/orders/channel/{channel} - Orders by channel",
                "/online/statistics - Order statistics",
                "/online/generate/*"
            ]
        }
    }

@router.get("/orders", response_model=StandardResponse)
async def get_online_orders(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    channel: Optional[str] = Query(None, description="Filter by channel: shopify, website, mobile_app, lazada, shopee"),
    status: Optional[str] = Query(None, description="Filter by status: pending, confirmed, shipping, delivered, completed, cancelled"),
    payment_status: Optional[str] = Query(None, description="Filter: paid, pending, cancelled"),
    start_date: Optional[str] = Query(None, description="Start date (ISO)"),
    end_date: Optional[str] = Query(None, description="End date (ISO)"),
    min_total: Optional[int] = Query(None, description="Minimum total in VND"),
    max_total: Optional[int] = Query(None, description="Maximum total in VND")
):
    """Get online orders with filters"""
    batch_file = ORDERS_DIR / "online_orders.json.gz"
    orders = load_compressed(batch_file)

    if not orders:
        return {
            "status": "error",
            "msg": "No orders data. Generate via /online/generate/orders",
            "data": [],
            "count": 0
        }

    filtered = orders

    if channel:
        filtered = [o for o in filtered if o.get("channel") == channel]
    if status:
        filtered = [o for o in filtered if o.get("status") == status]
    if payment_status:
        filtered = [o for o in filtered if o.get("payment_status") == payment_status]
    if start_date:
        filtered = [o for o in filtered if o.get("created_at", "") >= start_date]
    if end_date:
        filtered = [o for o in filtered if o.get("created_at", "") <= end_date]
    if min_total:
        filtered = [o for o in filtered if o.get("total", 0) >= min_total]
    if max_total:
        filtered = [o for o in filtered if o.get("total", 0) <= max_total]

    result = filtered[offset:offset + limit]

    return {
        "status": "success",
        "msg": "Orders retrieved successfully",
        "data": result,
        "count": len(result),
        "total": len(filtered)
    }

@router.get("/orders/{order_id}", response_model=StandardResponse)
async def get_order_detail(
    order_id: str = Path(...)
):
    """Get order details by order ID"""
    batch_file = ORDERS_DIR / "online_orders.json.gz"
    orders = load_compressed(batch_file)

    if not orders:
        return {
            "status": "error",
            "msg": "No orders data",
            "data": None
        }

    for order in orders:
        if order.get("order_id") == order_id:
            return {
                "status": "success",
                "msg": "Order found",
                "data": order
            }

    return {
        "status": "error",
        "msg": f"Order {order_id} not found",
        "data": None
    }

@router.get("/orders/customer/{customer_id}", response_model=StandardResponse)
async def get_customer_orders(
    customer_id: int = Path(..., ge=1),
    limit: int = Query(50, ge=1, le=200)
):
    """Get orders for a specific customer"""
    batch_file = ORDERS_DIR / "online_orders.json.gz"
    orders = load_compressed(batch_file)

    if not orders:
        return {
            "status": "error",
            "msg": "No orders data",
            "data": [],
            "count": 0
        }

    filtered = [o for o in orders if o.get("customer_id") == customer_id]
    filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    result = filtered[:limit]

    # Calculate customer stats
    total_spent = sum(o.get("total", 0) for o in filtered if o.get("status") == "completed")
    total_orders = len(filtered)
    completed_orders = len([o for o in filtered if o.get("status") == "completed"])

    return {
        "status": "success",
        "msg": f"Orders for customer {customer_id}",
        "data": {
            "orders": result,
            "customer_stats": {
                "total_orders": total_orders,
                "completed_orders": completed_orders,
                "total_spent_vnd": total_spent,
                "average_order_value": int(total_spent / completed_orders) if completed_orders > 0 else 0
            }
        },
        "count": len(result),
        "total": len(filtered)
    }

@router.get("/orders/channel/{channel}", response_model=StandardResponse)
async def get_channel_orders(
    channel: str = Path(..., description="Channel: shopify, website, mobile_app, lazada, shopee"),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None)
):
    """Get orders for a specific channel"""
    batch_file = ORDERS_DIR / "online_orders.json.gz"
    orders = load_compressed(batch_file)

    if not orders:
        return {
            "status": "error",
            "msg": "No orders data",
            "data": [],
            "count": 0
        }

    filtered = [o for o in orders if o.get("channel") == channel]
    if status:
        filtered = [o for o in filtered if o.get("status") == status]

    filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    result = filtered[:limit]

    return {
        "status": "success",
        "msg": f"Orders for channel {channel}",
        "data": result,
        "count": len(result),
        "total": len(filtered)
    }

@router.get("/statistics", response_model=StandardResponse)
async def get_statistics():
    """Get online order statistics"""
    batch_file = ORDERS_DIR / "online_orders.json.gz"
    orders = load_compressed(batch_file)

    if not orders:
        return {
            "status": "error",
            "msg": "No orders data",
            "data": None
        }

    # By channel
    channel_stats = {}
    for o in orders:
        ch = o.get("channel", "unknown")
        if ch not in channel_stats:
            channel_stats[ch] = {"count": 0, "total_revenue": 0, "completed": 0}
        channel_stats[ch]["count"] += 1
        if o.get("status") == "completed":
            channel_stats[ch]["completed"] += 1
            channel_stats[ch]["total_revenue"] += o.get("total", 0)

    # By status
    status_stats = {}
    for o in orders:
        st = o.get("status", "unknown")
        status_stats[st] = status_stats.get(st, 0) + 1

    # By payment method
    payment_stats = {}
    for o in orders:
        pm = o.get("payment_method", "unknown")
        payment_stats[pm] = payment_stats.get(pm, 0) + 1

    # Calculate totals
    completed = [o for o in orders if o.get("status") == "completed"]
    total_revenue = sum(o.get("total", 0) for o in completed)
    avg_order_value = int(total_revenue / len(completed)) if completed else 0

    # Top products
    product_sales = {}
    for o in orders:
        if o.get("status") != "completed":
            continue
        for item in o.get("line_items", []):
            pid = item.get("product_id")
            if pid:
                if pid not in product_sales:
                    product_sales[pid] = {"name": item.get("product_name"), "quantity": 0, "revenue": 0}
                product_sales[pid]["quantity"] += item.get("quantity", 0)
                product_sales[pid]["revenue"] += item.get("line_total", 0)

    top_products = sorted(product_sales.items(), key=lambda x: x[1]["revenue"], reverse=True)[:10]

    return {
        "status": "success",
        "msg": "Statistics retrieved",
        "data": {
            "total_orders": len(orders),
            "completed_orders": len(completed),
            "total_revenue_vnd": total_revenue,
            "average_order_value_vnd": avg_order_value,
            "conversion_rate": round(len(completed) / len(orders) * 100, 2) if orders else 0,
            "by_channel": channel_stats,
            "by_status": status_stats,
            "by_payment_method": payment_stats,
            "top_products": [
                {"product_id": pid, "name": data["name"], "quantity_sold": data["quantity"], "revenue_vnd": data["revenue"]}
                for pid, data in top_products
            ]
        }
    }

# Generation Endpoints
@router.post("/generate/orders", response_model=StandardResponse)
@router.get("/generate/orders", response_model=StandardResponse)
async def generate_orders_endpoint(
    background_tasks: BackgroundTasks,
    count: int = Query(50000, ge=100, le=500000),
    method: Optional[str] = Query(None, description="'new' to append")
):
    """Generate online orders"""
    try:
        await ensure_products_loaded()

        batch_file = ORDERS_DIR / "online_orders.json.gz"
        existing = load_compressed(batch_file)

        if existing and method != "new":
            return {
                "status": "warning",
                "msg": "Orders exist. Use 'method=new' to append.",
                "data": {"count": len(existing)},
                "count": len(existing)
            }

        if generation_status["is_generating"]:
            return {
                "status": "warning",
                "msg": "Generation in progress",
                "data": {"current": generation_status["orders"]["generated"]}
            }

        def generate():
            generation_status["is_generating"] = True
            try:
                mode = "append" if method == "new" else "replace"
                generate_all_orders(count, mode)
            finally:
                generation_status["is_generating"] = False

        background_tasks.add_task(generate)

        return {
            "status": "success",
            "msg": f"Online orders generation started ({count} orders)",
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

"""
Sapo POS API Router
Vietnam retail POS system for offline stores
"""

from fastapi import APIRouter, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime, timedelta
import random
from pathlib import Path
import gzip
import json
from shared.data_generator import (
    SHARED_PRODUCTS, SHARED_STAFF, SHARED_LOCATIONS,
    get_random_product, get_random_customer, get_random_staff, get_random_location,
    generate_transaction_id, generate_shared_locations, DATA_DIR, fake_vi, GENERATION_STATUS,
    ensure_products_loaded, ensure_staff_loaded, ensure_locations_loaded, PRIVATE_DIRS
)

router = APIRouter()

# Configuration
ORDERS_DIR = PRIVATE_DIRS["sapo"] #DATA_DIR / "sapo_orders"
ORDERS_DIR.mkdir(exist_ok=True)

TARGET_ORDERS = 1_000_000
ORDER_BATCH_SIZE = 50_000

generation_status = {
    "orders": {"generated": 0, "target": TARGET_ORDERS, "completed": False},
    "is_generating": False
}

# Standard Response Model
class StandardResponse(BaseModel):
    status: str = Field(..., example="success")
    msg: str = Field(..., example="Operation completed successfully")
    data: Any = Field(None)
    count: Optional[int] = Field(None)
    page: Optional[int] = Field(None)
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

def generate_order_batch(start_id, batch_size, locations):
    """Generate Sapo POS orders"""
    orders = []
    payment_methods = ["Tiền mặt", "Thẻ ATM", "Thẻ tín dụng", "Chuyển khoản", "Ví điện tử (MoMo/ZaloPay)"]
    order_statuses = ["completed", "cancelled", "refunded"]

    for i in range(start_id, start_id + batch_size):
        location = random.choice(locations) if locations else get_random_location()
        if not location:
            continue

        staff = get_random_staff()
        customer = get_random_customer()

        num_items = random.randint(1, 5)
        line_items = []
        subtotal_vnd = 0
        total_discount = 0
        transaction_id = generate_transaction_id()

        for j in range(num_items):
            product = get_random_product()
            if not product:
                continue

            quantity = random.randint(1, 3)
            price_vnd = product["price_vnd"]
            discount_percent = random.choice([0, 0, 0, 5, 10, 15])
            discount_amount = int(price_vnd * quantity * discount_percent / 100)
            discount_amount = round(discount_amount / 1000) * 1000
            line_total = price_vnd * quantity - discount_amount

            subtotal_vnd += line_total
            total_discount += discount_amount

            line_items.append({
                "id": i * 1000 + j,
                "product_id": product["id"],
                "variant_id": product["id"] * 10 + random.randint(1, 3),
                "sku": product["sku"],
                "barcode": product["barcode"],
                "product_name": product["name"],
                "quantity": quantity,
                "price_vnd": price_vnd,
                "discount_percent": discount_percent,
                "discount_amount": discount_amount,
                "line_amount": line_total,
                "transaction_id": transaction_id
            })

        vat_amount = int(subtotal_vnd * 0.1)
        vat_amount = round(vat_amount / 1000) * 1000
        total_vnd = subtotal_vnd + vat_amount

        order_date = datetime.now() - timedelta(
            days=random.randint(0, 365),
            hours=random.randint(9, 21),
            minutes=random.randint(0, 59)
        )

        order = {
            "id": i,
            "tenant_id": location.get("tenant_id", 1000),
            "code": f"HD{order_date.strftime('%y%m%d')}{str(i).zfill(6)}",
            "order_code": f"POS-{str(i).zfill(8)}",
            "location_id": location["id"],
            "location_name": location["name"],
            "location_code": location["code"],
            "transaction_id": transaction_id,
            "created_on": order_date.isoformat(),
            "modified_on": datetime.now().isoformat(),
            "finished_on": order_date.isoformat(),
            "status": random.choice(order_statuses),
            "source": "POS",
            "channel": "retail_offline",
            "customer": {
                "id": customer["id"],
                "name": f"Customer {customer['id']}",
                "phone": fake_vi.phone_number() if random.random() > 0.3 else None
            },
            "staff": {
                "id": staff["id"],
                "code": staff["code"],
                "full_name": staff["full_name"],
                "position": staff["position"]
            } if staff else None,
            "line_items": line_items,
            "total_before_discount": subtotal_vnd + total_discount,
            "total_discount": total_discount,
            "total_before_vat": subtotal_vnd,
            "vat_rate": 0.1,
            "vat_amount": vat_amount,
            "total_vnd": total_vnd,
            "payment_method": random.choice(payment_methods),
            "currency": "VND",
            "source": "sapo_pos"
        }
        orders.append(order)

    return orders

def generate_orders_in_batches():
    """Generate all Sapo orders"""
    print(f"🏪 Starting Sapo POS order generation: {TARGET_ORDERS:,} orders")

    locations = SHARED_LOCATIONS if SHARED_LOCATIONS else []

    if not locations:
        return {"error": "No locations available"}

    for batch_num in range(0, TARGET_ORDERS, ORDER_BATCH_SIZE):
        batch_size = min(ORDER_BATCH_SIZE, TARGET_ORDERS - batch_num)
        orders = generate_order_batch(batch_num + 1, batch_size, locations)

        batch_file = ORDERS_DIR / f"orders_batch_{batch_num // ORDER_BATCH_SIZE}.json.gz"
        save_compressed(orders, batch_file)

        generation_status["orders"]["generated"] = batch_num + batch_size
        print(f"Generated Sapo orders: {generation_status['orders']['generated']:,} / {TARGET_ORDERS:,}")

    generation_status["orders"]["completed"] = True
    print(f"✅ Sapo POS order generation completed!")

def load_order_batch(batch_num):
    batch_file = ORDERS_DIR / f"orders_batch_{batch_num}.json.gz"
    return load_compressed(batch_file)

# API Endpoints
@router.get("/", response_model=StandardResponse)
async def sapo_info():
    """Sapo POS API information"""
    return {
        "status": "success",
        "msg": "Sapo POS API - Vietnam Retail",
        "data": {
            "service": "Sapo POS API - Vietnam Retail",
            "market": "Vietnam Technology Retail - 50 Offline Stores",
            "locations": len(SHARED_LOCATIONS),
            "orders": f"{generation_status['orders']['generated']:,} / {TARGET_ORDERS:,}",
            "staff": len(SHARED_STAFF),
            "products": len(SHARED_PRODUCTS),
            "endpoints": [
                "/sapo/admin/locations",
                "/sapo/admin/products",
                "/sapo/admin/staff",
                "/sapo/admin/orders",
                "/sapo/generate/*"
            ]
        }
    }

@router.get("/admin/locations", response_model=StandardResponse)
async def get_locations():
    """Get all store locations"""
    # Try to load locations from file if not in memory
    ensure_locations_loaded()

    if not SHARED_LOCATIONS:
        return {
            "status": "error",
            "msg": "No locations data found. Please generate locations first via /sapo/generate/locations",
            "data": [],
            "count": 0
        }

    return {
        "status": "success",
        "msg": "Locations retrieved successfully",
        "data": SHARED_LOCATIONS,
        "count": len(SHARED_LOCATIONS),
        "total": len(SHARED_LOCATIONS)
    }

@router.get("/admin/products", response_model=StandardResponse)
async def get_products(
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0)
):
    """Get products"""
    # Try to load products from file if not in memory
    ensure_products_loaded()

    if not SHARED_PRODUCTS:
        return {
            "status": "error",
            "msg": "No products data found. Please generate products first via /shopify/generate/products",
            "data": [],
            "count": 0
        }

    products = SHARED_PRODUCTS[offset:offset + limit]
    return {
        "status": "success",
        "msg": "Products retrieved successfully",
        "data": products,
        "count": len(products),
        "total": len(SHARED_PRODUCTS)
    }

@router.get("/admin/staff", response_model=StandardResponse)
async def get_staff(
    location_id: int = Query(None, description="Filter by location")
):
    """Get staff members"""
    # Try to load staff from file if not in memory
    ensure_staff_loaded()

    if not SHARED_STAFF:
        return {
            "status": "error",
            "msg": "No staff data found. Please generate staff first via /shopify/generate/staff",
            "data": [],
            "count": 0
        }

    staff = SHARED_STAFF[:50]  # Return subset for demo
    return {
        "status": "success",
        "msg": "Staff retrieved successfully",
        "data": staff,
        "count": len(staff),
        "total": len(SHARED_STAFF)
    }

@router.get("/admin/orders", response_model=StandardResponse)
async def get_orders(
    limit: int = Query(50, ge=1, le=250),
    page: int = Query(1, ge=1),
    location_id: int = Query(None),
    status: str = Query(None)
):
    """Get paginated orders"""
    batch_num = ((page - 1) * limit) // ORDER_BATCH_SIZE
    offset_in_batch = ((page - 1) * limit) % ORDER_BATCH_SIZE

    # Try to load orders from file
    orders = load_order_batch(batch_num)
    if not orders:
        # Check if any order files exist
        order_files = list(ORDERS_DIR.glob("*.json.gz"))
        if not order_files:
            return {
                "status": "error",
                "msg": "No orders data found. Please generate orders first via /sapo/generate/orders",
                "data": [],
                "count": 0,
                "page": page
            }
        else:
            return {
                "status": "warning",
                "msg": f"Order batch {batch_num} not found. Available batches: 0 to {len(order_files)-1}",
                "data": [],
                "count": 0,
                "page": page
            }

    # Apply filters
    if location_id:
        orders = [o for o in orders if o["location_id"] == location_id]
    if status:
        orders = [o for o in orders if o["status"] == status]

    result = orders[offset_in_batch:offset_in_batch + limit]

    return {
        "status": "success",
        "msg": "Orders retrieved successfully",
        "data": result,
        "count": len(result),
        "page": page,
        "total": generation_status["orders"]["generated"]
    }

# Generation Sub-Endpoints
@router.post("/generate/locations", response_model=StandardResponse)
@router.get("/generate/locations", response_model=StandardResponse)
async def generate_locations_endpoint(
    count: int = Query(50, ge=10, le=100, description="Number of locations to generate"),
    method: Optional[str] = Query(None, description="Generation method: 'new' to append new data, 'no' or None to keep existing data")
):
    """Generate Vietnam store locations

    Parameters:
    - method='new': Generate and append new locations to existing data
    - method='no' or None: Keep existing data without generating new
    """
    try:
        # Ensure existing data is loaded
        ensure_locations_loaded()

        # Check if data already exists and method is not 'new'
        if GENERATION_STATUS["locations"]["generated"] and method != "new":
            return {
                "status": "warning",
                "msg": "Locations already exist. Use 'method=new' parameter to generate and append new data.",
                "data": {
                    "count": len(SHARED_LOCATIONS),
                    "hint": "Add parameter: method=new to append more locations"
                },
                "count": len(SHARED_LOCATIONS)
            }

        # Generate new locations with appropriate mode
        if method == "new":
            # Append mode
            locations = generate_shared_locations(count, mode="append")
            msg = f"Successfully appended {count} new locations. Total: {len(locations)}"
        else:
            # Replace mode (first time generation)
            locations = generate_shared_locations(count, mode="replace")
            msg = f"Successfully generated {len(locations)} store locations"

        # Update the module-level SHARED_LOCATIONS
        import shared.data_generator as dg
        dg.SHARED_LOCATIONS = locations

        return {
            "status": "success",
            "msg": msg,
            "data": {
                "total": len(locations),
                "newly_generated": count if method == "new" else len(locations),
                "mode": "append" if method == "new" else "replace",
                "sample": locations[-5:] if method == "new" else locations[:5]
            },
            "count": len(locations)
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Failed to generate locations: {str(e)}",
            "data": None
        }

@router.post("/generate/orders", response_model=StandardResponse)
@router.get("/generate/orders", response_model=StandardResponse)
async def generate_orders_endpoint(background_tasks: BackgroundTasks):
    """Generate Sapo orders"""
    try:
        if not SHARED_PRODUCTS:
            return {
                "status": "error",
                "msg": "Products must be generated first before orders",
                "data": None
            }

        if not SHARED_STAFF:
            return {
                "status": "error",
                "msg": "Staff must be generated first before orders",
                "data": None
            }

        if not SHARED_LOCATIONS:
            return {
                "status": "error",
                "msg": "Locations must be generated first before orders",
                "data": None
            }

        if generation_status["is_generating"]:
            return {
                "status": "warning",
                "msg": "Order generation already in progress",
                "data": {"current": generation_status["orders"]["generated"]},
                "count": generation_status["orders"]["generated"]
            }

        if generation_status["orders"]["completed"]:
            return {
                "status": "warning",
                "msg": "Orders already generated",
                "data": {"count": generation_status["orders"]["generated"]},
                "count": generation_status["orders"]["generated"]
            }

        def generate():
            generation_status["is_generating"] = True
            try:
                generate_orders_in_batches()
            finally:
                generation_status["is_generating"] = False

        background_tasks.add_task(generate)

        return {
            "status": "success",
            "msg": "Sapo POS order generation started in background",
            "data": {
                "target": TARGET_ORDERS,
                "estimated_time": "8-15 minutes"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Failed to start order generation: {str(e)}",
            "data": None
        }

@router.get("/generate/status", response_model=StandardResponse)
async def get_generation_status():
    """Get generation status"""
    return {
        "status": "success",
        "msg": "Generation status retrieved",
        "data": {
            "locations": GENERATION_STATUS["locations"],
            "products": GENERATION_STATUS["products"],
            "staff": GENERATION_STATUS["staff"],
            "orders": generation_status["orders"],
            "is_generating": generation_status["is_generating"]
        }
    }

@router.post("/generate/all", response_model=StandardResponse)
@router.get("/generate/all", response_model=StandardResponse)
async def generate_all_data(background_tasks: BackgroundTasks):
    """Generate all Sapo data (locations + orders)"""
    try:
        def generate_all():
            # Generate locations if not exists
            if not GENERATION_STATUS["locations"]["generated"]:
                print("Generating locations...")
                generate_shared_locations(50)

            # Generate orders
            if not generation_status["orders"]["completed"]:
                print("Generating orders...")
                generation_status["is_generating"] = True
                try:
                    generate_orders_in_batches()
                finally:
                    generation_status["is_generating"] = False

        background_tasks.add_task(generate_all)

        return {
            "status": "success",
            "msg": "Sapo POS full data generation started in background",
            "data": {
                "locations": 50,
                "orders": TARGET_ORDERS,
                "estimated_time": "10-15 minutes"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Failed to start generation: {str(e)}",
            "data": None
        }
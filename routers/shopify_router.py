"""
Shopify API Router
E-commerce platform for online sales
"""

from fastapi import APIRouter, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime, timedelta
import random
from pathlib import Path
import gzip
import json
from shared.data_generator import (
    SHARED_PRODUCTS, SHARED_STAFF, SHARED_CUSTOMERS,
    get_random_product, get_random_customer, get_random_staff,
    generate_transaction_id, generate_shared_products, generate_shared_customers,
    generate_shared_staff, DATA_DIR, GENERATION_STATUS
)

router = APIRouter()

# Configuration
ORDERS_DIR = DATA_DIR / "shopify_orders"
ORDERS_DIR.mkdir(exist_ok=True)

TARGET_ORDERS = 6_000_000
ORDER_BATCH_SIZE = 50_000

generation_status = {
    "orders": {"generated": 0, "target": TARGET_ORDERS, "completed": False},
    "is_generating": False
}

# Standard Response Model
class StandardResponse(BaseModel):
    status: str = Field(..., example="success", description="Response status: success, error, warning")
    msg: str = Field(..., example="Operation completed successfully", description="Response message")
    data: Any = Field(None, description="Response data")
    count: Optional[int] = Field(None, description="Number of records returned")
    page: Optional[int] = Field(None, description="Current page number")
    total: Optional[int] = Field(None, description="Total records available")

# Helper functions
def save_compressed(data, filepath):
    with gzip.open(filepath, 'wt', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def load_compressed(filepath):
    if not filepath.exists():
        return None
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        return json.load(f)

def generate_order_batch(start_id, batch_size):
    """Generate Shopify orders with shared metadata"""
    orders = []
    payment_statuses = ["paid", "pending", "partially_paid", "refunded"]

    for i in range(start_id, start_id + batch_size):
        customer = get_random_customer()
        is_vietnamese = random.random() < 0.95

        num_items = random.randint(1, 5)
        line_items = []
        subtotal_vnd = 0
        subtotal_usd = 0
        transaction_id = generate_transaction_id()

        for j in range(num_items):
            product = get_random_product()
            if not product:
                continue

            quantity = random.randint(1, 3)
            price_vnd = product["price_vnd"]
            price_usd = product["price_usd"]

            subtotal_vnd += price_vnd * quantity
            subtotal_usd += price_usd * quantity

            line_items.append({
                "id": i * 1000 + j,
                "product_id": product["id"],
                "product_name": product["name"],
                "sku": product["sku"],
                "quantity": quantity,
                "price_vnd": price_vnd,
                "price_usd": price_usd,
                "transaction_id": transaction_id
            })

        tax_vnd = int(subtotal_vnd * 0.1)
        tax_usd = round(subtotal_usd * 0.1, 2)
        shipping_vnd = random.choice([0, 30000, 50000])
        shipping_usd = round(shipping_vnd / 24000, 2)

        total_vnd = subtotal_vnd + tax_vnd + shipping_vnd
        total_usd = round(subtotal_usd + tax_usd + shipping_usd, 2)

        order_date = datetime.now() - timedelta(days=random.randint(0, 365))

        order = {
            "id": i,
            "order_number": f"ORD-{order_date.strftime('%Y%m%d')}-{str(i).zfill(6)}",
            "customer_id": customer["id"],
            "customer_name": f"Customer {customer['id']}",
            "customer_email": f"customer{customer['id']}@example.com",
            "transaction_id": transaction_id,
            "order_date": order_date.isoformat(),
            "updated_at": datetime.now().isoformat(),
            "payment_gateway": random.choice(["paypal", "mercury_bank"]),
            "payment_status": random.choice(payment_statuses),
            "fulfillment_status": random.choice(["fulfilled", "pending", "cancelled"]),
            "currency": "VND" if is_vietnamese else "USD",
            "subtotal_vnd": subtotal_vnd,
            "subtotal_usd": round(subtotal_usd, 2),
            "tax_vnd": tax_vnd,
            "tax_usd": tax_usd,
            "shipping_vnd": shipping_vnd,
            "shipping_usd": shipping_usd,
            "total_vnd": total_vnd,
            "total_usd": total_usd,
            "line_items": line_items,
            "channel": "online",
            "source": "shopify"
        }
        orders.append(order)

    return orders

def generate_orders_in_batches():
    """Generate all Shopify orders"""
    print(f"🛒 Starting Shopify order generation: {TARGET_ORDERS:,} orders")

    for batch_num in range(0, TARGET_ORDERS, ORDER_BATCH_SIZE):
        batch_size = min(ORDER_BATCH_SIZE, TARGET_ORDERS - batch_num)
        orders = generate_order_batch(batch_num + 1, batch_size)

        batch_file = ORDERS_DIR / f"orders_batch_{batch_num // ORDER_BATCH_SIZE}.json.gz"
        save_compressed(orders, batch_file)

        generation_status["orders"]["generated"] = batch_num + batch_size
        print(f"Generated Shopify orders: {generation_status['orders']['generated']:,} / {TARGET_ORDERS:,}")

    generation_status["orders"]["completed"] = True
    print(f"✅ Shopify order generation completed!")

def load_order_batch(batch_num):
    batch_file = ORDERS_DIR / f"orders_batch_{batch_num}.json.gz"
    return load_compressed(batch_file)

# API Endpoints
@router.get("/", response_model=StandardResponse)
async def shopify_info():
    """Shopify API endpoint information"""
    return {
        "status": "success",
        "msg": "Shopify E-commerce API",
        "data": {
            "service": "Shopify E-commerce API",
            "market": "Vietnam Technology Retail - Online Store",
            "orders": f"{generation_status['orders']['generated']:,} / {TARGET_ORDERS:,}",
            "products": len(SHARED_PRODUCTS),
            "staff": len(SHARED_STAFF),
            "endpoints": [
                "/shopify/admin/api/2024-01/products",
                "/shopify/admin/api/2024-01/orders",
                "/shopify/admin/api/2024-01/staff",
                "/shopify/generate/*"
            ]
        }
    }

@router.get("/admin/api/2024-01/products", response_model=StandardResponse)
async def get_products(
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0)
):
    """Get products with Vietnamese tech focus"""
    if not SHARED_PRODUCTS:
        return {
            "status": "error",
            "msg": "Products not generated yet. Please generate products first.",
            "data": None,
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

@router.get("/admin/api/2024-01/orders", response_model=StandardResponse)
async def get_orders(
    limit: int = Query(50, ge=1, le=250),
    page: int = Query(1, ge=1),
    payment_status: str = Query(None)
):
    """Get paginated orders"""
    batch_num = ((page - 1) * limit) // ORDER_BATCH_SIZE
    offset_in_batch = ((page - 1) * limit) % ORDER_BATCH_SIZE

    orders = load_order_batch(batch_num)
    if not orders:
        return {
            "status": "warning",
            "msg": "Orders not generated yet. Please generate orders first.",
            "data": [],
            "count": 0,
            "page": page
        }

    if payment_status:
        orders = [o for o in orders if o.get("payment_status") == payment_status]

    result = orders[offset_in_batch:offset_in_batch + limit]
    return {
        "status": "success",
        "msg": "Orders retrieved successfully",
        "data": result,
        "count": len(result),
        "page": page,
        "total": generation_status["orders"]["generated"]
    }

@router.get("/admin/api/2024-01/staff", response_model=StandardResponse)
async def get_staff():
    """Get all staff members"""
    if not SHARED_STAFF:
        return {
            "status": "error",
            "msg": "Staff not generated yet. Please generate staff first.",
            "data": None,
            "count": 0
        }

    return {
        "status": "success",
        "msg": "Staff retrieved successfully",
        "data": SHARED_STAFF,
        "count": len(SHARED_STAFF),
        "total": len(SHARED_STAFF)
    }

# Generation Sub-Endpoints
@router.post("/generate/products", response_model=StandardResponse)
@router.get("/generate/products", response_model=StandardResponse)
async def generate_products_endpoint(
    count: int = Query(1000, ge=100, le=5000, description="Number of products to generate"),
    new: bool = Query(False, description="If True, delete existing data and generate new. If False, keep existing data.")
):
    """Generate product catalog"""
    try:
        # Check if data already exists
        if GENERATION_STATUS["products"]["generated"] and not new:
            return {
                "status": "warning",
                "msg": "Products already exist. Use 'new=true' parameter to generate new data and replace existing.",
                "data": {
                    "count": len(SHARED_PRODUCTS),
                    "hint": "Add parameter: new=true to regenerate"
                },
                "count": len(SHARED_PRODUCTS)
            }

        # Clear existing data if new=true
        if new and GENERATION_STATUS["products"]["generated"]:
            print("🗑️  Clearing existing products...")
            from shared.data_generator import clear_generated_data
            clear_generated_data("products")

        # Generate new products
        products = generate_shared_products(count)

        # Update the module-level SHARED_PRODUCTS
        import shared.data_generator as dg
        dg.SHARED_PRODUCTS = products

        return {
            "status": "success",
            "msg": f"Successfully generated {len(products)} products" + (" (replaced existing)" if new else ""),
            "data": {
                "generated": len(products),
                "replaced": new,
                "sample": products[:5]
            },
            "count": len(products)
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Failed to generate products: {str(e)}",
            "data": None
        }

@router.post("/generate/customers", response_model=StandardResponse)
@router.get("/generate/customers", response_model=StandardResponse)
async def generate_customers_endpoint(
    background_tasks: BackgroundTasks,
    count: int = Query(2_000_000, ge=1000, le=5_000_000, description="Number of customers to generate"),
    new: bool = Query(False, description="If True, delete existing data and generate new")
):
    """Generate customer database"""
    try:
        # Check if data already exists
        if GENERATION_STATUS["customers"]["generated"] and not new:
            return {
                "status": "warning",
                "msg": "Customers already exist. Use 'new=true' parameter to generate new data and replace existing.",
                "data": {
                    "count": GENERATION_STATUS["customers"]["count"],
                    "hint": "Add parameter: new=true to regenerate"
                },
                "count": GENERATION_STATUS["customers"]["count"]
            }

        # Clear existing data if new=true
        if new and GENERATION_STATUS["customers"]["generated"]:
            print("🗑️  Clearing existing customers...")
            from shared.data_generator import clear_generated_data
            clear_generated_data("customers")

        def generate():
            generate_shared_customers(count)

        background_tasks.add_task(generate)

        return {
            "status": "success",
            "msg": f"Customer generation started in background for {count:,} customers" + (" (will replace existing)" if new else ""),
            "data": {
                "target": count,
                "replaced": new,
                "estimated_time": "5-10 minutes"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Failed to start customer generation: {str(e)}",
            "data": None
        }

@router.post("/generate/staff", response_model=StandardResponse)
@router.get("/generate/staff", response_model=StandardResponse)
async def generate_staff_endpoint(
    count: int = Query(300, ge=50, le=1000, description="Number of staff to generate"),
    new: bool = Query(False, description="If True, delete existing data and generate new")
):
    """Generate staff members"""
    try:
        # Check if data already exists
        if GENERATION_STATUS["staff"]["generated"] and not new:
            return {
                "status": "warning",
                "msg": "Staff already exist. Use 'new=true' parameter to generate new data and replace existing.",
                "data": {
                    "count": len(SHARED_STAFF),
                    "hint": "Add parameter: new=true to regenerate"
                },
                "count": len(SHARED_STAFF)
            }

        # Clear existing data if new=true
        if new and GENERATION_STATUS["staff"]["generated"]:
            print("🗑️  Clearing existing staff...")
            from shared.data_generator import clear_generated_data
            clear_generated_data("staff")

        # Generate new staff
        staff = generate_shared_staff(count)

        # Update the module-level SHARED_STAFF
        import shared.data_generator as dg
        dg.SHARED_STAFF = staff

        return {
            "status": "success",
            "msg": f"Successfully generated {len(staff)} staff members" + (" (replaced existing)" if new else ""),
            "data": {
                "generated": len(staff),
                "replaced": new,
                "sample": staff[:5]
            },
            "count": len(staff)
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Failed to generate staff: {str(e)}",
            "data": None
        }

@router.post("/generate/orders", response_model=StandardResponse)
@router.get("/generate/orders", response_model=StandardResponse)
async def generate_orders_endpoint(background_tasks: BackgroundTasks):
    """Generate Shopify orders in background"""
    try:
        if not SHARED_PRODUCTS:
            return {
                "status": "error",
                "msg": "Products must be generated first before orders",
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
            "msg": "Shopify order generation started in background",
            "data": {
                "target": TARGET_ORDERS,
                "estimated_time": "15-25 minutes"
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
    """Get generation status for all entities"""
    return {
        "status": "success",
        "msg": "Generation status retrieved",
        "data": {
            "products": GENERATION_STATUS["products"],
            "customers": GENERATION_STATUS["customers"],
            "staff": GENERATION_STATUS["staff"],
            "orders": generation_status["orders"],
            "is_generating": generation_status["is_generating"]
        }
    }

@router.post("/generate/all", response_model=StandardResponse)
@router.get("/generate/all", response_model=StandardResponse)
async def generate_all_data(background_tasks: BackgroundTasks):
    """Generate all data (products, customers, staff, orders)"""
    try:
        def generate_all():
            # Generate in sequence
            if not GENERATION_STATUS["products"]["generated"]:
                print("Generating products...")
                generate_shared_products(1000)

            if not GENERATION_STATUS["staff"]["generated"]:
                print("Generating staff...")
                generate_shared_staff(300)

            if not GENERATION_STATUS["customers"]["generated"]:
                print("Generating customers...")
                generate_shared_customers(2_000_000)

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
            "msg": "Full data generation started in background",
            "data": {
                "products": 1000,
                "staff": 300,
                "customers": 2_000_000,
                "orders": TARGET_ORDERS,
                "estimated_time": "30-50 minutes"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Failed to start generation: {str(e)}",
            "data": None
        }
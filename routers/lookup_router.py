"""
Lookup API Router
APIs for looking up transaction, customer, employee, and product details
"""

from fastapi import APIRouter, Query, Path
from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime
from pathlib import Path as FilePath
import gzip
import json
import shared.data_generator as data_generator
# from shared.data_generator import (
#     DATA_DIR, PRIVATE_DIRS, get_share_data_path, get_private_data_path,
#     get_customer_by_id, get_product_by_id, get_staff_by_id,
#     SHARED_PRODUCTS, SHARED_STAFF, SHARED_LOCATIONS, SHARED_SHOPS,
#     ensure_products_loaded, ensure_staff_loaded, ensure_locations_loaded, ensure_shops_loaded
# )

router = APIRouter()

# Standard Response Model
class StandardResponse(BaseModel):
    status: str = Field(..., example="success")
    msg: str = Field(..., example="Operation completed successfully")
    data: Any = Field(None)
    count: Optional[int] = Field(None)
    total: Optional[int] = Field(None)

# Helper functions
def load_compressed(filepath):
    if not filepath.exists():
        return None
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        return json.load(f)

def search_transactions_across_sources(transaction_id: str):
    """Search for a transaction across all data sources"""
    results = []

    # Search PayPal transactions
    paypal_file = data_generator.get_private_data("paypal", "transactions.json.gz")
    if not paypal_file.exists():
        paypal_file = data_generator.DATA_DIR / "paypal_transactions" / "transactions.json.gz"
    if paypal_file.exists():
        transactions = load_compressed(paypal_file)
        if transactions:
            for t in transactions:
                if t.get("transaction_id") == transaction_id:
                    results.append({"source": "paypal", "data": t})
                    break

    # Search Mercury transactions
    mercury_file = data_generator.get_private_data("mercury", "transactions.json.gz")
    if not mercury_file.exists():
        mercury_file = data_generator.DATA_DIR / "mercury_transactions" / "transactions.json.gz"
    if mercury_file.exists():
        transactions = load_compressed(mercury_file)
        if transactions:
            for t in transactions:
                if t.get("transaction_id") == transaction_id:
                    results.append({"source": "mercury", "data": t})
                    break

    # Search MoMo transactions
    momo_file = data_generator.get_private_data("momo", "transactions.json.gz")
    if momo_file.exists():
        transactions = load_compressed(momo_file)
        if transactions:
            for t in transactions:
                if t.get("transaction_id") == transaction_id or t.get("transId") == transaction_id:
                    results.append({"source": "momo", "data": t})
                    break

    # Search ZaloPay transactions
    zalopay_file = data_generator.get_private_data("zalopay", "transactions.json.gz")
    if zalopay_file.exists():
        transactions = load_compressed(zalopay_file)
        if transactions:
            for t in transactions:
                if t.get("transaction_id") == transaction_id or t.get("apptransid") == transaction_id:
                    results.append({"source": "zalopay", "data": t})
                    break

    # Search Shopify orders
    shopify_dir = data_generator.get_private_data("shopify", "orders")
    if not shopify_dir.exists():
        shopify_dir = data_generator.DATA_DIR / "shopify_orders"
    if shopify_dir.exists():
        for batch_file in FilePath(shopify_dir).glob("*.json.gz"):
            orders = load_compressed(batch_file)
            if orders:
                for o in orders:
                    if o.get("transaction_id") == transaction_id:
                        results.append({"source": "shopify", "data": o})
                        break
            if any(r["source"] == "shopify" for r in results):
                break

    # Search Sapo orders
    sapo_dir = data_generator.get_private_data("sapo", "orders")
    if not sapo_dir.exists():
        sapo_dir = data_generator.DATA_DIR / "sapo_orders"
    if sapo_dir.exists():
        for batch_file in FilePath(sapo_dir).glob("*.json.gz"):
            orders = load_compressed(batch_file)
            if orders:
                for o in orders:
                    if o.get("transaction_id") == transaction_id:
                        results.append({"source": "sapo", "data": o})
                        break
            if any(r["source"] == "sapo" for r in results):
                break

    # Search Odoo orders
    odoo_dir = data_generator.get_private_data("odoo", "orders")
    if not odoo_dir.exists():
        odoo_dir = data_generator.DATA_DIR / "odoo_orders"
    if odoo_dir.exists():
        for batch_file in FilePath(odoo_dir).glob("*.json.gz"):
            orders = load_compressed(batch_file)
            if orders:
                for o in orders:
                    if o.get("transaction_id") == transaction_id:
                        results.append({"source": "odoo", "data": o})
                        break
            if any(r["source"] == "odoo" for r in results):
                break

    return results

# API Endpoints
@router.get("/", response_model=StandardResponse)
async def lookup_info():
    """Lookup API information"""
    return {
        "status": "success",
        "msg": "Lookup API - Search transactions, customers, employees, products",
        "data": {
            "service": "Lookup API",
            "endpoints": [
                "/lookup/transaction/{transaction_id}",
                "/lookup/customer/{customer_id}",
                "/lookup/employee/{employee_id}",
                "/lookup/product/{product_id}",
                "/lookup/products",
                "/lookup/employees",
                "/lookup/customers"
            ]
        }
    }

@router.get("/transaction/{transaction_id}", response_model=StandardResponse)
async def check_transaction(
    transaction_id: str = Path(..., description="Transaction ID to look up (e.g., TXN20241124XXXXXXXX)")
):
    """
    Check transaction status across all payment sources

    Searches:
    - PayPal transactions
    - Mercury bank transactions
    - MoMo transactions
    - ZaloPay transactions
    - Shopify orders
    - Sapo orders
    - Odoo orders
    """
    results = search_transactions_across_sources(transaction_id)

    if not results:
        return {
            "status": "error",
            "msg": f"Transaction {transaction_id} not found in any source",
            "data": None,
            "count": 0
        }

    return {
        "status": "success",
        "msg": f"Transaction found in {len(results)} source(s)",
        "data": {
            "transaction_id": transaction_id,
            "found_in_sources": [r["source"] for r in results],
            "details": results
        },
        "count": len(results)
    }

@router.get("/customer/{customer_id}", response_model=StandardResponse)
async def get_customer_details(
    customer_id: int = Path(..., ge=1, description="Customer ID to look up")
):
    """
    Get detailed customer information by ID

    Returns customer profile including:
    - Personal information
    - Contact details
    - Location
    - Order statistics
    """
    customer = data_generator.get_customer_by_id(customer_id)

    if not customer:
        return {
            "status": "error",
            "msg": f"Customer with ID {customer_id} not found",
            "data": None
        }

    return {
        "status": "success",
        "msg": "Customer details retrieved successfully",
        "data": customer
    }

@router.get("/employee/{employee_id}", response_model=StandardResponse)
async def get_employee_details(
    employee_id: int = Path(..., ge=1, description="Employee/Staff ID to look up")
):
    """
    Get detailed employee information by ID

    Returns employee profile including:
    - Personal information
    - Position
    - Contact details
    - Employment status
    """
    employee = data_generator.get_staff_by_id(employee_id)

    if not employee:
        return {
            "status": "error",
            "msg": f"Employee with ID {employee_id} not found",
            "data": None
        }

    return {
        "status": "success",
        "msg": "Employee details retrieved successfully",
        "data": employee
    }

@router.get("/product/{product_id}", response_model=StandardResponse)
async def get_product_details(
    product_id: int = Path(..., ge=1, description="Product ID to look up")
):
    """
    Get detailed product information by ID

    Returns product details including:
    - Name and description
    - Pricing (VND and USD)
    - Category and brand
    - Stock information
    """
    product = data_generator.get_product_by_id(product_id)

    if not product:
        return {
            "status": "error",
            "msg": f"Product with ID {product_id} not found",
            "data": None
        }

    return {
        "status": "success",
        "msg": "Product details retrieved successfully",
        "data": product
    }

@router.get("/products", response_model=StandardResponse)
async def list_products(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None, description="Filter by category"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[int] = Query(None, description="Minimum price in VND"),
    max_price: Optional[int] = Query(None, description="Maximum price in VND")
):
    """
    List products with filtering options
    """
    await data_generator.ensure_products_loaded()

    if not data_generator.SHARED_PRODUCTS:
        return {
            "status": "error",
            "msg": "No products data found. Please generate products first.",
            "data": [],
            "count": 0
        }

    filtered = data_generator.SHARED_PRODUCTS

    if category:
        filtered = [p for p in filtered if p.get("category", "").lower() == category.lower()]
    if brand:
        filtered = [p for p in filtered if p.get("brand", "").lower() == brand.lower()]
    if min_price:
        filtered = [p for p in filtered if p.get("price_vnd", 0) >= min_price]
    if max_price:
        filtered = [p for p in filtered if p.get("price_vnd", 0) <= max_price]

    result = filtered[offset:offset + limit]

    return {
        "status": "success",
        "msg": "Products retrieved successfully",
        "data": result,
        "count": len(result),
        "total": len(filtered)
    }

@router.get("/employees", response_model=StandardResponse)
async def list_employees(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    position: Optional[str] = Query(None, description="Filter by position"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """
    List employees with filtering options
    """
    data_generator.ensure_staff_loaded()

    if not data_generator.SHARED_STAFF:
        return {
            "status": "error",
            "msg": "No staff data found. Please generate staff first.",
            "data": [],
            "count": 0
        }

    filtered = data_generator.SHARED_STAFF

    if position:
        filtered = [s for s in filtered if position.lower() in s.get("position", "").lower()]
    if status:
        filtered = [s for s in filtered if s.get("status", "").lower() == status.lower()]

    result = filtered[offset:offset + limit]

    return {
        "status": "success",
        "msg": "Employees retrieved successfully",
        "data": result,
        "count": len(result),
        "total": len(filtered)
    }

@router.get("/customers", response_model=StandardResponse)
async def list_customers(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    city: Optional[str] = Query(None, description="Filter by city"),
    country: Optional[str] = Query(None, description="Filter by country")
):
    """
    List customers with filtering options

    Note: Customers are stored in batches. This endpoint loads specific batches based on offset.
    """
    batch_size = 10_000
    batch_num = offset // batch_size
    offset_in_batch = offset % batch_size

    # Try new location first
    customer_dir = data_generator.get_share_data_path("customers")
    batch_file = FilePath(customer_dir) / f"customers_batch_{batch_num}.json.gz"

    # Fallback to old location
    if not batch_file.exists():
        batch_file = data_generator.DATA_DIR / "customers" / f"customers_batch_{batch_num}.json.gz"

    if not batch_file.exists():
        return {
            "status": "error",
            "msg": "No customers data found. Please generate customers first.",
            "data": [],
            "count": 0
        }

    customers = load_compressed(batch_file)
    if not customers:
        return {
            "status": "error",
            "msg": f"Customer batch {batch_num} not found",
            "data": [],
            "count": 0
        }

    # Apply filters
    filtered = customers
    if city:
        filtered = [c for c in filtered if city.lower() in c.get("city", "").lower()]
    if country:
        filtered = [c for c in filtered if country.lower() in c.get("country", "").lower()]

    result = filtered[offset_in_batch:offset_in_batch + limit]

    return {
        "status": "success",
        "msg": "Customers retrieved successfully",
        "data": result,
        "count": len(result),
        "total": len(filtered)
    }

@router.get("/locations", response_model=StandardResponse)
async def list_locations(
    limit: int = Query(50, ge=1, le=100),
    city: Optional[str] = Query(None, description="Filter by city")
):
    """
    List store locations
    """
    data_generator.ensure_locations_loaded()

    if not data_generator.SHARED_LOCATIONS:
        return {
            "status": "error",
            "msg": "No locations data found. Please generate locations first.",
            "data": [],
            "count": 0
        }

    filtered = data_generator.SHARED_LOCATIONS
    if city:
        filtered = [l for l in filtered if city.lower() in l.get("city", "").lower()]

    result = filtered[:limit]

    return {
        "status": "success",
        "msg": "Locations retrieved successfully",
        "data": result,
        "count": len(result),
        "total": len(filtered)
    }

@router.get("/shops", response_model=StandardResponse)
async def list_shops(
    limit: int = Query(50, ge=1, le=100),
    country: Optional[str] = Query(None, description="Filter by country"),
    currency: Optional[str] = Query(None, description="Filter by currency code")
):
    """
    List international shops
    """
    data_generator.ensure_shops_loaded()

    if not data_generator.SHARED_SHOPS:
        return {
            "status": "error",
            "msg": "No shops data found. Please generate shops first.",
            "data": [],
            "count": 0
        }

    filtered = data_generator.SHARED_SHOPS
    if country:
        filtered = [s for s in filtered if country.lower() in s.get("country", "").lower()]
    if currency:
        filtered = [s for s in filtered if s.get("currency_code", "").upper() == currency.upper()]

    result = filtered[:limit]

    return {
        "status": "success",
        "msg": "Shops retrieved successfully",
        "data": result,
        "count": len(result),
        "total": len(filtered)
    }

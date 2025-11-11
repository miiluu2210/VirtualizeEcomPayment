"""
PayPal API Router
Payment gateway for online transactions
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
    SHARED_PRODUCTS, get_random_customer, generate_transaction_id,
    DATA_DIR, fake_vi, fake_en, GENERATION_STATUS
)

router = APIRouter()

# Configuration
TRANSACTIONS_DIR = DATA_DIR / "paypal_transactions"
TRANSACTIONS_DIR.mkdir(exist_ok=True)

generation_status = {
    "transactions": {"generated": 0, "target": 300, "completed": False},
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

def generate_transactions_batch(count):
    """Generate PayPal transactions with shared transaction IDs"""
    transactions = []
    statuses = ["COMPLETED", "PENDING", "FAILED", "REVERSED", "CANCELLED"]
    types = ["PAYMENT", "REFUND", "TRANSFER"]

    for i in range(count):
        customer = get_random_customer()
        is_vietnamese = random.random() < 0.95

        amount_usd = round(random.uniform(10, 2000), 2)
        fee_usd = round(amount_usd * 0.034 + 0.30, 2)
        amount_vnd = int(amount_usd * 24000)

        transaction_id = generate_transaction_id()

        if is_vietnamese:
            given_name = fake_vi.first_name()
            surname = fake_vi.last_name()
            email = f"{given_name.lower()}.{surname.lower()}{customer['id']}@gmail.com"
        else:
            given_name = fake_en.first_name()
            surname = fake_en.last_name()
            email = f"{given_name.lower()}.{surname.lower()}{customer['id']}@gmail.com"

        transaction = {
            "transaction_id": transaction_id,
            "paypal_transaction_id": f"{random.randint(1000000000, 9999999999)}",
            "transaction_event_code": f"T{random.randint(1000, 9999)}",
            "transaction_initiation_date": (datetime.now() - timedelta(days=random.randint(0, 90))).isoformat(),
            "transaction_updated_date": datetime.now().isoformat(),
            "transaction_amount": {
                "currency_code": "USD",
                "value": str(amount_usd)
            },
            "transaction_amount_vnd": amount_vnd,
            "fee_amount": {
                "currency_code": "USD",
                "value": str(fee_usd)
            },
            "transaction_status": random.choice(statuses),
            "transaction_subject": f"Payment for TechStore Vietnam Order",
            "transaction_note": "Technology product purchase" if random.random() > 0.5 else "",
            "payer_info": {
                "account_id": f"ACCT-{random.randint(1000000000, 9999999999)}",
                "email_address": email,
                "address_status": "CONFIRMED" if random.random() > 0.3 else "UNCONFIRMED",
                "payer_status": "VERIFIED" if random.random() > 0.2 else "UNVERIFIED",
                "payer_name": {
                    "given_name": given_name,
                    "surname": surname
                },
                "country_code": "VN" if is_vietnamese else fake_en.country_code()
            },
            "shipping_info": {
                "name": f"{given_name} {surname}",
                "address": {
                    "line1": fake_vi.street_address() if is_vietnamese else fake_en.street_address(),
                    "city": fake_vi.city() if is_vietnamese else fake_en.city(),
                    "state": random.choice(["Hà Nội", "TP HCM", "Đà Nẵng"]) if is_vietnamese else fake_en.state_abbr(),
                    "postal_code": fake_vi.postcode() if is_vietnamese else fake_en.zipcode(),
                    "country_code": "VN" if is_vietnamese else "US"
                }
            },
            "transaction_type": random.choice(types),
            "payment_tracking_id": str(transaction_id),
            "invoice_id": f"INV-{str(random.randint(10000000, 99999999))}" if random.random() > 0.4 else None,
            "protection_eligibility": random.choice(["ELIGIBLE", "PARTIALLY_ELIGIBLE", "INELIGIBLE"]),
            "customer_id": customer["id"],
            "source": "paypal"
        }
        transactions.append(transaction)

    return transactions

def generate_all_transactions(count=300):
    """Generate all PayPal transactions"""
    print(f"💳 Starting PayPal transaction generation: {count:,} transactions")

    transactions = generate_transactions_batch(count)

    batch_file = TRANSACTIONS_DIR / "transactions.json.gz"
    save_compressed(transactions, batch_file)

    generation_status["transactions"]["generated"] = count
    generation_status["transactions"]["target"] = count
    generation_status["transactions"]["completed"] = True
    print(f"✅ PayPal transaction generation completed!")

    return transactions

# API Endpoints
@router.get("/", response_model=StandardResponse)
async def paypal_info():
    """PayPal API endpoint information"""
    return {
        "status": "success",
        "msg": "PayPal Payment Gateway API",
        "data": {
            "service": "PayPal Payment Gateway API",
            "market": "Vietnam Technology Retail - Online Payments",
            "transactions": f"{generation_status['transactions']['generated']:,} / {generation_status['transactions']['target']:,}",
            "endpoints": [
                "/paypal/v1/reporting/transactions",
                "/paypal/v1/payments/payment",
                "/paypal/v1/reporting/balances",
                "/paypal/generate/*"
            ]
        }
    }

@router.get("/v1/reporting/transactions", response_model=StandardResponse)
async def get_transactions(
    start_date: str = Query(None, description="Filter by start date (ISO 8601)"),
    end_date: str = Query(None, description="Filter by end date (ISO 8601)"),
    transaction_status: str = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=500)
):
    """Get PayPal transactions with filters"""
    batch_file = TRANSACTIONS_DIR / "transactions.json.gz"
    transactions = load_compressed(batch_file)

    if not transactions:
        return {
            "status": "warning",
            "msg": "Transactions not generated yet. Please generate transactions first.",
            "data": [],
            "count": 0
        }

    # Apply filters
    if transaction_status:
        transactions = [t for t in transactions if t["transaction_status"] == transaction_status]

    if start_date:
        transactions = [t for t in transactions if t["transaction_initiation_date"] >= start_date]

    if end_date:
        transactions = [t for t in transactions if t["transaction_initiation_date"] <= end_date]

    result = transactions[:limit]

    return {
        "status": "success",
        "msg": "Transactions retrieved successfully",
        "data": result,
        "count": len(result),
        "total": len(transactions)
    }

@router.get("/v1/payments/payment", response_model=StandardResponse)
async def get_payments(
    count: int = Query(50, ge=1, le=100)
):
    """Get payment records"""
    batch_file = TRANSACTIONS_DIR / "transactions.json.gz"
    transactions = load_compressed(batch_file)

    if not transactions:
        return {
            "status": "warning",
            "msg": "Payments not generated yet. Please generate transactions first.",
            "data": [],
            "count": 0
        }

    # Convert to simplified payment format
    payments = []
    for t in transactions[:count]:
        payments.append({
            "id": f"PAY-{t['paypal_transaction_id']}",
            "transaction_id": t["transaction_id"],
            "intent": "sale",
            "state": "completed" if t["transaction_status"] == "COMPLETED" else "pending",
            "create_time": t["transaction_initiation_date"],
            "total_amount": t["transaction_amount"]["value"],
            "currency": t["transaction_amount"]["currency_code"],
            "payment_method": "paypal"
        })

    return {
        "status": "success",
        "msg": "Payments retrieved successfully",
        "data": payments,
        "count": len(payments)
    }

@router.get("/v1/reporting/balances", response_model=StandardResponse)
async def get_balances():
    """Get account balances"""
    return {
        "status": "success",
        "msg": "Balances retrieved successfully",
        "data": {
            "balances": [
                {
                    "currency": "USD",
                    "primary": True,
                    "total_balance": {
                        "currency_code": "USD",
                        "value": str(round(random.uniform(10000, 50000), 2))
                    },
                    "available_balance": {
                        "currency_code": "USD",
                        "value": str(round(random.uniform(8000, 45000), 2))
                    },
                    "withheld_balance": {
                        "currency_code": "USD",
                        "value": str(round(random.uniform(0, 5000), 2))
                    }
                }
            ],
            "as_of_time": datetime.now().isoformat() + "Z"
        }
    }

# Generation Sub-Endpoints
@router.post("/generate/transactions", response_model=StandardResponse)
@router.get("/generate/transactions", response_model=StandardResponse)
async def generate_transactions_endpoint(
    background_tasks: BackgroundTasks,
    count: int = Query(300, ge=10, le=1000, description="Number of transactions to generate")
):
    """Generate PayPal transactions"""
    try:
        if generation_status["transactions"]["completed"]:
            return {
                "status": "warning",
                "msg": "Transactions already generated. Delete existing data to regenerate.",
                "data": {"count": generation_status["transactions"]["generated"]},
                "count": generation_status["transactions"]["generated"]
            }

        if generation_status["is_generating"]:
            return {
                "status": "warning",
                "msg": "Transaction generation already in progress",
                "data": {"current": generation_status["transactions"]["generated"]}
            }

        def generate():
            generation_status["is_generating"] = True
            try:
                generate_all_transactions(count)
            finally:
                generation_status["is_generating"] = False

        background_tasks.add_task(generate)

        return {
            "status": "success",
            "msg": f"PayPal transaction generation started for {count} transactions",
            "data": {
                "target": count,
                "estimated_time": "< 1 minute"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Failed to generate transactions: {str(e)}",
            "data": None
        }

@router.get("/generate/status", response_model=StandardResponse)
async def get_generation_status():
    """Get generation status"""
    return {
        "status": "success",
        "msg": "Generation status retrieved",
        "data": {
            "transactions": generation_status["transactions"],
            "is_generating": generation_status["is_generating"]
        }
    }

@router.post("/generate/all", response_model=StandardResponse)
@router.get("/generate/all", response_model=StandardResponse)
async def generate_all_data(
    background_tasks: BackgroundTasks,
    count: int = Query(300, ge=10, le=1000)
):
    """Generate all PayPal data"""
    return await generate_transactions_endpoint(background_tasks, count)
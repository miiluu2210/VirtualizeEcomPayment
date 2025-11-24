"""
ZaloPay Payment API Router
Vietnamese e-wallet payment gateway - Simulates real ZaloPay API responses
Based on ZaloPay Payment API documentation
"""

from fastapi import APIRouter, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime, timedelta
import random
import hashlib
import hmac
import uuid
from pathlib import Path
import gzip
import json

from shared.data_generator import (
    get_random_customer, generate_transaction_id,
    get_private_data_path, fake_vi, fake_en
)

router = APIRouter()

# Configuration
TRANSACTIONS_DIR = get_private_data_path("zalopay", "")
TRANSACTIONS_DIR.mkdir(exist_ok=True)

generation_status = {
    "transactions": {"generated": 0, "target": 500, "completed": False},
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

def generate_zalopay_app_trans_id():
    """Generate ZaloPay app transaction ID (format: YYMMDD_XXXXXX)"""
    return f"{datetime.now().strftime('%y%m%d')}_{random.randint(100000, 999999)}"

def generate_zalopay_zp_trans_id():
    """Generate ZaloPay transaction ID"""
    return random.randint(200000000000000, 299999999999999)

def generate_transactions_batch(count):
    """Generate ZaloPay transactions with realistic structure"""
    transactions = []

    # ZaloPay return codes
    return_codes = [
        (1, "Thanh cong"),
        (1, "Thanh cong"),
        (1, "Thanh cong"),
        (1, "Thanh cong"),
        (1, "Thanh cong"),
        (2, "That bai"),
        (3, "Dang xu ly"),
        (-49, "Request khong hop le"),
        (-54, "Giao dich khong ton tai"),
    ]

    # Sub return codes for successful transactions
    sub_return_codes = [
        (1, "Merchant balance updated"),
        (2, "Merchant balance not changed")
    ]

    # Payment channels
    channels = [
        38,   # ZaloPay Wallet
        36,   # Vietcombank
        37,   # ACB
        39,   # Visa/Master
        40,   # ATM
        41,   # Domestic card
    ]

    for i in range(count):
        customer = get_random_customer()
        transaction_id = generate_transaction_id()
        return_code, return_message = random.choice(return_codes)

        amount = random.choice([
            random.randint(10000, 100000),
            random.randint(100000, 500000),
            random.randint(500000, 2000000),
            random.randint(2000000, 10000000),
        ])
        amount = round(amount / 1000) * 1000

        app_trans_id = generate_zalopay_app_trans_id()
        zp_trans_id = generate_zalopay_zp_trans_id()

        server_time = datetime.now() - timedelta(
            days=random.randint(0, 90),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        # Determine is_processing based on return_code
        is_processing = return_code == 3

        sub_code, sub_message = random.choice(sub_return_codes) if return_code == 1 else (0, "")

        # Generate ZaloPay response structure (based on real API)
        transaction = {
            # Internal tracking
            "transaction_id": transaction_id,
            "customer_id": customer["id"],
            "source": "zalopay",

            # ZaloPay API Response fields (Query Order API)
            "return_code": return_code,
            "return_message": return_message,
            "sub_return_code": sub_code,
            "sub_return_message": sub_message,
            "is_processing": is_processing,
            "amount": amount,
            "discount_amount": int(amount * random.uniform(0, 0.1)) if random.random() > 0.8 else 0,

            # Transaction IDs
            "zp_trans_id": zp_trans_id,
            "app_trans_id": app_trans_id,
            "app_id": 2553,  # TechStore app ID
            "app_user": f"user_{customer['id']}",
            "app_time": int(server_time.timestamp() * 1000),
            "server_time": int(server_time.timestamp() * 1000),
            "server_time_iso": server_time.isoformat(),

            # Transaction details
            "embed_data": json.dumps({
                "preferred_payment_method": [],
                "redirecturl": "https://techstore.vn/payment/callback",
                "columninfo": {
                    "store_id": f"TS{random.randint(1, 50):03d}",
                    "customer_name": fake_vi.name()
                }
            }),
            "item": json.dumps([
                {
                    "itemid": f"PROD{random.randint(1, 1000):04d}",
                    "itemname": f"San pham {random.randint(1, 100)}",
                    "itemprice": amount,
                    "itemquantity": 1
                }
            ]),
            "description": f"Thanh toan don hang TechStore #{app_trans_id}",

            # Payment info
            "channel": random.choice(channels) if return_code == 1 else 0,
            "pmcid": random.choice(channels) if return_code == 1 else 0,
            "bank_code": random.choice(["VCB", "ACB", "TCB", "VPB", "MB", "BIDV", ""]),

            # Merchant info
            "merchant_user_id": f"merchant_{random.randint(1000, 9999)}",

            # Callback URL
            "callback_url": "https://techstore.vn/api/zalopay/callback",

            # Signature (mock)
            "mac": hashlib.sha256(f"{zp_trans_id}|{app_trans_id}|{amount}".encode()).hexdigest(),

            # Order URL (for redirect payment)
            "order_url": f"https://sbgateway.zalopay.vn/pay?order_token={uuid.uuid4().hex}" if return_code == 1 else None,

            # Refund history
            "refund_history": [] if random.random() > 0.1 else [{
                "refund_id": random.randint(100000000, 999999999),
                "mrefund_id": f"RF_{app_trans_id}",
                "amount": int(amount * 0.5) if random.random() > 0.5 else amount,
                "status": 1,
                "description": "Hoan tien don hang",
                "refund_time": int((server_time + timedelta(days=random.randint(1, 7))).timestamp() * 1000)
            }]
        }
        transactions.append(transaction)

    return transactions

def generate_all_transactions(count=500, mode="replace"):
    """Generate ZaloPay transactions"""
    print(f"Starting ZaloPay transaction generation: {count:,} transactions (mode: {mode})")

    new_transactions = generate_transactions_batch(count)
    batch_file = TRANSACTIONS_DIR / "transactions.json.gz"

    if mode == "append":
        existing = load_compressed(batch_file)
        if existing:
            all_transactions = existing + new_transactions
            print(f"Appending {count} new transactions to {len(existing)} existing")
        else:
            all_transactions = new_transactions
    else:
        all_transactions = new_transactions

    save_compressed(all_transactions, batch_file)

    generation_status["transactions"]["generated"] = len(all_transactions)
    generation_status["transactions"]["target"] = len(all_transactions)
    generation_status["transactions"]["completed"] = True
    print(f"ZaloPay transaction generation completed! Total: {len(all_transactions)}")

    return all_transactions

# API Endpoints - Following ZaloPay API structure
@router.get("/", response_model=StandardResponse)
async def zalopay_info():
    """ZaloPay Payment API information"""
    return {
        "status": "success",
        "msg": "ZaloPay Payment Gateway API",
        "data": {
            "service": "ZaloPay Payment Gateway API",
            "market": "Vietnam - E-wallet & Banking Payments",
            "transactions": f"{generation_status['transactions']['generated']:,} / {generation_status['transactions']['target']:,}",
            "endpoints": [
                "/zalopay/v2/query - Query order status",
                "/zalopay/v2/refund - Process refund",
                "/zalopay/v2/transactions - List transactions",
                "/zalopay/generate/*"
            ],
            "documentation": "https://docs.zalopay.vn/v2/"
        }
    }

@router.post("/v2/query", response_model=StandardResponse)
@router.get("/v2/query", response_model=StandardResponse)
async def query_order(
    app_trans_id: str = Query(None, description="App transaction ID (YYMMDD_XXXXXX)"),
    zp_trans_id: int = Query(None, description="ZaloPay transaction ID")
):
    """
    Query order status - ZaloPay API compatible

    This endpoint simulates ZaloPay's order query API.
    Returns order details in ZaloPay response format.
    """
    batch_file = TRANSACTIONS_DIR / "transactions.json.gz"
    transactions = load_compressed(batch_file)

    if not transactions:
        return {
            "status": "error",
            "msg": "No transactions data. Generate via /zalopay/generate/transactions",
            "data": {
                "return_code": -54,
                "return_message": "Giao dich khong ton tai"
            }
        }

    # Search by app_trans_id or zp_trans_id
    found = None
    for t in transactions:
        if app_trans_id and t.get("app_trans_id") == app_trans_id:
            found = t
            break
        if zp_trans_id and t.get("zp_trans_id") == zp_trans_id:
            found = t
            break

    if not found:
        return {
            "status": "error",
            "msg": "Transaction not found",
            "data": {
                "return_code": -54,
                "return_message": "Giao dich khong ton tai",
                "sub_return_code": 0,
                "sub_return_message": ""
            }
        }

    # Return ZaloPay-style response
    return {
        "status": "success",
        "msg": "Query successful",
        "data": {
            "return_code": found["return_code"],
            "return_message": found["return_message"],
            "sub_return_code": found.get("sub_return_code", 0),
            "sub_return_message": found.get("sub_return_message", ""),
            "is_processing": found.get("is_processing", False),
            "amount": found["amount"],
            "discount_amount": found.get("discount_amount", 0),
            "zp_trans_id": found["zp_trans_id"]
        }
    }

@router.get("/v2/transactions", response_model=StandardResponse)
async def get_transactions(
    limit: int = Query(50, ge=1, le=500),
    status: int = Query(None, description="Filter by return_code (1=success, 2=failed, 3=processing)"),
    start_date: str = Query(None, description="Start date (ISO format)"),
    end_date: str = Query(None, description="End date (ISO format)"),
    min_amount: int = Query(None, description="Minimum amount in VND"),
    max_amount: int = Query(None, description="Maximum amount in VND"),
    channel: int = Query(None, description="Payment channel (38=ZaloPay, 36=VCB, etc)")
):
    """Get ZaloPay transactions with filters"""
    batch_file = TRANSACTIONS_DIR / "transactions.json.gz"
    transactions = load_compressed(batch_file)

    if not transactions:
        return {
            "status": "error",
            "msg": "No transactions data. Generate via /zalopay/generate/transactions",
            "data": [],
            "count": 0
        }

    # Apply filters
    filtered = transactions

    if status is not None:
        filtered = [t for t in filtered if t.get("return_code") == status]

    if start_date:
        filtered = [t for t in filtered if t.get("server_time_iso", "") >= start_date]

    if end_date:
        filtered = [t for t in filtered if t.get("server_time_iso", "") <= end_date]

    if min_amount:
        filtered = [t for t in filtered if t.get("amount", 0) >= min_amount]

    if max_amount:
        filtered = [t for t in filtered if t.get("amount", 0) <= max_amount]

    if channel:
        filtered = [t for t in filtered if t.get("channel") == channel]

    # Sort by server_time descending
    filtered.sort(key=lambda x: x.get("server_time", 0), reverse=True)
    result = filtered[:limit]

    return {
        "status": "success",
        "msg": "Transactions retrieved successfully",
        "data": result,
        "count": len(result),
        "total": len(filtered)
    }

@router.get("/v2/statistics", response_model=StandardResponse)
async def get_statistics():
    """Get ZaloPay transaction statistics"""
    batch_file = TRANSACTIONS_DIR / "transactions.json.gz"
    transactions = load_compressed(batch_file)

    if not transactions:
        return {
            "status": "error",
            "msg": "No transactions data",
            "data": None
        }

    # Calculate statistics
    successful = [t for t in transactions if t.get("return_code") == 1]
    failed = [t for t in transactions if t.get("return_code") == 2]
    processing = [t for t in transactions if t.get("return_code") == 3]

    total_amount = sum(t.get("amount", 0) for t in successful)
    total_discount = sum(t.get("discount_amount", 0) for t in successful)
    avg_amount = total_amount / len(successful) if successful else 0

    # Group by channel
    channel_names = {
        38: "ZaloPay Wallet",
        36: "Vietcombank",
        37: "ACB",
        39: "Visa/Master",
        40: "ATM",
        41: "Domestic Card"
    }

    channel_stats = {}
    for t in successful:
        channel = t.get("channel", 0)
        channel_name = channel_names.get(channel, f"Channel {channel}")
        if channel_name not in channel_stats:
            channel_stats[channel_name] = {"count": 0, "total": 0}
        channel_stats[channel_name]["count"] += 1
        channel_stats[channel_name]["total"] += t.get("amount", 0)

    # Group by bank
    bank_stats = {}
    for t in successful:
        bank = t.get("bank_code", "Unknown") or "ZaloPay"
        if bank not in bank_stats:
            bank_stats[bank] = {"count": 0, "total": 0}
        bank_stats[bank]["count"] += 1
        bank_stats[bank]["total"] += t.get("amount", 0)

    return {
        "status": "success",
        "msg": "Statistics retrieved successfully",
        "data": {
            "total_transactions": len(transactions),
            "successful": len(successful),
            "failed": len(failed),
            "processing": len(processing),
            "total_amount_vnd": total_amount,
            "total_discount_vnd": total_discount,
            "net_amount_vnd": total_amount - total_discount,
            "average_amount_vnd": int(avg_amount),
            "success_rate": round(len(successful) / len(transactions) * 100, 2) if transactions else 0,
            "by_channel": channel_stats,
            "by_bank": bank_stats
        }
    }

# Generation Endpoints
@router.post("/generate/transactions", response_model=StandardResponse)
@router.get("/generate/transactions", response_model=StandardResponse)
async def generate_transactions_endpoint(
    background_tasks: BackgroundTasks,
    count: int = Query(500, ge=10, le=5000, description="Number of transactions to generate"),
    method: Optional[str] = Query(None, description="'new' to append, None to keep existing")
):
    """Generate ZaloPay transactions"""
    try:
        batch_file = TRANSACTIONS_DIR / "transactions.json.gz"
        existing = load_compressed(batch_file)

        if existing and method != "new":
            return {
                "status": "warning",
                "msg": "Transactions exist. Use 'method=new' to append new data.",
                "data": {"count": len(existing)},
                "count": len(existing)
            }

        if generation_status["is_generating"]:
            return {
                "status": "warning",
                "msg": "Generation in progress",
                "data": {"current": generation_status["transactions"]["generated"]}
            }

        def generate():
            generation_status["is_generating"] = True
            try:
                mode = "append" if method == "new" else "replace"
                generate_all_transactions(count, mode)
            finally:
                generation_status["is_generating"] = False

        background_tasks.add_task(generate)

        return {
            "status": "success",
            "msg": f"ZaloPay transaction generation started ({count} transactions)",
            "data": {
                "target": count,
                "mode": "append" if method == "new" else "replace"
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
        "msg": "Generation status",
        "data": generation_status
    }

@router.post("/generate/all", response_model=StandardResponse)
@router.get("/generate/all", response_model=StandardResponse)
async def generate_all_data(
    background_tasks: BackgroundTasks,
    count: int = Query(500, ge=10, le=5000)
):
    """Generate all ZaloPay data"""
    return await generate_transactions_endpoint(background_tasks, count)

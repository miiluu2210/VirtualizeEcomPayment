"""
MoMo Payment API Router
Vietnamese e-wallet payment gateway - Simulates real MoMo API responses
Based on MoMo Payment API documentation
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
TRANSACTIONS_DIR = get_private_data_path("momo", "")
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

def generate_momo_request_id():
    """Generate MoMo request ID"""
    return f"MOMO{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100000, 999999)}"

def generate_momo_order_id():
    """Generate MoMo order ID"""
    return f"ORD{datetime.now().strftime('%Y%m%d')}{random.randint(10000000, 99999999)}"

def generate_momo_trans_id():
    """Generate MoMo transaction ID (similar to real MoMo)"""
    return random.randint(2000000000000, 2999999999999)

def generate_transactions_batch(count):
    """Generate MoMo transactions with realistic structure"""
    transactions = []

    # MoMo result codes
    result_codes = [
        (0, "Thanh cong"),
        (0, "Thanh cong"),
        (0, "Thanh cong"),
        (0, "Thanh cong"),
        (0, "Thanh cong"),
        (9000, "Giao dich da duoc xu ly"),
        (10, "He thong dang bao tri"),
        (11, "Truy cap bi tu choi"),
        (12, "Phien ban API khong duoc ho tro"),
        (99, "Loi khong xac dinh")
    ]

    # Payment types
    pay_types = ["qr", "webApp", "credit", "napas"]

    for i in range(count):
        customer = get_random_customer()
        transaction_id = generate_transaction_id()
        result_code, message = random.choice(result_codes)

        amount = random.choice([
            random.randint(10000, 100000),      # Small transactions
            random.randint(100000, 500000),     # Medium transactions
            random.randint(500000, 2000000),    # Large transactions
            random.randint(2000000, 10000000),  # Very large transactions
        ])
        # Round to 1000 VND
        amount = round(amount / 1000) * 1000

        trans_id = generate_momo_trans_id()
        order_id = generate_momo_order_id()
        request_id = generate_momo_request_id()

        response_time = datetime.now() - timedelta(
            days=random.randint(0, 90),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        # Generate MoMo response structure (based on real API)
        transaction = {
            # Internal tracking
            "transaction_id": transaction_id,
            "customer_id": customer["id"],
            "source": "momo",

            # MoMo API Response fields
            "partnerCode": "TECHSTOREVN",
            "orderId": order_id,
            "requestId": request_id,
            "amount": amount,
            "orderInfo": f"Thanh toan don hang TechStore #{order_id}",
            "orderType": "momo_wallet",
            "transId": trans_id,
            "resultCode": result_code,
            "message": message,
            "payType": random.choice(pay_types),
            "responseTime": int(response_time.timestamp() * 1000),
            "responseTimeISO": response_time.isoformat(),

            # Extra info (as in real MoMo response)
            "extraData": {
                "store_id": f"TS{random.randint(1, 50):03d}",
                "customer_phone": fake_vi.phone_number(),
                "customer_name": fake_vi.name()
            },

            # Signature (mock)
            "signature": hashlib.sha256(f"{trans_id}{order_id}{amount}".encode()).hexdigest(),

            # Payment URL (for QR/Web payments)
            "payUrl": f"https://test-payment.momo.vn/v2/gateway/pay?token={uuid.uuid4().hex}" if result_code == 0 else None,
            "qrCodeUrl": f"https://test-payment.momo.vn/v2/gateway/qr/{uuid.uuid4().hex}" if result_code == 0 and random.random() > 0.5 else None,

            # Refund info (if applicable)
            "refundTrans": [] if random.random() > 0.1 else [{
                "orderId": f"RF{order_id}",
                "amount": int(amount * 0.5) if random.random() > 0.5 else amount,
                "resultCode": 0,
                "transId": generate_momo_trans_id(),
                "createdTime": int((response_time + timedelta(days=random.randint(1, 7))).timestamp() * 1000)
            }],

            # Promotion info
            "promotionInfo": [{
                "promoCode": f"TECH{random.randint(10, 99)}",
                "promoAmount": int(amount * random.uniform(0.05, 0.15)) if random.random() > 0.7 else 0,
                "promoDescription": "Khuyen mai TechStore"
            }] if random.random() > 0.8 else []
        }
        transactions.append(transaction)

    return transactions

def generate_all_transactions(count=500, mode="replace"):
    """Generate MoMo transactions"""
    print(f"Starting MoMo transaction generation: {count:,} transactions (mode: {mode})")

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
    print(f"MoMo transaction generation completed! Total: {len(all_transactions)}")

    return all_transactions

# API Endpoints - Following MoMo API structure
@router.get("/", response_model=StandardResponse)
async def momo_info():
    """MoMo Payment API information"""
    return {
        "status": "success",
        "msg": "MoMo Payment Gateway API",
        "data": {
            "service": "MoMo Payment Gateway API",
            "market": "Vietnam - E-wallet Payments",
            "transactions": f"{generation_status['transactions']['generated']:,} / {generation_status['transactions']['target']:,}",
            "endpoints": [
                "/momo/v2/gateway/api/query - Query transaction status",
                "/momo/v2/gateway/api/refund - Process refund",
                "/momo/v2/transactions - List all transactions",
                "/momo/generate/*"
            ],
            "documentation": "https://developers.momo.vn/v3/docs/payment/api/"
        }
    }

@router.post("/v2/gateway/api/query", response_model=StandardResponse)
@router.get("/v2/gateway/api/query", response_model=StandardResponse)
async def query_transaction(
    orderId: str = Query(None, description="Order ID to query"),
    requestId: str = Query(None, description="Request ID to query")
):
    """
    Query transaction status - MoMo API compatible

    This endpoint simulates MoMo's transaction query API.
    Returns transaction details in MoMo response format.
    """
    batch_file = TRANSACTIONS_DIR / "transactions.json.gz"
    transactions = load_compressed(batch_file)

    if not transactions:
        return {
            "status": "error",
            "msg": "No transactions data. Generate via /momo/generate/transactions",
            "data": {
                "resultCode": 99,
                "message": "Khong tim thay giao dich"
            }
        }

    # Search by orderId or requestId
    found = None
    for t in transactions:
        if orderId and t.get("orderId") == orderId:
            found = t
            break
        if requestId and t.get("requestId") == requestId:
            found = t
            break

    if not found:
        return {
            "status": "error",
            "msg": "Transaction not found",
            "data": {
                "partnerCode": "TECHSTOREVN",
                "orderId": orderId or "",
                "requestId": requestId or "",
                "resultCode": 99,
                "message": "Khong tim thay giao dich"
            }
        }

    # Return MoMo-style response
    return {
        "status": "success",
        "msg": "Query successful",
        "data": {
            "partnerCode": found["partnerCode"],
            "orderId": found["orderId"],
            "requestId": found["requestId"],
            "extraData": found.get("extraData", {}),
            "amount": found["amount"],
            "transId": found["transId"],
            "payType": found["payType"],
            "resultCode": found["resultCode"],
            "refundTrans": found.get("refundTrans", []),
            "message": found["message"],
            "responseTime": found["responseTime"],
            "promotionInfo": found.get("promotionInfo", [])
        }
    }

@router.get("/v2/transactions", response_model=StandardResponse)
async def get_transactions(
    limit: int = Query(50, ge=1, le=500),
    status: int = Query(None, description="Filter by result code (0=success)"),
    start_date: str = Query(None, description="Start date (ISO format)"),
    end_date: str = Query(None, description="End date (ISO format)"),
    min_amount: int = Query(None, description="Minimum amount in VND"),
    max_amount: int = Query(None, description="Maximum amount in VND")
):
    """Get MoMo transactions with filters"""
    batch_file = TRANSACTIONS_DIR / "transactions.json.gz"
    transactions = load_compressed(batch_file)

    if not transactions:
        return {
            "status": "error",
            "msg": "No transactions data. Generate via /momo/generate/transactions",
            "data": [],
            "count": 0
        }

    # Apply filters
    filtered = transactions

    if status is not None:
        filtered = [t for t in filtered if t.get("resultCode") == status]

    if start_date:
        filtered = [t for t in filtered if t.get("responseTimeISO", "") >= start_date]

    if end_date:
        filtered = [t for t in filtered if t.get("responseTimeISO", "") <= end_date]

    if min_amount:
        filtered = [t for t in filtered if t.get("amount", 0) >= min_amount]

    if max_amount:
        filtered = [t for t in filtered if t.get("amount", 0) <= max_amount]

    # Sort by response time descending
    filtered.sort(key=lambda x: x.get("responseTime", 0), reverse=True)
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
    """Get MoMo transaction statistics"""
    batch_file = TRANSACTIONS_DIR / "transactions.json.gz"
    transactions = load_compressed(batch_file)

    if not transactions:
        return {
            "status": "error",
            "msg": "No transactions data",
            "data": None
        }

    # Calculate statistics
    successful = [t for t in transactions if t.get("resultCode") == 0]
    total_amount = sum(t.get("amount", 0) for t in successful)
    avg_amount = total_amount / len(successful) if successful else 0

    # Group by pay type
    pay_type_stats = {}
    for t in successful:
        pay_type = t.get("payType", "unknown")
        if pay_type not in pay_type_stats:
            pay_type_stats[pay_type] = {"count": 0, "total": 0}
        pay_type_stats[pay_type]["count"] += 1
        pay_type_stats[pay_type]["total"] += t.get("amount", 0)

    return {
        "status": "success",
        "msg": "Statistics retrieved successfully",
        "data": {
            "total_transactions": len(transactions),
            "successful_transactions": len(successful),
            "failed_transactions": len(transactions) - len(successful),
            "total_amount_vnd": total_amount,
            "average_amount_vnd": int(avg_amount),
            "success_rate": round(len(successful) / len(transactions) * 100, 2) if transactions else 0,
            "by_pay_type": pay_type_stats
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
    """Generate MoMo transactions"""
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
            "msg": f"MoMo transaction generation started ({count} transactions)",
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
    """Generate all MoMo data"""
    return await generate_transactions_endpoint(background_tasks, count)

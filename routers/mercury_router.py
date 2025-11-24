"""
Mercury Bank API Router
Business banking for e-commerce transactions
"""

from fastapi import APIRouter, Query, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime, timedelta
import random
from pathlib import Path
import gzip
import json
import uuid
from shared.data_generator import generate_transaction_id, PRIVATE_DIRS, fake_vi, fake_en

router = APIRouter()

# Configuration
TRANSACTIONS_DIR = PRIVATE_DIRS["mercury"] #DATA_DIR / "mercury_transactions"
TRANSACTIONS_DIR.mkdir(exist_ok=True)

ACCOUNTS = []

generation_status = {
    "accounts": {"generated": 0, "target": 3, "completed": False},
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

def generate_accounts(count=10):
    """Generate Mercury bank accounts"""
    global ACCOUNTS
    accounts = []

    account_names = [
        "TechStore Vietnam Operating",
        "TechStore Vietnam Payroll",
        "TechStore Vietnam Savings"
    ]

    for i in range(min(count, len(account_names))):
        account = {
            "id": str(uuid.uuid4()),
            "name": account_names[i] if i < len(account_names) else f"TechStore Account {i+1}",
            "accountNumber": f"{random.randint(1000000000, 9999999999)}",
            "routingNumber": f"{random.randint(100000000, 999999999)}",
            "type": random.choice(["checking", "savings"]),
            "status": "active",
            "currentBalance": round(random.uniform(50000, 500000), 2),
            "availableBalance": round(random.uniform(45000, 450000), 2),
            "currency": "USD",
            "createdAt": (datetime.now() - timedelta(days=random.randint(365, 1095))).isoformat() + "Z",
            "legalBusinessName": "TechStore Vietnam Co., Ltd",
            "canReceiveTransactions": True,
            "canSendDomesticWires": True,
            "canSendInternationalWires": True,
            "limits": {
                "dailyWireLimit": 100000,
                "dailyAchLimit": 50000,
                "monthlyWireLimit": 2000000
            }
        }
        accounts.append(account)

    ACCOUNTS = accounts
    generation_status["accounts"]["generated"] = len(accounts)
    generation_status["accounts"]["target"] = count
    generation_status["accounts"]["completed"] = True

    save_compressed(accounts, TRANSACTIONS_DIR / "accounts.json.gz")
    return accounts

def generate_transactions_batch(count, accounts):
    """Generate Mercury bank transactions"""
    transactions = []

    transaction_types = [
        "debitCardPurchase", "incomingDomesticWire", "outgoingDomesticWire",
        "incomingAch", "outgoingAch", "fee", "internalTransfer"
    ]

    statuses = ["pending", "posted", "cancelled", "failed"]

    for i in range(count):
        account = random.choice(accounts)
        tx_type = random.choice(transaction_types)

        is_credit = tx_type in ["incomingDomesticWire", "incomingAch"]

        if tx_type == "fee":
            amount = round(random.uniform(1, 50), 2)
            is_credit = False
        elif tx_type == "debitCardPurchase":
            amount = round(random.uniform(10, 500), 2)
            is_credit = False
        else:
            amount = round(random.uniform(100, 50000), 2)

        transaction_id = generate_transaction_id()

        details = {}

        if tx_type in ["incomingDomesticWire", "outgoingDomesticWire"]:
            is_vietnamese = random.random() < 0.95
            if is_vietnamese:
                counterparty_name = f"{fake_vi.last_name()} {fake_vi.first_name()}"
            else:
                counterparty_name = fake_en.name()

            details = {
                "counterpartyName": counterparty_name,
                "counterpartyRoutingNumber": f"{random.randint(100000000, 999999999)}",
                "counterpartyAccountNumber": f"****{random.randint(1000, 9999)}",
                "wireReference": f"WIRE-{transaction_id}"
            }

        elif tx_type in ["incomingAch", "outgoingAch"]:
            details = {
                "counterpartyName": "PayPal Inc" if random.random() > 0.5 else "Shopify Payments",
                "achType": random.choice(["CCD", "PPD", "WEB"]),
                "traceNumber": f"{random.randint(10000000000000, 99999999999999)}"
            }

        elif tx_type == "debitCardPurchase":
            details = {
                "merchantName": random.choice([
                    "AWS Services", "Google Cloud", "Microsoft Azure",
                    "Office Supplies", "Tech Vendor"
                ]),
                "merchantCategory": "Business Services",
                "cardLast4": str(random.randint(1000, 9999))
            }

        elif tx_type == "fee":
            details = {
                "feeType": random.choice(["wire_fee", "account_fee", "service_fee"]),
                "description": "Banking service fee"
            }

        transaction = {
            "id": str(uuid.uuid4()),
            "transaction_id": transaction_id,
            "accountId": account["id"],
            "amount": amount if is_credit else -amount,
            "amount_usd": amount,
            "amount_vnd": int(amount * 24000),
            "bankDescription": f"{tx_type.replace('_', ' ').title()} - TechStore Vietnam",
            "createdAt": (datetime.now() - timedelta(days=random.randint(0, 90))).isoformat() + "Z",
            "postedAt": (datetime.now() - timedelta(days=random.randint(0, 90))).isoformat() + "Z" if random.random() > 0.1 else None,
            "status": random.choice(statuses) if random.random() > 0.8 else "posted",
            "kind": tx_type,
            "note": "Technology retail business transaction" if random.random() > 0.8 else None,
            "details": details,
            "source": "mercury_bank"
        }
        transactions.append(transaction)

    return transactions

def generate_all_transactions(count=1000000):
    """Generate all Mercury transactions"""
    print(f"🏦 Starting Mercury Bank transaction generation: {count:,} transactions")

    if not ACCOUNTS:
        generate_accounts(3)

    transactions = generate_transactions_batch(count, ACCOUNTS)

    batch_file = TRANSACTIONS_DIR / "transactions.json.gz"
    save_compressed(transactions, batch_file)

    generation_status["transactions"]["generated"] = count
    generation_status["transactions"]["target"] = count
    generation_status["transactions"]["completed"] = True
    print(f"✅ Mercury Bank transaction generation completed!")

    return transactions

# API Endpoints
@router.get("/", response_model=StandardResponse)
async def mercury_info():
    """Mercury Bank API information"""
    return {
        "status": "success",
        "msg": "Mercury Bank API",
        "data": {
            "service": "Mercury Bank API",
            "market": "Vietnam Technology Retail - Business Banking",
            "accounts": len(ACCOUNTS),
            "transactions": f"{generation_status['transactions']['generated']:,} / {generation_status['transactions']['target']:,}",
            "endpoints": [
                "/mercury/api/v1/accounts",
                "/mercury/api/v1/account/{accountId}",
                "/mercury/api/v1/account/{accountId}/transactions",
                "/mercury/api/v1/transactions",
                "/mercury/generate/*"
            ]
        }
    }

@router.get("/api/v1/accounts", response_model=StandardResponse)
async def get_accounts():
    """Get all bank accounts"""
    global ACCOUNTS

    if not ACCOUNTS:
        # Try to load from file
        accounts_file = TRANSACTIONS_DIR / "accounts.json.gz"
        if accounts_file.exists():
            ACCOUNTS = load_compressed(accounts_file)
        else:
            return {
                "status": "warning",
                "msg": "Accounts not generated yet. Please generate accounts first.",
                "data": [],
                "count": 0
            }

    return {
        "status": "success",
        "msg": "Accounts retrieved successfully",
        "data": ACCOUNTS,
        "count": len(ACCOUNTS)
    }

@router.get("/api/v1/account/{account_id}", response_model=StandardResponse)
async def get_account(account_id: str):
    """Get specific account by ID"""
    global ACCOUNTS

    if not ACCOUNTS:
        accounts_file = TRANSACTIONS_DIR / "accounts.json.gz"
        if accounts_file.exists():
            ACCOUNTS = load_compressed(accounts_file)

    if not ACCOUNTS:
        return {
            "status": "error",
            "msg": "Accounts not generated yet",
            "data": None
        }

    account = next((a for a in ACCOUNTS if a["id"] == account_id), None)
    if not account:
        return {
            "status": "error",
            "msg": f"Account {account_id} not found",
            "data": None
        }

    return {
        "status": "success",
        "msg": "Account retrieved successfully",
        "data": account
    }

@router.get("/api/v1/account/{account_id}/transactions", response_model=StandardResponse)
async def get_account_transactions(
    account_id: str,
    limit: int = Query(50, ge=1, le=500),
    status: str = Query(None),
    start: str = Query(None),
    end: str = Query(None)
):
    """Get transactions for specific account"""
    batch_file = TRANSACTIONS_DIR / "transactions.json.gz"
    transactions = load_compressed(batch_file)

    if not transactions:
        return {
            "status": "warning",
            "msg": "Transactions not generated yet. Please generate transactions first.",
            "data": [],
            "count": 0
        }

    # Filter by account
    filtered = [t for t in transactions if t["accountId"] == account_id]

    if status:
        filtered = [t for t in filtered if t["status"] == status]

    if start:
        filtered = [t for t in filtered if t["createdAt"] >= start]

    if end:
        filtered = [t for t in filtered if t["createdAt"] <= end]

    filtered.sort(key=lambda x: x["createdAt"], reverse=True)
    result = filtered[:limit]

    return {
        "status": "success",
        "msg": "Transactions retrieved successfully",
        "data": result,
        "count": len(result),
        "total": len(filtered)
    }

@router.get("/api/v1/transactions", response_model=StandardResponse)
async def get_all_transactions(
    limit: int = Query(50, ge=1, le=500),
    kind: str = Query(None)
):
    """Get all transactions"""
    batch_file = TRANSACTIONS_DIR / "transactions.json.gz"
    transactions = load_compressed(batch_file)

    if not transactions:
        return {
            "status": "warning",
            "msg": "Transactions not generated yet. Please generate transactions first.",
            "data": [],
            "count": 0
        }

    if kind:
        transactions = [t for t in transactions if t["kind"] == kind]

    transactions.sort(key=lambda x: x["createdAt"], reverse=True)
    result = transactions[:limit]

    return {
        "status": "success",
        "msg": "Transactions retrieved successfully",
        "data": result,
        "count": len(result),
        "total": len(transactions)
    }

@router.get("/api/v1/account/{account_id}/balance", response_model=StandardResponse)
async def get_account_balance(account_id: str):
    """Get account balance"""
    global ACCOUNTS

    if not ACCOUNTS:
        accounts_file = TRANSACTIONS_DIR / "accounts.json.gz"
        if accounts_file.exists():
            ACCOUNTS = load_compressed(accounts_file)

    if not ACCOUNTS:
        return {
            "status": "error",
            "msg": "Accounts not generated yet",
            "data": None
        }

    account = next((a for a in ACCOUNTS if a["id"] == account_id), None)
    if not account:
        return {
            "status": "error",
            "msg": f"Account {account_id} not found",
            "data": None
        }

    return {
        "status": "success",
        "msg": "Balance retrieved successfully",
        "data": {
            "accountId": account["id"],
            "currentBalance": account["currentBalance"],
            "availableBalance": account["availableBalance"],
            "currency": account["currency"],
            "asOf": datetime.now().isoformat() + "Z"
        }
    }

# Generation Sub-Endpoints
@router.post("/generate/accounts", response_model=StandardResponse)
@router.get("/generate/accounts", response_model=StandardResponse)
async def generate_accounts_endpoint(
    count: int = Query(3, ge=1, le=10, description="Number of accounts to generate")
):
    """Generate bank accounts"""
    global ACCOUNTS

    try:
        if generation_status["accounts"]["completed"]:
            return {
                "status": "warning",
                "msg": "Accounts already generated. Delete existing data to regenerate.",
                "data": {"count": len(ACCOUNTS)},
                "count": len(ACCOUNTS)
            }

        accounts = generate_accounts(count)
        ACCOUNTS = accounts

        return {
            "status": "success",
            "msg": f"Successfully generated {len(accounts)} bank accounts",
            "data": {
                "generated": len(accounts),
                "accounts": accounts
            },
            "count": len(accounts)
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Failed to generate accounts: {str(e)}",
            "data": None
        }

@router.post("/generate/transactions", response_model=StandardResponse)
@router.get("/generate/transactions", response_model=StandardResponse)
async def generate_transactions_endpoint(
    background_tasks: BackgroundTasks,
    count: int = Query(500, ge=10, le=5000, description="Number of transactions to generate")
):
    """Generate bank transactions"""
    try:
        if not ACCOUNTS:
            accounts_file = TRANSACTIONS_DIR / "accounts.json.gz"
            if not accounts_file.exists():
                return {
                    "status": "error",
                    "msg": "Accounts must be generated first before transactions",
                    "data": None
                }

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
            "msg": f"Mercury Bank transaction generation started for {count} transactions",
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
            "accounts": generation_status["accounts"],
            "transactions": generation_status["transactions"],
            "is_generating": generation_status["is_generating"]
        }
    }

@router.post("/generate/all", response_model=StandardResponse)
@router.get("/generate/all", response_model=StandardResponse)
async def generate_all_data(
    background_tasks: BackgroundTasks,
    account_count: int = Query(3, ge=1, le=10),
    transaction_count: int = Query(500, ge=10, le=5000)
):
    """Generate all Mercury data (accounts + transactions)"""
    try:
        def generate_all():
            if not generation_status["accounts"]["completed"]:
                generate_accounts(account_count)

            if not generation_status["transactions"]["completed"]:
                generation_status["is_generating"] = True
                try:
                    generate_all_transactions(transaction_count)
                finally:
                    generation_status["is_generating"] = False

        background_tasks.add_task(generate_all)

        return {
            "status": "success",
            "msg": "Mercury Bank full data generation started",
            "data": {
                "accounts": account_count,
                "transactions": transaction_count,
                "estimated_time": "< 2 minutes"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "msg": f"Failed to start generation: {str(e)}",
            "data": None
        }
"""
Unified Data Source API Simulator - Main Application
Technology Retail Store (GearVN-style) - Vietnam Market
All data sources on one FastAPI with separate routers
Port: 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="TechStore Vietnam - Unified API Simulator",
    version="3.0.0",
    description="""
    # 🛒 TechStore Vietnam - Multi-Source Data Simulator

    Simulates a complete e-commerce and retail technology store ecosystem similar to GearVN.
    All data sources share consistent metadata for realistic data pipeline development.

    ## 🏪 Business Context
    - **Market**: Vietnam technology retail (laptops, gaming gear, components)
    - **Channels**: Online (Shopify) + Offline stores (Sapo POS, Odoo POS)
    - **Customers**: 95% Vietnamese, 5% International
    - **Products**: Computer hardware, gaming peripherals, laptops, components

    ## 📊 Data Sources

    ### E-commerce & Online
    - **Shopify**: 6M orders, 2M customers (online store)
    - **PayPal**: Payment gateway transactions
    - **Mercury Bank**: Business banking transactions

    ### Offline Retail POS
    - **Sapo POS**: 1M orders from 50 Vietnam stores
    - **Odoo POS**: 800K orders from 30 international stores

    ## 🔗 Shared Metadata
    All generators share consistent:
    - Product catalog (ID, name, price, SKU)
    - Customer information
    - Transaction IDs and payment references
    - Order dates and timestamps

    ## 🌐 Language Support
    - Primary: Vietnamese (vi_VN)
    - Secondary: English for international customers

    ## 📈 Total Dataset
    - **7.8M+ Orders** across all channels
    - **2M+ Customers**
    - **1000+ Tech Products**
    - **80+ Store Locations**
    """,
    contact={
        "name": "TechStore Vietnam Data Engineering",
        "email": "dataeng@techstore.vn"
    },
    license_info={
        "name": "MIT License"
    }
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers after app is defined to avoid circular imports
from routers import shopify_router, paypal_router, mercury_router, sapo_router, odoo_router

# Include routers
app.include_router(shopify_router.router, prefix="/shopify", tags=["Shopify E-commerce"])
app.include_router(paypal_router.router, prefix="/paypal", tags=["PayPal Payments"])
app.include_router(mercury_router.router, prefix="/mercury", tags=["Mercury Banking"])
app.include_router(sapo_router.router, prefix="/sapo", tags=["Sapo POS Vietnam"])
app.include_router(odoo_router.router, prefix="/odoo", tags=["Odoo POS International"])


@app.on_event("startup")
async def startup_event():
    """Initialize shared data on startup"""
    print("🚀 Starting TechStore Vietnam API Simulator...")
    from shared.data_generator import initialize_shared_data
    await initialize_shared_data()
    print("✅ Shared data initialized")
    print("📡 API available at http://localhost:8000")
    print("📚 Documentation at http://localhost:8000/docs")


@app.get("/", tags=["Root"])
async def root():
    """
    ## Root Endpoint

    Returns API overview and available data sources.
    """
    return {
        "status": "success",
        "msg": "TechStore Vietnam - Unified API Simulator",
        "data": {
            "service": "TechStore Vietnam - Unified API Simulator",
            "version": "3.0.0",
            "market": "Vietnam Technology Retail",
            "documentation": "/docs",
            "data_sources": {
                "shopify": "/shopify/",
                "paypal": "/paypal/",
                "mercury": "/mercury/",
                "sapo": "/sapo/",
                "odoo": "/odoo/"
            },
            "endpoints": {
                "shopify": "/shopify/admin/api/2024-01/",
                "paypal": "/paypal/v1/",
                "mercury": "/mercury/api/v1/",
                "sapo": "/sapo/admin/",
                "odoo": "/odoo/api/"
            }
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "success",
        "msg": "Service is healthy",
        "data": {
            "service": "TechStore Vietnam API",
            "status": "healthy"
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
Shared Data Generator
Generates consistent product catalog, customers, and metadata
Used across all data source simulators

Updated structure:
- shared_data/share_data/ - Shared data across all routers (products, staff, customers, locations, shops)
- shared_data/private_data/{router_name}/ - Private data for each router
"""

from faker import Faker
from datetime import datetime, timedelta
import random
import uuid
from pathlib import Path
import json
import gzip
import asyncio

# Initialize Faker with Vietnamese locale
fake_vi = Faker('vi_VN')
fake_en = Faker('en_US')

# Shared data storage
SHARED_PRODUCTS = []
SHARED_CUSTOMERS = []
SHARED_STAFF = []
SHARED_LOCATIONS = []
SHARED_SHOPS = []
TRANSACTION_ID_COUNTER = 1000000

# Data directories - New structure
DATA_DIR = Path("./shared_data")
SHARE_DATA_DIR = DATA_DIR / "share_data"
PRIVATE_DATA_DIR = DATA_DIR / "private_data"

# Create directories
DATA_DIR.mkdir(exist_ok=True)
SHARE_DATA_DIR.mkdir(exist_ok=True)
PRIVATE_DATA_DIR.mkdir(exist_ok=True)

# Private data directories for each router
PRIVATE_DIRS = {
    "shopify": PRIVATE_DATA_DIR / "shopify",
    "sapo": PRIVATE_DATA_DIR / "sapo",
    "odoo": PRIVATE_DATA_DIR / "odoo",
    "paypal": PRIVATE_DATA_DIR / "paypal",
    "mercury": PRIVATE_DATA_DIR / "mercury",
    "momo": PRIVATE_DATA_DIR / "momo",
    "zalopay": PRIVATE_DATA_DIR / "zalopay",
    "cart_tracking": PRIVATE_DATA_DIR / "cart_tracking",
    "online_orders": PRIVATE_DATA_DIR / "online_orders"
}

# Create all private directories
for dir_path in PRIVATE_DIRS.values():
    dir_path.mkdir(exist_ok=True)

# Lock files to track generation status
GENERATION_STATUS = {
    "products": {"generated": False, "count": 0},
    "customers": {"generated": False, "count": 0},
    "staff": {"generated": False, "count": 0},
    "locations": {"generated": False, "count": 0},
    "shops": {"generated": False, "count": 0}
}

# Vietnamese technology product categories
TECH_CATEGORIES = {
    "Laptop": {
        "brands": ["ASUS", "MSI", "Acer", "Dell", "Lenovo", "HP", "Apple MacBook"],
        "models": ["Gaming", "Ultrabook", "Workstation", "Business", "Creator"],
        "price_range": (10_000_000, 50_000_000)  # VND
    },
    "PC/Máy tính": {
        "brands": ["Custom Build", "Pre-built Gaming"],
        "models": ["Gaming PC", "Workstation", "Office PC"],
        "price_range": (15_000_000, 100_000_000)
    },
    "Màn hình": {
        "brands": ["ASUS", "Samsung", "LG", "MSI", "AOC", "Dell"],
        "models": ["Gaming", "Professional", "4K", "Ultrawide"],
        "price_range": (2_000_000, 20_000_000)
    },
    "Bàn phím": {
        "brands": ["Logitech", "Corsair", "Razer", "SteelSeries", "Keychron", "Leopold"],
        "models": ["Mechanical", "Wireless", "Gaming", "TKL", "Full-size"],
        "price_range": (500_000, 5_000_000)
    },
    "Chuột": {
        "brands": ["Logitech", "Razer", "SteelSeries", "Corsair", "Asus ROG"],
        "models": ["Gaming", "Wireless", "Ergonomic", "Office"],
        "price_range": (300_000, 3_000_000)
    },
    "Tai nghe": {
        "brands": ["Sony", "Logitech", "HyperX", "SteelSeries", "Razer", "Audio-Technica"],
        "models": ["Gaming", "Wireless", "Studio", "True Wireless"],
        "price_range": (500_000, 8_000_000)
    },
    "Linh kiện PC": {
        "brands": ["Intel", "AMD", "NVIDIA", "Kingston", "Corsair", "Samsung"],
        "models": ["CPU", "GPU", "RAM", "SSD", "PSU", "Mainboard"],
        "price_range": (1_000_000, 30_000_000)
    },
    "Phụ kiện": {
        "brands": ["Generic", "Branded"],
        "models": ["Cable", "Adapter", "Hub", "Dock", "Stand", "Bag"],
        "price_range": (100_000, 2_000_000)
    }
}

_lock = asyncio.Lock()

def save_compressed(data, filepath):
    """Save data as compressed JSON"""
    with gzip.open(filepath, 'wt', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def load_compressed(filepath):
    """Load compressed JSON data"""
    if not filepath.exists():
        return None
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        return json.load(f)

def get_share_data_path(filename):
    """Get path for shared data file"""
    return SHARE_DATA_DIR / filename

def get_private_data_path(router_name, filename):
    """Get path for private data file"""
    if router_name in PRIVATE_DIRS:
        return PRIVATE_DIRS[router_name] / filename
    return PRIVATE_DATA_DIR / router_name / filename

def generate_product_name(category, brand, model):
    """Generate realistic Vietnamese product name"""
    names = {
        "Laptop": f"Laptop {brand} {model} {random.choice(['i5', 'i7', 'i9', 'Ryzen 5', 'Ryzen 7', 'M1', 'M2'])} {random.choice(['8GB', '16GB', '32GB'])} RAM",
        "PC/Máy tính": f"PC {model} {brand} {random.choice(['i5', 'i7', 'i9', 'Ryzen 5', 'Ryzen 7'])} | {random.choice(['RTX 3060', 'RTX 4060', 'RTX 4070'])}",
        "Màn hình": f"Màn hình {brand} {random.choice(['24', '27', '32', '34'])}inch {model} {random.choice(['Full HD', '2K', '4K'])} {random.choice(['60Hz', '144Hz', '165Hz', '240Hz'])}",
        "Bàn phím": f"Bàn phím {brand} {model} {random.choice(['Red Switch', 'Blue Switch', 'Brown Switch', 'Wireless', 'RGB'])}",
        "Chuột": f"Chuột {brand} {model} {random.choice(['Wireless', 'Wired', 'RGB', 'DPI cao'])}",
        "Tai nghe": f"Tai nghe {brand} {model} {random.choice(['Bluetooth', 'USB', 'Jack 3.5mm', 'Wireless'])}",
        "Linh kiện PC": f"{model} {brand} {random.choice(['Gen 12', 'Gen 13', 'AM5', 'DDR4', 'DDR5', 'PCIe 4.0'])}",
        "Phụ kiện": f"{model} {brand} cho {random.choice(['Laptop', 'PC', 'Gaming'])}"
    }
    return names.get(category, f"{brand} {model}")

# Helper functions to ensure data is loaded
async def ensure_products_loaded():
    """Ensure products are loaded into memory from file if available"""
    async with _lock:
        global SHARED_PRODUCTS

        if not SHARED_PRODUCTS or len(SHARED_PRODUCTS) == 0:
            # Try new location first
            products_file = get_share_data_path("products.json.gz")
            # Fallback to old location
            if not products_file.exists():
                products_file = DATA_DIR / "products.json.gz"

            if products_file.exists():
                SHARED_PRODUCTS = load_compressed(products_file)
        else:
            GENERATION_STATUS["products"]["generated"] = True
            GENERATION_STATUS["products"]["count"] = len(SHARED_PRODUCTS)


def ensure_staff_loaded():
    """Ensure staff are loaded into memory from file if available"""
    global SHARED_STAFF
    if not SHARED_STAFF:
        # Try new location first
        staff_file = get_share_data_path("staff.json.gz")
        # Fallback to old location
        if not staff_file.exists():
            staff_file = DATA_DIR / "staff.json.gz"

        if staff_file.exists():
            SHARED_STAFF = load_compressed(staff_file)
            if SHARED_STAFF:
                GENERATION_STATUS["staff"]["generated"] = True
                GENERATION_STATUS["staff"]["count"] = len(SHARED_STAFF)

def ensure_locations_loaded():
    """Ensure locations are loaded into memory from file if available"""
    global SHARED_LOCATIONS
    if not SHARED_LOCATIONS:
        # Try new location first
        locations_file = get_share_data_path("sapo_locations.json.gz")
        # Fallback to old location
        if not locations_file.exists():
            locations_file = DATA_DIR / "sapo_locations.json.gz"

        if locations_file.exists():
            SHARED_LOCATIONS = load_compressed(locations_file)
            if SHARED_LOCATIONS:
                GENERATION_STATUS["locations"]["generated"] = True
                GENERATION_STATUS["locations"]["count"] = len(SHARED_LOCATIONS)

def ensure_shops_loaded():
    """Ensure shops are loaded into memory from file if available"""
    global SHARED_SHOPS
    if not SHARED_SHOPS:
        # Try new location first
        shops_file = get_share_data_path("odoo_shops.json.gz")
        # Fallback to old location
        if not shops_file.exists():
            shops_file = DATA_DIR / "odoo_shops.json.gz"

        if shops_file.exists():
            SHARED_SHOPS = load_compressed(shops_file)
            if SHARED_SHOPS:
                GENERATION_STATUS["shops"]["generated"] = True
                GENERATION_STATUS["shops"]["count"] = len(SHARED_SHOPS)

def generate_shared_products(count=1000, mode="replace"):
    """
    Generate shared product catalog for all data sources
    Stored in: shared_data/share_data/products.json.gz

    Args:
        count: Number of products to generate
        mode: "replace" (default) - replace all data, "append" - add to existing data
    """
    global SHARED_PRODUCTS

    # Load existing data if mode is append
    start_id = 1
    if mode == "append":
        # Ensure existing data is loaded
        ensure_products_loaded()
        if SHARED_PRODUCTS:
            start_id = max(p["id"] for p in SHARED_PRODUCTS) + 1
            print(f"Appending {count} products starting from ID {start_id}")
        else:
            print(f"No existing products found, starting from ID 1")

    products = []
    for i in range(count):
        product_id = start_id + i
        category = random.choice(list(TECH_CATEGORIES.keys()))
        category_info = TECH_CATEGORIES[category]
        brand = random.choice(category_info["brands"])
        model = random.choice(category_info["models"])

        price_min, price_max = category_info["price_range"]
        cost_price_vnd = random.randint(price_min, price_max)
        # Round to nearest 100,000 VND
        cost_price_vnd = round(cost_price_vnd / 100_000) * 100_000
        sale_price_vnd = round(cost_price_vnd * random.uniform(1.2, 1.5) / 100_000) * 100_000

        # Convert to USD for international sales (approximate rate: 24,000 VND = 1 USD)
        cost_price_usd = round(cost_price_vnd / 24_000, 2)
        sale_price_usd = round(sale_price_vnd / 24_000, 2)

        product = {
            "id": product_id,
            "name": generate_product_name(category, brand, model),
            "name_en": f"{brand} {model}",
            "sku": fake_en.bothify("TECH-####-???").upper(),
            "barcode": fake_en.ean13(),
            "category": category,
            "brand": brand,
            "model": model,
            "price_vnd": sale_price_vnd,
            "price_usd": sale_price_usd,
            "cost_vnd": cost_price_vnd,
            "cost_usd": cost_price_usd,
            "currency_primary": "VND",
            "warranty_months": random.choice([12, 24, 36]),
            "stock_quantity": random.randint(0, 500),
            "description_vi": f"Sản phẩm chính hãng {brand}, bảo hành {random.choice([12, 24, 36])} tháng",
            "description_en": f"Original {brand} product with warranty",
            "weight_kg": round(random.uniform(0.1, 5), 2),
            "created_at": (datetime.now() - timedelta(days=random.randint(30, 730))).isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        products.append(product)

    # Combine with existing data if append mode
    if mode == "append" and SHARED_PRODUCTS:
        all_products = SHARED_PRODUCTS + products
    else:
        all_products = products

    SHARED_PRODUCTS = all_products

    # Save to new location
    save_compressed(all_products, get_share_data_path("products.json.gz"))

    # Update status
    GENERATION_STATUS["products"]["generated"] = True
    GENERATION_STATUS["products"]["count"] = len(all_products)

    return all_products

def generate_vietnamese_name():
    """Generate realistic Vietnamese name"""
    last_names = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Huynh", "Phan", "Vu", "Vo", "Dang", "Bui", "Do", "Ho", "Ngo", "Duong"]
    middle_names = ["Van", "Thi", "Huu", "Duc", "Minh", "Anh", "Tuan", "Hoang", "Thanh", "Quoc", "Bao", "Nhu"]
    first_names_male = ["Hung", "Dung", "Nam", "Long", "Khang", "Phong", "Tung", "Quan", "Thang", "Hai", "Dat", "Kien"]
    first_names_female = ["Linh", "Huong", "Mai", "Lan", "Ha", "Nga", "Trang", "Thao", "Nhung", "Hong", "Anh", "Chi"]

    last = random.choice(last_names)
    middle = random.choice(middle_names)

    if random.random() > 0.5:  # Male
        first = random.choice(first_names_male)
    else:  # Female
        first = random.choice(first_names_female)

    return f"{last} {middle} {first}"

def generate_shared_customers(count=2_000_000, batch_size=10_000):
    """
    Generate shared customer base
    Stored in: shared_data/share_data/customers/
    """
    print(f"Generating {count:,} shared customers...")

    customer_dir = get_share_data_path("customers")
    if isinstance(customer_dir, Path):
        customer_dir.mkdir(exist_ok=True)
    else:
        Path(customer_dir).mkdir(exist_ok=True)

    total_generated = 0

    for batch_num in range(0, count, batch_size):
        batch_customers = []
        current_batch_size = min(batch_size, count - batch_num)

        for i in range(batch_num, batch_num + current_batch_size):
            is_vietnamese = random.random() < 0.95  # 95% Vietnamese customers

            if is_vietnamese:
                full_name = generate_vietnamese_name()
                name_parts = full_name.split()
                first_name = " ".join(name_parts[:-1])
                last_name = name_parts[-1]
                email = f"{fake_vi.user_name()}{i}@gmail.com"
                phone = fake_vi.phone_number()
                city = random.choice(["Ha Noi", "TP Ho Chi Minh", "Da Nang", "Hai Phong", "Can Tho", "Bien Hoa", "Nha Trang"])
                country = "Vietnam"
            else:
                first_name = fake_en.first_name()
                last_name = fake_en.last_name()
                full_name = f"{first_name} {last_name}"
                email = f"{first_name.lower()}.{last_name.lower()}{i}@gmail.com"
                phone = fake_en.phone_number()
                city = fake_en.city()
                country = fake_en.country()

            customer = {
                "id": i + 1,
                "full_name": full_name,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": phone,
                "city": city,
                "country": country,
                "is_vietnamese": is_vietnamese,
                "language": "vi" if is_vietnamese else "en",
                "created_at": (datetime.now() - timedelta(days=random.randint(1, 730))).isoformat(),
                "total_orders": 0,
                "total_spent_vnd": 0,
                "total_spent_usd": 0
            }
            batch_customers.append(customer)

        # Save batch to new location
        batch_file = Path(customer_dir) / f"customers_batch_{batch_num // batch_size}.json.gz"
        save_compressed(batch_customers, batch_file)

        total_generated += current_batch_size

        if total_generated % 100_000 == 0:
            print(f"Generated {total_generated:,} customers...")

    # Update status
    GENERATION_STATUS["customers"]["generated"] = True
    GENERATION_STATUS["customers"]["count"] = count

    print(f"Generated {count:,} customers")
    return count

def generate_shared_staff(count=300, mode="replace"):
    """
    Generate staff members for stores
    Stored in: shared_data/share_data/staff.json.gz

    Args:
        count: Number of staff to generate
        mode: "replace" (default) - replace all data, "append" - add to existing data
    """
    global SHARED_STAFF

    # Load existing data if mode is append
    start_id = 1
    if mode == "append":
        ensure_staff_loaded()
        if SHARED_STAFF:
            start_id = max(s["id"] for s in SHARED_STAFF) + 1
            print(f"Appending {count} staff starting from ID {start_id}")
        else:
            print(f"No existing staff found, starting from ID 1")

    positions = [
        "Nhan vien ban hang", "Nhan vien tu van", "Thu ngan",
        "Quan ly ca", "Quan ly cua hang", "Ky thuat vien",
        "Nhan vien kho", "Truong phong"
    ]

    staff = []
    for i in range(count):
        staff_id = start_id + i
        full_name = generate_vietnamese_name()

        staff_member = {
            "id": staff_id,
            "code": f"NV{str(staff_id).zfill(4)}",
            "full_name": full_name,
            "email": f"nhanvien{staff_id}@techstore.vn",
            "phone": fake_vi.phone_number(),
            "position": random.choice(positions),
            "hire_date": (datetime.now() - timedelta(days=random.randint(30, 1095))).isoformat(),
            "status": "active"
        }
        staff.append(staff_member)

    # Combine with existing data if append mode
    if mode == "append" and SHARED_STAFF:
        all_staff = SHARED_STAFF + staff
    else:
        all_staff = staff

    SHARED_STAFF = all_staff

    # Save to new location
    save_compressed(all_staff, get_share_data_path("staff.json.gz"))

    # Update status
    GENERATION_STATUS["staff"]["generated"] = True
    GENERATION_STATUS["staff"]["count"] = len(all_staff)

    return all_staff

def generate_shared_locations(count=50, mode="replace"):
    """
    Generate Vietnam store locations
    Stored in: shared_data/share_data/sapo_locations.json.gz

    Args:
        count: Number of locations to generate
        mode: "replace" (default) - replace all data, "append" - add to existing data
    """
    global SHARED_LOCATIONS

    # Load existing data if mode is append
    start_id = 1
    if mode == "append":
        ensure_locations_loaded()
        if SHARED_LOCATIONS:
            start_id = max(loc["id"] for loc in SHARED_LOCATIONS) + 1
            print(f"Appending {count} locations starting from ID {start_id}")
        else:
            print(f"No existing locations found, starting from ID 1")

    cities = [
        "Ha Noi", "Ha Noi", "Ha Noi", "Ha Noi", "Ha Noi",
        "Ha Noi", "Ha Noi", "Ha Noi", "Ha Noi", "Ha Noi",  # 10 stores in Hanoi
        "TP Ho Chi Minh", "TP Ho Chi Minh", "TP Ho Chi Minh", "TP Ho Chi Minh", "TP Ho Chi Minh",
        "TP Ho Chi Minh", "TP Ho Chi Minh", "TP Ho Chi Minh", "TP Ho Chi Minh", "TP Ho Chi Minh",
        "TP Ho Chi Minh", "TP Ho Chi Minh", "TP Ho Chi Minh", "TP Ho Chi Minh", "TP Ho Chi Minh",  # 15 stores in HCMC
        "Da Nang", "Da Nang", "Da Nang",  # 3 stores
        "Hai Phong", "Hai Phong",  # 2 stores
        "Can Tho", "Can Tho",  # 2 stores
        "Bien Hoa", "Nha Trang", "Hue", "Vung Tau", "Buon Ma Thuot",
        "Quy Nhon", "Thai Nguyen", "Vinh", "Nam Dinh", "Ha Long",
        "Phan Thiet", "Long Xuyen", "Thu Dau Mot", "Pleiku", "My Tho",
        "Ben Tre", "Cao Lanh", "Tay Ninh", "Rach Gia", "Ca Mau"
    ]

    districts_hanoi = ["Hoan Kiem", "Dong Da", "Ba Dinh", "Cau Giay", "Hai Ba Trung", "Thanh Xuan", "Long Bien", "Hoang Mai"]
    districts_hcmc = ["Quan 1", "Quan 3", "Quan 5", "Quan 10", "Tan Binh", "Phu Nhuan", "Binh Thanh", "Go Vap", "Thu Duc"]

    locations = []
    for i in range(count):
        location_id = start_id + i
        # Cycle through cities if count > len(cities)
        city = cities[i % len(cities)]

        if city == "Ha Noi":
            district = random.choice(districts_hanoi)
        elif city == "TP Ho Chi Minh":
            district = random.choice(districts_hcmc)
        else:
            district = "Trung tam"

        location = {
            "id": location_id,
            "tenant_id": random.randint(1000, 9999),
            "name": f"TechStore {city} - {district}",
            "code": f"CN{str(location_id).zfill(3)}",
            "address": fake_vi.street_address(),
            "district": district,
            "city": city,
            "country": "Vietnam",
            "phone": fake_vi.phone_number(),
            "email": f"chinhanh{location_id}@techstore.vn",
            "status": "active",
            "created_on": (datetime.now() - timedelta(days=random.randint(180, 1095))).isoformat(),
            "modified_on": datetime.now().isoformat(),
            "latitude": str(round(random.uniform(8.0, 23.0), 6)),
            "longitude": str(round(random.uniform(102.0, 109.0), 6))
        }
        locations.append(location)

    # Combine with existing data if append mode
    if mode == "append" and SHARED_LOCATIONS:
        all_locations = SHARED_LOCATIONS + locations
    else:
        all_locations = locations

    SHARED_LOCATIONS = all_locations

    # Save to new location
    save_compressed(all_locations, get_share_data_path("sapo_locations.json.gz"))

    # Update status
    GENERATION_STATUS["locations"]["generated"] = True
    GENERATION_STATUS["locations"]["count"] = len(all_locations)

    return all_locations

def generate_shared_shops(count=30, mode="replace"):
    """
    Generate international POS shop configurations
    Stored in: shared_data/share_data/odoo_shops.json.gz

    Args:
        count: Number of shops to generate
        mode: "replace" (default) - replace all data, "append" - add to existing data
    """
    global SHARED_SHOPS

    # Load existing data if mode is append
    start_id = 1
    if mode == "append":
        ensure_shops_loaded()
        if SHARED_SHOPS:
            start_id = max(shop["id"] for shop in SHARED_SHOPS) + 1
            print(f"Appending {count} shops starting from ID {start_id}")
        else:
            print(f"No existing shops found, starting from ID 1")

    cities = [
        ("Singapore", "SGD", "Singapore"),
        ("Singapore", "SGD", "Singapore"),
        ("Singapore", "SGD", "Singapore"),
        ("Bangkok", "THB", "Thailand"),
        ("Bangkok", "THB", "Thailand"),
        ("Kuala Lumpur", "MYR", "Malaysia"),
        ("Kuala Lumpur", "MYR", "Malaysia"),
        ("Jakarta", "IDR", "Indonesia"),
        ("Manila", "PHP", "Philippines"),
        ("Hong Kong", "HKD", "Hong Kong"),
        ("Hong Kong", "HKD", "Hong Kong"),
        ("Seoul", "KRW", "South Korea"),
        ("Tokyo", "JPY", "Japan"),
        ("Sydney", "AUD", "Australia"),
        ("Melbourne", "AUD", "Australia"),
        ("Auckland", "NZD", "New Zealand"),
        ("Dubai", "AED", "UAE"),
        ("London", "GBP", "UK"),
        ("London", "GBP", "UK"),
        ("Paris", "EUR", "France"),
        ("Berlin", "EUR", "Germany"),
        ("Amsterdam", "EUR", "Netherlands"),
        ("Barcelona", "EUR", "Spain"),
        ("New York", "USD", "USA"),
        ("Los Angeles", "USD", "USA"),
        ("San Francisco", "USD", "USA"),
        ("Toronto", "CAD", "Canada"),
        ("Vancouver", "CAD", "Canada"),
        ("Mumbai", "INR", "India"),
        ("Bangalore", "INR", "India")
    ]

    shops = []
    for i in range(count):
        shop_id = start_id + i
        # Cycle through cities if count > len(cities)
        city, currency, country = cities[i % len(cities)]

        shop = {
            "id": shop_id,
            "name": f"TechStore {city} - {fake_en.street_name()}",
            "company_id": random.randint(1, 5),
            "company_name": "TechStore International Ltd.",
            "pricelist_id": shop_id,
            "currency_id": shop_id,
            "currency_code": currency,
            "warehouse_id": shop_id,
            "warehouse_name": f"Warehouse {city}",
            "picking_type_id": shop_id + 100,
            "journal_id": shop_id + 200,
            "city": city,
            "country": country,
            "module_pos_discount": True,
            "create_date": (datetime.now() - timedelta(days=random.randint(365, 1095))).isoformat(),
            "write_date": datetime.now().isoformat()
        }
        shops.append(shop)

    # Combine with existing data if append mode
    if mode == "append" and SHARED_SHOPS:
        all_shops = SHARED_SHOPS + shops
    else:
        all_shops = shops

    SHARED_SHOPS = all_shops

    # Save to new location
    save_compressed(all_shops, get_share_data_path("odoo_shops.json.gz"))

    # Update status
    GENERATION_STATUS["shops"]["generated"] = True
    GENERATION_STATUS["shops"]["count"] = len(all_shops)

    return all_shops

def generate_transaction_id():
    """Generate unique transaction ID across all systems"""
    global TRANSACTION_ID_COUNTER
    TRANSACTION_ID_COUNTER += 1
    return f"TXN{datetime.now().strftime('%Y%m%d')}{str(TRANSACTION_ID_COUNTER).zfill(8)}"

def get_random_product():
    """Get random product from shared catalog"""
    ensure_products_loaded()
    return random.choice(SHARED_PRODUCTS) if SHARED_PRODUCTS else None

def get_random_customer():
    """Get random customer from shared database"""
    customer_id = random.randint(1, 2_000_000)
    return {"id": customer_id}

def get_random_staff():
    """Get random staff member"""
    ensure_staff_loaded()
    return random.choice(SHARED_STAFF) if SHARED_STAFF else None

def get_random_location():
    """Get random location"""
    ensure_locations_loaded()
    return random.choice(SHARED_LOCATIONS) if SHARED_LOCATIONS else None

def get_random_shop():
    """Get random shop"""
    ensure_shops_loaded()
    return random.choice(SHARED_SHOPS) if SHARED_SHOPS else None

# Customer lookup functions
def get_customer_by_id(customer_id: int):
    """Get customer details by ID from batched files"""
    # Calculate which batch the customer is in
    batch_size = 10_000
    batch_num = (customer_id - 1) // batch_size

    # Try new location first
    customer_dir = get_share_data_path("customers")
    batch_file = Path(customer_dir) / f"customers_batch_{batch_num}.json.gz"

    # Fallback to old location
    if not batch_file.exists():
        batch_file = DATA_DIR / "customers" / f"customers_batch_{batch_num}.json.gz"

    if not batch_file.exists():
        return None

    customers = load_compressed(batch_file)
    if not customers:
        return None

    # Find the customer in the batch
    for customer in customers:
        if customer["id"] == customer_id:
            return customer

    return None

def get_product_by_id(product_id: int):
    """Get product details by ID"""
    ensure_products_loaded()
    for product in SHARED_PRODUCTS:
        if product["id"] == product_id:
            return product
    return None

def get_staff_by_id(staff_id: int):
    """Get staff details by ID"""
    ensure_staff_loaded()
    for staff in SHARED_STAFF:
        if staff["id"] == staff_id:
            return staff
    return None

async def initialize_shared_data():
    """Initialize all shared data on startup"""
    global SHARED_PRODUCTS, SHARED_STAFF, SHARED_LOCATIONS, SHARED_SHOPS

    # Check new location first, then fallback to old location
    products_file = get_share_data_path("products.json.gz")
    if not products_file.exists():
        products_file = DATA_DIR / "products.json.gz"

    staff_file = get_share_data_path("staff.json.gz")
    if not staff_file.exists():
        staff_file = DATA_DIR / "staff.json.gz"

    locations_file = get_share_data_path("sapo_locations.json.gz")
    if not locations_file.exists():
        locations_file = DATA_DIR / "sapo_locations.json.gz"

    shops_file = get_share_data_path("odoo_shops.json.gz")
    if not shops_file.exists():
        shops_file = DATA_DIR / "odoo_shops.json.gz"

    if products_file.exists():
        print("Loading existing products...")
        SHARED_PRODUCTS = load_compressed(products_file)
        GENERATION_STATUS["products"]["generated"] = True
        GENERATION_STATUS["products"]["count"] = len(SHARED_PRODUCTS)
        print(f"Loaded {len(SHARED_PRODUCTS)} products from file")
    else:
        print("No product data found. Generate via /generate/products endpoint")

    if staff_file.exists():
        print("Loading existing staff...")
        SHARED_STAFF = load_compressed(staff_file)
        GENERATION_STATUS["staff"]["generated"] = True
        GENERATION_STATUS["staff"]["count"] = len(SHARED_STAFF)
        print(f"Loaded {len(SHARED_STAFF)} staff members from file")
    else:
        print("No staff data found. Generate via /generate/staff endpoint")

    if locations_file.exists():
        print("Loading existing locations...")
        SHARED_LOCATIONS = load_compressed(locations_file)
        GENERATION_STATUS["locations"]["generated"] = True
        GENERATION_STATUS["locations"]["count"] = len(SHARED_LOCATIONS)
        print(f"Loaded {len(SHARED_LOCATIONS)} locations from file")
    else:
        print("No location data found. Generate via /generate/locations endpoint")

    if shops_file.exists():
        print("Loading existing shops...")
        SHARED_SHOPS = load_compressed(shops_file)
        GENERATION_STATUS["shops"]["generated"] = True
        GENERATION_STATUS["shops"]["count"] = len(SHARED_SHOPS)
        print(f"Loaded {len(SHARED_SHOPS)} shops from file")
    else:
        print("No shop data found. Generate via /generate/shops endpoint")

    # Check customers in new location first
    customer_dir = get_share_data_path("customers")
    if not Path(customer_dir).exists() or not list(Path(customer_dir).glob("*.json.gz")):
        customer_dir = DATA_DIR / "customers"

    if Path(customer_dir).exists() and list(Path(customer_dir).glob("*.json.gz")):
        customer_batches = len(list(Path(customer_dir).glob("*.json.gz")))
        estimated_count = customer_batches * 10_000
        GENERATION_STATUS["customers"]["generated"] = True
        GENERATION_STATUS["customers"]["count"] = estimated_count
        print(f"Found {customer_batches} customer batches (~{estimated_count:,} customers) in files")
    else:
        print("No customer data found. Generate via /generate/customers endpoint")

def clear_generated_data(data_type: str):
    """Clear generated data files"""
    if data_type == "products":
        # Clear from both locations
        for filepath in [get_share_data_path("products.json.gz"), DATA_DIR / "products.json.gz"]:
            if filepath.exists():
                filepath.unlink()
        GENERATION_STATUS["products"]["generated"] = False
        GENERATION_STATUS["products"]["count"] = 0
        global SHARED_PRODUCTS
        SHARED_PRODUCTS = []

    elif data_type == "staff":
        for filepath in [get_share_data_path("staff.json.gz"), DATA_DIR / "staff.json.gz"]:
            if filepath.exists():
                filepath.unlink()
        GENERATION_STATUS["staff"]["generated"] = False
        GENERATION_STATUS["staff"]["count"] = 0
        global SHARED_STAFF
        SHARED_STAFF = []

    elif data_type == "customers":
        for customer_dir in [get_share_data_path("customers"), DATA_DIR / "customers"]:
            if Path(customer_dir).exists():
                for file in Path(customer_dir).glob("*.json.gz"):
                    file.unlink()
        GENERATION_STATUS["customers"]["generated"] = False
        GENERATION_STATUS["customers"]["count"] = 0

    elif data_type == "locations":
        for filepath in [get_share_data_path("sapo_locations.json.gz"), DATA_DIR / "sapo_locations.json.gz"]:
            if filepath.exists():
                filepath.unlink()
        GENERATION_STATUS["locations"]["generated"] = False
        GENERATION_STATUS["locations"]["count"] = 0
        global SHARED_LOCATIONS
        SHARED_LOCATIONS = []

    elif data_type == "shops":
        for filepath in [get_share_data_path("odoo_shops.json.gz"), DATA_DIR / "odoo_shops.json.gz"]:
            if filepath.exists():
                filepath.unlink()
        GENERATION_STATUS["shops"]["generated"] = False
        GENERATION_STATUS["shops"]["count"] = 0
        global SHARED_SHOPS
        SHARED_SHOPS = []

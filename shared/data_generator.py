"""
Shared Data Generator
Generates consistent product catalog, customers, and metadata
Used across all data source simulators
"""

from faker import Faker
from datetime import datetime, timedelta
import random
import uuid
from pathlib import Path
import json
import gzip

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

# Data directory
DATA_DIR = Path("./shared_data")
DATA_DIR.mkdir(exist_ok=True)

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

def generate_shared_products(count=1000):
    """Generate shared product catalog for all data sources"""
    global SHARED_PRODUCTS

    products = []
    for i in range(count):
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
            "id": i + 1,
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

    SHARED_PRODUCTS = products

    # Save to file
    save_compressed(products, DATA_DIR / "products.json.gz")

    # Update status
    GENERATION_STATUS["products"]["generated"] = True
    GENERATION_STATUS["products"]["count"] = len(products)

    return products

def generate_vietnamese_name():
    """Generate realistic Vietnamese name"""
    last_names = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương"]
    middle_names = ["Văn", "Thị", "Hữu", "Đức", "Minh", "Anh", "Tuấn", "Hoàng", "Thanh", "Quốc", "Bảo", "Như"]
    first_names_male = ["Hùng", "Dũng", "Nam", "Long", "Khang", "Phong", "Tùng", "Quân", "Thắng", "Hải", "Đạt", "Kiên"]
    first_names_female = ["Linh", "Hương", "Mai", "Lan", "Hà", "Nga", "Trang", "Thảo", "Nhung", "Hồng", "Anh", "Chi"]

    last = random.choice(last_names)
    middle = random.choice(middle_names)

    if random.random() > 0.5:  # Male
        first = random.choice(first_names_male)
    else:  # Female
        first = random.choice(first_names_female)

    return f"{last} {middle} {first}"

def generate_shared_customers(count=2_000_000, batch_size=10_000):
    """Generate shared customer base"""
    print(f"Generating {count:,} shared customers...")

    customer_dir = DATA_DIR / "customers"
    customer_dir.mkdir(exist_ok=True)

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
                city = random.choice(["Hà Nội", "TP Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ", "Biên Hòa", "Nha Trang"])
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

        # Save batch
        batch_file = customer_dir / f"customers_batch_{batch_num // batch_size}.json.gz"
        save_compressed(batch_customers, batch_file)

        total_generated += current_batch_size

        if total_generated % 100_000 == 0:
            print(f"Generated {total_generated:,} customers...")

    # Update status
    GENERATION_STATUS["customers"]["generated"] = True
    GENERATION_STATUS["customers"]["count"] = count

    print(f"✅ Generated {count:,} customers")
    return count

def generate_shared_staff(count=300):
    """Generate staff members for stores"""
    global SHARED_STAFF

    positions = [
        "Nhân viên bán hàng", "Nhân viên tư vấn", "Thu ngân",
        "Quản lý ca", "Quản lý cửa hàng", "Kỹ thuật viên",
        "Nhân viên kho", "Trưởng phòng"
    ]

    staff = []
    for i in range(count):
        full_name = generate_vietnamese_name()

        staff_member = {
            "id": i + 1,
            "code": f"NV{str(i+1).zfill(4)}",
            "full_name": full_name,
            "email": f"nhanvien{i+1}@techstore.vn",
            "phone": fake_vi.phone_number(),
            "position": random.choice(positions),
            "hire_date": (datetime.now() - timedelta(days=random.randint(30, 1095))).isoformat(),
            "status": "active"
        }
        staff.append(staff_member)

    SHARED_STAFF = staff

    # Save to file
    save_compressed(staff, DATA_DIR / "staff.json.gz")

    # Update status
    GENERATION_STATUS["staff"]["generated"] = True
    GENERATION_STATUS["staff"]["count"] = len(staff)

    return staff

def generate_shared_locations(count=50):
    """Generate Vietnam store locations"""
    global SHARED_LOCATIONS

    cities = [
        "Hà Nội", "Hà Nội", "Hà Nội", "Hà Nội", "Hà Nội",
        "Hà Nội", "Hà Nội", "Hà Nội", "Hà Nội", "Hà Nội",  # 10 stores in Hanoi
        "TP Hồ Chí Minh", "TP Hồ Chí Minh", "TP Hồ Chí Minh", "TP Hồ Chí Minh", "TP Hồ Chí Minh",
        "TP Hồ Chí Minh", "TP Hồ Chí Minh", "TP Hồ Chí Minh", "TP Hồ Chí Minh", "TP Hồ Chí Minh",
        "TP Hồ Chí Minh", "TP Hồ Chí Minh", "TP Hồ Chí Minh", "TP Hồ Chí Minh", "TP Hồ Chí Minh",  # 15 stores in HCMC
        "Đà Nẵng", "Đà Nẵng", "Đà Nẵng",  # 3 stores
        "Hải Phòng", "Hải Phòng",  # 2 stores
        "Cần Thơ", "Cần Thơ",  # 2 stores
        "Biên Hòa", "Nha Trang", "Huế", "Vũng Tàu", "Buôn Ma Thuột",
        "Quy Nhơn", "Thái Nguyên", "Vinh", "Nam Định", "Hạ Long",
        "Phan Thiết", "Long Xuyên", "Thủ Dầu Một", "Pleiku", "Mỹ Tho",
        "Bến Tre", "Cao Lãnh", "Tây Ninh", "Rạch Giá", "Cà Mau"
    ]

    districts_hanoi = ["Hoàn Kiếm", "Đống Đa", "Ba Đình", "Cầu Giấy", "Hai Bà Trưng", "Thanh Xuân", "Long Biên", "Hoàng Mai"]
    districts_hcmc = ["Quận 1", "Quận 3", "Quận 5", "Quận 10", "Tân Bình", "Phú Nhuận", "Bình Thạnh", "Gò Vấp", "Thủ Đức"]

    locations = []
    for i in range(count):
        city = cities[i]

        if city == "Hà Nội":
            district = random.choice(districts_hanoi)
        elif city == "TP Hồ Chí Minh":
            district = random.choice(districts_hcmc)
        else:
            district = "Trung tâm"

        location = {
            "id": i + 1,
            "tenant_id": random.randint(1000, 9999),
            "name": f"TechStore {city} - {district}",
            "code": f"CN{str(i+1).zfill(3)}",
            "address": fake_vi.street_address(),
            "district": district,
            "city": city,
            "country": "Vietnam",
            "phone": fake_vi.phone_number(),
            "email": f"chinhanh{i+1}@techstore.vn",
            "status": "active",
            "created_on": (datetime.now() - timedelta(days=random.randint(180, 1095))).isoformat(),
            "modified_on": datetime.now().isoformat(),
            "latitude": str(round(random.uniform(8.0, 23.0), 6)),
            "longitude": str(round(random.uniform(102.0, 109.0), 6))
        }
        locations.append(location)

    SHARED_LOCATIONS = locations

    # Save to file
    save_compressed(locations, DATA_DIR / "sapo_locations.json.gz")

    # Update status
    GENERATION_STATUS["locations"]["generated"] = True
    GENERATION_STATUS["locations"]["count"] = len(locations)

    return locations

def generate_shared_shops(count=30):
    """Generate international POS shop configurations"""
    global SHARED_SHOPS

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
    for i, (city, currency, country) in enumerate(cities):
        shop = {
            "id": i + 1,
            "name": f"TechStore {city} - {fake_en.street_name()}",
            "company_id": random.randint(1, 5),
            "company_name": "TechStore International Ltd.",
            "pricelist_id": i + 1,
            "currency_id": i + 1,
            "currency_code": currency,
            "warehouse_id": i + 1,
            "warehouse_name": f"Warehouse {city}",
            "picking_type_id": i + 100,
            "journal_id": i + 200,
            "city": city,
            "country": country,
            "module_pos_discount": True,
            "create_date": (datetime.now() - timedelta(days=random.randint(365, 1095))).isoformat(),
            "write_date": datetime.now().isoformat()
        }
        shops.append(shop)

    SHARED_SHOPS = shops

    # Save to file
    save_compressed(shops, DATA_DIR / "odoo_shops.json.gz")

    # Update status
    GENERATION_STATUS["shops"]["generated"] = True
    GENERATION_STATUS["shops"]["count"] = len(shops)

    return shops

def generate_transaction_id():
    """Generate unique transaction ID across all systems"""
    global TRANSACTION_ID_COUNTER
    TRANSACTION_ID_COUNTER += 1
    return f"TXN{datetime.now().strftime('%Y%m%d')}{str(TRANSACTION_ID_COUNTER).zfill(8)}"

def get_random_product():
    """Get random product from shared catalog"""
    return random.choice(SHARED_PRODUCTS) if SHARED_PRODUCTS else None

def get_random_customer():
    """Get random customer from shared database"""
    customer_id = random.randint(1, 2_000_000)
    return {"id": customer_id}

def get_random_staff():
    """Get random staff member"""
    return random.choice(SHARED_STAFF) if SHARED_STAFF else None

def get_random_location():
    """Get random location"""
    return random.choice(SHARED_LOCATIONS) if SHARED_LOCATIONS else None

def get_random_shop():
    """Get random shop"""
    return random.choice(SHARED_SHOPS) if SHARED_SHOPS else None

async def initialize_shared_data():
    """Initialize all shared data on startup"""
    global SHARED_PRODUCTS, SHARED_STAFF, SHARED_LOCATIONS, SHARED_SHOPS

    # Check if data already exists
    products_file = DATA_DIR / "products.json.gz"
    staff_file = DATA_DIR / "staff.json.gz"
    locations_file = DATA_DIR / "sapo_locations.json.gz"
    shops_file = DATA_DIR / "odoo_shops.json.gz"

    if products_file.exists():
        print("📦 Loading existing products...")
        SHARED_PRODUCTS = load_compressed(products_file)
        GENERATION_STATUS["products"]["generated"] = True
        GENERATION_STATUS["products"]["count"] = len(SHARED_PRODUCTS)
        print(f"✅ Loaded {len(SHARED_PRODUCTS)} products from file")
    else:
        print("⚠️  No product data found. Generate via /generate/products endpoint")

    if staff_file.exists():
        print("👥 Loading existing staff...")
        SHARED_STAFF = load_compressed(staff_file)
        GENERATION_STATUS["staff"]["generated"] = True
        GENERATION_STATUS["staff"]["count"] = len(SHARED_STAFF)
        print(f"✅ Loaded {len(SHARED_STAFF)} staff members from file")
    else:
        print("⚠️  No staff data found. Generate via /generate/staff endpoint")

    if locations_file.exists():
        print("🏪 Loading existing locations...")
        SHARED_LOCATIONS = load_compressed(locations_file)
        GENERATION_STATUS["locations"]["generated"] = True
        GENERATION_STATUS["locations"]["count"] = len(SHARED_LOCATIONS)
        print(f"✅ Loaded {len(SHARED_LOCATIONS)} locations from file")
    else:
        print("⚠️  No location data found. Generate via /generate/locations endpoint")

    if shops_file.exists():
        print("🛍️  Loading existing shops...")
        SHARED_SHOPS = load_compressed(shops_file)
        GENERATION_STATUS["shops"]["generated"] = True
        GENERATION_STATUS["shops"]["count"] = len(SHARED_SHOPS)
        print(f"✅ Loaded {len(SHARED_SHOPS)} shops from file")
    else:
        print("⚠️  No shop data found. Generate via /generate/shops endpoint")

    # Check customers
    customer_dir = DATA_DIR / "customers"
    if customer_dir.exists() and list(customer_dir.glob("*.json.gz")):
        customer_batches = len(list(customer_dir.glob("*.json.gz")))
        estimated_count = customer_batches * 10_000
        GENERATION_STATUS["customers"]["generated"] = True
        GENERATION_STATUS["customers"]["count"] = estimated_count
        print(f"✅ Found {customer_batches} customer batches (~{estimated_count:,} customers) in files")
    else:
        print("⚠️  No customer data found. Generate via /generate/customers endpoint")

def clear_generated_data(data_type: str):
    """Clear generated data files"""
    if data_type == "products":
        products_file = DATA_DIR / "products.json.gz"
        if products_file.exists():
            products_file.unlink()
        GENERATION_STATUS["products"]["generated"] = False
        GENERATION_STATUS["products"]["count"] = 0
        global SHARED_PRODUCTS
        SHARED_PRODUCTS = []

    elif data_type == "staff":
        staff_file = DATA_DIR / "staff.json.gz"
        if staff_file.exists():
            staff_file.unlink()
        GENERATION_STATUS["staff"]["generated"] = False
        GENERATION_STATUS["staff"]["count"] = 0
        global SHARED_STAFF
        SHARED_STAFF = []

    elif data_type == "customers":
        customer_dir = DATA_DIR / "customers"
        if customer_dir.exists():
            for file in customer_dir.glob("*.json.gz"):
                file.unlink()
        GENERATION_STATUS["customers"]["generated"] = False
        GENERATION_STATUS["customers"]["count"] = 0

    elif data_type == "locations":
        locations_file = DATA_DIR / "sapo_locations.json.gz"
        if locations_file.exists():
            locations_file.unlink()
        GENERATION_STATUS["locations"]["generated"] = False
        GENERATION_STATUS["locations"]["count"] = 0
        global SHARED_LOCATIONS
        SHARED_LOCATIONS = []

    elif data_type == "shops":
        shops_file = DATA_DIR / "odoo_shops.json.gz"
        if shops_file.exists():
            shops_file.unlink()
        GENERATION_STATUS["shops"]["generated"] = False
        GENERATION_STATUS["shops"]["count"] = 0
        global SHARED_SHOPS
        SHARED_SHOPS = []
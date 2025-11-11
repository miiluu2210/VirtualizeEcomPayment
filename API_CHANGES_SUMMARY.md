# API Changes Summary - Data Caching & Generation Method

## Tóm tắt thay đổi

Refactor lại hệ thống API data generation và caching với các cải tiến sau:

### 1. **data_generator.py** ✅ Hoàn thành
- Thêm helper functions: `ensure_products_loaded()`, `ensure_staff_loaded()`, `ensure_locations_loaded()`, `ensure_shops_loaded()`
- Cập nhật tất cả `generate_*()` functions với parameter `mode`:
  - `mode="replace"` (default): Thay thế toàn bộ data
  - `mode="append"`: Thêm data mới vào data cũ, giữ nguyên tính toàn vẹn ID
- Auto-increment IDs khi append để đảm bảo không trùng lặp

### 2. **shopify_router.py** ✅ Hoàn thành
**GET Endpoints:**
- `/admin/api/2024-01/products`: Tự động load data từ file nếu có
- `/admin/api/2024-01/orders`: Tự động load data từ file, trả về error message rõ ràng nếu không có
- `/admin/api/2024-01/staff`: Tự động load data từ file

**Generate Endpoints:**
- `/generate/products`: Thay `new: bool` thành `method: Optional[str]`
  - `method="new"`: Append thêm products mới
  - `method="no"` hoặc None: Giữ nguyên data cũ
- `/generate/staff`: Tương tự pattern
- `/generate/customers`: Chỉ hỗ trợ replace mode (do batch file complexity)

### 3. **sapo_router.py** ✅ Hoàn thành
**GET Endpoints:**
- `/admin/locations`: Tự động load từ file
- `/admin/products`: Tự động load từ file
- `/admin/staff`: Tự động load từ file
- `/admin/orders`: Tự động load từ file với error handling

**Generate Endpoints:**
- `/generate/locations`: Hỗ trợ `method` parameter với append mode

### 4. **paypal_router.py** ✅ Hoàn thành
**GET Endpoints:**
- `/v1/reporting/transactions`: Cải thiện error message
- `/v1/payments/payment`: Cải thiện error message

**Generate Endpoints:**
- `/generate/transactions`: Hỗ trợ `method` parameter
  - Cập nhật `generate_all_transactions()` với mode parameter
  - Append mode: gộp transactions cũ + mới

### 5. **mercury_router.py** ⚠️ Cần hoàn thiện
**GET Endpoints:** Đã có logic load từ file (OK)

**Generate Endpoints:** Cần cập nhật:
- `/generate/accounts`: Thêm `method` parameter
- `/generate/transactions`: Thêm `method` parameter, cập nhật `generate_all_transactions(mode="append")`

### 6. **odoo_router.py** ⚠️ Cần tái implement
**Vấn đề phát hiện:** File này hiện tại là bản copy 100% của mercury_router.py

**Cần làm:**
- Implement Odoo POS logic riêng với `SHARED_SHOPS`
- Generate shops endpoint
- Transactions phù hợp với POS system

---

## Cách sử dụng API sau khi cập nhật

### Lần đầu tiên (Generate data mới):
```bash
# Không cần truyền method hoặc method=no
GET /shopify/generate/products?count=1000
GET /shopify/generate/staff?count=300
GET /sapo/generate/locations?count=50
```

### Append thêm data mới:
```bash
# Sử dụng method=new
GET /shopify/generate/products?count=500&method=new
GET /shopify/generate/staff?count=100&method=new
GET /sapo/generate/locations?count=20&method=new
```

### Giữ nguyên data cũ:
```bash
# Không truyền method hoặc method=no
GET /shopify/generate/products?method=no
# Response: Warning với hint để dùng method=new nếu muốn append
```

---

## Tính toàn vẹn dữ liệu

### Product IDs
- Khi append: IDs tự động tiếp tục từ max ID hiện tại + 1
- Example: Có 1000 products (ID 1-1000), append 500 → IDs 1001-1500

### Transaction IDs
- Shared counter `TRANSACTION_ID_COUNTER` đảm bảo unique across all systems
- Format: `TXN{YYYYMMDD}{counter:08d}`

### Customer IDs
- Generated với ID sequence, không hỗ trợ append (batch file management)

---

## Testing

Sau khi hoàn thiện mercury & odoo routers, cần test:

1. **Generate lần đầu:**
   - Verify data được tạo và lưu file
   - Verify IDs bắt đầu từ 1

2. **Load data:**
   - Restart server
   - Gọi GET endpoints → data được load tự động

3. **Append data:**
   - Gọi generate với method=new
   - Verify IDs tiếp tục không trùng
   - Verify total count = old + new

4. **Keep existing:**
   - Gọi generate với method=no
   - Verify trả về warning với hint

---

## Next Steps

1. ✅ Commit changes hiện tại (data_generator, shopify, sapo, paypal)
2. ⚠️ Hoàn thiện mercury_router.py với pattern tương tự
3. ⚠️ Tái implement odoo_router.py cho Odoo POS (hiện đang duplicate mercury)
4. ✅ Test toàn bộ flow
5. ✅ Update documentation

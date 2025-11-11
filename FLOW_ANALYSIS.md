# Phân Tích Luồng Chạy Ứng Dụng với Gunicorn

## 📋 Tổng Quan

Ứng dụng Flask được deploy với **Gunicorn** (WSGI HTTP Server) trong container Podman. Tài liệu này mô tả chi tiết luồng xử lý từ khi container khởi động đến khi request được xử lý.

---

## 🔄 Luồng Khởi Động (Startup Flow)

### 1. **Container Startup** (Podman/Docker)

```
podman compose up
    ↓
Container "podman_test_app" được tạo từ Dockerfile
    ↓
WORKDIR /app được thiết lập
    ↓
CMD ["gunicorn", "wsgi:app", "-b", "0.0.0.0:5000", "-w", "2", "--timeout", "120"]
```

**Giải thích:**
- `gunicorn`: Lệnh khởi chạy Gunicorn WSGI server
- `wsgi:app`: Module `wsgi.py` và biến `app` trong đó
- `-b 0.0.0.0:5000`: Bind address và port
- `-w 2`: Số worker processes (2 workers)
- `--timeout 120`: Timeout cho mỗi request (120 giây)

### 2. **Gunicorn Master Process**

```
Gunicorn Master Process khởi động
    ↓
Đọc cấu hình: wsgi:app
    ↓
Import module wsgi.py
```

### 3. **Import wsgi.py**

```python
# wsgi.py
from app import create_app  # ← Bước này

app = create_app()  # ← Tạo Flask app instance
```

**Luồng import:**
```
wsgi.py
    ↓ import
app/__init__.py
    ↓ from .main import bp
app/main.py
    ↓ import các dependencies
    - Flask Blueprint
    - mysql.connector
    - faiss
    - numpy
```

### 4. **Flask App Initialization**

```python
# app/__init__.py
def create_app() -> Flask:
    app = Flask(__name__)  # ← Tạo Flask application instance
    
    from .main import bp as main_bp  # ← Import blueprint
    app.register_blueprint(main_bp)  # ← Đăng ký routes
    
    return app  # ← Trả về Flask app
```

**Kết quả:**
- Flask app được tạo với tất cả routes đã đăng ký:
  - `GET /health`
  - `GET /db-ping`
  - `POST /faiss/search`

### 5. **Gunicorn Worker Processes**

```
Master Process
    ↓
Fork 2 Worker Processes (do -w 2)
    ↓
Mỗi worker có 1 bản sao Flask app
    ↓
Workers sẵn sàng nhận request
```

**Lưu ý quan trọng:**
- Mỗi worker process có **bản sao riêng** của Flask app
- Không chia sẻ memory giữa các workers
- Master process quản lý workers (restart nếu crash)

---

## 🌐 Luồng Xử Lý Request (Request Flow)

### Khi có HTTP Request đến:

```
1. Client Request
   GET http://localhost:5000/health
        ↓
2. Podman Port Mapping
   Host:5000 → Container:5000
        ↓
3. Gunicorn Master Process
   Nhận connection
        ↓
4. Load Balancing
   Master chọn 1 worker (round-robin)
        ↓
5. Worker Process
   Worker nhận request
        ↓
6. WSGI Interface
   Gunicorn gọi app(environ, start_response)
        ↓
7. Flask Application
   Flask routing engine tìm route handler
        ↓
8. Route Handler
   @bp.get("/health") → health() function
        ↓
9. Response
   return jsonify({"status": "ok"})
        ↓
10. Gunicorn
    Gửi HTTP response về client
```

### Chi Tiết từng bước:

#### **Bước 6-7: WSGI Interface**

```python
# Gunicorn gọi Flask app như WSGI application
def application(environ, start_response):
    # environ: Dictionary chứa request info (method, path, headers, ...)
    # start_response: Callable để set status và headers
    
    # Flask xử lý:
    request = Request(environ)  # Tạo Flask request object
    response = app.full_dispatch_request()  # Dispatch request
    return response  # Trả về response
```

#### **Bước 8: Route Handler Execution**

```python
# app/main.py
@bp.get("/health")
def health():
    return jsonify({"status": "ok"})
    # Flask tự động convert thành HTTP response
    # Content-Type: application/json
    # Status: 200 OK
```

---

## 📊 So Sánh: Với và Không có Gunicorn

### ❌ **Không có Gunicorn** (Flask Development Server)

```python
# wsgi.py
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

**Đặc điểm:**
- ✅ Dễ development, hot-reload
- ❌ Single-threaded, không xử lý concurrent requests tốt
- ❌ Không phù hợp production
- ❌ Không có process management
- ❌ Performance kém

### ✅ **Có Gunicorn** (Production WSGI Server)

```bash
gunicorn wsgi:app -w 2 -b 0.0.0.0:5000
```

**Đặc điểm:**
- ✅ Multi-worker: Xử lý nhiều requests đồng thời
- ✅ Process management: Tự động restart workers nếu crash
- ✅ Production-ready: Tối ưu performance
- ✅ Load balancing: Phân phối requests giữa workers
- ✅ Timeout handling: Tự động kill requests quá lâu
- ✅ Graceful shutdown: Đợi requests hoàn thành trước khi shutdown

---

## 🔍 Ví Dụ Cụ Thể: Request đến `/db-ping`

### Request Flow:

```
1. Client: GET http://localhost:5000/db-ping
        ↓
2. Gunicorn Master nhận connection
        ↓
3. Master chọn Worker 1 (giả sử)
        ↓
4. Worker 1 gọi Flask app
        ↓
5. Flask routing: Tìm route "/db-ping"
        ↓
6. Tìm thấy: @bp.get("/db-ping") → db_ping()
        ↓
7. Thực thi db_ping():
   - Tạo MySQL connection
   - Execute "SELECT 1"
   - Đóng connection
   - Trả về JSON response
        ↓
8. Flask tạo HTTP response
        ↓
9. Gunicorn gửi response về client
        ↓
10. Client nhận: {"db": "ok"}
```

### Code Execution:

```python
# app/main.py
@bp.get("/db-ping")
def db_ping():
    try:
        # Bước 1: Kết nối MySQL
        conn = get_db_connection()
        # → mysql.connector.connect(host="mysql", ...)
        
        # Bước 2: Tạo cursor và execute query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        _ = cursor.fetchone()
        
        # Bước 3: Cleanup
        cursor.close()
        conn.close()
        
        # Bước 4: Trả về response
        return jsonify({"db": "ok"})
        # → HTTP 200 OK, Content-Type: application/json
    except Exception as exc:
        return jsonify({"db": "error", "detail": str(exc)}), 500
```

---

## 🏗️ Kiến Trúc Multi-Worker

### Master-Worker Model:

```
┌─────────────────────────────────┐
│   Gunicorn Master Process       │
│   - Quản lý workers             │
│   - Nhận connections            │
│   - Load balancing              │
│   - Process management          │
└──────────────┬──────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌──────▼──────┐
│  Worker 1   │  │  Worker 2   │
│  Flask App  │  │  Flask App  │
│  Instance   │  │  Instance   │
└─────────────┘  └─────────────┘
       │                │
       └───────┬────────┘
               │
       ┌───────▼────────┐
       │   MySQL DB     │
       │   (Container)  │
       └────────────────┘
```

### Lợi Ích:

1. **Concurrency**: 2 workers = xử lý 2 requests đồng thời
2. **Fault Tolerance**: Nếu 1 worker crash, master restart nó
3. **Load Distribution**: Requests được phân phối đều
4. **Resource Isolation**: Mỗi worker có memory riêng

---

## ⚙️ Cấu Hình Gunicorn

### Tham số hiện tại:

```bash
gunicorn wsgi:app \
    -b 0.0.0.0:5000 \      # Bind address
    -w 2 \                 # 2 workers
    --timeout 120          # 120s timeout
```

### Tối ưu hóa đề xuất:

```bash
gunicorn wsgi:app \
    -b 0.0.0.0:5000 \
    -w 4 \                 # Tăng workers (2 * CPU cores)
    --threads 2 \          # Threads per worker
    --timeout 120 \
    --keepalive 5 \        # Keep-alive connections
    --max-requests 1000 \  # Restart worker sau N requests
    --max-requests-jitter 100 \
    --access-logfile - \   # Log access
    --error-logfile -      # Log errors
```

### Công thức tính Workers:

```
workers = (2 * CPU_cores) + 1
```

Ví dụ: 2 CPU cores → `(2 * 2) + 1 = 5 workers`

---

## 🔄 Lifecycle của Request

### Timeline:

```
T0: Client gửi request
    ↓
T1: Gunicorn Master nhận connection (0.1ms)
    ↓
T2: Master chọn worker (0.1ms)
    ↓
T3: Worker nhận request (0.1ms)
    ↓
T4: Flask routing (0.5ms)
    ↓
T5: Route handler execution (50-500ms)
    - Database query: 10-100ms
    - FAISS search: 5-50ms
    - Business logic: 1-10ms
    ↓
T6: Response generation (1ms)
    ↓
T7: Gunicorn gửi response (0.1ms)
    ↓
T8: Client nhận response
```

**Total: ~50-600ms** (tùy vào route handler)

---

## 🐛 Debugging và Monitoring

### Logs:

```bash
# Xem logs của container
podman logs podman_test_app

# Xem logs real-time
podman logs -f podman_test_app
```

### Kiểm tra Workers:

```bash
# Vào container
podman exec -it podman_test_app bash

# Kiểm tra processes
ps aux | grep gunicorn
# Sẽ thấy: 1 master + 2 workers
```

### Test Performance:

```bash
# Test với multiple requests
for i in {1..10}; do
    curl http://localhost:5000/health &
done
wait
```

---

## 📝 Tóm Tắt

### Luồng chính:

1. **Container khởi động** → Gunicorn master process
2. **Gunicorn import wsgi.py** → Tạo Flask app
3. **Master fork workers** → Mỗi worker có Flask app instance
4. **Request đến** → Master phân phối cho worker
5. **Worker xử lý** → Flask routing → Route handler
6. **Response về** → Gunicorn gửi về client

### Ưu điểm Gunicorn:

- ✅ Multi-process: Xử lý concurrent requests
- ✅ Production-ready: Tối ưu performance
- ✅ Fault tolerance: Tự động restart workers
- ✅ Load balancing: Phân phối requests
- ✅ Configurable: Nhiều tùy chọn cấu hình

### Best Practices:

- Sử dụng Gunicorn cho production
- Số workers = (2 * CPU cores) + 1
- Set timeout hợp lý (120s cho heavy operations)
- Monitor worker processes
- Log access và error logs

---

## 🔗 Tài Liệu Tham Khảo

- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [WSGI Specification](https://peps.python.org/pep-3333/)
- [Flask Deployment Options](https://flask.palletsprojects.com/en/3.0.x/deploying/)


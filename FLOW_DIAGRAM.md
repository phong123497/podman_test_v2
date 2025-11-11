# Sơ Đồ Luồng Chạy Ứng Dụng với Gunicorn

## 🚀 Luồng Khởi Động (Startup)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. PODMAN COMPOSE START                                      │
│    $ podman compose up                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CONTAINER STARTUP                                         │
│    - Build image từ Dockerfile                               │
│    - Mount volumes: ./app → /app/app                         │
│    - Set environment variables                               │
│    - Execute CMD: gunicorn wsgi:app ...                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. GUNICORN MASTER PROCESS                                   │
│    - Parse command: wsgi:app                                 │
│    - Import module: wsgi.py                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. IMPORT wsgi.py                                            │
│    from app import create_app                                │
│    app = create_app()  ← Tạo Flask app                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. IMPORT app/__init__.py                                    │
│    - Tạo Flask instance: Flask(__name__)                     │
│    - Import blueprint: from .main import bp                  │
│    - Register routes: app.register_blueprint(main_bp)        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. IMPORT app/main.py                                        │
│    - Import dependencies: Flask, mysql.connector, faiss      │
│    - Define Blueprint: bp = Blueprint("main", __name__)      │
│    - Define routes: /health, /db-ping, /faiss/search         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. GUNICORN FORK WORKERS                                     │
│    - Master process fork 2 worker processes                  │
│    - Mỗi worker có bản sao Flask app instance                │
│    - Workers sẵn sàng nhận requests                          │
└─────────────────────────────────────────────────────────────┘
```

## 🌐 Luồng Xử Lý Request

```
┌─────────────────────────────────────────────────────────────┐
│ CLIENT REQUEST                                               │
│ GET http://localhost:5000/health                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ PODMAN PORT MAPPING                                          │
│ Host:5000 → Container:5000                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ GUNICORN MASTER PROCESS                                      │
│ - Nhận TCP connection                                        │
│ - Parse HTTP request                                         │
│ - Chọn worker (round-robin)                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ WORKER PROCESS (Worker 1 hoặc Worker 2)                      │
│ - Nhận request từ master                                     │
│ - Gọi WSGI application: app(environ, start_response)         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ FLASK APPLICATION                                            │
│ - Parse request: method, path, headers, body                 │
│ - Routing: Tìm route handler cho "/health"                   │
│ - Match route: @bp.get("/health") → health()                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ ROUTE HANDLER                                                │
│ def health():                                                │
│     return jsonify({"status": "ok"})                         │
│ - Tạo JSON response                                          │
│ - Set HTTP headers: Content-Type: application/json           │
│ - Return Response object                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ GUNICORN WORKER                                              │
│ - Nhận Response từ Flask                                     │
│ - Convert thành HTTP response                                │
│ - Gửi về master process                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ GUNICORN MASTER                                              │
│ - Gửi HTTP response về client                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ CLIENT RECEIVES RESPONSE                                     │
│ HTTP 200 OK                                                  │
│ {"status": "ok"}                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🏗️ Kiến Trúc Multi-Worker

```
                    ┌──────────────────────┐
                    │   CLIENT REQUESTS     │
                    │  (HTTP Connections)   │
                    └──────────┬───────────┘
                               │
                               ▼
        ┌──────────────────────────────────────┐
        │  GUNICORN MASTER PROCESS (PID 1)     │
        │  - Nhận connections                  │
        │  - Load balancing                    │
        │  - Process management                │
        └──────────────┬───────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌───────────────┐           ┌───────────────┐
│  WORKER 1     │           │  WORKER 2     │
│  (PID 10)     │           │  (PID 11)     │
│               │           │               │
│  Flask App    │           │  Flask App    │
│  Instance     │           │  Instance     │
│               │           │               │
│  Routes:      │           │  Routes:      │
│  - /health    │           │  - /health    │
│  - /db-ping   │           │  - /db-ping   │
│  - /faiss/... │           │  - /faiss/... │
└───────┬───────┘           └───────┬───────┘
        │                           │
        └───────────────┬───────────┘
                        │
                        ▼
        ┌───────────────────────────┐
        │   MYSQL CONTAINER         │
        │   (podman_test_mysql)     │
        │   Port: 3306              │
        └───────────────────────────┘
```

## 🔄 Request Routing Example: `/db-ping`

```
Request: GET /db-ping
    │
    ├─► Gunicorn Master
    │       │
    │       ├─► Select Worker 1
    │       │
    │       └─► Worker 1 receives request
    │               │
    │               ├─► Flask Routing Engine
    │               │       │
    │               │       ├─► Match route: @bp.get("/db-ping")
    │               │       │
    │               │       └─► Call handler: db_ping()
    │               │               │
    │               │               ├─► get_db_connection()
    │               │               │       │
    │               │               │       ├─► Connect to MySQL
    │               │               │       │   host: mysql (container name)
    │               │               │       │   port: 3306
    │               │               │       │
    │               │               │       └─► Return connection
    │               │               │
    │               │               ├─► Execute query: SELECT 1
    │               │               │
    │               │               ├─► Close connection
    │               │               │
    │               │               └─► Return: jsonify({"db": "ok"})
    │               │
    │               └─► Flask creates HTTP Response
    │                       │
    │                       ├─► Status: 200 OK
    │                       ├─► Headers: Content-Type: application/json
    │                       └─► Body: {"db": "ok"}
    │
    └─► Gunicorn sends response to client
```

## ⚡ Performance với Multiple Requests

### Scenario: 5 concurrent requests

```
Time    Request 1    Request 2    Request 3    Request 4    Request 5
─────────────────────────────────────────────────────────────────────
T0      → Master     → Master     → Master     → Master     → Master
T1      → Worker 1   → Worker 2   → Worker 1   → Worker 2   → Queue
T2      Processing   Processing   Processing   Processing   Wait...
T3      Processing   Processing   Processing   Processing   Wait...
T4      ← Response   ← Response   ← Response   ← Response   → Worker 1
T5      Done         Done         Done         Done         Processing
T6      -            -            -            -            ← Response
T7      -            -            -            -            Done
```

**Lưu ý:**
- Worker 1 và Worker 2 xử lý đồng thời
- Request 5 phải đợi worker rảnh
- Với 2 workers, tối đa 2 requests đồng thời

## 🔍 So Sánh: Development vs Production

### Development (Flask Dev Server)

```
python wsgi.py
    │
    └─► Flask Development Server
            │
            ├─► Single-threaded
            ├─► Hot-reload enabled
            ├─► Debug mode
            └─► Không phù hợp production
```

### Production (Gunicorn)

```
gunicorn wsgi:app -w 2
    │
    ├─► Gunicorn Master
    │       │
    │       ├─► Worker 1 (Flask App)
    │       ├─► Worker 2 (Flask App)
    │       ├─► Multi-process
    │       ├─► Production-ready
    │       └─► Fault tolerance
    │
    └─► Xử lý concurrent requests hiệu quả
```

## 📊 Metrics và Monitoring

### Process Tree

```
gunicorn (master, PID 1)
├── gunicorn (worker 1, PID 10)
│   └── Flask app instance
└── gunicorn (worker 2, PID 11)
    └── Flask app instance
```

### Resource Usage

```
Memory:
- Master: ~50MB
- Worker 1: ~100MB (Flask app + dependencies)
- Worker 2: ~100MB (Flask app + dependencies)
Total: ~250MB

CPU:
- Master: Low (chỉ quản lý)
- Workers: Medium-High (xử lý requests)
```

### Request Throughput

```
1 Worker:  ~100 requests/second
2 Workers: ~200 requests/second
4 Workers: ~400 requests/second
```

---

## 🎯 Tóm Tắt Luồng Chính

1. **Startup**: Container → Gunicorn Master → Import wsgi.py → Create Flask App → Fork Workers
2. **Request**: Client → Master → Worker → Flask Routing → Route Handler → Response
3. **Architecture**: Master-Worker model với load balancing
4. **Benefits**: Concurrent processing, fault tolerance, production-ready


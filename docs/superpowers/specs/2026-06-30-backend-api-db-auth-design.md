# Design: Backend API + Database (SQL Server) + Auth (Subsystem 3)

## Mục tiêu

Xây lớp backend API + database + auth cho Q-SmartEnergy, biến PoC Streamlit hiện tại thành 1 web app multi-user thật: đăng ký/đăng nhập, mỗi user tự quản lý danh sách thiết bị, chạy tối ưu hóa, xem lịch sử. Frontend là React (`client/`, đã có sẵn scaffold Vite). Backend tái sử dụng TOÀN BỘ pipeline Python hiện có (`calc.py`, `appliance_catalog.py`, `data_prep.py`, `qubo_builder.py`, `quantum_runner.py`, `visualizer.py`) — không port logic sang ngôn ngữ khác.

Đây là subsystem 3 trong 3 subsystem đã decompose từ yêu cầu ban đầu (1: data model — DONE; 2: storytelling + lịch chỉnh sửa — chưa brainstorm, làm sau subsystem này; 3: kiến trúc app — spec này).

## 1. Backend: FastAPI (Python)

Lớp wrapper REST mỏng quanh pipeline đã có. KHÔNG đổi logic core (`qubo_builder.build_qubo`, `quantum_runner.QuantumScheduler`, v.v.) — chỉ thêm route handler gọi chúng.

### Cấu trúc thư mục (mới)

```
server/                  # MỚI — ngang hàng với client/ và q-smartenergy/
  main.py                 # FastAPI app, đăng ký routers
  database.py              # SQLAlchemy engine/session, connection string từ .env
  models.py                 # ORM models: User, ApplianceModel, ScheduleModel
  auth.py                     # JWT encode/decode, bcrypt hash/verify, get_current_user dependency
  routers/
    auth_router.py             # /auth/register, /auth/login
    appliances_router.py        # /appliances CRUD
    optimize_router.py           # /optimize, /schedules
  requirements.txt              # fastapi, uvicorn, sqlalchemy, pyodbc, python-jose, passlib[bcrypt], pytest, httpx
  .env.example                   # mẫu JWT_SECRET, DB connection string (KHÔNG commit .env thật)
  tests/
```

`server/` import trực tiếp các module trong `q-smartenergy/` (vd `from calc import ...`, `from appliance_catalog import ...`) — chạy server với `PYTHONPATH` trỏ vào `q-smartenergy/` (vd `PYTHONPATH=../q-smartenergy uvicorn server.main:app`, ghi rõ trong README setup), KHÔNG copy/port lại code.

## 2. Database: SQL Server (đã cài sẵn trên máy), qua SQLAlchemy + pyodbc

Đổi sang DB khác sau này chỉ cần đổi connection string (SQLAlchemy abstraction).

### Schema

```
users
  id            INT PK IDENTITY
  username      NVARCHAR(50) UNIQUE NOT NULL
  password_hash NVARCHAR(255) NOT NULL   -- bcrypt hash, KHÔNG lưu plaintext
  created_at    DATETIME2 DEFAULT SYSUTCDATETIME()

appliances
  id              INT PK IDENTITY
  user_id         INT FK -> users.id
  name            NVARCHAR(100) NOT NULL
  power_w         FLOAT NOT NULL
  duration_hours  FLOAT NOT NULL
  candidate_hours NVARCHAR(50)   -- lưu dạng "7,13" (comma-separated), rỗng "" nếu is_flexible=False
  is_flexible     BIT NOT NULL DEFAULT 1
  created_at      DATETIME2 DEFAULT SYSUTCDATETIME()

schedules
  id                INT PK IDENTITY
  user_id           INT FK -> users.id
  created_at        DATETIME2 DEFAULT SYSUTCDATETIME()
  day_of_month      INT NOT NULL
  weather_condition NVARCHAR(20) NOT NULL
  solver_used       NVARCHAR(30) NOT NULL
  used_fallback     BIT NOT NULL
  energy            FLOAT NOT NULL
  schedule_json     NVARCHAR(MAX) NOT NULL   -- {"Tên thiết bị": giờ, ...} dạng JSON string
  monthly_kwh       FLOAT NOT NULL    -- snapshot: appliance_catalog.total_monthly_kwh(user's appliances) lúc chạy
  bill_before_vnd   FLOAT NOT NULL    -- snapshot: tính riêng cho user này (xem mục 4)
  bill_after_vnd    FLOAT NOT NULL
```

Khi user đăng ký: seed `appliances` từ `appliance_catalog.HOUSEHOLD_APPLIANCES` (12 thiết bị mặc định, copy vào DB gắn `user_id` của họ). Sau đó CRUD tự do (thêm/sửa/xóa), không còn ràng buộc với catalog gốc.

## 3. Auth: JWT + bcrypt

- `POST /auth/register` (username, password) → hash bcrypt, tạo user, seed appliances, trả JWT.
- `POST /auth/login` (username, password) → verify bcrypt, trả JWT.
- Logout: phía client tự xóa token (JWT stateless, không cần endpoint).
- JWT secret đọc từ biến môi trường (`.env`, KHÔNG hard-code, KHÔNG commit vào git). Token hết hạn sau 24h (đủ cho 1 buổi demo, không cần refresh-token — refresh là nice-to-have nếu cần phiên dài hơn).
- Password tối thiểu 8 ký tự (validate ở FastAPI Pydantic schema, lỗi rõ ràng nếu không đủ) — không yêu cầu phức tạp hơn (chữ hoa/số/ký tự đặc biệt) cho PoC.
- CORS middleware khai báo rõ origin của React dev server (vd `http://localhost:5173`) — tránh lỗi CORS khi 2 service chạy port khác nhau.

## 4. Tính hóa đơn RIÊNG cho từng user (không dùng số global tĩnh của calc.py)

`calc.py` thêm 1 tham số optional (additive, không phá API cũ):

```python
def grid_purchase_kwh(self_consumption_rate: float, monthly_kwh: float = None) -> float:
    """monthly_kwh: nếu None, dùng module-level MONTHLY_KWH (hành vi cũ, không đổi cho mọi
    caller hiện có). Truyền riêng để tính cho 1 user cụ thể (xem backend bill_service)."""
    if monthly_kwh is None:
        monthly_kwh = MONTHLY_KWH
    solar_self_consumed = SOLAR_MONTHLY_GENERATION_KWH * self_consumption_rate
    return monthly_kwh - solar_self_consumed
```

Backend tính bill cho 1 user:
```python
user_monthly_kwh = appliance_catalog.total_monthly_kwh(user_appliances)  # từ DB, không phải HOUSEHOLD_APPLIANCES tĩnh
bill_before = calc.calculate_bill(calc.grid_purchase_kwh(calc.SELF_CONSUMPTION_BEFORE, user_monthly_kwh))
bill_after = calc.calculate_bill(calc.grid_purchase_kwh(calc.SELF_CONSUMPTION_AFTER, user_monthly_kwh))
```
`EVN_TIERS`/`VAT_RATE`/`SELF_CONSUMPTION_BEFORE/AFTER` dùng chung cho mọi user (chính sách EVN + giả định solar, không đặc thù từng người). Nếu user xóa/thêm thiết bị, `bill_before/after` đổi theo NGAY — không còn là số tĩnh không phản hồi hành động của user.

## 5. API Endpoints

| Method | Path | Việc làm |
|---|---|---|
| POST | `/auth/register` | Tạo user, seed appliances, trả JWT |
| POST | `/auth/login` | Verify, trả JWT |
| GET | `/appliances` | List thiết bị của user hiện tại (theo JWT) |
| POST | `/appliances` | Thêm thiết bị mới |
| PUT | `/appliances/{id}` | Sửa thiết bị |
| DELETE | `/appliances/{id}` | Xóa thiết bị |
| POST | `/optimize` | Input: day_of_month, weather_condition, use_quantum. Chạy pipeline trên thiết bị FLEXIBLE của user (lọc qua `split_by_flexibility`), tính bill riêng cho user (mục 4), lưu vào `schedules`, trả về: schedule, energy, solver_used, monthly_kwh, bill_before, bill_after, savings_percent, 2 ảnh PNG base64 (Gantt + bar chart từ `visualizer.py`) |
| GET | `/schedules` | Lịch sử các lần optimize của user (mới nhất trước) |

`/optimize` dùng `appliance_catalog.split_by_flexibility(user_appliances)` để tách flexible (vào `qubo_builder.build_qubo`) khỏi fixed (chỉ tính vào `monthly_kwh`, không phải biến QUBO) — đúng kiến trúc đã có từ subsystem 1.

## 6. Render chart: ảnh PNG base64, không vẽ lại bằng React

`visualizer.plot_schedule_gantt`/`plot_cost_comparison` đã có, trả `matplotlib.figure.Figure`. Backend convert sang PNG bytes → base64 string → nhúng vào JSON response. Frontend chỉ cần `<img src="data:image/png;base64,...">`. Không cần thư viện chart JS, không cần viết lại logic vẽ. Chart tương tác/kéo-thả thật (nếu cần) là việc của subsystem 2 sau, không phải đây.

## 7. Ẩn QUBO/QAOA khỏi UI chính

Trang chính (Dashboard) dùng wording: "Tối ưu hóa lịch chạy", "Kết quả tiết kiệm" — không nhắc QUBO/QAOA. Một trang riêng "Công nghệ" (route `/tech` hoặc tương tự) giải thích kỹ thuật cho ai muốn xem (giám khảo hỏi sâu).

## 8. Testing với SQL Server

Test backend chạy thẳng vào instance SQL Server đã cài (không SQLite riêng cho test) — mỗi test wrap trong transaction, rollback ở cuối (`pytest` fixture dùng SQLAlchemy session + `transaction.rollback()`), không để lại data rác. Cần 1 connection string riêng cho test (DB name khác, vd `q_smartenergy_test`) để không đụng data thật.

## 9. Must-have vs Nice-to-have

**Must-have (demo):**
- FastAPI wrapper quanh pipeline có sẵn, đúng 5 endpoint nhóm ở mục 5
- SQL Server: 3 bảng users/appliances/schedules, seed appliances lúc đăng ký
- JWT register/login, bcrypt hash, CORS + secret qua biến môi trường
- Bill tính riêng theo user (mục 4) — KHÔNG dùng số tĩnh
- React: trang login/register, CRUD thiết bị, nút tối ưu hóa → hiện Gantt+bar chart (ảnh PNG từ backend), trang lịch sử
- Ẩn QUBO/QAOA khỏi UI chính

**Nice-to-have (cắt nếu thiếu thời gian, KHÔNG làm trước must-have):**
- Onboarding tutorial từng bước
- Quên mật khẩu / xác thực email
- Đa hộ gia đình/user (1 user hiện chỉ có 1 bộ thiết bị)
- Progress indicator real-time khi optimize (QAOA ~1-2s nên ít cần)
- Rate-limiting chống brute-force login
- Chart tương tác/kéo-thả native React (việc của subsystem 2)

## 10. Ngoài phạm vi

- Storytelling/diễn giải tự nhiên cho chart, lịch chỉnh sửa kéo-thả real-time — subsystem 2, brainstorm riêng.
- Deploy lên cloud/hosting thật — chỉ cần chạy local cho demo.

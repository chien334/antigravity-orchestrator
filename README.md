# 🚀 Antigravity Multi-Agent Orchestrator Kit

Bộ công cụ thiết lập và điều phối đội ngũ AI Agent tự động hóa (**Multi-Agent Orchestrator Swarm**) dành cho Google Antigravity (`agy`), được đóng gói độc lập để chia sẻ và cài đặt dễ dàng cho các thành viên trong đội ngũ kỹ thuật.

Phiên bản mới nâng cấp toàn diện lên **Kiến Trúc Đội Ngũ 5 Tầng Bảng Tuần Hoàn (5-Tier Periodic Table Fleet Architecture)** bổ sung tích hợp hạng nhất cho **Gemini 4 Hydrogen** (High-Throughput Agentic Workhorse — 198 tok/s, 2.5x speed, tiết kiệm 95% chi phí cache) song hành cùng **Gemini 4 Carbon** (Frontier Reasoning) và **Gemini 4 Argon** (Deep Architectural Reasoning), hệ thống ngắt mạch tự phục hồi (**Fast-Retry Circuit Breaker**), hàng đợi sẵn sàng DAG tự động (**DAG Ready-Queue Evaluator**), bảng phân tích tài chính theo từng model (**5-Tier Financial Analytics**), và cơ chế xuất biên bản kiểm toán (**Mission Audit Exporter**).

---

## 🌟 Tính Năng Nổi Bật

- **Kiến trúc 1-Agent = 1-Skill**: Phân quyền rành mạch giữa các persona chuyên biệt (`spec-engineer`, `task-planner`, `builder`, `test-engineer`, `code-reviewer`, `security-auditor`, `debugger`, `observability`).
- **Chuỗi Handoff Không Loãng Ngữ Cảnh (Zero Context Bloat)**: Output của Bước N tự động trở thành Input con trỏ (`file:///...`) cho Bước N+1 thông qua các Artifact chuẩn hóa (`.spec.md` ➔ `.plan.md` ➔ Code ➔ `test_report.json` ➔ `review_signoff.md` ➔ `security_audit.md`).
- **Định Tuyến Model 5 Tầng Bảng Tuần Hoàn (5-Tier Periodic Table Routing)**:
  - ✦ **Tier 1: Gemini 4 Carbon** (`gemini-4-carbon`, Frontier Reasoning): Dành cho kiểm toán an ninh mạng chuyên sâu, phân tích lỗ hổng OWASP/CVE, đặc tả kiến trúc PRD mức độ phức tạp cao, và cô lập lỗi đa thành phần. Hỗ trợ `reasoning_effort` (`low`, `medium`, `high`). Giá: $2.00 in / $10.00 out / $0.50 cache (USD / 1M tokens).
  - ✦ **Tier 2: Gemini 4 Argon** (`gemini-4-argon`, Deep Reasoning): Dành cho lập kế hoạch kiến trúc hệ thống, phân rã Task DAG, review code 5 trục chất lượng, và điều phối fleet. Hỗ trợ `reasoning_effort: medium | high`. Giá: $1.25 in / $5.00 out / $0.3125 cache.
  - ✦ **Tier 3: Gemini 4 Hydrogen** (`gemini-4-hydrogen`, High-Throughput Workhorse - MỚI): Ngựa thồ tốc độ cao (198 tok/s, nhanh hơn 2.5x so với Flash) dành cho parallel builders, sinh test suite tự động, trinh sát codebase, và lặp giao diện UI. Hỗ trợ mức tư duy sâu **`xhigh`** độc quyền. Đơn giá đọc cache siêu rẻ **$0.075 / 1M tokens** (tiết kiệm tới 95%). Giá: $1.50 in / $7.50 out / $0.075 cache.
  - ⚡ **Tier 4: Gemini 3.8 Flash** (`gemini-3.8-flash`, Cost-Efficient Builder / Bulk): Dành cho các worker viết code và sinh bộ test song song ở chế độ tiết kiệm chi phí (`cost_saving`). Giá: $0.075 in / $0.30 out / $0.01875 cache.
  - ⚡ **Tier 5: Gemini 3.8 Flash-Lite** (`gemini-3.8-flash-lite`, Ultra-Fast Micro-Tier): Dành cho logging nhịp tim telemetry, định dạng tài liệu, và linting nhanh. Giá: $0.0375 in / $0.15 out / $0.01 cache.
- **Mô Hình "Fast Hands, Deep Brain" & Fast-Retry Circuit Breaker**:
  - *Scout-Then-Architect*: Hydrogen trinh sát thần tốc codebase, trả về URI con trỏ gọn nhẹ (`file:///...#L10-L40`), giúp Argon nhận ngữ cảnh cô đọng (<4k tokens, giảm 80% chi phí).
  - *Fan-Out Song Song + Dual Quality Gate*: Lên tới 8 Hydrogen builder cùng test-engineer chạy song song ở vận tốc 198 tok/s, sau đó nghiệm thu qua 2 cổng gác: Review 5 trục chất lượng (Argon) và Quét bảo mật OWASP (Carbon).
  - *Fast-Retry Circuit Breaker*: Nếu gặp lỗi, Hydrogen tự sửa 1 lượt với `reasoning_effort: xhigh`. Nếu lỗi tiếp tục lặp lại (`retry_count >= 2`), kích hoạt ngắt mạch tự động leo thang lên Gemini 4 Carbon (`high` effort) để chẩn đoán gốc rễ.
- **Tự Động Hóa Hàng Đợi Sẵn Sàng DAG (Automated DAG Ready-Queue)**: Endpoint `GET /api/dag/ready` và lệnh `client.py next-ready` tự động phân tích điều kiện phụ thuộc `depends_on`, phát hiện ngay các task đủ điều kiện để kích hoạt Fan-Out đồng thời trong cùng một lượt.
- **Thực Thi Song Song (Parallel Worker Fan-Out / Fan-In)**: Hỗ trợ worker chạy đồng thời trên các phạm vi file tách biệt (`parallel_group`, `depends_on`) đảm bảo bất biến không xung đột file (**Decoupled File Scope Invariant**).
- **Phân Tích Tài Chính 5 Tầng Model (Per-Model Financial Analytics)**: Đo lường chi tiết số token (Input, Output, Cache Read), chi phí quy đổi USD & VNĐ (tỷ giá cố định 25.400 VND/USD), và tỷ lệ trúng bộ nhớ đệm (Cache Hit Rate %) riêng biệt cho Carbon, Argon, Hydrogen, Flash, và Flash-Lite.
- **Xuất Báo Cáo Kiểm Toán Tự Động (Mission Audit Exporter)**: Endpoint `GET /api/audit/export?format=markdown|json` và lệnh `client.py export` tạo báo cáo nghiệm thu hoàn chỉnh sau mỗi chiến dịch phát triển.
- **Web Dashboard Thời Gian Thực (SSE & SQLite)**: Giao diện tối Dark-mode hiện đại, huy hiệu Obsidian Emerald cho Carbon, huy hiệu Electric Cyan (`#06b6d4`) cho Hydrogen, nhãn nhịp đập tư duy (`xhigh`), biểu đồ DAG trực quan bằng SVG, và modal Sandbox thử nghiệm Smart Router kèm mô phỏng Circuit Breaker.
- **Zero Dependency Runtime**: Hoạt động hoàn toàn trên Python Standard Library (`sqlite3`, `http.server`, `urllib`, `json`, `argparse`, `threading`), không yêu cầu cài đặt thêm bất kỳ thư viện pip nào.

---

## 📦 Cấu Trúc Thư Mục Bộ Cài Đặt

```
antigravity-orchestrator/
├── README.md                      # Tài liệu tổng quan & hướng dẫn sử dụng
├── install.sh                     # Script cài đặt tự động 1-click (Linux / macOS)
├── install.ps1                    # Script cài đặt tự động (Windows PowerShell)
├── Makefile                       # Phím tắt thao tác nhanh (make install, make test, ...)
├── docs/
│   ├── ANTIGRAVITY_CLI_SETUP.md   # Hướng dẫn chi tiết cài đặt & BUILD SOURCE Antigravity CLI
│   ├── WORKFLOW_GUIDE.md          # Đặc tả chi tiết 6 giai đoạn workflow liên hoàn
│   ├── ARCHITECTURE.md            # Thiết kế kiến trúc DAG, Token Telemetry, 5-Tier Models & SQLite
│   ├── specs/                     # Nơi lưu trữ tài liệu đặc tả (Output Stage 1)
│   ├── plans/                     # Nơi lưu trữ kiến trúc kỹ thuật & Task DAG (Output Stage 2)
│   ├── reports/                   # Nơi lưu trữ kết quả kiểm thử tự động JSON (Output Stage 4)
│   ├── reviews/                   # Nơi lưu trữ biên bản nghiệm thu code review (Output Stage 5)
│   └── security/                  # Nơi lưu trữ báo cáo quét bảo mật OWASP (Output Stage 6)
├── packages/
│   ├── orchestrator/
│   │   ├── models.py              # Model Registry 5 tầng, bảng giá & tính toán chi phí token
│   │   ├── router.py              # Smart Router (speed_first, circuit breaker), DAG Ready & Audit
│   │   ├── server.py              # Server Dashboard SSE + SQLite DB + REST API Endpoints
│   │   ├── dashboard.py           # Single-page Web Console HTML/JS + SVG DAG Visualizer (Cyan styling)
│   │   ├── client.py              # Python SDK & CLI điều phối telemetry (hỗ trợ xhigh, retry-count)
│   │   └── requirements.txt       # Zero dependency (sử dụng thư viện chuẩn Python)
│   ├── skills/                    # Thư viện 20 Gói Agent Skills (Chuẩn 1-Agent = 1-Skill của addyosmani)
│   │   ├── multi-agent-orchestrator/   # Skill trung tâm điều phối 5 tầng và theo dõi telemetry
│   │   ├── spec-driven-development/    # spec-engineer: Đặc tả, user stories, acceptance criteria
│   │   ├── planning-and-task-breakdown/# task-planner: Phân rã kiến trúc, DAG, parallel groups
│   │   ├── api-and-interface-design/   # task-planner: Thiết kế contract, schemas, boundary types
│   │   ├── frontend-ui-engineering/    # builder: Xây dựng UI frontend production-grade
│   │   ├── frontend-design/            # builder: Thiết kế thẩm mỹ, typography, layout
│   │   ├── incremental-implementation/ # builder: Thực thi code từng bước, minimal blast radius
│   │   ├── test-driven-development/    # test-engineer: TDD, unit test, mock, assertion gates
│   │   ├── code-review-and-quality/    # code-reviewer: Review 5 trục chất lượng & clean code
│   │   ├── code-simplification/        # code-simplifier: Tối giản code, dọn nợ kỹ thuật
│   │   ├── security-and-hardening/     # security-auditor: Quét OWASP, auth/authz, secret leaks
│   │   ├── performance-optimization/   # performance-auditor: Tối ưu Core Web Vitals, N+1 query
│   │   ├── debugging-and-error-recovery/# debugger: Cách ly nguyên nhân gốc rễ, phục hồi lỗi
│   │   ├── documentation-and-adrs/     # Tài liệu hóa kiến trúc và quyết định kỹ thuật
│   │   ├── git-workflow-and-versioning/# Quản lý nhánh, commit semantic, PR review
│   │   ├── ci-cd-and-automation/       # Pipeline CI/CD, tự động hóa quality gates
│   │   ├── shipping-and-launch/        # Danh mục kiểm tra tiền phát hành (Pre-launch checks)
│   │   ├── source-driven-development/  # Lập trình dựa trên tài liệu nguồn chính thống
│   │   ├── doubt-driven-development/   # Thẩm định phản biện các quyết định quan trọng
│   │   └── observability-and-instrumentation/ # Giám sát, logging, metrics sản xuất
│   ├── workflows/                 # Danh sách slash commands tích hợp trong Antigravity
│   │   ├── orchestrator.md        # /orchestrator (Khởi tạo phiên điều phối 5 tầng)
│   │   ├── workflow-pipeline.md   # /workflow-pipeline (Chạy liên hoàn xuyên suốt)
│   │   ├── workflow-spec.md       # /workflow-spec (Stage 1: Gemini 4 Carbon)
│   │   ├── workflow-plan.md       # /workflow-plan (Stage 2: Gemini 4 Argon)
│   │   ├── workflow-build.md      # /workflow-build (Stage 3: Gemini 4 Hydrogen 198 tok/s)
│   │   ├── workflow-test.md       # /workflow-test (Stage 4: Gemini 4 Hydrogen kiểm thử)
│   │   ├── workflow-review.md     # /workflow-review (Stage 5: Gemini 4 Argon nghiệm thu)
│   │   └── workflow-security.md   # /workflow-security (Stage 6: Gemini 4 Carbon quét bảo mật)
│   └── commands/
│       └── orchestrator.toml      # Cấu hình slash command TOML
└── tests/
    ├── test_orchestrator.py       # Bộ kiểm thử tự động cốt lõi (100% pass)
    ├── test_carbon_evolution.py   # Bộ kiểm thử mở rộng Gemini 4 Carbon, Router & Analytics
    └── test_hydrogen_routing.py   # Bộ kiểm thử toàn diện Gemini 4 Hydrogen, Circuit Breaker & xhigh
```

---

## ⚡ Cài Đặt Nhanh (Quick Start)

### 1. Dành cho Linux / macOS
Mở terminal và chạy lệnh cài đặt tự động:
```bash
git clone https://github.com/your-org/antigravity-orchestrator.git
cd antigravity-orchestrator
chmod +x install.sh
./install.sh
```

Cài đặt vào thư mục mã nguồn dự án mục tiêu:
```bash
./install.sh /path/to/your-project
```

### 2. Dành cho Windows (PowerShell)
Mở PowerShell dưới quyền người dùng:
```powershell
git clone https://github.com/your-org/antigravity-orchestrator.git
cd antigravity-orchestrator
.\install.ps1
```

---

## 🚦 Vận Hành Bộ Công Cụ

### 1. Khởi động Web Dashboard Server
```bash
# Khởi chạy server trên cổng 8484
python3 packages/orchestrator/server.py --port 8484

# Hoặc qua Makefile
make run-server
```
Truy cập giao diện Web:
- **Dashboard UI:** [http://localhost:8484](http://localhost:8484)
- **Luồng dữ liệu SSE:** `http://localhost:8484/events`
- **Mô hình định tuyến:** `http://localhost:8484/api/models`
- **Hàng đợi DAG:** `http://localhost:8484/api/dag/ready`
- **Phân tích tài chính:** `http://localhost:8484/api/analytics/models`
- **Xuất kiểm toán:** `http://localhost:8484/api/audit/export?format=markdown`

### 2. Kích hoạt trong Phiên làm việc Antigravity (`agy`)
Mở terminal tại dự án của bạn và chạy `agy`:
```bash
agy
```
Sau đó trong khung chat Antigravity, gõ:
```
/orchestrator
```
hoặc chạy toàn bộ quy trình liên hoàn:
```
/workflow-pipeline
```

---

## 💻 CLI & SDK Reference (`client.py`)

Bộ công cụ cung cấp giao diện dòng lệnh mạnh mẽ cho subagent và orchestrator:

### 1. Cập nhật trạng thái Task & Đo lường Token
```bash
# Cập nhật task trên Gemini 4 Hydrogen với tốc độ 198 tok/s
python3 packages/orchestrator/client.py update \
  --task BUILD-01 \
  --agent builder \
  --status running \
  --progress 25 \
  --model gemini-4-hydrogen \
  --reasoning-effort high \
  --complexity medium \
  --group BUILD-PARALLEL \
  --scope "src/components/Dashboard.tsx" \
  --notes "Building UI component at 198 tok/sec"
```

Khi hoàn thành task, ghi nhận số lượng token tiêu hao (hưởng chiết khấu 95% cache):
```bash
python3 packages/orchestrator/client.py update \
  --task BUILD-01 \
  --agent builder \
  --status completed \
  --progress 100 \
  --input-tokens 24000 \
  --output-tokens 1800 \
  --cache-tokens 65000 \
  --notes "Implementation passed local build checks"
```

### 2. Đề xuất Model Thông minh (`recommend`)
```bash
# Đề xuất ở chế độ tốc độ cao (speed_first)
python3 packages/orchestrator/client.py recommend \
  --agent builder \
  --complexity medium \
  --budget-mode speed_first \
  --retry-count 0

# Kiểm tra cơ chế ngắt mạch (Circuit Breaker Tripped khi retry >= 2)
python3 packages/orchestrator/client.py recommend \
  --agent builder \
  --complexity medium \
  --retry-count 2

# Nhiệm vụ bảo mật luôn được ghim chặt vào Gemini 4 Carbon
python3 packages/orchestrator/client.py recommend \
  --agent security-auditor \
  --complexity critical \
  --security-impact
```

### 3. Tìm kiếm Task Sẵn sàng trong DAG (`next-ready`)
```bash
python3 packages/orchestrator/client.py next-ready
```

### 4. Liệt kê Danh mục Model & Đơn giá 5 Tầng (`models`)
```bash
python3 packages/orchestrator/client.py models
```

### 5. Xuất Báo Cáo Kiểm Toán Chiến Dịch (`export`)
```bash
# Xuất định dạng Markdown
python3 packages/orchestrator/client.py export --format markdown --out docs/reports/mission_audit_report.md

# Xuất định dạng JSON
python3 packages/orchestrator/client.py export --format json --out docs/reports/mission_audit_report.json
```

---

## 🌐 Danh Sách REST Endpoints

| Phương thức | Đường dẫn | Chức năng | Tham số / Body |
|---|---|---|---|
| `GET` | `/` | Giao diện Web Console Dark-mode (Cyan & Emerald) | Không |
| `GET` | `/events` | Luồng dữ liệu Server-Sent Events (SSE) | Không |
| `GET` | `/api/state` | Trả về toàn bộ trạng thái tasks, logs, metrics | Không |
| `GET` | `/api/models` | Trả về danh mục mô hình 5 tầng trong `MODEL_REGISTRY` | Không |
| `POST` | `/api/router/recommend` | Đề xuất model, mức tư duy và trạng thái Circuit Breaker | `{"agent_type": "...", "complexity": "...", "budget_mode": "speed_first", "retry_count": 0, "has_security_impact": false}` |
| `GET` | `/api/dag/ready` | Tính toán các task không bị chặn trong DAG | Không |
| `GET` | `/api/analytics/models` | Báo cáo chi tiêu token và VNĐ theo 5 model | Không |
| `GET` | `/api/audit/export` | Xuất biên bản kiểm toán nhiệm vụ | `?format=markdown` hoặc `?format=json` |
| `POST` | `/api/tasks` | Tạo mới hoặc cập nhật trạng thái task | `{"task_id": "...", "status": "...", "reasoning_effort": "xhigh", ...}` |
| `POST` | `/api/logs` | Ghi nhận một log telemetry mới | `{"task_id": "...", "level": "info", "message": "..."}` |
| `POST` | `/api/reset` | Xóa sạch trạng thái DB và logs | Không |

---

## 🧪 Kiểm Thử Tự Động (Automated Testing)

Chạy toàn bộ bộ kiểm thử để xác nhận tính toàn vẹn hệ thống:
```bash
python3 -m unittest discover tests/ -v
```
Hoặc dùng Makefile:
```bash
make test
```

---

## 👥 Chia Sẻ Cho Đội Ngũ (Team Collaboration)

Để chia sẻ repo này lên hệ thống Git nội bộ:
```bash
git add .
git commit -m "feat: 5-tier Gemini 4 Hydrogen routing, Fast Hands Deep Brain topologies & docs"
git push origin main
```
Thành viên khác chỉ cần `git clone`, chạy `./install.sh`, và khởi động hệ thống điều phối ngay lập tức!

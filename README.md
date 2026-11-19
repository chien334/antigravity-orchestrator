# 🚀 Antigravity Multi-Agent Orchestrator Kit

Bộ công cụ thiết lập và điều phối đội ngũ AI Agent tự động hóa (**Multi-Agent Orchestrator Swarm**) dành cho Google Antigravity (`agy`), được đóng gói độc lập để chia sẻ và cài đặt dễ dàng cho các thành viên trong đội ngũ kỹ thuật.

Phiên bản mới nâng cấp toàn diện lên **Kiến Trúc Đội Ngũ Bảng Tuần Hoàn Tối Ưu SWE với Gemini 4 Neon (Periodic Table SWE Fleet Architecture)** — bổ sung tích hợp hạng nhất cho **Gemini 4 Neon** (Nguyên tố #10 `Ne` — SWE Frontier & Bộ Não Điều Phối `gemini-pro-orchestrator-neon`: Coding Agent Index #1 `58.64`, Intelligence `61` `xhigh`, `~105 tok/s` nhanh gấp 2x Carbon/Argon, `$3.00/$15.00/$0.15` tiết kiệm 95% cache, giảm ~32% chi phí/tác vụ so với Carbon) song hành cùng **Gemini 4 Hydrogen** (`198 tok/s`, tiết kiệm ~24% quota khi ghép đôi với Neon) và **Gemini 4 Carbon** (bảo vệ tuyệt đối Stage 6 Security Audit & Circuit Breaker Stage 3), đi kèm hệ thống ngắt mạch 3 tầng (**3-Stage Fast-Retry Circuit Breaker**), hàng đợi sẵn sàng DAG tự động (**DAG Ready-Queue Evaluator**), bảng phân tích tài chính theo từng model, và cơ chế xuất biên bản kiểm toán (**Mission Audit Exporter**).

---

## 🌟 Tính Năng Nổi Bật

- **Kiến trúc 1-Agent = 1-Skill**: Phân quyền rành mạch giữa các persona chuyên biệt (`spec-engineer`, `task-planner`, `builder`, `test-engineer`, `code-reviewer`, `security-auditor`, `debugger`, `observability`).
- **Chuỗi Handoff Không Loãng Ngữ Cảnh (Zero Context Bloat)**: Output của Bước N tự động trở thành Input con trỏ (`file:///...`) cho Bước N+1 thông qua các Artifact chuẩn hóa (`.spec.md` ➔ `.plan.md` ➔ Code ➔ `test_report.json` ➔ `review_signoff.md` ➔ `security_audit.md`).
- **Định Tuyến Model Bảng Tuần Hoàn (Gemini 4 Neon SWE Fleet Routing)**:
  - ✦ **Tier 1: Gemini 4 Carbon** (`gemini-4-carbon`, Frontier Security & Escalation): Khóa chặt cho Stage 6 Security Audit, tác vụ auth/crypto/OWASP/CVE/migration (`has_security_impact`, `complexity == "critical"`), và Circuit Breaker Stage 3 (`retry_count >= 3`). Hỗ trợ `reasoning_effort` (`low`, `medium`, `high`). Giá: $2.00 in / $10.00 out / $0.50 cache *(tăng lên $4/$20 từ 01/12/2026)*.
  - ⚡✦ **Tier 1.5 / 2: Gemini 4 Neon** (`gemini-4-neon` / `gemini-pro-orchestrator-neon`, SWE Frontier & Orchestrator Brain - MỚI): Nguyên tố #10 — Coding Agent Index #1 (`58.64`), Intelligence `61` (hỗ trợ **`xhigh`**), tốc độ `~105 tok/s` (gấp 2x Carbon/Argon), tiết kiệm ~32% chi phí/tác vụ so với Carbon. **Thay thế hoàn toàn `gemini-4-argon`** ở `orchestrator`, `task-planner`, `code-reviewer`, đồng thời **đảm nhận** `spec-engineer` (phi bảo mật), `debugger`, `performance-auditor`, `builder` đa file (`>= 4` files), và Circuit Breaker Stage 2 (`retry_count == 2`). Giá: **$3.00 in / $15.00 out / $0.15 cache** (giảm 95% cache read).
  - ✦ **Tier 2b: Gemini 4 Argon** (`gemini-4-argon`, Legacy Deep Reasoning): Đã được thay thế bởi `gemini-4-neon` trong luồng SWE mặc định; giữ lại làm entry tương thích lịch sử & fallback dự phòng. Giá legacy: $1.25 in / $5.00 out / $0.3125 cache *(giá API chính thức $2/$10 ➔ $4/$20 từ 01/12/2026)*.
  - ⚡ **Tier 3: Gemini 4 Hydrogen** (`gemini-4-hydrogen`, High-Throughput Workhorse): Đôi tay tốc độ cao (**198 tok/s**, nhanh gấp ~2x Neon và tránh độ trễ TTFT ~40s) ghép đôi cùng `Orchestrator (Neon)` (tiết kiệm ~24% quota) cho các `builder` phạm vi gọn (`<= 3` files), `test-engineer`, `scout`, và lặp giao diện UI. Hỗ trợ **`xhigh`** cho lượt tự sửa lỗi Stage 1. Giá: $1.50 in / $7.50 out / $0.075 cache (giảm 95% cache).
  - ⚡ **Tier 4: Gemini 3.8 Flash** (`gemini-3.8-flash`, Cost-Efficient & Active Micro-Tier): Mặc định hiện hành (`low` effort) cho chế độ `cost_saving`, scaffolding, `doc-generator`, `code-simplifier`, và telemetry/linting (thay thế `gemini-3.8-flash-lite` không có trong runtime thực tế). Giá live: $0.75 in / $3.75 out / $0.075 cache. *(Legacy `gemini-3.8-flash-lite` chỉ còn là alias lịch sử cho DB).*
- **Mô Hình "Fast Hands, Deep Brain" & 3-Stage Fast-Retry Circuit Breaker**:
  - *Scout-Then-Architect*: Hydrogen trinh sát thần tốc codebase, trả về URI con trỏ gọn nhẹ (`file:///...#L10-L40`), giúp **Gemini 4 Neon** nhận ngữ cảnh cô đọng (<4k tokens, giảm 80% chi phí).
  - *Fan-Out Song Song + Dual Quality Gate*: Lên tới 8 Hydrogen builder (`<= 3` files) cùng `test-engineer` chạy song song ở 198 tok/s (các refactor `>= 4` files giao cho Neon), sau đó nghiệm thu qua 2 cổng gác: Review 5 trục chất lượng (**Gemini 4 Neon**) và Quét bảo mật OWASP (**Gemini 4 Carbon**).
  - *3-Stage Fast-Retry Circuit Breaker*: Nếu gặp lỗi, Stage 1 (`retry_count == 1`) Hydrogen tự sửa 1 lượt với `reasoning_effort: xhigh`; Stage 2 (`retry_count == 2`) leo thang lên **Gemini 4 Neon** (`high`/`xhigh`); Stage 3 (`retry_count >= 3` hoặc chạm ranh giới bảo mật) ngắt mạch cứng lên **Gemini 4 Carbon** (`high` effort).
- **Tự Động Hóa Hàng Đợi Sẵn Sàng DAG (Automated DAG Ready-Queue)**: Endpoint `GET /api/dag/ready` và lệnh `client.py next-ready` tự động phân tích điều kiện phụ thuộc `depends_on`, phát hiện ngay các task đủ điều kiện để kích hoạt Fan-Out đồng thời trong cùng một lượt.
- **Thực Thi Song Song (Parallel Worker Fan-Out / Fan-In)**: Hỗ trợ worker chạy đồng thời trên các phạm vi file tách biệt (`parallel_group`, `depends_on`) đảm bảo bất biến không xung đột file (**Decoupled File Scope Invariant**).
- **Phân Tích Tài Chính Theo Model (Per-Model Financial Analytics)**: Đo lường chi tiết số token (Input, Output, Cache Read), chi phí quy đổi USD & VNĐ (tỷ giá cố định 25.400 VND/USD), và tỷ lệ trúng bộ nhớ đệm (Cache Hit Rate %) riêng biệt cho Carbon, Neon, Argon, Hydrogen, và 3.8 Flash.
- **Xuất Báo Cáo Kiểm Toán Tự Động (Mission Audit Exporter)**: Endpoint `GET /api/audit/export?format=markdown|json` và lệnh `client.py export` tạo báo cáo nghiệm thu hoàn chỉnh sau mỗi chiến dịch phát triển.
- **Web Dashboard Thời Gian Thực (SSE & SQLite)**: Giao diện tối Dark-mode hiện đại, huy hiệu Obsidian Emerald cho Carbon, **Neon Violet (`#a855f7`) cho Gemini 4 Neon / `gemini-pro-orchestrator-neon`**, huy hiệu Electric Cyan (`#06b6d4`) cho Hydrogen, huy hiệu Teal cho **Gemini Desktop App**, nhãn nhịp đập tư duy (`xhigh`), biểu đồ DAG trực quan bằng SVG, modal Sandbox thử nghiệm Smart Router kèm mô phỏng 3-Stage Circuit Breaker, và bảng theo dõi hàng đợi **Desktop Worker + AGY Quota Saved**.
- **Cầu Nối Gemini Desktop App Đa Nền Tảng & Chính Sách Phân Bổ Ngang Hàng Có Điều Kiện 60% (`ORCHESTRATOR_DESKTOP_SHARE=0.60`)**:
  - **Cổng Kiểm Tra Tiền Khởi Động (`desktop-doctor` / `GET /api/desktop/status`)**:
    - **Khi Gemini Desktop App ĐÃ cài đặt & sẵn sàng (`ready == true` trên macOS hoặc Windows)**: `gemini-desktop-app` vận hành như một **mô hình ngang hàng hạng nhất (first-class peer model)** (`mode="task"`, `background=True`, `allow_edits=True/False`, `0` lần chuyển focus, `$0.00` chi phí token API AGY), được ưu tiên **~60% tổng khối lượng công việc SWE** (`ORCHESTRATOR_DESKTOP_SHARE=0.60`): đảm nhận các giai đoạn nặng tuần tự (`spec-engineer`, `task-planner`, `code-reviewer`, `debugger`, `performance-auditor`, `doc-generator`) + **tối đa 1 builder nặng cho mỗi `parallel_group`** (đảm bảo khóa FIFO một cửa sổ của `Gemini.app` KHÔNG BAO GIỜ chặn Fan-Out song song!). Phần **~40% còn lại** chạy đồng thời trên AGY API (`gemini-4-hydrogen` `198 tok/s` cho các builder/tester/scout song song còn lại, `gemini-4-neon` xử lý tràn tải khi hàng đợi Desktop bận, và `gemini-4-carbon` `high` khóa chặt Rule 1 Security Audits).
    - **Khi Gemini Desktop App CHƯA cài đặt hoặc CHƯA sẵn sàng (`ready == false`, ví dụ thiếu app hoặc màn hình đang khóa)** — hoặc truyền `--no-desktop` / `--api-only`: Tự động chuyển về **100% đội hình API thuần (`Gemini 4 Neon` + `Gemini 4 Hydrogen` + `Gemini 4 Carbon` + `Gemini 3.8 Flash`)** một cách mượt mà như trước đây!
  - **Thực Thi Nền Im Lặng (`--background`, mặc định `True`) — 0% cướp focus cửa sổ**:
    - **macOS (`macos_ax`)**: Tự động phát hiện `com.google.GeminiMacOS` / `com.google.gemini` (`/Applications/Gemini.app`), mở phiên mới qua deep link `googlegemini://newchat?ext_src=app_shortcut`, hỗ trợ **2 chế độ tương tác**: **`Task` mode (Mặc định — `--mode task`)** gắn trực tiếp thư mục dự án (`--workspace <path>`, tự động mặc định `os.getcwd()`) qua daemon-thread `AXPress` trên menu `Folders` (`ConnectedFolderNSMenu`, không di chuyển con trỏ `CGEvent`) giúp Gemini App đọc/xử lý file theo đường dẫn tương đối (`allow_edits=False` cho phân tích chỉ đọc, hoặc `allow_edits=True` cho tối đa 1 builder nặng/nhóm), và **`Chat` mode (`--mode chat`)** cho prompt độc lập. Trong chế độ nền mặc định (`background=True`), hệ thống ghi trực tiếp `AXValue` + bấm gửi `AXPress` (không gõ phím, không chạm clipboard), theo dõi thụ động `~/Library/Caches/com.google.GeminiMacOS/Logs/diagnostic*.log` suốt 15–240 giây (**0% gián đoạn focus** khi bạn làm việc ở ứng dụng khác), trích xuất nguyên văn `AXStaticText.AXDescription`, và khôi phục tức thì `AXFrontmost` nếu `OmnichatWindow` từng bị ẩn. Cờ **`--allow-foreground` (chỉ bật khi cần)** chỉ dùng đúng 1 lần khi đăng ký thư mục mới chưa có bookmark qua hộp thoại macOS `NSOpenPanel` (`Add new folder…`).
    - **Windows (`windows_uia`)**: Tự động tìm `Gemini.exe` (`%LOCALAPPDATA%\Programs\Gemini\Gemini.exe`, Start Menu, Edge/Chrome PWA) và chạy PowerShell `-Sta -WindowStyle Minimized` sử dụng thuần `.NET UIAutomation` (**`ValuePattern` + `InvokePattern` + `TextPattern`**) với **`0` `SetForegroundWindow`, `0` `SendKeys`, `0` `Clipboard`** thông qua file tạm riêng tư (`0600`).
    - **Linux (`linux_pwa`) & CI (`mock`)**: Hỗ trợ Chromium/Edge PWA (`--app=https://gemini.google.com`) trên X11/Wayland (`wl-copy`/`xclip`/`xdotool`) và trình giả lập `MockGeminiDriver` cho CI/headless.
    - **Lá Chắn Bảo Mật & Chống Cắt Xén**: `SecretRedactor` (ẩn tự động 8 loại khóa API/JWT/PEM/DSN trước khi gửi hoặc lưu SQLite `prompt_preview`, hỗ trợ `--strict-secrets`), **Zero-Clipboard Silent Mode** (không chạm clipboard khi chạy `AXValue`/`UIAutomation` nền; giữ **Clipboard Save/Restore** `try...finally <= 300ms` cho đường fallback), **Split-Literal Sentinel Protocol** (`<<<AGY_DESKTOP_START:{job_id}>>>` / `<<<AGY_DESKTOP_DONE:{job_id}>>>` + `>= 500ms` stability debounce), khóa cửa sổ đơn (`threading.Lock` + `fcntl.flock`/`msvcrt.locking` + hàng đợi FIFO `desktop_jobs`), và xuất kết quả chuẩn hóa về `docs/reports/desktop_worker/{job_id}.md`.
- **Zero Dependency Runtime**: Hoạt động hoàn toàn trên Python Standard Library (`sqlite3`, `http.server`, `urllib`, `json`, `argparse`, `threading`, `plistlib`), không yêu cầu cài đặt thêm bất kỳ thư viện pip nào.

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
│   │   └── desktop_worker/        # Báo cáo phân tích từ Gemini Desktop App Worker ({job_id}.md)
│   ├── reviews/                   # Nơi lưu trữ biên bản nghiệm thu code review (Output Stage 5)
│   └── security/                  # Nơi lưu trữ báo cáo quét bảo mật OWASP (Output Stage 6)
├── packages/
│   ├── orchestrator/
│   │   ├── models.py              # Model Registry 5 tầng + EXTERNAL_WORKERS (gemini-desktop-app) & Quota Saved
│   │   ├── router.py              # Smart Router (hybrid_desktop, speed_first, circuit breaker), DAG Ready & Audit
│   │   ├── desktop_worker.py      # Cross-Platform Gemini Desktop App Bridge (macOS/Windows/Linux/Mock + SecretRedactor)
│   │   ├── server.py              # Server Dashboard SSE + SQLite DB (tasks, logs, desktop_jobs) + REST API Endpoints
│   │   ├── dashboard.py           # Single-page Web Console HTML/JS + SVG DAG + Desktop Worker Modal & Quota Saved KPI
│   │   ├── client.py              # Python SDK & CLI điều phối telemetry + desktop-doctor/ask/jobs/cancel
│   │   └── requirements.txt       # Zero dependency (sử dụng thư viện chuẩn Python)
│   ├── skills/                    # Thư viện Gói Agent Skills (Chuẩn 1-Agent = 1-Skill của addyosmani)
│   │   ├── multi-agent-orchestrator/   # Skill trung tâm điều phối 5 tầng và theo dõi telemetry
│   │   ├── gemini-desktop-worker/      # Skill offload tác vụ phân tích nặng sang Gemini Desktop App ($0.00 API)
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
│   │   ├── orchestrator.md        # /orchestrator (Khởi tạo phiên điều phối Neon SWE Fleet)
│   │   ├── workflow-pipeline.md   # /workflow-pipeline (Chạy liên hoàn xuyên suốt)
│   │   ├── workflow-spec.md       # /workflow-spec (Stage 1: Gemini 4 Neon / Carbon nếu bảo mật)
│   │   ├── workflow-plan.md       # /workflow-plan (Stage 2: Gemini 4 Neon)
│   │   ├── workflow-build.md      # /workflow-build (Stage 3: Hydrogen <=3f 198 tok/s | Neon >=4f)
│   │   ├── workflow-test.md       # /workflow-test (Stage 4: Gemini 4 Hydrogen kiểm thử)
│   │   ├── workflow-review.md     # /workflow-review (Stage 5: Gemini 4 Neon nghiệm thu 5 trục)
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

# Kiểm tra cơ chế ngắt mạch 3 tầng (retry=2 leo thang lên Neon, retry>=3 lên Carbon)
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

### 6. Gemini Desktop App Worker Bridge & 60% Peer Allocation (`desktop-doctor`, `allocate-dag`, `desktop-ask`, `desktop-jobs`, `desktop-cancel`)
```bash
# 1. Cổng kiểm tra tính sẵn sàng của Gemini Desktop App trên macOS / Windows / Linux / Mock
python3 packages/orchestrator/client.py desktop-doctor --format text

# 2. Tự động phân bổ DAG theo tỷ lệ 60% Desktop Peer / 40% AGY API (tự động fallback 100% API nếu ready == false)
ORCHESTRATOR_DESKTOP_SHARE=0.60 python3 packages/orchestrator/client.py allocate-dag \
  --target-desktop-share 0.60 \
  --apply

#    Ép dùng 100% đội hình API thuần (tắt phân bổ Desktop)
python3 packages/orchestrator/client.py allocate-dag --no-desktop --apply
python3 packages/orchestrator/client.py allocate-dag --api-only --apply

# 3. Đề xuất định tuyến Hybrid Desktop cho tác vụ phân tích chỉ đọc
python3 packages/orchestrator/client.py recommend \
  --agent spec-engineer \
  --complexity high \
  --budget-mode hybrid_desktop \
  --desktop-available \
  --read-only

# 3. Gửi tác vụ phân tích nặng sang Gemini Desktop App ($0.00 chi phí API AGY)
#    Chạy nền im lặng mặc định (--background, background=True): 0% cướp focus & 0 chạm clipboard!
#    Task mode (mặc định) gắn workspace qua Folders (ConnectedFolderNSMenu) — chỉ cần đường dẫn tương đối
python3 packages/orchestrator/client.py desktop-ask \
  --task SPEC-01 \
  --mode task \
  --workspace . \
  --background \
  --prompt "Inspect docs/specs/my_large_spec.md and packages/orchestrator/router.py (read-only, zero edits)." \
  --driver auto \
  --timeout 180

#    Đăng ký thư mục mới chưa có bookmark trên macOS (chỉ cần --allow-foreground đúng 1 lần cho NSOpenPanel "Add new folder…")
python3 packages/orchestrator/client.py desktop-ask \
  --task SPEC-01B \
  --mode task \
  --workspace /path/to/new-project \
  --allow-foreground \
  --prompt "Inspect README.md (read-only)." \
  --driver auto

#    Hoặc Chat mode độc lập không gắn thư mục workspace
python3 packages/orchestrator/client.py desktop-dispatch \
  --task SPEC-02 \
  --mode chat \
  --prompt-file docs/specs/my_large_spec.md \
  --async

# 4. Theo dõi hàng đợi desktop_jobs hoặc hủy job đang chạy
python3 packages/orchestrator/client.py desktop-jobs --limit 20 --format text
python3 packages/orchestrator/client.py desktop-cancel --job-id dsk-20261117-a1b2
```

---

## 🌐 Danh Sách REST Endpoints

| Phương thức | Đường dẫn | Chức năng | Tham số / Body |
|---|---|---|---|
| `GET` | `/` | Giao diện Web Console Dark-mode (Cyan, Emerald & Teal Desktop Pill) | Không |
| `GET` | `/events` | Luồng dữ liệu Server-Sent Events (SSE) gồm `desktop_job_*` | Không |
| `GET` | `/api/state` | Trả về toàn bộ trạng thái tasks, logs, metrics (kèm `desktop_quota_saved_*`) | Không |
| `GET` | `/api/models` | Trả về danh mục mô hình 5 tầng (`MODEL_REGISTRY`) + `external_workers` | Không |
| `POST` | `/api/router/recommend` | Đề xuất model, mức tư duy, Circuit Breaker & `hybrid_desktop` offload | `{"agent_type": "...", "complexity": "...", "budget_mode": "hybrid_desktop", "desktop_available": true, "read_only": true}` |
| `POST` | `/api/router/allocate-dag` | Phân bổ DAG có điều kiện 60% `gemini-desktop-app` (`ORCHESTRATOR_DESKTOP_SHARE`) hoặc tự động fallback 100% API khi `ready == false` | `{"target_desktop_share": 0.60, "apply": true, "no_desktop": false, "api_only": false}` |
| `GET` | `/api/desktop/status` | Kiểm tra trạng thái Gemini Desktop App theo OS & quota đã tiết kiệm | `?driver=auto&target_os=auto&app_path=...` |
| `POST` | `/api/desktop/dispatch` | Đưa job phân tích (mặc định `mode: "task"`, `background: true` chạy nền không cướp focus, đã scrub secrets & bọc Sentinel) vào hàng đợi Desktop | `{"prompt": "...", "task_id": "...", "mode": "task", "workspace": ".", "background": true, "allow_foreground": false, "driver": "auto", "redact_secrets": true, "async_mode": true}` |
| `GET` | `/api/desktop/jobs` | Liệt kê danh sách `desktop_jobs` & tổng hợp `AGY Quota Saved` | `?job_id=...&status=...&limit=50` |
| `GET` | `/api/desktop/jobs/{job_id}` | Truy xuất chi tiết một desktop job và con trỏ `artifact_path` | Path param `job_id` |
| `POST` | `/api/desktop/cancel` | Hủy job desktop đang chờ hoặc đang chạy (hoặc `POST /api/desktop/jobs/{job_id}/cancel`) | `{"job_id": "..."}` |
| `GET` | `/api/dag/ready` | Tính toán các task không bị chặn trong DAG | Không |
| `GET` | `/api/analytics/models` | Báo cáo chi tiêu token, VNĐ theo 5 model & `desktop_saved_usd` | Không |
| `GET` | `/api/audit/export` | Xuất biên bản kiểm toán nhiệm vụ | `?format=markdown` hoặc `?format=json` |
| `POST` | `/api/tasks` | Tạo mới hoặc cập nhật trạng thái task | `{"task_id": "...", "status": "...", "reasoning_effort": "xhigh", ...}` |
| `POST` | `/api/logs` | Ghi nhận một log telemetry mới | `{"task_id": "...", "level": "info", "message": "..."}` |
| `POST` | `/api/reset` | Xóa sạch trạng thái DB (`tasks`, `logs`, `desktop_jobs`) | Không |

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

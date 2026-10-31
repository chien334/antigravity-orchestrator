# 🚀 Antigravity Multi-Agent Orchestrator Kit

Bộ công cụ thiết lập và điều phối đội ngũ AI Agent tự động hóa (**Multi-Agent Orchestrator Swarm**) dành cho Google Antigravity (`agy`), được đóng gói độc lập để chia sẻ và cài đặt dễ dàng cho các thành viên trong đội ngũ kỹ thuật.

---

## 🌟 Tính Năng Nổi Bật

- **Kiến trúc 1-Agent = 1-Skill**: Phân quyền rành mạch giữa các persona chuyên biệt (`spec-engineer`, `task-planner`, `builder`, `test-engineer`, `code-reviewer`, `security-auditor`).
- **Chuỗi Handoff Không Loãng Ngữ Cảnh (Zero Context Bloat)**: Output của Bước N tự động trở thành Input con trỏ (`file:///...`) cho Bước N+1 thông qua các Artifact chuẩn hóa (`.spec.md` ➔ `.plan.md` ➔ Code ➔ `test_report.json` ➔ `review_signoff.md` ➔ `security_audit.md`).
- **Định Tuyến Model Thông Minh (Model Tiering)**:
  - ✦ **Gemini 4 Argon** (Pro reasoning): Cho lập kế hoạch kiến trúc, review code, phân tích bảo mật và giải quyết vấn đề phức tạp.
  - ⚡ **Gemini 3.8 Flash** (Cost-efficient): Cho các worker thực thi viết code và unit test song song, tiết kiệm hơn 70% chi phí.
- **Thực Thi Song Song (Parallel Worker Fan-Out / Fan-In)**: Hỗ trợ worker chạy đồng thời trên các phạm vi file tách biệt (`parallel_group`, `depends_on`).
- **Web Dashboard Thời Gian Thực (SSE & SQLite)**: Giao diện tối Dark-mode hiện đại, theo dõi tiến độ từng worker, streaming log và thống kê đo lường Token tiêu hao (Input, Output, Cache Read).
- **Tích Hợp Sâu Slash Command**: Hỗ trợ gọi lệnh trực tiếp từ thanh chat của Antigravity (`/orchestrator`, `/workflow-pipeline`, `/workflow-spec`, ...).

---

## 📦 Cấu Trúc Thư Mục Bộ Cài Đặt

```
antigravity-orchestrator-setup/
├── README.md                      # Tài liệu tổng quan & hướng dẫn sử dụng
├── install.sh                     # Script cài đặt tự động 1-click (Linux / macOS)
├── install.ps1                    # Script cài đặt tự động (Windows PowerShell)
├── Makefile                       # Phím tắt thao tác nhanh (make install, make test, ...)
├── docs/
│   ├── ANTIGRAVITY_CLI_SETUP.md   # Hướng dẫn chi tiết cài đặt & BUILD SOURCE Antigravity CLI
│   ├── WORKFLOW_GUIDE.md          # Đặc tả chi tiết 6 giai đoạn workflow liên hoàn
│   └── ARCHITECTURE.md            # Thiết kế kiến trúc DAG, Token Telemetry & SQLite
├── packages/
│   ├── orchestrator/
│   │   ├── server.py              # Server Dashboard SSE + SQLite DB + Token Telemetry
│   │   ├── client.py              # CLI & Python library gửi telemetry
│   │   └── requirements.txt       # Zero dependency (sử dụng thư viện chuẩn Python)
│   ├── skills/
│   │   └── multi-agent-orchestrator/
│   │       └── SKILL.md           # Định nghĩa skill điều phối 1-Agent = 1-Skill
│   ├── workflows/                 # Danh sách slash commands tích hợp trong Antigravity
│   │   ├── orchestrator.md        # /orchestrator (Khởi tạo phiên điều phối)
│   │   ├── workflow-pipeline.md   # /workflow-pipeline (Chạy liên hoàn xuyên suốt)
│   │   ├── workflow-spec.md       # /workflow-spec (Stage 1: Làm rõ yêu cầu)
│   │   ├── workflow-plan.md       # /workflow-plan (Stage 2: Kiến trúc & Task DAG)
│   │   ├── workflow-build.md      # /workflow-build (Stage 3: Worker code song song)
│   │   ├── workflow-test.md       # /workflow-test (Stage 4: Viết & chạy test)
│   │   ├── workflow-review.md     # /workflow-review (Stage 5: Review 5 trục)
│   │   └── workflow-security.md   # /workflow-security (Stage 6: Quét bảo mật)
│   └── commands/
│       └── orchestrator.toml      # Cấu hình slash command TOML
└── tests/
    └── test_orchestrator.py       # Bộ kiểm thử tự động 12 test cases (100% pass)
```

---

## ⚡ Cài Đặt Nhanh (Quick Start)

### 1. Dành cho Linux / macOS
Mở terminal và chạy lệnh cài đặt tự động:
```bash
git clone <URL_REPO_CUA_BAN> antigravity-orchestrator-setup
cd antigravity-orchestrator-setup
chmod +x install.sh
./install.sh
```

Nếu muốn cài đặt và gắn cấu hình trực tiếp vào thư mục mã nguồn dự án cụ thể:
```bash
./install.sh /path/to/your-project
```

### 2. Dành cho Windows (PowerShell)
Mở PowerShell dưới quyền người dùng và thực thi:
```powershell
git clone <URL_REPO_CUA_BAN> antigravity-orchestrator-setup
cd antigravity-orchestrator-setup
.\install.ps1
```

---

## 🛠️ Cài Đặt & Build Source Antigravity CLI (`agy`)

Bộ công cụ này hoạt động trên nền tảng **Google Antigravity CLI (`agy`)**.

### Cách 1: Tải Bản Cài Đặt Chính Thức (Khuyến nghị)
- **Linux / macOS:**
  ```bash
  curl -fsSL https://antigravity.google/cli/install.sh | bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
  agy --version
  ```
- **Windows (PowerShell):**
  ```powershell
  irm https://antigravity.google/cli/install.ps1 | iex
  agy --version
  ```

### Cách 2: Hướng Dẫn Cài Đặt & Build Mã Nguồn (Build from Source)
Xem hướng dẫn chi tiết từng bước tại tài liệu [docs/ANTIGRAVITY_CLI_SETUP.md](docs/ANTIGRAVITY_CLI_SETUP.md), bao gồm:
1. **Build Python SDK từ source**: Clone `https://github.com/google-antigravity/antigravity-sdk-python.git` và build file Wheel nội bộ (`pip install -e .`).
2. **Build Go Binaries**: Thiết lập toolchain Go 1.22+, `CGO_ENABLED=1`, và compile binary `agy`.
3. **Cấu hình Xác thực**: Thiết lập API key (`GEMINI_API_KEY`) hoặc đăng nhập Google Cloud Vertex AI service account cho đội ngũ doanh nghiệp.

---

## 🚦 Vận Hành Bộ Công Cụ

### 1. Khởi động Web Dashboard Server
```bash
# Khởi chạy server trên cổng 8484 với SQLite DB tự động
python3 packages/orchestrator/server.py --port 8484

# Hoặc dùng Makefile
make run-server
```
Truy cập giao diện Web tại:
- **Dashboard:** [http://localhost:8484](http://localhost:8484)
- **Luồng dữ liệu SSE:** `http://localhost:8484/events`

### 2. Kích hoạt trong Phiên làm việc Antigravity
Mở terminal tại dự án của bạn và chạy `agy`:
```bash
agy
```
Sau đó trong khung chat, bạn chỉ cần gõ:
```
/orchestrator
```
hoặc chạy toàn bộ quy trình:
```
/workflow-pipeline
```

Hệ thống sẽ tự động phân rã công việc, gọi các subagent chuyên môn, định tuyến Gemini 4 Argon / Gemini 3.8 Flash, chạy song song các worker và cập nhật trực tiếp lên dashboard!

---

## 🧪 Kiểm Thử Tự Động (Automated Testing)

Đảm bảo toàn bộ 12 bài kiểm thử (REST, SSE, SQLite Persistence, CLI) vượt qua trước khi push:
```bash
make test
# hoặc
python3 tests/test_orchestrator.py
```

---

## 👥 Chia Sẻ Cho Các Thành Viên Trong Team (Team Collaboration)

Để chia sẻ repo này lên GitHub / GitLab nội bộ công ty:
```bash
cd antigravity-orchestrator-setup
git init
git add .
git commit -m "feat: Initial release of Antigravity Multi-Agent Orchestrator Kit"
git remote add origin https://github.com/<your-org>/antigravity-orchestrator-setup.git
git branch -M main
git push -u origin main
```

Mỗi thành viên trong team chỉ cần:
1. `git clone` repo về máy.
2. Chạy `./install.sh`.
3. Bắt đầu làm việc với Antigravity CLI và Orchestrator Dashboard ngay lập tức!

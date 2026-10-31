# Google Antigravity CLI (`agy`) & Source Build Guide

Tài liệu hướng dẫn chi tiết cách cài đặt, cấu hình và build mã nguồn cho **Google Antigravity CLI (`agy`)** trên Linux, macOS và Windows.

---

## 1. Tổng quan về Antigravity CLI (`agy`)

Antigravity CLI (`agy`) là giao diện dòng lệnh (Terminal-based AI Pair Programmer) của Google Antigravity. Nó cho phép lập trình viên tương tác với các model AI cao cấp như **Gemini 4 Argon** và **Gemini 3.8 Flash**, thực thi các subagent, chạy slash commands và kết nối trực tiếp với Model Context Protocol (MCP).

- **Đường dẫn nhị phân mặc định (Linux / macOS):** `~/.local/bin/agy`
- **Đường dẫn nhị phân mặc định (Windows):** `%LOCALAPPDATA%\agy\bin\agy.exe`
- **Thư mục cấu hình cá nhân:** `~/.gemini/antigravity-cli/settings.json`

---

## 2. Phương pháp 1: Cài đặt Bản dựng Sẵn (Official Pre-compiled Binary)

Đây là cách nhanh nhất và ổn định nhất để triển khai cho các thành viên trong đội ngũ:

### Trên Linux / macOS
```bash
# Tự động tải và cài đặt phiên bản mới nhất
curl -fsSL https://antigravity.google/cli/install.sh | bash

# Đảm bảo ~/.local/bin nằm trong biến môi trường PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Kiểm tra phiên bản cài đặt thành công
agy --version
```

### Trên Windows
- **PowerShell (khuyến nghị):**
  ```powershell
  irm https://antigravity.google/cli/install.ps1 | iex
  ```
- **Command Prompt (CMD):**
  ```cmd
  curl -fsSL https://antigravity.google/cli/install.cmd -o install.cmd && install.cmd && del install.cmd
  ```

---

## 3. Phương pháp 2: Hướng dẫn Cài đặt & Build Mã Nguồn (Build from Source)

Nếu đội ngũ của bạn cần tùy biến mã nguồn, chạy trong môi trường private network, hoặc nhúng Antigravity vào runtime riêng, hãy thực hiện theo các bước build source dưới đây:

### A. Build Antigravity Python SDK từ Source (`google-antigravity`)
Antigravity cung cấp Python SDK chính thức tại repository: `https://github.com/google-antigravity/antigravity-sdk-python`.

1. **Yêu cầu môi trường:**
   - Python `>= 3.10`
   - `git`, `pip`, `build`, `wheel`

2. **Clone và Build Source:**
   ```bash
   # 1. Clone repository chính thức
   git clone https://github.com/google-antigravity/antigravity-sdk-python.git
   cd antigravity-sdk-python

   # 2. Tạo môi trường ảo riêng biệt
   python3 -m venv .venv
   source .venv/bin/activate

   # 3. Cài đặt các công cụ build
   pip install --upgrade pip build wheel setuptools

   # 4. Cài đặt chế độ phát triển (Editable Mode)
   pip install -e .

   # Hoặc build thành file Wheel (.whl) để phân phối nội bộ:
   python3 -m build --wheel
   # File .whl sinh ra tại: dist/google_antigravity-*.whl
   ```

3. **Cài đặt file Wheel nội bộ cho các máy khác:**
   ```bash
   pip install dist/google_antigravity-*.whl
   ```

---

### B. Build Go Binaries & Native Tooling
Bộ CLI lõi của Antigravity được viết bằng Go (`go >= 1.22`):

1. **Chuẩn bị Go Toolchain:**
   ```bash
   # Kiểm tra phiên bản Go
   go version  # Yêu cầu go1.22 trở lên
   ```

2. **Cấu hình biến môi trường Build:**
   ```bash
   export CGO_ENABLED=1
   export GOOS=linux        # hoặc darwin (macOS), windows
   export GOARCH=amd64      # hoặc arm64 cho Apple Silicon M1/M2/M3
   ```

3. **Compile Binary:**
   ```bash
   # Build binary tối ưu kích thước và bảo mật
   go build -ldflags="-s -w -X main.version=1.3.2" -o ~/.local/bin/agy ./cmd/agy
   chmod +x ~/.local/bin/agy
   ```

---

### C. Build Node/TypeScript Extensions & Sidecars (Nếu có)
Các UI Cockpit hoặc sidecar module sử dụng Node.js:
```bash
# Yêu cầu Node >= 20 và pnpm >= 9
pnpm install --frozen-lockfile
pnpm build
```

---

## 4. Cấu hình Môi trường & Xác thực (Authentication)

Sau khi cài đặt xong binary `agy`, bạn cần cấu hình khóa API hoặc tài khoản Google Cloud:

### 1. Cấu hình Gemini API Key (Khuyến nghị cho developer cá nhân)
```bash
export GEMINI_API_KEY="AIzaSy..."
# Thêm vào ~/.bashrc hoặc ~/.zshrc để dùng vĩnh viễn:
echo 'export GEMINI_API_KEY="AIzaSy..."' >> ~/.bashrc
```

### 2. Cấu hình Google Cloud Vertex AI (Khuyến nghị cho Enterprise / Team)
Nếu công ty sử dụng Vertex AI trên GCP:
```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

### 3. Đăng nhập tương tác lần đầu
Chạy lệnh xác thực tích hợp:
```bash
agy
# CLI sẽ hiển thị liên kết đăng nhập OAuth trên trình duyệt nếu chưa có API key.
```

---

## 5. Các Flag & Tùy chọn Quan trọng của `agy`

| Cờ (Flag) | Tác dụng | Trường hợp sử dụng |
| :--- | :--- | :--- |
| `agy` | Khởi động phiên tương tác TUI | Làm việc pair programming hàng ngày |
| `agy --continue` (`-c`) | Tiếp tục phiên làm việc gần nhất | Phục hồi context sau khi tắt terminal |
| `agy --model <model-id>` | Chọn model chỉ định | Ví dụ: `--model gemini-4-argon` hoặc `--model gemini-3.8-flash` |
| `agy --effort <level>` | Mức độ suy luận tư duy | `low`, `medium`, `high`, `xhigh` |
| `agy --dangerously-skip-permissions` | Bỏ qua xác nhận cấp quyền tool | Dùng trong CI/CD pipeline hoặc chạy batch ngầm |
| `agy --print "prompt"` | Chạy prompt 1 lần không tương tác | Chạy script tự động |

---

## 6. Khắc phục Sự cố Thường gặp (Troubleshooting)

### Lỗi 1: `command not found: agy`
- **Nguyên nhân:** Thư mục `~/.local/bin` chưa được nạp vào biến `PATH`.
- **Cách sửa:**
  ```bash
  export PATH="$HOME/.local/bin:$PATH"
  which agy
  ```

### Lỗi 2: `Permission denied: /usr/local/bin`
- **Nguyên nhân:** Cài đặt yêu cầu root nếu ghi vào thư mục hệ thống.
- **Cách sửa:** Antigravity ưu tiên cài vào user space (`$HOME/.local/bin`), không cần `sudo`.

### Lỗi 3: Không hiển thị slash command `/orchestrator`
- **Nguyên nhân:** Chưa cài file workflow vào `~/.gemini/config/workflows/`.
- **Cách sửa:** Chạy `./install.sh` từ thư mục bộ công cụ này để tự động nạp.

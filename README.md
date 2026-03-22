# SunLon Key Management System 🔑

Hệ thống quản lý key cho ứng dụng SunLon với server Flask và client GUI.

## 📋 Mô tả

Hệ thống bao gồm:
- **Server Key** (Flask API): Quản lý key, xác thực, admin panel
- **Client GUI** (CustomTkinter): Giao diện người dùng với xác thực key
- **Database SQLite**: Lưu trữ key và logs

## 🚀 Cài đặt

### 1. Clone repository
```bash
git clone https://github.com/your-username/sunlon-key-system.git
cd sunlon-key-system
```

### 2. Tạo virtual environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

## 🎯 Sử dụng

### Chạy Server Key
```bash
python key_server.py
```
Server chạy tại: `http://localhost:5000`

### Chạy Client GUI
```bash
python sunlon_client.py
```

## 📚 API Endpoints

### User Endpoints
- `POST /api/register` - Đăng ký key mới
- `POST /api/verify` - Xác thực key

### Admin Endpoints (cần Admin Key)
- `GET /api/keys` - Lấy danh sách keys
- `DELETE /api/keys/<key_hash>` - Xóa key
- `POST /api/keys/<key_hash>/toggle` - Khóa/mở khóa key
- `GET /api/stats` - Thống kê

## 🔐 Bảo mật

- Key được hash SHA256 trước khi lưu
- Admin key bảo vệ endpoints quản lý
- IP tracking và logging
- Tự động vô hiệu hóa key hết hạn

## 🛠️ Tính năng

- ✅ Quản lý key với thời hạn
- ✅ Giao diện GUI đẹp
- ✅ Xác thực tự động
- ✅ Admin panel
- ✅ Logging đầy đủ
- ✅ Database SQLite
- ✅ CORS enabled

## 📝 Cấu hình

### Environment Variables
```bash
SECRET_KEY=your_secret_key
ADMIN_KEY=your_admin_key
```

### Mặc định
- Admin Key: `admin123`
- Port: `5000`
- Database: `keys.db`

## 🚀 Deploy

### Local
```bash
python key_server.py
```

### Production (Render)
```yaml
# render.yaml
services:
  - type: web
    name: sunlon-key-server
    runtime: python
    repo: https://github.com/your-repo
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn key_server:app
    envVars:
      - key: SECRET_KEY
        generateValue: true
      - key: ADMIN_KEY
        value: your_admin_key_here
```

## 📞 Liên hệ

Nếu có vấn đề, hãy tạo issue trên GitHub.

## 📄 License

MIT License
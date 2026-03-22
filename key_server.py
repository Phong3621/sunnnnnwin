# key_server.py
"""
Server quản lý key cho ứng dụng SunLon
API Endpoints:
- POST /api/register - Đăng ký key mới
- POST /api/verify - Xác thực key
- GET /api/keys - Lấy danh sách key (admin)
- DELETE /api/keys/<key_id> - Xóa key (admin)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import hashlib
import secrets
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
CORS(app)  # Cho phép client gọi API

# Cấu hình
DATABASE = 'keys.db'
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
ADMIN_KEY = os.environ.get('ADMIN_KEY', 'admin123')  # Key admin mặc định

# ==================== DATABASE ====================

def init_db():
    """Khởi tạo database"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Bảng keys
    c.execute('''CREATE TABLE IF NOT EXISTS keys
                 (id TEXT PRIMARY KEY,
                  user_name TEXT NOT NULL,
                  created_at TIMESTAMP NOT NULL,
                  expires_at TIMESTAMP NOT NULL,
                  is_active BOOLEAN DEFAULT 1,
                  last_used TIMESTAMP,
                  used_count INTEGER DEFAULT 0)''')
    
    # Bảng logs
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  key_id TEXT,
                  action TEXT,
                  ip_address TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

def generate_key():
    """Tạo key mới (16 ký tự ngẫu nhiên)"""
    return secrets.token_hex(8).upper()

def hash_key(key):
    """Mã hóa key để lưu trong DB (bảo mật hơn)"""
    return hashlib.sha256(key.encode()).hexdigest()

# ==================== DECORATORS ====================

def require_admin(f):
    """Decorator yêu cầu admin key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_key = request.headers.get('X-Admin-Key')
        if not admin_key or admin_key != ADMIN_KEY:
            return jsonify({'error': 'Unauthorized', 'message': 'Invalid admin key'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ==================== API ENDPOINTS ====================

@app.route('/api/register', methods=['POST'])
def register_key():
    """
    Đăng ký key mới
    Body: {"user_name": "username", "days": 30}
    """
    try:
        data = request.get_json()
        user_name = data.get('user_name')
        days = data.get('days', 30)  # Mặc định 30 ngày
        
        if not user_name:
            return jsonify({'error': 'user_name is required'}), 400
        
        # Tạo key mới
        key = generate_key()
        key_hash = hash_key(key)
        
        # Thời gian hết hạn
        created_at = datetime.now()
        expires_at = created_at + timedelta(days=days)
        
        # Lưu vào DB
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''INSERT INTO keys (id, user_name, created_at, expires_at)
                     VALUES (?, ?, ?, ?)''',
                  (key_hash, user_name, created_at, expires_at))
        conn.commit()
        conn.close()
        
        # Ghi log
        log_action(key_hash, 'register', request.remote_addr)
        
        return jsonify({
            'success': True,
            'key': key,
            'user_name': user_name,
            'expires_at': expires_at.isoformat(),
            'message': f'Key created successfully. Valid for {days} days'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify', methods=['POST'])
def verify_key():
    """
    Xác thực key
    Body: {"key": "KEY_HERE"}
    """
    try:
        data = request.get_json()
        key = data.get('key')
        
        if not key:
            return jsonify({'error': 'key is required'}), 400
        
        key_hash = hash_key(key)
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Lấy thông tin key
        c.execute('''SELECT id, user_name, created_at, expires_at, is_active, used_count
                     FROM keys WHERE id = ?''', (key_hash,))
        result = c.fetchone()
        
        if not result:
            return jsonify({
                'valid': False,
                'message': 'Key không tồn tại'
            }), 404
        
        key_id, user_name, created_at, expires_at, is_active, used_count = result
        
        # Kiểm tra key có active không
        if not is_active:
            return jsonify({
                'valid': False,
                'message': 'Key đã bị khóa'
            }), 403
        
        # Kiểm tra hết hạn
        expires_at_date = datetime.fromisoformat(expires_at)
        if expires_at_date < datetime.now():
            # Tự động vô hiệu hóa key hết hạn
            c.execute('UPDATE keys SET is_active = 0 WHERE id = ?', (key_hash,))
            conn.commit()
            return jsonify({
                'valid': False,
                'message': f'Key đã hết hạn từ {expires_at_date.strftime("%d/%m/%Y")}'
            }), 403
        
        # Cập nhật last_used và used_count
        c.execute('''UPDATE keys 
                     SET last_used = ?, used_count = used_count + 1
                     WHERE id = ?''',
                  (datetime.now(), key_hash))
        conn.commit()
        
        # Ghi log
        log_action(key_hash, 'verify', request.remote_addr)
        
        conn.close()
        
        # Tính số ngày còn lại
        days_left = (expires_at_date - datetime.now()).days
        
        return jsonify({
            'valid': True,
            'user_name': user_name,
            'expires_at': expires_at,
            'days_left': days_left,
            'used_count': used_count + 1,
            'message': f'Xác thực thành công! Còn {days_left} ngày sử dụng'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/keys', methods=['GET'])
@require_admin
def get_keys():
    """Lấy danh sách tất cả keys (admin)"""
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''SELECT id, user_name, created_at, expires_at, is_active, last_used, used_count
                     FROM keys ORDER BY created_at DESC''')
        rows = c.fetchall()
        conn.close()
        
        keys = []
        for row in rows:
            keys.append({
                'key_hash': row[0][:8] + '...',  # Chỉ hiển thị 8 ký tự đầu
                'user_name': row[1],
                'created_at': row[2],
                'expires_at': row[3],
                'is_active': bool(row[4]),
                'last_used': row[5],
                'used_count': row[6]
            })
        
        return jsonify({'keys': keys})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/keys/<key_hash>', methods=['DELETE'])
@require_admin
def delete_key(key_hash):
    """Xóa key (admin)"""
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('DELETE FROM keys WHERE id = ?', (key_hash,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Key deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/keys/<key_hash>/toggle', methods=['POST'])
@require_admin
def toggle_key(key_hash):
    """Khóa/mở khóa key (admin)"""
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Lấy trạng thái hiện tại
        c.execute('SELECT is_active FROM keys WHERE id = ?', (key_hash,))
        result = c.fetchone()
        
        if not result:
            return jsonify({'error': 'Key not found'}), 404
        
        new_status = not result[0]
        c.execute('UPDATE keys SET is_active = ? WHERE id = ?', (new_status, key_hash))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'is_active': new_status,
            'message': f'Key {"activated" if new_status else "deactivated"}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
@require_admin
def get_stats():
    """Thống kê tổng quan (admin)"""
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Tổng số key
        c.execute('SELECT COUNT(*) FROM keys')
        total_keys = c.fetchone()[0]
        
        # Số key active
        c.execute('SELECT COUNT(*) FROM keys WHERE is_active = 1')
        active_keys = c.fetchone()[0]
        
        # Số key hết hạn
        c.execute('SELECT COUNT(*) FROM keys WHERE expires_at < datetime("now")')
        expired_keys = c.fetchone()[0]
        
        # Tổng số lần sử dụng
        c.execute('SELECT SUM(used_count) FROM keys')
        total_used = c.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'total_keys': total_keys,
            'active_keys': active_keys,
            'expired_keys': expired_keys,
            'total_usage': total_used
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def log_action(key_id, action, ip_address):
    """Ghi log hoạt động"""
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''INSERT INTO logs (key_id, action, ip_address)
                     VALUES (?, ?, ?)''', (key_id, action, ip_address))
        conn.commit()
        conn.close()
    except:
        pass

# ==================== RUN SERVER ====================

if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("🚀 Key Management Server")
    print("=" * 50)
    print(f"Admin Key: {ADMIN_KEY}")
    print(f"API URL: http://localhost:5000")
    print("\nEndpoints:")
    print("  POST   /api/register  - Register new key")
    print("  POST   /api/verify    - Verify key")
    print("  GET    /api/keys      - List all keys (admin)")
    print("  DELETE /api/keys/<id> - Delete key (admin)")
    print("  POST   /api/keys/<id>/toggle - Toggle key (admin)")
    print("  GET    /api/stats     - Get statistics (admin)")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
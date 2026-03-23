"""
Server quản lý key SunLon
Chạy trên VPS hoặc máy chủ riêng
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import secrets
import datetime
import json
from functools import wraps

app = Flask(__name__)
CORS(app)

# Khởi tạo database
def init_db():
    conn = sqlite3.connect('sunlon_keys.db')
    c = conn.cursor()
    
    # Bảng quản lý key
    c.execute('''CREATE TABLE IF NOT EXISTS keys
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  key_code TEXT UNIQUE NOT NULL,
                  user_name TEXT,
                  user_email TEXT,
                  device_id TEXT,
                  status TEXT DEFAULT 'active',
                  expire_date DATE,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  last_login TIMESTAMP,
                  login_count INTEGER DEFAULT 0,
                  notes TEXT)''')
    
    # Bảng log hoạt động
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  key_code TEXT,
                  action TEXT,
                  ip_address TEXT,
                  user_agent TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Bảng cấu hình hệ thống
    c.execute('''CREATE TABLE IF NOT EXISTS config
                 (key TEXT PRIMARY KEY,
                  value TEXT,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Thêm admin user mặc định (tạo key admin)
    c.execute("SELECT * FROM config WHERE key='admin_key'")
    if not c.fetchone():
        admin_key = generate_key()
        c.execute("INSERT INTO config (key, value) VALUES ('admin_key', ?)", (admin_key,))
        print(f"Admin Key: {admin_key}")
    
    conn.commit()
    conn.close()

def generate_key():
    """Tạo key ngẫu nhiên"""
    return secrets.token_hex(16).upper()

def hash_key(key):
    """Mã hóa key để lưu trữ"""
    return hashlib.sha256(key.encode()).hexdigest()

def log_activity(key_code, action, ip, user_agent):
    """Ghi log hoạt động"""
    conn = sqlite3.connect('sunlon_keys.db')
    c = conn.cursor()
    c.execute("INSERT INTO logs (key_code, action, ip_address, user_agent) VALUES (?, ?, ?, ?)",
              (key_code, action, ip, user_agent))
    conn.commit()
    conn.close()

def require_auth(f):
    """Decorator yêu cầu xác thực admin"""
    @wraps(f)
    def decorated(*args, **kwargs):
        admin_key = request.headers.get('X-Admin-Key')
        if not admin_key:
            return jsonify({'error': 'Unauthorized'}), 401
        
        conn = sqlite3.connect('sunlon_keys.db')
        c = conn.cursor()
        c.execute("SELECT value FROM config WHERE key='admin_key'")
        result = c.fetchone()
        conn.close()
        
        if not result or result[0] != admin_key:
            return jsonify({'error': 'Invalid admin key'}), 401
        
        return f(*args, **kwargs)
    return decorated

# ==================== API ENDPOINTS ====================

@app.route('/api/verify', methods=['POST'])
def verify_key():
    """Xác thực key"""
    data = request.json
    key_code = data.get('key_code', '').upper()
    device_id = data.get('device_id', '')
    user_agent = request.headers.get('User-Agent', '')
    ip = request.remote_addr
    
    if not key_code:
        return jsonify({'valid': False, 'error': 'Missing key code'}), 400
    
    conn = sqlite3.connect('sunlon_keys.db')
    c = conn.cursor()
    
    # Kiểm tra key
    c.execute("SELECT user_name, user_email, status, expire_date, login_count FROM keys WHERE key_code=?", (key_code,))
    result = c.fetchone()
    
    if not result:
        log_activity(key_code, 'invalid_key', ip, user_agent)
        return jsonify({'valid': False, 'error': 'Key không tồn tại'})
    
    user_name, user_email, status, expire_date, login_count = result
    
    # Kiểm tra trạng thái
    if status != 'active':
        log_activity(key_code, f'inactive_{status}', ip, user_agent)
        return jsonify({'valid': False, 'error': f'Key đã bị {status}'})
    
    # Kiểm tra hạn sử dụng
    if expire_date:
        expire_date_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d').date()
        if expire_date_obj < datetime.date.today():
            log_activity(key_code, 'expired', ip, user_agent)
            return jsonify({'valid': False, 'error': 'Key đã hết hạn'})
    
    # Cập nhật thông tin đăng nhập
    c.execute("UPDATE keys SET last_login=CURRENT_TIMESTAMP, login_count=login_count+1, device_id=? WHERE key_code=?", 
              (device_id, key_code))
    conn.commit()
    
    log_activity(key_code, 'login_success', ip, user_agent)
    
    # Trả về thông tin key
    return jsonify({
        'valid': True,
        'user_name': user_name,
        'user_email': user_email,
        'expire_date': expire_date,
        'login_count': login_count + 1,
        'message': 'Xác thực thành công'
    })

@app.route('/api/register', methods=['POST'])
def register_key():
    """Đăng ký key mới (cần admin key)"""
    admin_key = request.headers.get('X-Admin-Key')
    data = request.json
    
    if not admin_key:
        return jsonify({'error': 'Missing admin key'}), 401
    
    # Xác thực admin
    conn = sqlite3.connect('sunlon_keys.db')
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key='admin_key'")
    result = c.fetchone()
    
    if not result or result[0] != admin_key:
        return jsonify({'error': 'Invalid admin key'}), 401
    
    # Tạo key mới
    key_code = generate_key()
    user_name = data.get('user_name', 'Unknown')
    user_email = data.get('user_email', '')
    expire_days = data.get('expire_days', 30)  # Mặc định 30 ngày
    notes = data.get('notes', '')
    
    expire_date = (datetime.date.today() + datetime.timedelta(days=expire_days)).strftime('%Y-%m-%d')
    
    c.execute("""INSERT INTO keys (key_code, user_name, user_email, expire_date, notes) 
                 VALUES (?, ?, ?, ?, ?)""", 
              (key_code, user_name, user_email, expire_date, notes))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'key_code': key_code,
        'expire_date': expire_date,
        'message': 'Tạo key thành công'
    })

@app.route('/api/keys', methods=['GET'])
@require_auth
def list_keys():
    """Lấy danh sách tất cả keys"""
    conn = sqlite3.connect('sunlon_keys.db')
    c = conn.cursor()
    c.execute("""SELECT key_code, user_name, user_email, status, expire_date, 
                        created_at, last_login, login_count, notes 
                 FROM keys ORDER BY created_at DESC""")
    keys = []
    for row in c.fetchall():
        keys.append({
            'key_code': row[0],
            'user_name': row[1],
            'user_email': row[2],
            'status': row[3],
            'expire_date': row[4],
            'created_at': row[5],
            'last_login': row[6],
            'login_count': row[7],
            'notes': row[8]
        })
    conn.close()
    return jsonify(keys)

@app.route('/api/key/<key_code>', methods=['PUT'])
@require_auth
def update_key(key_code):
    """Cập nhật thông tin key"""
    data = request.json
    
    conn = sqlite3.connect('sunlon_keys.db')
    c = conn.cursor()
    
    updates = []
    params = []
    
    if 'status' in data:
        updates.append("status=?")
        params.append(data['status'])
    if 'expire_days' in data:
        expire_date = (datetime.date.today() + datetime.timedelta(days=data['expire_days'])).strftime('%Y-%m-%d')
        updates.append("expire_date=?")
        params.append(expire_date)
    if 'notes' in data:
        updates.append("notes=?")
        params.append(data['notes'])
    
    if updates:
        params.append(key_code)
        query = f"UPDATE keys SET {', '.join(updates)} WHERE key_code=?"
        c.execute(query, params)
        conn.commit()
    
    conn.close()
    return jsonify({'success': True, 'message': 'Cập nhật thành công'})

@app.route('/api/key/<key_code>', methods=['DELETE'])
@require_auth
def delete_key(key_code):
    """Xóa key"""
    conn = sqlite3.connect('sunlon_keys.db')
    c = conn.cursor()
    c.execute("DELETE FROM keys WHERE key_code=?", (key_code,))
    c.execute("DELETE FROM logs WHERE key_code=?", (key_code,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Xóa key thành công'})

@app.route('/api/logs', methods=['GET'])
@require_auth
def get_logs():
    """Lấy log hoạt động"""
    limit = request.args.get('limit', 100, type=int)
    conn = sqlite3.connect('sunlon_keys.db')
    c = conn.cursor()
    c.execute("""SELECT key_code, action, ip_address, user_agent, timestamp 
                 FROM logs ORDER BY timestamp DESC LIMIT ?""", (limit,))
    logs = []
    for row in c.fetchall():
        logs.append({
            'key_code': row[0],
            'action': row[1],
            'ip_address': row[2],
            'user_agent': row[3],
            'timestamp': row[4]
        })
    conn.close()
    return jsonify(logs)

@app.route('/api/stats', methods=['GET'])
@require_auth
def get_stats():
    """Lấy thống kê"""
    conn = sqlite3.connect('sunlon_keys.db')
    c = conn.cursor()
    
    # Tổng số keys
    c.execute("SELECT COUNT(*) FROM keys")
    total_keys = c.fetchone()[0]
    
    # Keys active
    c.execute("SELECT COUNT(*) FROM keys WHERE status='active'")
    active_keys = c.fetchone()[0]
    
    # Keys hết hạn
    c.execute("SELECT COUNT(*) FROM keys WHERE expire_date < date('now')")
    expired_keys = c.fetchone()[0]
    
    # Tổng số lần đăng nhập hôm nay
    c.execute("SELECT COUNT(*) FROM logs WHERE action='login_success' AND date(timestamp)=date('now')")
    today_logins = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'total_keys': total_keys,
        'active_keys': active_keys,
        'expired_keys': expired_keys,
        'today_logins': today_logins
    })

# ==================== CHẠY SERVER ====================
if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("SunLon Key Management Server")
    print("=" * 50)
    print("Server đang chạy tại: http://localhost:5000")
    print("Admin Key được lưu trong database")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
    
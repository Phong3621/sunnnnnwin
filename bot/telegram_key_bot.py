"""
Telegram Bot - SunLon Key Manager PRO
Đã fix: 
- Lỗi request.url_root trong Telegram handler
- Lỗi 409 Conflict
- Rate limit chống spam
- Hash HWID bảo mật
"""

import telebot
from telebot import types
import sqlite3
import secrets
import datetime
import os
import logging
import time
import threading
import hashlib
import sys
from datetime import timedelta
from flask import Flask, jsonify, request, render_template_string

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CẤU HÌNH ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
DB_PATH = 'sunlon_keys.db'
PORT = int(os.environ.get('PORT', 10000))

# URL công khai của bot (THAY THẾ request.url_root)
PUBLIC_URL = os.environ.get('RAILWAY_PUBLIC_DOMAIN', 'https://sunnnnnwin-production.up.railway.app')
BOT_WEB_URL = PUBLIC_URL

# Rate limit
REQUEST_LOG = {}
RATE_LIMIT_SECONDS = 1

if not BOT_TOKEN:
    print("❌ LỖI: Thiếu BOT_TOKEN!")
    exit(1)

try:
    bot = telebot.TeleBot(BOT_TOKEN)
    bot_info = bot.get_me()
    print(f"✅ Bot đã kết nối!")
    print(f"   Username: @{bot_info.username}")
except Exception as e:
    print(f"❌ Lỗi: {e}")
    exit(1)

# Xóa webhook cũ
try:
    bot.delete_webhook()
    print("✅ Webhook deleted")
except:
    pass
time.sleep(1)

# ==================== HELPER ====================
def is_spam(ip):
    now = time.time()
    if ip in REQUEST_LOG and now - REQUEST_LOG[ip] < RATE_LIMIT_SECONDS:
        return True
    REQUEST_LOG[ip] = now
    return False

def hash_hwid(hwid):
    return hashlib.sha256(hwid.encode()).hexdigest()

# ==================== DATABASE ====================
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_code TEXT UNIQUE NOT NULL,
            user_name TEXT,
            created_by TEXT,
            status TEXT DEFAULT 'active',
            expire_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_hwid_hash TEXT,
            used_at TIMESTAMP,
            device_name TEXT,
            device_info TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_code TEXT,
            action TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS reset_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_code TEXT,
            user_id TEXT,
            status TEXT DEFAULT 'pending',
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
        conn.close()
        print(f"✅ Database initialized at {DB_PATH}")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def generate_key():
    return secrets.token_hex(6).upper()

def is_admin(user_id):
    try:
        return int(user_id) == ADMIN_ID
    except:
        return False

def log_activity(key_code, action, ip=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO logs (key_code, action, ip_address) VALUES (?, ?, ?)", 
                  (key_code, action, ip))
        conn.commit()
        conn.close()
    except:
        pass

# ==================== HTML TEMPLATE ====================
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SunLon Key Manager</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #eee;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 {
            text-align: center;
            color: #ffd700;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .stats {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        .stat-card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px 30px;
            text-align: center;
        }
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #ffd700;
        }
        .stat-label { font-size: 0.9em; color: #aaa; }
        table {
            width: 100%;
            border-collapse: collapse;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            overflow: hidden;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        th { background: rgba(255,215,0,0.2); color: #ffd700; }
        tr:hover { background: rgba(255,255,255,0.05); }
        .active { color: #00ff00; font-weight: bold; }
        .expired { color: #ff4444; font-weight: bold; }
        .revoked { color: #ff8800; font-weight: bold; }
        .device {
            font-family: monospace;
            font-size: 12px;
            background: rgba(0,0,0,0.3);
            padding: 4px 8px;
            border-radius: 5px;
            display: inline-block;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #666;
            font-size: 12px;
        }
        @media (max-width: 768px) {
            th, td { padding: 8px 10px; font-size: 12px; }
            .stat-number { font-size: 1.8em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎲 SUNLON KEY MANAGER</h1>
        <div class="stats">
            <div class="stat-card"><div class="stat-number">{total}</div><div class="stat-label">Tổng key</div></div>
            <div class="stat-card"><div class="stat-number">{active}</div><div class="stat-label">Đang hoạt động</div></div>
            <div class="stat-card"><div class="stat-number">{used}</div><div class="stat-label">Đã kích hoạt</div></div>
            <div class="stat-card"><div class="stat-number">{expired}</div><div class="stat-label">Hết hạn</div></div>
        </div>
        <table>
            <thead>
                <tr><th>Key</th><th>Người dùng</th><th>Trạng thái</th><th>Hết hạn</th><th>Thiết bị</th><th>Kích hoạt</th></tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        <div class="footer">
            🔒 Bảo mật bằng HWID | 🖥️ Mỗi key chỉ dùng 1 thiết bị | 🤖 Bot: @{bot_username}
        </div>
    </div>
</body>
</html>
"""

# ==================== FLASK WEB SERVER ====================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM keys")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM keys WHERE status='active'")
        active = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM keys WHERE used_hwid_hash IS NOT NULL")
        used = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM keys WHERE expire_date < date('now') AND expire_date IS NOT NULL")
        expired = c.fetchone()[0]
        
        c.execute("""
            SELECT key_code, user_name, status, expire_date, device_name, used_at 
            FROM keys ORDER BY created_at DESC
        """)
        keys = c.fetchall()
        conn.close()
        
        rows = ""
        for key in keys:
            key_code, user_name, status, expire_date, device, used_at = key
            
            is_expired = False
            if expire_date:
                try:
                    expire_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d').date()
                    is_expired = expire_obj < datetime.date.today()
                except:
                    pass
            
            if is_expired:
                status_class = "expired"
                status_text = "HẾT HẠN"
            elif status == 'active':
                status_class = "active"
                status_text = "ACTIVE"
            else:
                status_class = "revoked"
                status_text = "REVOKED"
            
            device_display = f'<span class="device">{device if device else "Chưa kích hoạt"}</span>'
            used_at_display = used_at[:10] if used_at else "Chưa"
            
            rows += f"""
            <tr>
                <td><code>{key_code}</code></td>
                <td>{user_name}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{expire_date if expire_date else 'Vĩnh viễn'}</td>
                <td>{device_display}</td>
                <td>{used_at_display}</td>
            </tr>
            """
        
        return render_template_string(
            DASHBOARD_HTML,
            total=total,
            active=active,
            used=used,
            expired=expired,
            rows=rows,
            bot_username=bot_info.username
        )
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

@web_app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'bot': '@' + bot_info.username}), 200

@web_app.route('/checkkey')
def check_key_api():
    ip = request.remote_addr
    if is_spam(ip):
        return jsonify({'valid': False, 'error': 'Too many requests'}), 429
    
    try:
        key_code = request.args.get('key', '').upper()
        raw_hwid = request.args.get('hwid', '')
        device_name = request.args.get('device_name', 'Unknown')
        device_info = request.args.get('device_info', '')
        
        if not key_code:
            return jsonify({'valid': False, 'error': 'Missing key'}), 400
        if not raw_hwid:
            return jsonify({'valid': False, 'error': 'Missing HWID'}), 400
        
        hwid_hash = hash_hwid(raw_hwid)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT user_name, status, expire_date, used_hwid_hash, device_name
            FROM keys WHERE key_code=?
        """, (key_code,))
        result = c.fetchone()
        
        if not result:
            log_activity(key_code, 'invalid_key', ip)
            conn.close()
            return jsonify({'valid': False, 'error': 'Key không tồn tại'})
        
        user_name, status, expire_date, stored_hwid, saved_device = result
        
        if status != 'active':
            conn.close()
            return jsonify({'valid': False, 'error': f'Key đã bị {status}'})
        
        if expire_date:
            expire_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d').date()
            if expire_obj < datetime.date.today():
                log_activity(key_code, 'expired', ip)
                conn.close()
                return jsonify({'valid': False, 'error': f'Key hết hạn từ {expire_date}'})
            days_left = (expire_obj - datetime.date.today()).days
        else:
            days_left = 999
        
        if stored_hwid:
            if hwid_hash != stored_hwid:
                log_activity(key_code, 'hwid_mismatch', ip)
                conn.close()
                return jsonify({
                    'valid': False,
                    'error': 'Key đã dùng trên thiết bị khác',
                    'device': saved_device,
                    'request_reset': True
                })
        else:
            c.execute("""
                UPDATE keys SET used_hwid_hash=?, used_at=CURRENT_TIMESTAMP,
                    device_name=?, device_info=?
                WHERE key_code=?
            """, (hwid_hash, device_name, device_info, key_code))
            conn.commit()
            log_activity(key_code, 'activated', ip)
        
        conn.close()
        
        return jsonify({
            'valid': True,
            'user': user_name,
            'expire': expire_date if expire_date else 'Vĩnh viễn',
            'days_left': days_left,
            'device': saved_device if stored_hwid else device_name
        })
        
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 500

@web_app.route('/reset_device')
def reset_device_api():
    ip = request.remote_addr
    if is_spam(ip):
        return jsonify({'success': False, 'error': 'Too many requests'}), 429
    
    try:
        key_code = request.args.get('key', '').upper()
        raw_hwid = request.args.get('hwid', '')
        
        if not key_code or not raw_hwid:
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400
        
        hwid_hash = hash_hwid(raw_hwid)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT user_name, used_hwid_hash, status FROM keys WHERE key_code=?", (key_code,))
        result = c.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'Key không tồn tại'})
        
        user_name, stored_hwid, status = result
        
        if status != 'active':
            conn.close()
            return jsonify({'success': False, 'error': f'Key đã bị {status}'})
        
        if not stored_hwid:
            conn.close()
            return jsonify({'success': False, 'error': 'Key chưa được kích hoạt'})
        
        if hwid_hash != stored_hwid:
            conn.close()
            return jsonify({'success': False, 'error': 'HWID không khớp'})
        
        c.execute("INSERT INTO reset_requests (key_code, user_id, status) VALUES (?, ?, 'pending')", 
                  (key_code, user_name))
        conn.commit()
        conn.close()
        
        log_activity(key_code, 'reset_requested', ip)
        
        admin_msg = f"""🔔 YÊU CẦU RESET THIẾT BỊ

🔑 Key: {key_code}
👤 Người dùng: {user_name}

Dùng: /resetkey {key_code} để xác nhận"""
        
        bot.send_message(ADMIN_ID, admin_msg)
        
        return jsonify({'success': True, 'message': 'Yêu cầu reset đã gửi đến admin'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def run_web():
    web_app.run(host='0.0.0.0', port=PORT, threaded=True)

# ==================== TELEGRAM COMMANDS ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if is_admin(user_id):
        text = f"""🎲 SUNLON KEY MANAGER PRO

Xin chào Admin {user_name}!

📌 Lệnh Admin:
/createkey [tên] [ngày] - Tạo key mới
/listkeys - Xem danh sách
/checkkey [key] - Kiểm tra key
/resetkey [key] - Reset thiết bị
/revokekey [key] - Vô hiệu key
/deletekey [key] - Xóa key
/stats - Xem thống kê
/getdb - Tải database

🌐 Web Dashboard:
{BOT_WEB_URL}

💡 Ví dụ: /createkey Nguyen Van A 30"""
    else:
        text = f"""🎲 SUNLON KEY SYSTEM PRO

Xin chào {user_name}!

🔑 Kiểm tra key: /check [key]
🔄 Reset thiết bị: /reset [key]

📞 Liên hệ admin để được hỗ trợ"""
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['createkey'])
def create_key(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Bạn không có quyền!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Sai cú pháp!\n/createkey [tên] [ngày]")
        return
    
    if len(args) >= 3:
        try:
            expire_days = int(args[-1])
            user_name = ' '.join(args[1:-1])
        except ValueError:
            user_name = ' '.join(args[1:])
            expire_days = 30
    else:
        user_name = args[1]
        expire_days = 30
    
    key_code = generate_key()
    expire_date = None
    if expire_days > 0:
        expire_date = (datetime.date.today() + timedelta(days=expire_days)).strftime('%Y-%m-%d')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO keys (key_code, user_name, created_by, expire_date) VALUES (?, ?, ?, ?)",
                  (key_code, user_name, str(message.from_user.id), expire_date))
        conn.commit()
        
        text = f"""✅ KEY MỚI!

🔑 Key: {key_code}
👤 Người dùng: {user_name}
📅 Hạn: {expire_date if expire_date else 'Vĩnh viễn'}

📌 API check: /checkkey?key={key_code}&hwid=YOUR_HWID
🌐 Xem dashboard: {BOT_WEB_URL}"""
        
        bot.reply_to(message, text)
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi: {str(e)}")
    finally:
        conn.close()

@bot.message_handler(commands=['listkeys'])
def list_keys(message):
    if not is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT key_code, user_name, status, expire_date, device_name FROM keys ORDER BY created_at DESC LIMIT 20")
    keys = c.fetchall()
    conn.close()
    
    if not keys:
        bot.reply_to(message, "📭 Chưa có key nào!")
        return
    
    text = "📋 DANH SÁCH KEY (20 gần nhất)\n\n"
    for key in keys:
        key_code, user_name, status, expire_date, device = key
        
        is_expired = False
        if expire_date:
            try:
                expire_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d').date()
                is_expired = expire_obj < datetime.date.today()
            except:
                pass
        
        if is_expired:
            icon = "⚠️"
            status_text = "HẾT HẠN"
        elif status == 'active':
            icon = "🟢"
            status_text = "ACTIVE"
        else:
            icon = "🔴"
            status_text = status.upper()
        
        text += f"{icon} {key_code}\n"
        text += f"   👤 {user_name}\n"
        text += f"   📅 {expire_date if expire_date else 'Vĩnh viễn'}\n"
        text += f"   📊 {status_text}\n"
        if device:
            text += f"   🖥️ {device}\n"
        text += "\n"
    
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.reply_to(message, text[i:i+4000])
    else:
        bot.reply_to(message, text)

@bot.message_handler(commands=['check'])
def check_key(message):
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Dùng: /check [KEY]")
        return
    
    key_code = args[1].upper()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_name, status, expire_date, device_name FROM keys WHERE key_code=?", (key_code,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        bot.reply_to(message, f"❌ Key {key_code} không tồn tại!")
        return
    
    user_name, status, expire_date, device = result
    
    if status != 'active':
        bot.reply_to(message, "❌ Key đã bị vô hiệu!")
        return
    
    if expire_date:
        try:
            expire_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d').date()
            days_left = (expire_obj - datetime.date.today()).days
            if days_left < 0:
                bot.reply_to(message, f"⚠️ Key đã hết hạn từ {expire_date}")
                return
            expire_text = f"{expire_date} (còn {days_left} ngày)"
        except:
            expire_text = expire_date
    else:
        expire_text = "Vĩnh viễn"
    
    device_text = f"\n🖥️ Thiết bị: {device}" if device else ""
    
    text = f"""✅ THÔNG TIN KEY

🔑 {key_code}
👤 {user_name}
📅 {expire_text}{device_text}

🎉 Key hợp lệ!"""
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['resetkey'])
def reset_key(message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Dùng: /resetkey [KEY]")
        return
    
    key_code = args[1].upper()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_name, device_name FROM keys WHERE key_code=?", (key_code,))
    result = c.fetchone()
    
    if not result:
        bot.reply_to(message, f"❌ Key {key_code} không tồn tại!")
        conn.close()
        return
    
    user_name, device = result
    
    c.execute("""
        UPDATE keys SET used_hwid_hash=NULL, used_at=NULL, device_name=NULL, device_info=NULL
        WHERE key_code=?
    """, (key_code,))
    conn.commit()
    conn.close()
    
    text = f"""✅ ĐÃ RESET THIẾT BỊ!

🔑 Key: {key_code}
👤 {user_name}
🖥️ Thiết bị cũ: {device if device else 'Unknown'}

💡 Người dùng có thể kích hoạt lại trên thiết bị mới."""
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['reset'])
def reset_request(message):
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Dùng: /reset [KEY]")
        return
    
    key_code = args[1].upper()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_name, used_hwid_hash FROM keys WHERE key_code=?", (key_code,))
    result = c.fetchone()
    
    if not result:
        bot.reply_to(message, f"❌ Key {key_code} không tồn tại!")
        conn.close()
        return
    
    user_name, used_hwid = result
    
    if not used_hwid:
        bot.reply_to(message, f"ℹ️ Key chưa được kích hoạt!")
        conn.close()
        return
    
    c.execute("SELECT * FROM reset_requests WHERE key_code=? AND status='pending'", (key_code,))
    if c.fetchone():
        bot.reply_to(message, f"⏳ Yêu cầu reset đang chờ xử lý!")
        conn.close()
        return
    
    c.execute("INSERT INTO reset_requests (key_code, user_id) VALUES (?, ?)", (key_code, str(message.from_user.id)))
    conn.commit()
    conn.close()
    
    admin_msg = f"""🔔 YÊU CẦU RESET THIẾT BỊ

🔑 Key: {key_code}
👤 Người dùng: {user_name}
🆔 User ID: {message.from_user.id}

Dùng: /resetkey {key_code} để xác nhận"""
    
    bot.send_message(ADMIN_ID, admin_msg)
    bot.reply_to(message, f"✅ Đã gửi yêu cầu reset cho key {key_code}!")

@bot.message_handler(commands=['stats'])
def stats(message):
    if not is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM keys")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM keys WHERE status='active'")
    active = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM keys WHERE used_hwid_hash IS NOT NULL")
    used = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM keys WHERE expire_date < date('now') AND expire_date IS NOT NULL")
    expired = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM reset_requests WHERE status='pending'")
    pending = c.fetchone()[0]
    conn.close()
    
    rate = (used / total * 100) if total > 0 else 0
    
    text = f"""📊 THỐNG KÊ KEY

📌 Tổng quan:
• Tổng số keys: {total}
• Đang hoạt động: {active} 🟢
• Đã kích hoạt: {used} ✅
• Hết hạn: {expired} ⚠️

📈 Reset chờ: {pending}
💡 Tỷ lệ kích hoạt: {rate:.1f}%"""
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['getdb'])
def get_db(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Bạn không có quyền!")
        return
    
    if os.path.exists(DB_PATH):
        with open(DB_PATH, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"📁 Database\n🕐 {datetime.datetime.now()}")
    else:
        bot.reply_to(message, "❌ Database chưa được tạo!")

@bot.message_handler(commands=['revokekey'])
def revoke_key(message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Dùng: /revokekey [KEY]")
        return
    
    key_code = args[1].upper()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE keys SET status='revoked' WHERE key_code=?", (key_code,))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ Đã vô hiệu key: {key_code}")

@bot.message_handler(commands=['deletekey'])
def delete_key(message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Dùng: /deletekey [KEY]")
        return
    
    key_code = args[1].upper()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Xóa", callback_data=f"del_{key_code}"),
               types.InlineKeyboardButton("❌ Hủy", callback_data="cancel"))
    
    bot.reply_to(message, f"⚠️ Xóa key: {key_code}?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data.startswith("del_"):
        key_code = call.data[4:]
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM keys WHERE key_code=?", (key_code,))
        c.execute("DELETE FROM logs WHERE key_code=?", (key_code,))
        c.execute("DELETE FROM reset_requests WHERE key_code=?", (key_code,))
        conn.commit()
        conn.close()
        bot.edit_message_text(f"✅ Đã xóa key: {key_code}", call.message.chat.id, call.message.message_id)
    elif call.data == "cancel":
        bot.edit_message_text("❌ Đã hủy", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.reply_to(message, "❓ Dùng /start để xem hướng dẫn")

# ==================== CHẠY BOT ====================
if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print("🤖 SunLon Bot PRO")
    print(f"   Bot: @{bot_info.username}")
    print(f"   Admin ID: {ADMIN_ID}")
    print(f"   Dashboard: {BOT_WEB_URL}")
    print("=" * 60)
    
    # Chạy web server
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    print("🌐 Web server started")
    
    # Chạy bot với xử lý lỗi 409
    while True:
        try:
            print("🤖 Bot polling started...")
            bot.polling(
                non_stop=True,
                interval=1,
                timeout=30,
                long_polling_timeout=30,
                skip_pending=True
            )
        except Exception as e:
            error_msg = str(e)
            if "409" in error_msg or "Conflict" in error_msg:
                print("⚠️ Conflict detected, removing webhook...")
                try:
                    bot.delete_webhook()
                    time.sleep(2)
                except:
                    pass
                print("🔄 Retrying...")
            else:
                print(f"⚠️ Error: {e}")
                time.sleep(10)

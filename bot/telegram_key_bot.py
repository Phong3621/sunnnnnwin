"""
Telegram Bot - SunLon Key Manager PRO
Tính năng:
- API check key với HWID
- Reset thiết bị cho key
- Log đầy đủ hoạt động
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
from datetime import timedelta
from flask import Flask, jsonify, request, send_file

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CẤU HÌNH ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
DB_PATH = 'sunlon_keys.db'
PORT = int(os.environ.get('PORT', 10000))

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

# ==================== DATABASE ====================
def init_db():
    """Khởi tạo database với cấu trúc PRO"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Bảng keys với HWID support
        c.execute('''CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_code TEXT UNIQUE NOT NULL,
            user_name TEXT,
            created_by TEXT,
            status TEXT DEFAULT 'active',
            expire_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_by TEXT,
            used_hwid TEXT,
            used_at TIMESTAMP,
            device_name TEXT,
            device_info TEXT,
            notes TEXT
        )''')
        
        # Bảng logs
        c.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_code TEXT,
            action TEXT,
            ip_address TEXT,
            user_agent TEXT,
            hwid TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Bảng reset requests
        c.execute('''CREATE TABLE IF NOT EXISTS reset_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_code TEXT,
            user_id TEXT,
            status TEXT DEFAULT 'pending',
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )''')
        
        conn.commit()
        conn.close()
        print("✅ Database PRO initialized")
        return True
    except Exception as e:
        print(f"❌ Database init error: {e}")
        return False

def generate_key():
    """Tạo key ngẫu nhiên 12 ký tự"""
    return secrets.token_hex(6).upper()

def is_admin(user_id):
    """Kiểm tra admin"""
    try:
        return int(user_id) == ADMIN_ID
    except:
        return False

def log_activity(key_code, action, ip=None, user_agent=None, hwid=None):
    """Ghi log hoạt động"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO logs (key_code, action, ip_address, user_agent, hwid) 
            VALUES (?, ?, ?, ?, ?)
        """, (key_code, action, ip, user_agent, hwid))
        conn.commit()
        conn.close()
    except:
        pass

# ==================== FLASK WEB SERVER ====================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    """Trang chủ - thông tin bot"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM keys")
        total_keys = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM keys WHERE status='active'")
        active_keys = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM keys WHERE used_by IS NOT NULL")
        used_keys = c.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'online',
            'bot_name': bot_info.first_name,
            'bot_username': bot_info.username,
            'version': 'PRO 2.1',
            'total_keys': total_keys,
            'active_keys': active_keys,
            'used_keys': used_keys,
            'admin_id': ADMIN_ID,
            'timestamp': datetime.datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@web_app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'bot': '@' + bot_info.username}), 200

@web_app.route('/checkkey')
def check_key_api():
    """
    API kiểm tra key - Xác thực HWID mỗi lần check
    Cách dùng: GET /checkkey?key=ABC123&hwid=DEVICE_ID&device_name=PC01
    Trả về: {"valid": true, "user": "Nguyen Van A", "expire": "2026-04-01"}
    """
    try:
        key_code = request.args.get('key', '').upper()
        hwid = request.args.get('hwid', '')
        device_name = request.args.get('device_name', 'Unknown')
        device_info = request.args.get('device_info', '')
        ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        if not key_code:
            return jsonify({'valid': False, 'error': 'Missing key code'}), 400
        
        if not hwid:
            return jsonify({'valid': False, 'error': 'Missing HWID'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Kiểm tra key
        c.execute("""
            SELECT user_name, status, expire_date, used_by, used_hwid, device_name, device_info
            FROM keys 
            WHERE key_code = ?
        """, (key_code,))
        result = c.fetchone()
        
        if not result:
            log_activity(key_code, 'invalid_key', ip, user_agent, hwid)
            conn.close()
            return jsonify({'valid': False, 'error': 'Key không tồn tại'})
        
        user_name, status, expire_date, used_by, used_hwid, saved_device, saved_info = result
        
        # Kiểm tra trạng thái
        if status != 'active':
            log_activity(key_code, f'inactive_{status}', ip, user_agent, hwid)
            conn.close()
            return jsonify({'valid': False, 'error': f'Key đã bị {status}'})
        
        # Kiểm tra hết hạn
        days_left = 999
        if expire_date:
            expire_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d').date()
            if expire_obj < datetime.date.today():
                log_activity(key_code, 'expired', ip, user_agent, hwid)
                conn.close()
                return jsonify({'valid': False, 'error': f'Key đã hết hạn từ {expire_date}'})
            days_left = (expire_obj - datetime.date.today()).days
        
        # KIỂM TRA HWID - Chống share key
        if used_hwid:
            # Key đã được kích hoạt, kiểm tra HWID
            if hwid != used_hwid:
                log_activity(key_code, 'hwid_mismatch', ip, user_agent, hwid)
                conn.close()
                return jsonify({
                    'valid': False, 
                    'error': 'Key đã được kích hoạt trên thiết bị khác!',
                    'current_device': saved_device,
                    'request_reset': True
                })
        else:
            # Key chưa được kích hoạt, lưu HWID và thông tin thiết bị
            c.execute("""
                UPDATE keys 
                SET used_by=?, used_hwid=?, used_at=CURRENT_TIMESTAMP, 
                    device_name=?, device_info=?
                WHERE key_code=?
            """, (user_name, hwid, device_name, device_info, key_code))
            conn.commit()
            log_activity(key_code, 'activated', ip, user_agent, hwid)
        
        conn.close()
        
        # Trả về thông tin key
        return jsonify({
            'valid': True,
            'user': user_name,
            'expire': expire_date if expire_date else 'Vĩnh viễn',
            'days_left': days_left,
            'device': saved_device if used_hwid else device_name,
            'message': 'Key hợp lệ',
            'first_time': used_hwid is None
        })
        
    except Exception as e:
        logger.error(f"Check key API error: {e}")
        return jsonify({'valid': False, 'error': str(e)}), 500

@web_app.route('/reset_device')
def reset_device_api():
    """
    API yêu cầu reset thiết bị
    Cách dùng: GET /reset_device?key=ABC123&hwid=DEVICE_ID
    """
    try:
        key_code = request.args.get('key', '').upper()
        hwid = request.args.get('hwid', '')
        ip = request.remote_addr
        
        if not key_code or not hwid:
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Kiểm tra key và HWID
        c.execute("""
            SELECT user_name, used_hwid, status 
            FROM keys 
            WHERE key_code = ?
        """, (key_code,))
        result = c.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'Key không tồn tại'})
        
        user_name, used_hwid, status = result
        
        if status != 'active':
            conn.close()
            return jsonify({'success': False, 'error': f'Key đã bị {status}'})
        
        if not used_hwid:
            conn.close()
            return jsonify({'success': False, 'error': 'Key chưa được kích hoạt'})
        
        if hwid != used_hwid:
            conn.close()
            return jsonify({'success': False, 'error': 'HWID không khớp với thiết bị đang dùng'})
        
        # Ghi nhận yêu cầu reset
        c.execute("""
            INSERT INTO reset_requests (key_code, user_id, status) 
            VALUES (?, ?, 'pending')
        """, (key_code, user_name))
        conn.commit()
        conn.close()
        
        # Gửi thông báo đến admin
        admin_msg = f"""
🔔 *YÊU CẦU RESET THIẾT BỊ*

🔑 Key: `{key_code}`
👤 Người dùng: {user_name}
🖥️ HWID cũ: {used_hwid[:16]}...

Dùng lệnh: /resetkey {key_code} để xác nhận
        """
        bot.send_message(ADMIN_ID, admin_msg, parse_mode='Markdown')
        
        return jsonify({
            'success': True,
            'message': 'Yêu cầu reset đã được gửi đến admin. Vui lòng chờ xử lý.'
        })
        
    except Exception as e:
        logger.error(f"Reset device API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def run_web():
    """Chạy Flask web server"""
    print(f"🌐 Web server đang chạy trên port {PORT}")
    web_app.run(host='0.0.0.0', port=PORT)

# ==================== TELEGRAM COMMANDS ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if is_admin(user_id):
        text = f"""
🎲 *SUNLON KEY MANAGER PRO* 🎲

Xin chào Admin *{user_name}*!

📌 *Lệnh Admin:*
/createkey [tên] [ngày] - Tạo key
/listkeys - Xem danh sách
/checkkey [key] - Kiểm tra key
/resetkey [key] - Reset thiết bị
/revokekey [key] - Vô hiệu key
/deletekey [key] - Xóa key
/stats - Xem thống kê
/getdb - Tải database
/logs - Xem log hoạt động

📌 *API Endpoints:*
• GET /checkkey?key=XXX&hwid=ID - Check key
• GET /reset_device?key=XXX&hwid=ID - Yêu cầu reset
• GET /health - Health check

💡 *Ví dụ:* /createkey Nguyen Van A 30
        """
    else:
        text = f"""
🎲 *SUNLON KEY SYSTEM PRO* 🎲

Xin chào *{user_name}*!

🔑 Kiểm tra key: /check [key]
🔄 Reset thiết bị: /reset [key]

📞 Liên hệ admin để được hỗ trợ
        """
    
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['createkey'])
def create_key(message):
    """Tạo key mới"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Bạn không có quyền!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Sai cú pháp!\n/createkey [tên] [ngày]")
        return
    
    # Xử lý tên và số ngày
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
        c.execute("""
            INSERT INTO keys (key_code, user_name, created_by, expire_date, notes) 
            VALUES (?, ?, ?, ?, ?)
        """, (key_code, user_name, str(message.from_user.id), expire_date, f"Created on {datetime.datetime.now()}"))
        conn.commit()
        
        text = f"""
✅ *KEY MỚI!*

🔑 *Key:* `{key_code}`
👤 *Người dùng:* {user_name}
📅 *Hạn sử dụng:* {expire_date if expire_date else 'Vĩnh viễn'}

📌 *API check key:*
GET /checkkey?key={key_code}&hwid=YOUR_HWID

🔄 *Reset thiết bị:*
GET /reset_device?key={key_code}&hwid=YOUR_HWID
        """
        bot.reply_to(message, text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi: {str(e)}")
    finally:
        conn.close()

@bot.message_handler(commands=['resetkey'])
def reset_key_device(message):
    """Reset thiết bị cho key (admin)"""
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Dùng: /resetkey [KEY]")
        return
    
    key_code = args[1].upper()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Kiểm tra key
    c.execute("""
        SELECT user_name, used_hwid, device_name, status 
        FROM keys 
        WHERE key_code = ?
    """, (key_code,))
    result = c.fetchone()
    
    if not result:
        bot.reply_to(message, f"❌ Key `{key_code}` không tồn tại!", parse_mode='Markdown')
        conn.close()
        return
    
    user_name, used_hwid, device_name, status = result
    
    if status != 'active':
        bot.reply_to(message, f"❌ Key đã bị {status}!")
        conn.close()
        return
    
    if not used_hwid:
        bot.reply_to(message, f"ℹ️ Key chưa được kích hoạt trên thiết bị nào!")
        conn.close()
        return
    
    # Reset thiết bị
    c.execute("""
        UPDATE keys 
        SET used_hwid = NULL, used_by = NULL, used_at = NULL, device_name = NULL, device_info = NULL
        WHERE key_code = ?
    """, (key_code,))
    
    # Cập nhật reset request
    c.execute("""
        UPDATE reset_requests 
        SET status='resolved', resolved_at=CURRENT_TIMESTAMP 
        WHERE key_code=? AND status='pending'
    """, (key_code,))
    
    conn.commit()
    conn.close()
    
    log_activity(key_code, 'reset_by_admin', None, None, None)
    
    text = f"""
✅ *ĐÃ RESET THIẾT BỊ!*

🔑 Key: `{key_code}`
👤 Người dùng: {user_name}
🖥️ Thiết bị cũ: {device_name if device_name else 'Unknown'}

💡 Người dùng có thể kích hoạt lại trên thiết bị mới.
    """
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['reset'])
def reset_request(message):
    """Người dùng yêu cầu reset thiết bị"""
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Dùng: /reset [KEY]")
        return
    
    key_code = args[1].upper()
    user_id = message.from_user.id
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Kiểm tra key
    c.execute("""
        SELECT user_name, used_hwid, status 
        FROM keys 
        WHERE key_code = ?
    """, (key_code,))
    result = c.fetchone()
    
    if not result:
        bot.reply_to(message, f"❌ Key `{key_code}` không tồn tại!", parse_mode='Markdown')
        conn.close()
        return
    
    user_name, used_hwid, status = result
    
    if status != 'active':
        bot.reply_to(message, f"❌ Key đã bị {status}!")
        conn.close()
        return
    
    if not used_hwid:
        bot.reply_to(message, f"ℹ️ Key chưa được kích hoạt trên thiết bị nào!")
        conn.close()
        return
    
    # Kiểm tra đã có request pending chưa
    c.execute("""
        SELECT * FROM reset_requests 
        WHERE key_code=? AND status='pending'
    """, (key_code,))
    if c.fetchone():
        bot.reply_to(message, f"⏳ Yêu cầu reset của key `{key_code}` đang chờ xử lý!", parse_mode='Markdown')
        conn.close()
        return
    
    # Tạo request mới
    c.execute("""
        INSERT INTO reset_requests (key_code, user_id, status) 
        VALUES (?, ?, 'pending')
    """, (key_code, str(user_id)))
    conn.commit()
    conn.close()
    
    # Thông báo cho admin
    admin_msg = f"""
🔔 *YÊU CẦU RESET THIẾT BỊ*

🔑 Key: `{key_code}`
👤 Người dùng: {user_name}
🆔 User ID: {user_id}

Dùng lệnh: /resetkey {key_code} để xác nhận
    """
    bot.send_message(ADMIN_ID, admin_msg, parse_mode='Markdown')
    
    bot.reply_to(message, f"""
✅ Đã gửi yêu cầu reset cho key `{key_code}`!

📌 Admin sẽ xử lý trong thời gian sớm nhất.
    """, parse_mode='Markdown')

@bot.message_handler(commands=['listkeys'])
def list_keys(message):
    if not is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT key_code, user_name, status, expire_date, used_hwid, device_name 
        FROM keys 
        ORDER BY created_at DESC 
        LIMIT 20
    """)
    keys = c.fetchall()
    conn.close()
    
    if not keys:
        bot.reply_to(message, "📭 Chưa có key nào!")
        return
    
    text = "📋 *DANH SÁCH KEY (20 gần nhất)*\n\n"
    for key in keys:
        key_code, user_name, status, expire_date, hwid, device = key
        
        is_expired = False
        if expire_date:
            try:
                expire_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d').date()
                is_expired = expire_obj < datetime.date.today()
            except:
                pass
        
        if is_expired:
            icon = '⚠️'
            status_text = 'HẾT HẠN'
        elif status == 'active':
            icon = '🟢'
            status_text = 'ACTIVE'
        else:
            icon = '🔴'
            status_text = status.upper()
        
        text += f"{icon} `{key_code}`\n"
        text += f"   👤 {user_name}\n"
        text += f"   📅 {expire_date if expire_date else 'Vĩnh viễn'}\n"
        text += f"   📊 {status_text}\n"
        if hwid:
            text += f"   🖥️ {device if device else 'Unknown'} | HWID: {hwid[:12]}...\n"
        text += "\n"
    
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.reply_to(message, text[i:i+4000], parse_mode='Markdown')
    else:
        bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['check'])
def check_key(message):
    """Kiểm tra key (user) - Hiển thị thông tin key"""
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Dùng: /check [KEY]")
        return
    
    key_code = args[1].upper()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT user_name, status, expire_date, used_hwid, device_name, used_at
        FROM keys 
        WHERE key_code=?
    """, (key_code,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        bot.reply_to(message, f"❌ Key `{key_code}` không tồn tại!", parse_mode='Markdown')
        return
    
    user_name, status, expire_date, hwid, device, used_at = result
    
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
    
    device_status = "✅ Đã kích hoạt" if hwid else "⚡ Chưa kích hoạt"
    device_info = f"\n🖥️ Thiết bị: {device}" if device else ""
    
    text = f"""
✅ *THÔNG TIN KEY*

🔑 `{key_code}`
👤 {user_name}
📅 {expire_text}
{device_status}{device_info}

🎉 Key hợp lệ!
    """
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['checkkey'])
def check_key_admin(message):
    """Kiểm tra key (admin)"""
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Dùng: /checkkey [KEY]")
        return
    
    key_code = args[1].upper()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT key_code, user_name, status, expire_date, used_hwid, device_name, used_at, created_at 
        FROM keys 
        WHERE key_code=?
    """, (key_code,))
    result = c.fetchone()
    
    # Lấy reset requests
    c.execute("""
        SELECT status, requested_at FROM reset_requests 
        WHERE key_code=? ORDER BY requested_at DESC LIMIT 1
    """, (key_code,))
    reset_req = c.fetchone()
    conn.close()
    
    if not result:
        bot.reply_to(message, f"❌ Key {key_code} không tồn tại!")
        return
    
    key_code, user_name, status, expire_date, hwid, device, used_at, created_at = result
    
    reset_status = ""
    if reset_req:
        req_status, req_time = reset_req
        reset_status = f"\n📌 Reset request: {req_status} ({req_time[:10]})"
    
    text = f"""
📋 *THÔNG TIN KEY*

🔑 *Key:* `{key_code}`
👤 *Người dùng:* {user_name}
📊 *Trạng thái:* {status}
📅 *Hạn sử dụng:* {expire_date if expire_date else 'Vĩnh viễn'}
🖥️ *Thiết bị:* {device if device else 'Chưa kích hoạt'}
🔑 *HWID:* {hwid if hwid else 'Chưa'}
🕐 *Ngày tạo:* {created_at[:10]}
📌 *Kích hoạt lúc:* {used_at if used_at else 'Chưa'}{reset_status}
    """
    bot.reply_to(message, text, parse_mode='Markdown')

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
    
    c.execute("SELECT COUNT(*) FROM keys WHERE status='revoked'")
    revoked = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM keys WHERE used_hwid IS NOT NULL")
    used = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM keys WHERE expire_date < date('now') AND expire_date IS NOT NULL")
    expired = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM logs WHERE date(timestamp)=date('now')")
    today_checks = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM reset_requests WHERE status='pending'")
    pending_resets = c.fetchone()[0]
    
    conn.close()
    
    text = f"""
📊 *THỐNG KÊ KEY PRO*

📌 *Tổng quan:*
• Tổng số keys: *{total}*
• Đang hoạt động: *{active}* 🟢
• Đã vô hiệu: *{revoked}* 🔴
• Đã kích hoạt: *{used}* ✅
• Hết hạn: *{expired}* ⚠️

📈 *Hoạt động:*
• Check hôm nay: *{today_checks}*
• Reset chờ xử lý: *{pending_resets}*

💡 *Tỷ lệ kích hoạt:* {used/total*100:.1f}% (nếu total > 0)
    """
    bot.reply_to(message, text, parse_mode='Markdown')

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
    
    log_activity(key_code, 'revoked')
    bot.reply_to(message, f"✅ Đã vô hiệu key: `{key_code}`", parse_mode='Markdown')

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
    btn_yes = types.InlineKeyboardButton("✅ Xóa", callback_data=f"del_{key_code}")
    btn_no = types.InlineKeyboardButton("❌ Hủy", callback_data="cancel")
    markup.add(btn_yes, btn_no)
    
    bot.reply_to(message, f"⚠️ Xóa key: `{key_code}`?", 
                 parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['getdb'])
def get_database_telegram(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Bạn không có quyền!")
        return
    
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, 'rb') as f:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM keys")
                count = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM reset_requests WHERE status='pending'")
                pending = c.fetchone()[0]
                conn.close()
                
                bot.send_document(
                    message.chat.id,
                    f,
                    caption=f"📁 Database PRO\n📊 Số key: {count}\n⏳ Reset pending: {pending}\n🕐 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
        else:
            bot.reply_to(message, "❌ Database chưa được tạo!")
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['logs'])
def show_logs(message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    limit = 20
    if len(args) > 1:
        try:
            limit = int(args[1])
        except:
            pass
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT key_code, action, ip_address, hwid, timestamp 
        FROM logs 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (limit,))
    logs = c.fetchall()
    conn.close()
    
    if not logs:
        bot.reply_to(message, "📭 Chưa có log nào!")
        return
    
    text = f"📋 *LOG HOẠT ĐỘNG ({limit} gần nhất)*\n\n"
    for log in logs:
        key_code, action, ip, hwid, timestamp = log
        text += f"🕐 {timestamp[:16]}\n"
        text += f"   🔑 `{key_code}` | {action}\n"
        text += f"   🌐 {ip}\n"
        if hwid:
            text += f"   🖥️ HWID: {hwid[:16]}...\n"
        text += "\n"
    
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.reply_to(message, text[i:i+4000], parse_mode='Markdown')
    else:
        bot.reply_to(message, text, parse_mode='Markdown')

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
        
        bot.edit_message_text(f"✅ Đã xóa key: `{key_code}`", 
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              parse_mode='Markdown')
    elif call.data == "cancel":
        bot.edit_message_text("❌ Đã hủy", 
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id)

@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.reply_to(message, "❓ Dùng /start để xem hướng dẫn")

# ==================== CHẠY BOT ====================
if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print("🤖 SunLon Bot PRO đang chạy...")
    print(f"   Bot: @{bot_info.username}")
    print(f"   Admin ID: {ADMIN_ID}")
    print(f"   Port: {PORT}")
    print("=" * 60)
    print("🌐 API Endpoints:")
    print(f"   GET /health - Health check")
    print(f"   GET /checkkey?key=XXX&hwid=ID - Check key (có HWID)")
    print(f"   GET /reset_device?key=XXX&hwid=ID - Yêu cầu reset")
    print(f"   GET /stats - Thống kê (admin)")
    print("=" * 60)
    
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"⚠️ Lỗi: {e}")
            time.sleep(10)

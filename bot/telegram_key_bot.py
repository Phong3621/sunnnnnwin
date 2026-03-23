"""
Telegram Bot - SunLon Key Manager PRO
Đã fix lỗi 409 conflict
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
import re
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

# Xóa webhook cũ nếu có
try:
    bot.remove_webhook()
    print("✅ Đã xóa webhook cũ")
except:
    pass
time.sleep(1)

# ==================== DATABASE ====================
def init_db():
    """Khởi tạo database"""
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
            used_by TEXT,
            used_hwid TEXT,
            used_at TIMESTAMP,
            device_name TEXT,
            device_info TEXT,
            notes TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_code TEXT,
            action TEXT,
            ip_address TEXT,
            user_agent TEXT,
            hwid TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
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
        print("✅ Database initialized")
        return True
    except Exception as e:
        print(f"❌ Database init error: {e}")
        return False

def generate_key():
    return secrets.token_hex(6).upper()

def is_admin(user_id):
    try:
        return int(user_id) == ADMIN_ID
    except:
        return False

def log_activity(key_code, action, ip=None, user_agent=None, hwid=None):
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
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM keys")
        total_keys = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM keys WHERE status='active'")
        active_keys = c.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'online',
            'bot_name': bot_info.first_name,
            'bot_username': bot_info.username,
            'total_keys': total_keys,
            'active_keys': active_keys
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@web_app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'bot': '@' + bot_info.username}), 200

@web_app.route('/checkkey')
def check_key_api():
    try:
        key_code = request.args.get('key', '').upper()
        hwid = request.args.get('hwid', '')
        device_name = request.args.get('device_name', 'Unknown')
        device_info = request.args.get('device_info', '')
        ip = request.remote_addr
        
        if not key_code:
            return jsonify({'valid': False, 'error': 'Missing key code'}), 400
        
        if not hwid:
            return jsonify({'valid': False, 'error': 'Missing HWID'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT user_name, status, expire_date, used_by, used_hwid, device_name
            FROM keys WHERE key_code = ?
        """, (key_code,))
        result = c.fetchone()
        
        if not result:
            log_activity(key_code, 'invalid_key', ip, None, hwid)
            conn.close()
            return jsonify({'valid': False, 'error': 'Key khong ton tai'})
        
        user_name, status, expire_date, used_by, used_hwid, saved_device = result
        
        if status != 'active':
            conn.close()
            return jsonify({'valid': False, 'error': f'Key da bi {status}'})
        
        days_left = 999
        if expire_date:
            expire_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d').date()
            if expire_obj < datetime.date.today():
                log_activity(key_code, 'expired', ip, None, hwid)
                conn.close()
                return jsonify({'valid': False, 'error': f'Key het han tu {expire_date}'})
            days_left = (expire_obj - datetime.date.today()).days
        
        if used_hwid:
            if hwid != used_hwid:
                log_activity(key_code, 'hwid_mismatch', ip, None, hwid)
                conn.close()
                return jsonify({
                    'valid': False,
                    'error': 'Key da duoc kich hoat tren thiet bi khac',
                    'device': saved_device,
                    'request_reset': True
                })
        else:
            c.execute("""
                UPDATE keys SET used_by=?, used_hwid=?, used_at=CURRENT_TIMESTAMP,
                    device_name=?, device_info=?
                WHERE key_code=?
            """, (user_name, hwid, device_name, device_info, key_code))
            conn.commit()
            log_activity(key_code, 'activated', ip, None, hwid)
        
        conn.close()
        
        return jsonify({
            'valid': True,
            'user': user_name,
            'expire': expire_date if expire_date else 'Vinh vien',
            'days_left': days_left,
            'device': saved_device if used_hwid else device_name
        })
        
    except Exception as e:
        logger.error(f"Check key API error: {e}")
        return jsonify({'valid': False, 'error': str(e)}), 500

@web_app.route('/reset_device')
def reset_device_api():
    try:
        key_code = request.args.get('key', '').upper()
        hwid = request.args.get('hwid', '')
        ip = request.remote_addr
        
        if not key_code or not hwid:
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT user_name, used_hwid, status FROM keys WHERE key_code = ?", (key_code,))
        result = c.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'Key khong ton tai'})
        
        user_name, used_hwid, status = result
        
        if status != 'active':
            conn.close()
            return jsonify({'success': False, 'error': f'Key da bi {status}'})
        
        if not used_hwid:
            conn.close()
            return jsonify({'success': False, 'error': 'Key chua duoc kich hoat'})
        
        if hwid != used_hwid:
            conn.close()
            return jsonify({'success': False, 'error': 'HWID khong khop'})
        
        c.execute("""
            INSERT INTO reset_requests (key_code, user_id, status) 
            VALUES (?, ?, 'pending')
        """, (key_code, user_name))
        conn.commit()
        conn.close()
        
        log_activity(key_code, 'reset_requested', ip, None, hwid)
        
        admin_msg = f"""🔔 YEU CAU RESET THIET BI

🔑 Key: {key_code}
👤 Nguoi dung: {user_name}

Dung lenh: /resetkey {key_code} de xac nhan"""
        
        bot.send_message(ADMIN_ID, admin_msg)
        
        return jsonify({
            'success': True,
            'message': 'Yeu cau reset da gui den admin'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def run_web():
    print(f"🌐 Web server running on port {PORT}")
    web_app.run(host='0.0.0.0', port=PORT)

# ==================== TELEGRAM COMMANDS ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if is_admin(user_id):
        text = f"""🎲 SUNLON KEY MANAGER PRO

Xin chào Admin {user_name}!

📌 Lenh Admin:
/createkey [ten] [ngay] - Tao key moi
/listkeys - Xem danh sach
/checkkey [key] - Kiem tra key
/resetkey [key] - Reset thiet bi
/revokekey [key] - Vo hieu key
/deletekey [key] - Xoa key
/stats - Xem thong ke
/getdb - Tai database
/logs - Xem log hoat dong

💡 Vi du: /createkey Nguyen Van A 30"""
    else:
        text = f"""🎲 SUNLON KEY SYSTEM PRO

Xin chao {user_name}!

🔑 Kiem tra key: /check [key]
🔄 Reset thiet bi: /reset [key]

📞 Lien he admin de duoc ho tro"""
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['createkey'])
def create_key(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Ban khong co quyen!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Sai cu phap!\n/createkey [ten] [ngay]")
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
        c.execute("""
            INSERT INTO keys (key_code, user_name, created_by, expire_date, notes) 
            VALUES (?, ?, ?, ?, ?)
        """, (key_code, user_name, str(message.from_user.id), expire_date, f"Created on {datetime.datetime.now()}"))
        conn.commit()
        
        text = f"""✅ KEY MOI!

🔑 Key: {key_code}
👤 Nguoi dung: {user_name}
📅 Han su dung: {expire_date if expire_date else 'Vinh vien'}

📌 API check key:
GET /checkkey?key={key_code}&hwid=YOUR_HWID"""
        
        bot.reply_to(message, text)
    except Exception as e:
        bot.reply_to(message, f"❌ Loi: {str(e)}")
    finally:
        conn.close()

@bot.message_handler(commands=['listkeys'])
def list_keys(message):
    if not is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT key_code, user_name, status, expire_date, used_hwid, device_name 
        FROM keys ORDER BY created_at DESC LIMIT 20
    """)
    keys = c.fetchall()
    conn.close()
    
    if not keys:
        bot.reply_to(message, "📭 Chua co key nao!")
        return
    
    text = "📋 DANH SACH KEY (20 gan nhat)\n\n"
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
            icon = "⚠️"
            status_text = "HET HAN"
        elif status == 'active':
            icon = "🟢"
            status_text = "ACTIVE"
        else:
            icon = "🔴"
            status_text = status.upper()
        
        text += f"{icon} {key_code}\n"
        text += f"   👤 {user_name}\n"
        text += f"   📅 {expire_date if expire_date else 'Vinh vien'}\n"
        text += f"   📊 {status_text}\n"
        if hwid:
            text += f"   🖥️ {device if device else 'Unknown'}\n"
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
        bot.reply_to(message, "❌ Dung: /check [KEY]")
        return
    
    key_code = args[1].upper()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT user_name, status, expire_date, used_hwid, device_name
        FROM keys WHERE key_code=?
    """, (key_code,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        bot.reply_to(message, f"❌ Key {key_code} khong ton tai!")
        return
    
    user_name, status, expire_date, hwid, device = result
    
    if status != 'active':
        bot.reply_to(message, "❌ Key da bi vo hieu!")
        return
    
    if expire_date:
        try:
            expire_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d').date()
            days_left = (expire_obj - datetime.date.today()).days
            if days_left < 0:
                bot.reply_to(message, f"⚠️ Key da het han tu {expire_date}")
                return
            expire_text = f"{expire_date} (con {days_left} ngay)"
        except:
            expire_text = expire_date
    else:
        expire_text = "Vinh vien"
    
    device_status = "✅ Da kich hoat" if hwid else "⚡ Chua kich hoat"
    device_info = f"\n🖥️ Thiet bi: {device}" if device else ""
    
    text = f"""✅ THONG TIN KEY

🔑 {key_code}
👤 {user_name}
📅 {expire_text}
{device_status}{device_info}

🎉 Key hop le!"""
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['resetkey'])
def reset_key_device(message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Dung: /resetkey [KEY]")
        return
    
    key_code = args[1].upper()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT user_name, used_hwid, device_name, status FROM keys WHERE key_code = ?", (key_code,))
    result = c.fetchone()
    
    if not result:
        bot.reply_to(message, f"❌ Key {key_code} khong ton tai!")
        conn.close()
        return
    
    user_name, used_hwid, device_name, status = result
    
    if status != 'active':
        bot.reply_to(message, f"❌ Key da bi {status}!")
        conn.close()
        return
    
    if not used_hwid:
        bot.reply_to(message, f"ℹ️ Key chua duoc kich hoat!")
        conn.close()
        return
    
    c.execute("""
        UPDATE keys SET used_hwid = NULL, used_by = NULL, used_at = NULL, device_name = NULL, device_info = NULL
        WHERE key_code = ?
    """, (key_code,))
    
    c.execute("""
        UPDATE reset_requests SET status='resolved', resolved_at=CURRENT_TIMESTAMP
        WHERE key_code=? AND status='pending'
    """, (key_code,))
    
    conn.commit()
    conn.close()
    
    log_activity(key_code, 'reset_by_admin')
    
    text = f"""✅ DA RESET THIET BI!

🔑 Key: {key_code}
👤 Nguoi dung: {user_name}
🖥️ Thiet bi cu: {device_name if device_name else 'Unknown'}

💡 Nguoi dung co the kich hoat lai tren thiet bi moi."""
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['reset'])
def reset_request(message):
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Dung: /reset [KEY]")
        return
    
    key_code = args[1].upper()
    user_id = message.from_user.id
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT user_name, used_hwid, status FROM keys WHERE key_code = ?", (key_code,))
    result = c.fetchone()
    
    if not result:
        bot.reply_to(message, f"❌ Key {key_code} khong ton tai!")
        conn.close()
        return
    
    user_name, used_hwid, status = result
    
    if status != 'active':
        bot.reply_to(message, f"❌ Key da bi {status}!")
        conn.close()
        return
    
    if not used_hwid:
        bot.reply_to(message, f"ℹ️ Key chua duoc kich hoat!")
        conn.close()
        return
    
    c.execute("SELECT * FROM reset_requests WHERE key_code=? AND status='pending'", (key_code,))
    if c.fetchone():
        bot.reply_to(message, f"⏳ Yeu cau reset cua key {key_code} dang cho xu ly!")
        conn.close()
        return
    
    c.execute("INSERT INTO reset_requests (key_code, user_id, status) VALUES (?, ?, 'pending')", (key_code, str(user_id)))
    conn.commit()
    conn.close()
    
    log_activity(key_code, 'reset_requested_by_user')
    
    admin_msg = f"""🔔 YEU CAU RESET THIET BI

🔑 Key: {key_code}
👤 Nguoi dung: {user_name}
🆔 User ID: {user_id}

Dung lenh: /resetkey {key_code} de xac nhan"""
    
    bot.send_message(ADMIN_ID, admin_msg)
    
    bot.reply_to(message, f"""✅ Da gui yeu cau reset cho key {key_code}!

📌 Admin se xu ly trong thoi gian som nhat.""")

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
    
    c.execute("SELECT COUNT(*) FROM keys WHERE used_hwid IS NOT NULL")
    used = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM keys WHERE expire_date < date('now') AND expire_date IS NOT NULL")
    expired = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM reset_requests WHERE status='pending'")
    pending = c.fetchone()[0]
    
    conn.close()
    
    text = f"""📊 THONG KE KEY PRO

📌 Tong quan:
• Tong so keys: {total}
• Dang hoat dong: {active} 🟢
• Da kich hoat: {used} ✅
• Het han: {expired} ⚠️

📈 Reset cho xu ly: {pending}

💡 Ty le kich hoat: {used/total*100:.1f}% (neu total > 0)"""
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['revokekey'])
def revoke_key(message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Dung: /revokekey [KEY]")
        return
    
    key_code = args[1].upper()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE keys SET status='revoked' WHERE key_code=?", (key_code,))
    conn.commit()
    conn.close()
    
    log_activity(key_code, 'revoked')
    bot.reply_to(message, f"✅ Da vo hieu key: {key_code}")

@bot.message_handler(commands=['deletekey'])
def delete_key(message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Dung: /deletekey [KEY]")
        return
    
    key_code = args[1].upper()
    
    markup = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton("✅ Xoa", callback_data=f"del_{key_code}")
    btn_no = types.InlineKeyboardButton("❌ Huy", callback_data="cancel")
    markup.add(btn_yes, btn_no)
    
    bot.reply_to(message, f"⚠️ Xoa key: {key_code}?", reply_markup=markup)

@bot.message_handler(commands=['getdb'])
def get_database_telegram(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Ban khong co quyen!")
        return
    
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, 'rb') as f:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM keys")
                count = c.fetchone()[0]
                conn.close()
                
                bot.send_document(
                    message.chat.id,
                    f,
                    caption=f"📁 Database\n📊 So key: {count}\n🕐 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
        else:
            bot.reply_to(message, "❌ Database chua duoc tao!")
    except Exception as e:
        bot.reply_to(message, f"❌ Loi: {str(e)}")

@bot.message_handler(commands=['logs'])
def show_logs(message):
    if not is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT key_code, action, ip_address, hwid, timestamp 
        FROM logs ORDER BY timestamp DESC LIMIT 20
    """)
    logs = c.fetchall()
    conn.close()
    
    if not logs:
        bot.reply_to(message, "📭 Chua co log nao!")
        return
    
    text = "📋 LOG HOAT DONG (20 gan nhat)\n\n"
    for log in logs:
        key_code, action, ip, hwid, timestamp = log
        text += f"🕐 {timestamp[:16]}\n"
        text += f"   🔑 {key_code} | {action}\n"
        text += f"   🌐 {ip}\n"
        if hwid:
            text += f"   🖥️ HWID: {hwid[:16]}...\n"
        text += "\n"
    
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.reply_to(message, text[i:i+4000])
    else:
        bot.reply_to(message, text)

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
        
        bot.edit_message_text(f"✅ Da xoa key: {key_code}", 
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id)
    elif call.data == "cancel":
        bot.edit_message_text("❌ Da huy", 
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id)

@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.reply_to(message, "❓ Dung /start de xem huong dan")

# ==================== CHẠY BOT ====================
if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print("🤖 SunLon Bot PRO dang chay...")
    print(f"   Bot: @{bot_info.username}")
    print(f"   Admin ID: {ADMIN_ID}")
    print("=" * 60)
    print("🌐 API Endpoints:")
    print(f"   GET /health - Health check")
    print(f"   GET /checkkey?key=XXX&hwid=ID - Check key")
    print(f"   GET /reset_device?key=XXX&hwid=ID - Reset device")
    print("=" * 60)
    
    # Chạy web server trong thread riêng
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    print("🌐 Web server started")
    
    # Chạy bot với xử lý conflict
    retry_count = 0
    while True:
        try:
            print("🤖 Bot polling started...")
            # Dùng polling với skip_pending và restart_on_change
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                skip_pending=True,
                restart_on_change=True
            )
        except Exception as e:
            error_msg = str(e)
            if "409" in error_msg or "Conflict" in error_msg:
                retry_count += 1
                print(f"⚠️ Conflict detected (attempt {retry_count}), restarting...")
                # Xóa webhook và thử lại
                try:
                    bot.remove_webhook()
                    print("✅ Webhook removed")
                except:
                    pass
                time.sleep(5)
                if retry_count > 3:
                    print("🔄 Restarting bot...")
                    retry_count = 0
            else:
                print(f"⚠️ Error: {e}")
                time.sleep(10)

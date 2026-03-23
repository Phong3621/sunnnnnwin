"""
Telegram Bot - SunLon Key Manager
<<<<<<< HEAD
Hỗ trợ cả Background Worker và Web Service (với Flask health check)
Deploy trên Render
=======
Phiên bản tối giản cho Render
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
"""

import telebot
from telebot import types
import sqlite3
import secrets
import datetime
import os
import logging
import time
<<<<<<< HEAD
import threading
=======
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
from datetime import timedelta
from flask import Flask, jsonify

# Cấu hình logging
<<<<<<< HEAD
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
=======
logging.basicConfig(level=logging.INFO)
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
logger = logging.getLogger(__name__)

# ==================== CẤU HÌNH ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))
<<<<<<< HEAD
DB_PATH = 'sunlon_keys.db'
PORT = int(os.environ.get('PORT', 10000))

if not BOT_TOKEN:
    print("❌ LỖI: Thiếu BOT_TOKEN environment variable!")
    print("Vui lòng thêm BOT_TOKEN vào Environment Variables trên Render")
=======

if not BOT_TOKEN:
    print("❌ LỖI: Thiếu BOT_TOKEN!")
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
    exit(1)

if ADMIN_ID == 0:
    print("⚠️ CẢNH BÁO: ADMIN_ID chưa được cấu hình!")
<<<<<<< HEAD
    print("Vui lòng thêm ADMIN_ID vào Environment Variables trên Render")
=======
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20

try:
    bot = telebot.TeleBot(BOT_TOKEN)
    bot_info = bot.get_me()
<<<<<<< HEAD
    print(f"✅ Bot đã kết nối thành công!")
=======
    print(f"✅ Bot đã kết nối!")
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
    print(f"   Username: @{bot_info.username}")
    print(f"   Name: {bot_info.first_name}")
except Exception as e:
<<<<<<< HEAD
    print(f"❌ Lỗi kết nối bot: {e}")
    exit(1)

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
            used_at TIMESTAMP,
            notes TEXT
        )''')
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database init error: {e}")
        return False
=======
    print(f"❌ Lỗi: {e}")
    exit(1)

# Database
DB_PATH = 'sunlon_keys.db'

def init_db():
    """Khởi tạo database"""
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
        used_at TIMESTAMP
    )''')
    conn.commit()
    conn.close()
    print("✅ Database initialized")
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20

def generate_key():
    """Tạo key ngẫu nhiên"""
    return secrets.token_hex(6).upper()

def is_admin(user_id):
    """Kiểm tra admin"""
    try:
        return int(user_id) == ADMIN_ID
    except:
        return False

<<<<<<< HEAD
def get_key_info(key_code):
    """Lấy thông tin key"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT key_code, user_name, status, expire_date, used_by, created_at FROM keys WHERE key_code=?", (key_code,))
    result = c.fetchone()
    conn.close()
    return result

# ==================== FLASK WEB SERVER (CHO RENDER) ====================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    """Trang chủ - hiển thị thông tin bot"""
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
            'active_keys': active_keys,
            'admin_id': ADMIN_ID,
            'timestamp': datetime.datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@web_app.route('/health')
def health():
    """Health check endpoint cho Render"""
    return jsonify({'status': 'healthy', 'bot': '@' + bot_info.username}), 200

@web_app.route('/getdb')
def get_database():
    """API để tải database (chỉ admin có token)"""
    # Kiểm tra token đơn giản (có thể cải thiện thêm)
    admin_token = os.environ.get('ADMIN_TOKEN', '')
    request_token = request.headers.get('X-Admin-Token', '')
    
    if admin_token and request_token != admin_token:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, 'rb') as f:
                from flask import send_file
                return send_file(
                    DB_PATH,
                    as_attachment=True,
                    download_name=f'sunlon_keys_{datetime.datetime.now().strftime("%Y%m%d")}.db',
                    mimetype='application/x-sqlite3'
                )
        else:
            return jsonify({'error': 'Database not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_web():
    """Chạy Flask web server"""
    print(f"🌐 Web server đang chạy trên port {PORT}")
    web_app.run(host='0.0.0.0', port=PORT)

# ==================== TELEGRAM COMMANDS ====================
=======
# ==================== COMMANDS ====================
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20

@bot.message_handler(commands=['start'])
def start_command(message):
    """Lệnh start"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if is_admin(user_id):
        text = f"""
<<<<<<< HEAD
🎲 *SUNLON KEY MANAGER* 🎲
=======
🎲 *SUNLON KEY BOT* 🎲
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20

Xin chào Admin *{user_name}*!

📌 *Lệnh:*
/createkey [tên] [ngày] - Tạo key
/listkeys - Xem danh sách
/check [key] - Kiểm tra key
/stats - Xem thống kê
/getdb - Tải database keys

💡 *Ví dụ:* 
/createkey Nguyen Van A 30
<<<<<<< HEAD
/listkeys
        """
    else:
        text = f"""
🎲 *SUNLON KEY SYSTEM* 🎲
=======
        """
    else:
        text = f"""
🎲 *SUNLON KEY BOT* 🎲
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20

Xin chào *{user_name}*!

🔑 Kiểm tra key: /check [key]

📞 Liên hệ admin để được cấp key
        """
    
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['createkey'])
def create_key(message):
    """Tạo key mới"""
    if not is_admin(message.from_user.id):
<<<<<<< HEAD
        bot.reply_to(message, "❌ Bạn không có quyền tạo key!")
        return
    
    args = message.text.split()
    
    if len(args) < 2:
        bot.reply_to(message, """
❌ *Sai cú pháp!*

Cách dùng:
/createkey [tên người dùng] [số ngày]

📌 *Ví dụ:*
/createkey Nguyen Van A 30
/createkey Tran Thi B 7
/createkey Le Van C 0  (key vĩnh viễn)
        """, parse_mode='Markdown')
=======
        bot.reply_to(message, "❌ Bạn không có quyền!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Sai cú pháp!\n/createkey [tên] [ngày]")
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
        return
    
    # Xử lý tên và số ngày
    if len(args) >= 3:
        try:
            expire_days = int(args[-1])
            user_name = ' '.join(args[1:-1])
<<<<<<< HEAD
        except ValueError:
=======
        except:
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
            user_name = ' '.join(args[1:])
            expire_days = 30
    else:
        user_name = args[1]
        expire_days = 30
    
<<<<<<< HEAD
    # Tạo key
    key_code = generate_key()
    expire_date = None
    
    if expire_days > 0:
        expire_date = (datetime.date.today() + timedelta(days=expire_days)).strftime('%Y-%m-%d')
    
    # Lưu vào database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        c.execute("""
            INSERT INTO keys (key_code, user_name, created_by, expire_date, notes) 
            VALUES (?, ?, ?, ?, ?)
        """, (key_code, user_name, str(message.from_user.id), expire_date, f"Created on {datetime.datetime.now()}"))
=======
    key_code = generate_key()
    expire_date = None
    if expire_days > 0:
        expire_date = (datetime.date.today() + timedelta(days=expire_days)).strftime('%Y-%m-%d')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO keys (key_code, user_name, created_by, expire_date) 
            VALUES (?, ?, ?, ?)
        """, (key_code, user_name, str(message.from_user.id), expire_date))
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
        conn.commit()
        
        text = f"""
✅ *KEY MỚI!*

🔑 `{key_code}`
👤 {user_name}
📅 {expire_date if expire_date else 'Vĩnh viễn'}

💡 Gửi key này cho người dùng
        """
        bot.reply_to(message, text, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi: {str(e)}")
    finally:
        conn.close()

@bot.message_handler(commands=['listkeys'])
def list_keys(message):
    """Xem danh sách key"""
    if not is_admin(message.from_user.id):
<<<<<<< HEAD
        bot.reply_to(message, "❌ Bạn không có quyền xem danh sách!")
=======
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
<<<<<<< HEAD
        SELECT key_code, user_name, status, expire_date, used_by, created_at 
        FROM keys 
        ORDER BY created_at DESC 
        LIMIT 20
=======
        SELECT key_code, user_name, status, expire_date 
        FROM keys 
        ORDER BY created_at DESC 
        LIMIT 15
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
    """)
    keys = c.fetchall()
    conn.close()
    
    if not keys:
<<<<<<< HEAD
        bot.reply_to(message, "📭 Chưa có key nào được tạo!")
        return
    
    text = "📋 *DANH SÁCH KEY (20 gần nhất)*\n\n"
    for key in keys:
        key_code, user_name, status, expire_date, used_by, created_at = key
=======
        bot.reply_to(message, "📭 Chưa có key nào!")
        return
    
    text = "📋 *DANH SÁCH KEY*\n\n"
    for key in keys:
        key_code, user_name, status, expire_date = key
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
        
        # Kiểm tra hết hạn
        is_expired = False
        if expire_date:
            try:
                expire_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d').date()
                is_expired = expire_obj < datetime.date.today()
            except:
                pass
        
<<<<<<< HEAD
        status_icon = {
            'active': '🟢',
            'revoked': '🔴'
        }.get(status, '⚪')
        
        if is_expired:
            status_icon = '⚠️'
            status_text = 'HẾT HẠN'
        else:
            status_text = status.upper()
        
        text += f"{status_icon} `{key_code}`\n"
        text += f"   👤 {user_name}\n"
        text += f"   📅 Hạn: {expire_date if expire_date else 'Vĩnh viễn'}\n"
        text += f"   📊 {status_text}\n"
        text += f"   🕐 {created_at[:10]}\n\n"
=======
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
        text += f"   📊 {status_text}\n\n"
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
    
    # Gửi từng phần nếu quá dài
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.reply_to(message, text[i:i+4000], parse_mode='Markdown')
    else:
        bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['check'])
def check_key(message):
<<<<<<< HEAD
    """Kiểm tra key cho người dùng"""
    args = message.text.split()
    
    if len(args) != 2:
        bot.reply_to(message, "❌ *Sai cú pháp!*\nDùng: `/check [KEY]`", parse_mode='Markdown')
=======
    """Kiểm tra key"""
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Dùng: /check [KEY]")
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
        return
    
    key_code = args[1].upper()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
<<<<<<< HEAD
        SELECT key_code, user_name, status, expire_date, used_by 
=======
        SELECT user_name, status, expire_date 
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
        FROM keys 
        WHERE key_code=?
    """, (key_code,))
    result = c.fetchone()
<<<<<<< HEAD
    
    if not result:
        bot.reply_to(message, f"❌ *Key `{key_code}` không tồn tại!*", parse_mode='Markdown')
        conn.close()
        return
    
    key_code, user_name, status, expire_date, used_by = result
    
    # Kiểm tra hết hạn
    is_expired = False
    if expire_date:
        try:
            expire_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d').date()
            is_expired = expire_obj < datetime.date.today()
        except:
            pass
    
    if status != 'active' or is_expired:
        if is_expired:
            bot.reply_to(message, f"⚠️ *Key `{key_code}` đã hết hạn!*\n📅 Hết hạn ngày: {expire_date}", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"❌ *Key `{key_code}` đã bị vô hiệu!*", parse_mode='Markdown')
        conn.close()
        return
    
    # Cập nhật thời gian sử dụng
    if not used_by:
        c.execute("""
            UPDATE keys 
            SET used_by=?, used_at=CURRENT_TIMESTAMP 
            WHERE key_code=?
        """, (str(message.from_user.id), key_code))
        conn.commit()
    
=======
    conn.close()
    
    if not result:
        bot.reply_to(message, f"❌ Key `{key_code}` không tồn tại!", parse_mode='Markdown')
        return
    
    user_name, status, expire_date = result
    
    # Kiểm tra trạng thái
    if status != 'active':
        bot.reply_to(message, "❌ Key đã bị vô hiệu!")
        return
    
    # Kiểm tra hết hạn
    if expire_date:
        try:
            expire_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d').date()
            if expire_obj < datetime.date.today():
                bot.reply_to(message, f"⚠️ Key đã hết hạn từ {expire_date}")
                return
        except:
            pass
    
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
    text = f"""
✅ *KEY HỢP LỆ!*

🔑 `{key_code}`
👤 {user_name}
📅 {expire_date if expire_date else 'Vĩnh viễn'}

<<<<<<< HEAD
🎉 Key có thể sử dụng để kích hoạt SunLon Client!
    """
    
    bot.reply_to(message, text, parse_mode='Markdown')
    conn.close()

@bot.message_handler(commands=['checkkey', 'check_key'])
def check_key_admin(message):
    """Kiểm tra key (admin)"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Bạn không có quyền!")
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Sai cú pháp! Dùng: /checkkey [KEY]")
        return
    
    key_code = args[1].upper()
    info = get_key_info(key_code)
    
    if not info:
        bot.reply_to(message, f"❌ Key {key_code} không tồn tại!")
        return
    
    key_code, user_name, status, expire_date, used_by, created_at = info
    
    text = f"""
📋 *THÔNG TIN KEY*

🔑 *Key:* `{key_code}`
👤 *Người dùng:* {user_name}
📊 *Trạng thái:* {status}
📅 *Hạn sử dụng:* {expire_date if expire_date else 'Vĩnh viễn'}
👥 *Đã sử dụng bởi:* {used_by if used_by else 'Chưa sử dụng'}
🕐 *Ngày tạo:* {created_at[:10]}
    """
    
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['revokekey', 'revoke_key'])
def revoke_key(message):
    """Vô hiệu hóa key"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Bạn không có quyền!")
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Sai cú pháp! Dùng: /revokekey [KEY]")
        return
    
    key_code = args[1].upper()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE keys SET status='revoked' WHERE key_code=?", (key_code,))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ Đã vô hiệu hóa key: `{key_code}`", parse_mode='Markdown')

@bot.message_handler(commands=['deletekey', 'delete_key'])
def delete_key(message):
    """Xóa key"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Bạn không có quyền!")
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Sai cú pháp! Dùng: /deletekey [KEY]")
        return
    
    key_code = args[1].upper()
    
    # Xác nhận xóa
    markup = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton("✅ Xóa", callback_data=f"del_{key_code}")
    btn_no = types.InlineKeyboardButton("❌ Hủy", callback_data="cancel")
    markup.add(btn_yes, btn_no)
    
    bot.reply_to(message, f"⚠️ Bạn có chắc muốn xóa key: `{key_code}`?", 
                 parse_mode='Markdown', reply_markup=markup)
=======
🎉 Key có thể sử dụng!
    """
    bot.reply_to(message, text, parse_mode='Markdown')
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20

@bot.message_handler(commands=['stats'])
def stats(message):
    """Thống kê"""
    if not is_admin(message.from_user.id):
<<<<<<< HEAD
        bot.reply_to(message, "❌ Bạn không có quyền!")
=======
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
<<<<<<< HEAD
    # Tổng số keys
    c.execute("SELECT COUNT(*) FROM keys")
    total = c.fetchone()[0]
    
    # Keys active
    c.execute("SELECT COUNT(*) FROM keys WHERE status='active'")
    active = c.fetchone()[0]
    
    # Keys revoked
    c.execute("SELECT COUNT(*) FROM keys WHERE status='revoked'")
    revoked = c.fetchone()[0]
    
    # Keys đã sử dụng
    c.execute("SELECT COUNT(*) FROM keys WHERE used_by IS NOT NULL")
    used = c.fetchone()[0]
    
    # Keys hết hạn
    c.execute("SELECT COUNT(*) FROM keys WHERE expire_date < date('now') AND expire_date IS NOT NULL")
    expired = c.fetchone()[0]
    
    # Keys sắp hết hạn (7 ngày)
    c.execute("SELECT COUNT(*) FROM keys WHERE expire_date BETWEEN date('now') AND date('now', '+7 days')")
    expiring_soon = c.fetchone()[0]
=======
    c.execute("SELECT COUNT(*) FROM keys")
    total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM keys WHERE status='active'")
    active = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM keys WHERE status='revoked'")
    revoked = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM keys WHERE expire_date < date('now') AND expire_date IS NOT NULL")
    expired = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM keys WHERE used_by IS NOT NULL")
    used = c.fetchone()[0]
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
    
    conn.close()
    
    text = f"""
📊 *THỐNG KÊ KEY*

📌 *Tổng quan:*
• Tổng số keys: *{total}*
<<<<<<< HEAD
• Keys đang hoạt động: *{active}* 🟢
• Keys đã vô hiệu: *{revoked}* 🔴
• Keys đã sử dụng: *{used}* ✅
• Keys hết hạn: *{expired}* ⚠️
• Keys sắp hết hạn: *{expiring_soon}* ⏰

💡 *Tỷ lệ sử dụng:* {used/total*100:.1f}% (nếu total > 0)
    """
    
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['getdb'])
def get_database(message):
    """Tải database keys (chỉ admin)"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Bạn không có quyền tải database!")
        return
    
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, 'rb') as f:
                # Đếm số key trong database
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM keys")
                count = c.fetchone()[0]
                conn.close()
                
                bot.send_document(
                    message.chat.id, 
                    f,
                    caption=f"📁 Database keys\n📊 Số key: {count}\n🕐 Ngày tạo: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                logger.info(f"Database sent to admin {message.from_user.id}")
        else:
            bot.reply_to(message, "❌ Database chưa được khởi tạo!")
    except Exception as e:
        logger.error(f"Error sending database: {e}")
        bot.reply_to(message, f"❌ Lỗi: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Xử lý callback xóa key"""
    try:
        if call.data.startswith("del_"):
            key_code = call.data[4:]
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM keys WHERE key_code=?", (key_code,))
            conn.commit()
            conn.close()
            
            bot.edit_message_text(f"✅ Đã xóa key: `{key_code}`", 
                                  chat_id=call.message.chat.id,
                                  message_id=call.message.message_id,
                                  parse_mode='Markdown')
=======
• Đang hoạt động: *{active}* 🟢
• Đã vô hiệu: *{revoked}* 🔴
• Đã sử dụng: *{used}* ✅
• Hết hạn: *{expired}* ⚠️

💡 *Tỷ lệ sử dụng:* {used/total*100:.1f}% (nếu total > 0)
    """
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['revokekey'])
def revoke_key(message):
    """Vô hiệu key"""
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
    
    bot.reply_to(message, f"✅ Đã vô hiệu key: `{key_code}`", parse_mode='Markdown')

@bot.message_handler(commands=['deletekey'])
def delete_key(message):
    """Xóa key"""
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Dùng: /deletekey [KEY]")
        return
    
    key_code = args[1].upper()
    
    # Xác nhận xóa
    markup = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton("✅ Xóa", callback_data=f"del_{key_code}")
    btn_no = types.InlineKeyboardButton("❌ Hủy", callback_data="cancel")
    markup.add(btn_yes, btn_no)
    
    bot.reply_to(message, f"⚠️ Xóa key: `{key_code}`?", 
                 parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Xử lý callback"""
    if call.data.startswith("del_"):
        key_code = call.data[4:]
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM keys WHERE key_code=?", (key_code,))
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
<<<<<<< HEAD
def echo_all(message):
    """Xử lý tin nhắn không phải lệnh"""
    bot.reply_to(message, "❓ *Không hiểu lệnh!*\nDùng `/start` để xem danh sách lệnh.", parse_mode='Markdown')

# ==================== CHẠY BOT ====================
if __name__ == "__main__":
    # Khởi tạo database
    if not init_db():
        print("❌ Không thể khởi tạo database! Bot sẽ thoát.")
        exit(1)
    
    print("=" * 60)
    print("🤖 SunLon Key Bot - Đang chạy 24/7")
    print("=" * 60)
    print(f"   Bot: @{bot_info.username}")
    print(f"   Admin ID: {ADMIN_ID}")
    print(f"   Database: {DB_PATH}")
    print(f"   Port: {PORT}")
    print("=" * 60)
    print("Các lệnh đã sẵn sàng!")
    print("=" * 60)
    
    # Chạy web server trong thread riêng
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    print("🌐 Web server started on thread")
    
    # Chạy bot với xử lý lỗi
=======
def echo(message):
    """Tin nhắn không hợp lệ"""
    bot.reply_to(message, "❓ Dùng /start để xem hướng dẫn")

# ==================== CHẠY BOT ====================
if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("🤖 SunLon Bot đang chạy...")
    print(f"   Bot: @{bot_info.username}")
    print(f"   Admin ID: {ADMIN_ID}")
    print("=" * 50)
    
    # Chạy bot
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20
    while True:
        try:
            print("🤖 Bot polling started...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"⚠️ Lỗi: {e}")
<<<<<<< HEAD
            print("Đang thử kết nối lại sau 10 giây...")
            time.sleep(10)
=======
            print("Thử lại sau 10 giây...")
            time.sleep(10)
>>>>>>> 244213efb808f7ddf3fd891d9296d62101d9ed20

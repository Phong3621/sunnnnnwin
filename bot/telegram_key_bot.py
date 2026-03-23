"""
Telegram Bot - SunLon Key Manager
Phiên bản tối giản cho Render
"""

import telebot
from telebot import types
import sqlite3
import secrets
import datetime
import os
import logging
import time
from datetime import timedelta

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CẤU HÌNH ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

if not BOT_TOKEN:
    print("❌ LỖI: Thiếu BOT_TOKEN!")
    exit(1)

if ADMIN_ID == 0:
    print("⚠️ CẢNH BÁO: ADMIN_ID chưa được cấu hình!")

try:
    bot = telebot.TeleBot(BOT_TOKEN)
    bot_info = bot.get_me()
    print(f"✅ Bot đã kết nối!")
    print(f"   Username: @{bot_info.username}")
except Exception as e:
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

def generate_key():
    """Tạo key ngẫu nhiên"""
    return secrets.token_hex(6).upper()

def is_admin(user_id):
    """Kiểm tra admin"""
    try:
        return int(user_id) == ADMIN_ID
    except:
        return False

# ==================== COMMANDS ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    """Lệnh start"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if is_admin(user_id):
        text = f"""
🎲 *SUNLON KEY BOT* 🎲

Xin chào Admin *{user_name}*!

📌 *Lệnh:*
/createkey [tên] [ngày] - Tạo key
/listkeys - Xem danh sách
/check [key] - Kiểm tra key
/stats - Xem thống kê

💡 *Ví dụ:* 
/createkey Nguyen Van A 30
        """
    else:
        text = f"""
🎲 *SUNLON KEY BOT* 🎲

Xin chào *{user_name}*!

🔑 Kiểm tra key: /check [key]

📞 Liên hệ admin để được cấp key
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
        except:
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
            INSERT INTO keys (key_code, user_name, created_by, expire_date) 
            VALUES (?, ?, ?, ?)
        """, (key_code, user_name, str(message.from_user.id), expire_date))
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
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT key_code, user_name, status, expire_date 
        FROM keys 
        ORDER BY created_at DESC 
        LIMIT 15
    """)
    keys = c.fetchall()
    conn.close()
    
    if not keys:
        bot.reply_to(message, "📭 Chưa có key nào!")
        return
    
    text = "📋 *DANH SÁCH KEY*\n\n"
    for key in keys:
        key_code, user_name, status, expire_date = key
        
        # Kiểm tra hết hạn
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
        text += f"   📊 {status_text}\n\n"
    
    # Gửi từng phần nếu quá dài
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.reply_to(message, text[i:i+4000], parse_mode='Markdown')
    else:
        bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['check'])
def check_key(message):
    """Kiểm tra key"""
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Dùng: /check [KEY]")
        return
    
    key_code = args[1].upper()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT user_name, status, expire_date 
        FROM keys 
        WHERE key_code=?
    """, (key_code,))
    result = c.fetchone()
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
    
    text = f"""
✅ *KEY HỢP LỆ!*

🔑 `{key_code}`
👤 {user_name}
📅 {expire_date if expire_date else 'Vĩnh viễn'}

🎉 Key có thể sử dụng!
    """
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats(message):
    """Thống kê"""
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
    
    c.execute("SELECT COUNT(*) FROM keys WHERE expire_date < date('now') AND expire_date IS NOT NULL")
    expired = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM keys WHERE used_by IS NOT NULL")
    used = c.fetchone()[0]
    
    conn.close()
    
    text = f"""
📊 *THỐNG KÊ KEY*

📌 *Tổng quan:*
• Tổng số keys: *{total}*
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
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"⚠️ Lỗi: {e}")
            print("Thử lại sau 10 giây...")
            time.sleep(10)

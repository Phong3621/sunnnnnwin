"""
Telegram Bot tạo key cho SunLon Client - Phiên bản sửa lỗi database
"""

import telebot
from telebot import types
import sqlite3
import secrets
import datetime
import os
import logging
import sys
from datetime import timedelta

# BẬT LOGGING
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ==================== CẤU HÌNH ====================
BOT_TOKEN = "8436395927:AAFxOj1LLdzEYm8fsGUTC3EbcS2KGiDo7p8"
ADMIN_ID = 8547071506

# KIỂM TRA TOKEN
if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    print("❌ LỖI: Bạn chưa cấu hình BOT_TOKEN!")
    sys.exit(1)

try:
    bot = telebot.TeleBot(BOT_TOKEN)
    bot_info = bot.get_me()
    print(f"✅ Bot đã kết nối thành công!")
    print(f"   Tên bot: {bot_info.first_name}")
    print(f"   Username: @{bot_info.username}")
except Exception as e:
    print(f"❌ LỖI KẾT NỐI BOT: {e}")
    sys.exit(1)

# Khởi tạo database với cấu trúc đầy đủ
def init_db():
    """Khởi tạo database với tất cả các cột cần thiết"""
    try:
        conn = sqlite3.connect('sunlon_keys.db')
        c = conn.cursor()
        
        # Xóa bảng cũ nếu có (comment dòng này nếu muốn giữ dữ liệu cũ)
        # c.execute("DROP TABLE IF EXISTS keys")
        
        # Tạo bảng mới với đầy đủ cột
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
        
        # Kiểm tra và thêm các cột nếu thiếu
        c.execute("PRAGMA table_info(keys)")
        columns = [column[1] for column in c.fetchall()]
        
        # Thêm các cột còn thiếu
        if 'created_by' not in columns:
            c.execute("ALTER TABLE keys ADD COLUMN created_by TEXT")
            print("✅ Đã thêm cột created_by")
        
        if 'notes' not in columns:
            c.execute("ALTER TABLE keys ADD COLUMN notes TEXT")
            print("✅ Đã thêm cột notes")
        
        if 'used_by' not in columns:
            c.execute("ALTER TABLE keys ADD COLUMN used_by TEXT")
            print("✅ Đã thêm cột used_by")
        
        if 'used_at' not in columns:
            c.execute("ALTER TABLE keys ADD COLUMN used_at TIMESTAMP")
            print("✅ Đã thêm cột used_at")
        
        conn.commit()
        
        # Hiển thị cấu trúc bảng
        c.execute("PRAGMA table_info(keys)")
        print("\n📋 Cấu trúc bảng keys:")
        for col in c.fetchall():
            print(f"   - {col[1]}: {col[2]}")
        
        # Đếm số key hiện có
        c.execute("SELECT COUNT(*) FROM keys")
        count = c.fetchone()[0]
        print(f"\n📊 Số key hiện có: {count}")
        
        conn.close()
        logger.info("Database initialized successfully")
        print("✅ Database đã được khởi tạo thành công!")
        return True
        
    except Exception as e:
        logger.error(f"Database init error: {e}")
        print(f"❌ Lỗi database: {e}")
        return False

def generate_key():
    """Tạo key ngẫu nhiên 12 ký tự"""
    return secrets.token_hex(6).upper()

def is_admin(user_id):
    """Kiểm tra admin"""
    try:
        user_id_int = int(user_id) if isinstance(user_id, str) else user_id
        admin_id_int = int(ADMIN_ID) if isinstance(ADMIN_ID, str) else ADMIN_ID
        return user_id_int == admin_id_int
    except Exception as e:
        logger.error(f"Check admin error: {e}")
        return False

# ==================== XỬ LÝ LỆNH ====================

@bot.message_handler(commands=['start'])
def start_command(message):
    """Lệnh start"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        logger.info(f"Start command from user: {user_id} - {user_name}")
        
        if is_admin(user_id):
            text = f"""
🎲 *SUNLON KEY MANAGER* 🎲

Xin chào Admin *{user_name}*!

📌 *Lệnh dành cho Admin:*
/createkey [tên] [ngày] - Tạo key mới
/listkeys - Xem danh sách key
/checkkey [key] - Kiểm tra key
/revokekey [key] - Vô hiệu key
/deletekey [key] - Xóa key
/stats - Xem thống kê

📌 *Lệnh dành cho người dùng:*
/check [key] - Kiểm tra key của bạn

💡 *Ví dụ:* 
/createkey Nguyen Van A 30
/createkey ADMIN 1
/listkeys
            """
        else:
            text = f"""
🎲 *SUNLON KEY SYSTEM* 🎲

Xin chào *{user_name}*!

🔑 Bạn có thể kiểm tra key của mình bằng lệnh:
/check [key]

📞 Liên hệ admin để được cấp key
            """
        
        bot.reply_to(message, text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Start command error: {e}")
        bot.reply_to(message, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['createkey', 'create_key'])
def create_key(message):
    """Tạo key mới"""
    try:
        user_id = message.from_user.id
        logger.info(f"Create key command from user: {user_id}")
        
        if not is_admin(user_id):
            bot.reply_to(message, "❌ Bạn không có quyền tạo key!")
            return
        
        args = message.text.split()
        logger.debug(f"Arguments: {args}")
        
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
        
        logger.info(f"Creating key for: {user_name}, expire_days: {expire_days}")
        
        # Tạo key
        key_code = generate_key()
        expire_date = None
        
        if expire_days > 0:
            expire_date = (datetime.date.today() + timedelta(days=expire_days)).strftime('%Y-%m-%d')
        
        # Lưu vào database
        conn = sqlite3.connect('sunlon_keys.db')
        c = conn.cursor()
        
        try:
            c.execute("""
                INSERT INTO keys (key_code, user_name, created_by, expire_date, notes) 
                VALUES (?, ?, ?, ?, ?)
            """, (key_code, user_name, str(user_id), expire_date, f"Created by admin on {datetime.datetime.now()}"))
            conn.commit()
            logger.info(f"Key created: {key_code}")
        except Exception as e:
            logger.error(f"Insert error: {e}")
            conn.close()
            bot.reply_to(message, f"❌ Lỗi khi lưu key: {str(e)}")
            return
        
        conn.close()
        
        # Gửi kết quả
        text = f"""
✅ *KEY MỚI ĐÃ ĐƯỢC TẠO!*

🔑 *Key:* `{key_code}`
👤 *Người dùng:* {user_name}
📅 *Hạn sử dụng:* {expire_date if expire_date else 'Vĩnh viễn'}
📊 *Số ngày:* {expire_days if expire_days > 0 else 'Vĩnh viễn'}

💡 *Gửi key này cho người dùng:*
`{key_code}`

📝 *Người dùng kiểm tra bằng lệnh:*
/check {key_code}
        """
        
        bot.reply_to(message, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Create key error: {e}")
        bot.reply_to(message, f"❌ Lỗi khi tạo key: {str(e)}")

@bot.message_handler(commands=['listkeys', 'list_keys'])
def list_keys(message):
    """Xem danh sách key"""
    try:
        user_id = message.from_user.id
        logger.info(f"List keys command from user: {user_id}")
        
        if not is_admin(user_id):
            bot.reply_to(message, "❌ Bạn không có quyền xem danh sách!")
            return
        
        conn = sqlite3.connect('sunlon_keys.db')
        c = conn.cursor()
        c.execute("""
            SELECT key_code, user_name, status, expire_date, used_by, created_at 
            FROM keys 
            ORDER BY created_at DESC 
            LIMIT 20
        """)
        keys = c.fetchall()
        conn.close()
        
        if not keys:
            bot.reply_to(message, "📭 Chưa có key nào được tạo!")
            return
        
        text = "📋 *DANH SÁCH KEY (20 gần nhất)*\n\n"
        for key in keys:
            key_code, user_name, status, expire_date, used_by, created_at = key
            
            # Kiểm tra hết hạn
            is_expired = False
            if expire_date:
                try:
                    expire_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d').date()
                    is_expired = expire_obj < datetime.date.today()
                except:
                    pass
            
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
        
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                bot.reply_to(message, part, parse_mode='Markdown')
        else:
            bot.reply_to(message, text, parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"List keys error: {e}")
        bot.reply_to(message, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['check'])
def check_key(message):
    """Kiểm tra key cho người dùng"""
    try:
        args = message.text.split()
        
        if len(args) != 2:
            bot.reply_to(message, "❌ *Sai cú pháp!*\nDùng: `/check [KEY]`", parse_mode='Markdown')
            return
        
        key_code = args[1].upper()
        logger.info(f"User check key: {key_code} from {message.from_user.id}")
        
        conn = sqlite3.connect('sunlon_keys.db')
        c = conn.cursor()
        c.execute("""
            SELECT key_code, user_name, status, expire_date, used_by 
            FROM keys 
            WHERE key_code=?
        """, (key_code,))
        result = c.fetchone()
        
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
        
        text = f"""
✅ *KEY HỢP LỆ!*

🔑 *Key:* `{key_code}`
👤 *Người dùng:* {user_name}
📅 *Hạn sử dụng:* {expire_date if expire_date else 'Vĩnh viễn'}

🎉 Key có thể sử dụng để kích hoạt SunLon Client!
        """
        
        bot.reply_to(message, text, parse_mode='Markdown')
        conn.close()
        
    except Exception as e:
        logger.error(f"Check key error: {e}")
        bot.reply_to(message, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['checkkey', 'check_key'])
def check_key_admin(message):
    """Kiểm tra key (admin)"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            bot.reply_to(message, "❌ Bạn không có quyền!")
            return
        
        args = message.text.split()
        if len(args) != 2:
            bot.reply_to(message, "❌ Sai cú pháp! Dùng: /checkkey [KEY]")
            return
        
        key_code = args[1].upper()
        
        conn = sqlite3.connect('sunlon_keys.db')
        c = conn.cursor()
        c.execute("""
            SELECT key_code, user_name, status, expire_date, used_by, created_at, notes 
            FROM keys 
            WHERE key_code=?
        """, (key_code,))
        result = c.fetchone()
        conn.close()
        
        if not result:
            bot.reply_to(message, f"❌ Key {key_code} không tồn tại!")
            return
        
        key_code, user_name, status, expire_date, used_by, created_at, notes = result
        
        text = f"""
📋 *THÔNG TIN KEY*

🔑 *Key:* `{key_code}`
👤 *Người dùng:* {user_name}
📊 *Trạng thái:* {status}
📅 *Hạn sử dụng:* {expire_date if expire_date else 'Vĩnh viễn'}
👥 *Đã sử dụng bởi:* {used_by if used_by else 'Chưa sử dụng'}
🕐 *Ngày tạo:* {created_at[:10]}
📝 *Ghi chú:* {notes if notes else 'Không có'}
        """
        
        bot.reply_to(message, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Check key admin error: {e}")
        bot.reply_to(message, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['revokekey', 'revoke_key'])
def revoke_key(message):
    """Vô hiệu hóa key"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            bot.reply_to(message, "❌ Bạn không có quyền!")
            return
        
        args = message.text.split()
        if len(args) != 2:
            bot.reply_to(message, "❌ Sai cú pháp! Dùng: /revokekey [KEY]")
            return
        
        key_code = args[1].upper()
        
        conn = sqlite3.connect('sunlon_keys.db')
        c = conn.cursor()
        c.execute("UPDATE keys SET status='revoked' WHERE key_code=?", (key_code,))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ Đã vô hiệu hóa key: `{key_code}`", parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Revoke key error: {e}")
        bot.reply_to(message, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['deletekey', 'delete_key'])
def delete_key(message):
    """Xóa key"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
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
        
    except Exception as e:
        logger.error(f"Delete key error: {e}")
        bot.reply_to(message, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['stats'])
def stats(message):
    """Thống kê"""
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            bot.reply_to(message, "❌ Bạn không có quyền!")
            return
        
        conn = sqlite3.connect('sunlon_keys.db')
        c = conn.cursor()
        
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
        
        conn.close()
        
        text = f"""
📊 *THỐNG KÊ KEY*

📌 *Tổng quan:*
• Tổng số keys: *{total}*
• Keys đang hoạt động: *{active}* 🟢
• Keys đã vô hiệu: *{revoked}* 🔴
• Keys đã sử dụng: *{used}* ✅
• Keys hết hạn: *{expired}* ⚠️

💡 *Tỷ lệ sử dụng:* {used/total*100:.1f}% (nếu total > 0)
        """
        
        bot.reply_to(message, text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        bot.reply_to(message, f"❌ Lỗi: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Xử lý callback xóa key"""
    try:
        if call.data.startswith("del_"):
            key_code = call.data[4:]
            
            conn = sqlite3.connect('sunlon_keys.db')
            c = conn.cursor()
            c.execute("DELETE FROM keys WHERE key_code=?", (key_code,))
            conn.commit()
            conn.close()
            
            bot.edit_message_text(f"✅ Đã xóa key: `{key_code}`", 
                                  chat_id=call.message.chat.id,
                                  message_id=call.message.message_id,
                                  parse_mode='Markdown')
        
        elif call.data == "cancel":
            bot.edit_message_text("❌ Đã hủy thao tác", 
                                  chat_id=call.message.chat.id,
                                  message_id=call.message.message_id)
    except Exception as e:
        logger.error(f"Callback error: {e}")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """Xử lý tin nhắn không phải lệnh"""
    try:
        logger.info(f"Unknown command from {message.from_user.id}: {message.text}")
        bot.reply_to(message, "❓ *Không hiểu lệnh!*\nDùng `/start` để xem danh sách lệnh.", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Echo error: {e}")

# ==================== CHẠY BOT ====================
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 SunLon Key Bot - Phiên bản sửa lỗi database")
    print("=" * 60)
    
    # Khởi tạo database
    if not init_db():
        print("❌ Không thể khởi tạo database! Bot sẽ thoát.")
        sys.exit(1)
    
    print(f"\n📌 Thông tin bot:")
    print(f"   Token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
    print(f"   Admin ID: {ADMIN_ID}")
    print(f"\n✅ Bot đã sẵn sàng!")
    print("=" * 60)
    print("Các lệnh hỗ trợ:")
    print("   /createkey [tên] [ngày] - Tạo key")
    print("   /listkeys - Xem danh sách")
    print("   /checkkey [key] - Kiểm tra key (admin)")
    print("   /revokekey [key] - Vô hiệu key")
    print("   /deletekey [key] - Xóa key")
    print("   /check [key] - Kiểm tra key (người dùng)")
    print("   /stats - Thống kê")
    print("=" * 60)
    print("Bot đang chạy...")
    print("Nhấn Ctrl+C để dừng bot")
    print("=" * 60)
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"Bot polling error: {e}")
            print(f"⚠️ Lỗi: {e}")
            print("Đang thử kết nối lại sau 5 giây...")
            import time
            time.sleep(5)
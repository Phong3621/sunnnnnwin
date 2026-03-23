"""
SunLon Client với xác thực key từ Telegram Bot và Server
"""

import customtkinter as ctk
import requests
import sqlite3
import datetime
import threading
import os
import json
import hashlib
import platform
import uuid
from datetime import datetime, timedelta
from tkinter import messagebox

# Cấu hình
API_URL = "https://apisunhpt.onrender.com/sunlon"
AUTH_SERVER = "http://localhost:5000"  # Thay bằng server của bạn
REFRESH_INTERVAL = 5

# File lưu key
KEY_FILE = "sunlon_key.json"


class KeyValidator:
    """Xác thực key với nhiều phương thức"""
    
    def __init__(self):
        self.key_code = None
        self.is_valid = False
        self.key_info = None
        self.use_server = False  # Có dùng server không
        self.load_key()
    
    def get_device_id(self):
        """Lấy ID thiết bị duy nhất"""
        try:
            system = platform.system()
            node = platform.node()
            processor = platform.processor()
            machine = platform.machine()
            
            unique_string = f"{system}{node}{processor}{machine}"
            if os.path.exists('/sys/class/net/eth0/address'):
                with open('/sys/class/net/eth0/address', 'r') as f:
                    unique_string += f.read().strip()
            
            return hashlib.sha256(unique_string.encode()).hexdigest()[:32]
        except:
            return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:32]
    
    def load_key(self):
        """Đọc key đã lưu"""
        if os.path.exists(KEY_FILE):
            try:
                with open(KEY_FILE, 'r') as f:
                    data = json.load(f)
                    self.key_code = data.get('key_code')
                    # Kiểm tra lại key
                    if self.key_code:
                        self.validate_key(self.key_code)
            except:
                pass
    
    def save_key(self, key_code):
        """Lưu key"""
        with open(KEY_FILE, 'w') as f:
            json.dump({'key_code': key_code, 'saved_at': datetime.now().isoformat()}, f)
        self.key_code = key_code
    
    def validate_with_server(self, key_code):
        """Xác thực qua server API"""
        try:
            device_id = self.get_device_id()
            response = requests.post(
                f"{AUTH_SERVER}/api/verify",
                json={
                    'key_code': key_code,
                    'device_id': device_id
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('valid'):
                    self.key_info = {
                        'user_name': data.get('user_name'),
                        'expire_date': data.get('expire_date'),
                        'email': data.get('user_email')
                    }
                    return True, "Xác thực thành công"
                else:
                    return False, data.get('error', 'Key không hợp lệ')
            else:
                return False, "Server xác thực không phản hồi"
                
        except Exception as e:
            return False, f"Lỗi kết nối server: {str(e)}"
    
    def validate_with_local_db(self, key_code):
        """Xác thực qua database local (từ bot)"""
        try:
            if os.path.exists('sunlon_keys.db'):
                conn = sqlite3.connect('sunlon_keys.db')
                c = conn.cursor()
                c.execute("SELECT user_name, status, expire_date FROM keys WHERE key_code=?", (key_code,))
                result = c.fetchone()
                conn.close()
                
                if result:
                    user_name, status, expire_date = result
                    
                    if status != 'active':
                        return False, "Key đã bị vô hiệu hóa"
                    
                    if expire_date:
                        expire_obj = datetime.strptime(expire_date, '%Y-%m-%d').date()
                        if expire_obj < datetime.now().date():
                            return False, f"Key đã hết hạn từ ngày {expire_date}"
                    
                    self.key_info = {
                        'user_name': user_name,
                        'expire_date': expire_date
                    }
                    return True, "Key hợp lệ"
                else:
                    return False, "Key không tồn tại"
            else:
                return False, "Không tìm thấy database"
                
        except Exception as e:
            return False, f"Lỗi xác thực: {str(e)}"
    
    def validate_key(self, key_code):
        """Kiểm tra key - ưu tiên server trước, sau đó local"""
        # Thử xác thực qua server trước
        if self.use_server:
            valid, message = self.validate_with_server(key_code)
            if valid:
                self.is_valid = True
                return True, message
        
        # Nếu server không dùng được, dùng local DB
        valid, message = self.validate_with_local_db(key_code)
        self.is_valid = valid
        return valid, message
    
    def check_and_update(self):
        """Kiểm tra và cập nhật key"""
        if self.key_code:
            valid, message = self.validate_key(self.key_code)
            return valid, message
        return False, "Chưa có key"


class LoginDialog:
    """Dialog nhập key"""
    
    def __init__(self, parent, validator):
        self.parent = parent
        self.validator = validator
        self.dialog = None
        
    def show(self):
        """Hiển thị dialog đăng nhập"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("Kích hoạt SunLon")
        self.dialog.geometry("500x500")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - 250
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - 250
        self.dialog.geometry(f"+{x}+{y}")
        
        # Nội dung
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Logo
        title = ctk.CTkLabel(
            main_frame,
            text="🎲 SUNLON PRO 🎲",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#FFD700"
        )
        title.pack(pady=(0, 10))
        
        subtitle = ctk.CTkLabel(
            main_frame,
            text="Nhập key để kích hoạt",
            font=ctk.CTkFont(size=12)
        )
        subtitle.pack(pady=(0, 20))
        
        # Key input
        self.key_entry = ctk.CTkEntry(
            main_frame,
            placeholder_text="Nhập key của bạn",
            font=ctk.CTkFont(size=14),
            width=400,
            height=45
        )
        self.key_entry.pack(pady=(0, 15))
        
        # Message
        self.message_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#FF4444"
        )
        self.message_label.pack(pady=(0, 10))
        
        # Buttons
        verify_btn = ctk.CTkButton(
            main_frame,
            text="Kích hoạt",
            command=self.verify_key,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        verify_btn.pack(pady=(0, 10))
        
        # Hướng dẫn
        guide_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        guide_frame.pack(fill="x", pady=(20, 0))
        
        guide_text = """
📌 *CÁCH LẤY KEY:*

1️⃣ Liên hệ Admin qua Telegram
2️⃣ Admin sẽ cấp cho bạn 1 key
3️⃣ Nhập key vào ô trên và nhấn "Kích hoạt"

💡 *Kiểm tra key trên Telegram:*
Gửi /check [key] đến bot @SunLonKeyBot

📞 *Liên hệ admin:* @admin_username
        """
        
        guide = ctk.CTkLabel(
            guide_frame,
            text=guide_text,
            font=ctk.CTkFont(size=11),
            justify="left",
            text_color="#888888"
        )
        guide.pack(pady=15, padx=15)
        
        # Bind Enter
        self.key_entry.bind('<Return>', lambda e: self.verify_key())
        self.key_entry.focus()
    
    def verify_key(self):
        """Xác thực key"""
        key_code = self.key_entry.get().strip().upper()
        if not key_code:
            self.message_label.configure(text="Vui lòng nhập key", text_color="#FF4444")
            return
        
        self.message_label.configure(text="Đang xác thực...", text_color="#FFD700")
        verify_btn = self.dialog.focus_get()
        
        def verify_thread():
            valid, message = self.validator.validate_key(key_code)
            self.dialog.after(0, lambda: self.on_verify_result(valid, message, key_code))
        
        threading.Thread(target=verify_thread, daemon=True).start()
    
    def on_verify_result(self, valid, message, key_code):
        """Xử lý kết quả xác thực"""
        if valid:
            self.validator.save_key(key_code)
            self.message_label.configure(text="✅ " + message, text_color="#00FF00")
            self.dialog.after(1500, self.dialog.destroy)
        else:
            self.message_label.configure(text="❌ " + message, text_color="#FF4444")


class SunLonApp:
    def __init__(self):
        self.validator = KeyValidator()
        
        self.root = ctk.CTk()
        self.root.title("SunLon - Cầu Tài Xỉu Pro")
        self.root.geometry("800x700")
        self.root.resizable(False, False)
        
        # Biến thống kê
        self.total_predictions = 0
        self.correct_predictions = 0
        self.last_ket_qua = None
        self.last_du_doan = None
        self.countdown = REFRESH_INTERVAL
        self.history = []
        
        # Kiểm tra key
        if not self.validator.is_valid:
            self.show_login()
        else:
            self.init_main_app()
    
    def show_login(self):
        """Hiển thị màn hình đăng nhập"""
        # Frame đăng nhập
        self.login_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.login_frame.pack(fill="both", expand=True)
        
        # Center content
        center_frame = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        center_frame.pack(expand=True)
        
        # Logo
        logo = ctk.CTkLabel(
            center_frame,
            text="🎲 SUNLON PRO 🎲",
            font=ctk.CTkFont(size=48, weight="bold"),
            text_color="#FFD700"
        )
        logo.pack(pady=(0, 20))
        
        # Loading
        loading = ctk.CTkLabel(
            center_frame,
            text="Đang kiểm tra key...",
            font=ctk.CTkFont(size=14)
        )
        loading.pack(pady=20)
        
        # Progress bar
        progress = ctk.CTkProgressBar(center_frame, width=300)
        progress.pack(pady=10)
        progress.start()
        
        # Kiểm tra key tự động
        def check_key():
            if self.validator.key_code:
                valid, message = self.validator.validate_key(self.validator.key_code)
                if valid:
                    self.root.after(0, self.start_main_app)
                else:
                    self.root.after(0, self.show_key_dialog)
            else:
                self.root.after(1000, self.show_key_dialog)
        
        threading.Thread(target=check_key, daemon=True).start()
    
    def show_key_dialog(self):
        """Hiển thị dialog nhập key"""
        if hasattr(self, 'login_frame'):
            self.login_frame.destroy()
        
        dialog = LoginDialog(self.root, self.validator)
        dialog.show()
        
        # Chờ dialog đóng
        self.check_dialog_status(dialog)
    
    def check_dialog_status(self, dialog):
        """Kiểm tra dialog đã đóng chưa"""
        if dialog.dialog and dialog.dialog.winfo_exists():
            self.root.after(500, lambda: self.check_dialog_status(dialog))
        else:
            if self.validator.is_valid:
                self.start_main_app()
    
    def start_main_app(self):
        """Khởi động ứng dụng chính"""
        if hasattr(self, 'login_frame'):
            self.login_frame.destroy()
        
        self.init_main_app()
        
        # Hiển thị thông báo chào mừng
        if self.validator.key_info:
            welcome_text = f"Chào mừng {self.validator.key_info['user_name']}!"
            if self.validator.key_info.get('expire_date'):
                days_left = (datetime.strptime(self.validator.key_info['expire_date'], '%Y-%m-%d').date() - datetime.now().date()).days
                welcome_text += f" Còn {days_left} ngày sử dụng"
            self.root.title(f"SunLon - {welcome_text}")
    
    def init_main_app(self):
        """Khởi tạo giao diện chính"""
        self.setup_ui()
        self.update_loop()
        self.countdown_loop()
    
    def setup_ui(self):
        """Thiết lập giao diện"""
        # Frame chính
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_frame = ctk.CTkFrame(self.main_frame, corner_radius=15)
        header_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ctk.CTkLabel(
            header_frame, 
            text="🎲 SUNLON - CẦU TÀI XỈU PRO 🎲", 
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#FFD700"
        )
        title_label.pack(pady=15)
        
        # Control frame
        control_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        control_frame.pack(pady=(0, 10))
        
        self.time_label = ctk.CTkLabel(
            control_frame, 
            text="⏱️ Đang khởi tạo...", 
            font=ctk.CTkFont(size=12)
        )
        self.time_label.pack(side="left", padx=10)
        
        # User info
        if self.validator.key_info:
            user_text = f"👤 {self.validator.key_info['user_name']}"
            if self.validator.key_info.get('expire_date'):
                user_text += f" | 📅 HSD: {self.validator.key_info['expire_date']}"
            user_label = ctk.CTkLabel(
                control_frame,
                text=user_text,
                font=ctk.CTkFont(size=11),
                text_color="#00FF00"
            )
            user_label.pack(side="right", padx=10)
        
        theme_switch = ctk.CTkSwitch(
            control_frame,
            text="🌙 Dark Mode",
            command=self.toggle_theme,
            progress_color="#FFD700"
        )
        theme_switch.pack(side="right", padx=10)
        theme_switch.select()
        
        # 2 cột
        columns_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        columns_frame.pack(fill="both", expand=True)
        
        # Cột trái
        left_col = ctk.CTkFrame(columns_frame, corner_radius=15)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Cột phải
        right_col = ctk.CTkFrame(columns_frame, corner_radius=15)
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        # Card thông tin
        info_card = ctk.CTkFrame(left_col, corner_radius=15, border_width=2, border_color="#FFD700")
        info_card.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(info_card, text="📊 THÔNG TIN HIỆN TẠI", font=ctk.CTkFont(size=18, weight="bold"), text_color="#FFD700").pack(pady=(15, 10))
        
        info_grid = ctk.CTkFrame(info_card, fg_color="transparent")
        info_grid.pack(pady=10, padx=20)
        
        ctk.CTkLabel(info_grid, text="Phiên:", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w", pady=8)
        self.phien_label = ctk.CTkLabel(info_grid, text="---", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00FF00")
        self.phien_label.grid(row=0, column=1, sticky="w", padx=20)
        
        ctk.CTkLabel(info_grid, text="Tổng:", font=ctk.CTkFont(size=14, weight="bold")).grid(row=1, column=0, sticky="w", pady=8)
        self.tong_label = ctk.CTkLabel(info_grid, text="---", font=ctk.CTkFont(size=16, weight="bold"), text_color="#FFA500")
        self.tong_label.grid(row=1, column=1, sticky="w", padx=20)
        
        ctk.CTkLabel(info_grid, text="Cầu (Pattern):", font=ctk.CTkFont(size=14, weight="bold")).grid(row=2, column=0, sticky="w", pady=8)
        self.pattern_label = ctk.CTkLabel(info_grid, text="---", font=ctk.CTkFont(size=12), wraplength=250)
        self.pattern_label.grid(row=2, column=1, sticky="w", padx=20)
        
        ctk.CTkLabel(info_grid, text="Kết quả:", font=ctk.CTkFont(size=14, weight="bold")).grid(row=3, column=0, sticky="w", pady=8)
        self.ketqua_label = ctk.CTkLabel(info_grid, text="---", font=ctk.CTkFont(size=20, weight="bold"))
        self.ketqua_label.grid(row=3, column=1, sticky="w", padx=20)
        
        ctk.CTkLabel(info_grid, text="Dự đoán:", font=ctk.CTkFont(size=14, weight="bold")).grid(row=4, column=0, sticky="w", pady=8)
        self.dudoan_label = ctk.CTkLabel(info_grid, text="---", font=ctk.CTkFont(size=18, weight="bold"))
        self.dudoan_label.grid(row=4, column=1, sticky="w", padx=20)
        
        ctk.CTkLabel(info_grid, text="So sánh:", font=ctk.CTkFont(size=14, weight="bold")).grid(row=5, column=0, sticky="w", pady=8)
        self.sosanh_label = ctk.CTkLabel(info_grid, text="---", font=ctk.CTkFont(size=11), wraplength=250)
        self.sosanh_label.grid(row=5, column=1, sticky="w", padx=20)
        
        # Card thống kê
        stats_card = ctk.CTkFrame(right_col, corner_radius=15, border_width=2, border_color="#FFD700")
        stats_card.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(stats_card, text="📈 THỐNG KÊ DỰ ĐOÁN", font=ctk.CTkFont(size=18, weight="bold"), text_color="#FFD700").pack(pady=(15, 10))
        
        stats_grid = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_grid.pack(pady=10, padx=20)
        
        ctk.CTkLabel(stats_grid, text="Tổng số lần:", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", pady=5)
        self.total_label = ctk.CTkLabel(stats_grid, text="0", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00FF00")
        self.total_label.grid(row=0, column=1, sticky="e", padx=10)
        
        ctk.CTkLabel(stats_grid, text="✅ Đúng:", font=ctk.CTkFont(size=13)).grid(row=1, column=0, sticky="w", pady=5)
        self.correct_label = ctk.CTkLabel(stats_grid, text="0", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00FF00")
        self.correct_label.grid(row=1, column=1, sticky="e", padx=10)
        
        ctk.CTkLabel(stats_grid, text="❌ Sai:", font=ctk.CTkFont(size=13)).grid(row=2, column=0, sticky="w", pady=5)
        self.wrong_label = ctk.CTkLabel(stats_grid, text="0", font=ctk.CTkFont(size=16, weight="bold"), text_color="#FF4444")
        self.wrong_label.grid(row=2, column=1, sticky="e", padx=10)
        
        ctk.CTkLabel(stats_grid, text="🎯 Tỷ lệ:", font=ctk.CTkFont(size=13)).grid(row=3, column=0, sticky="w", pady=5)
        self.accuracy_label = ctk.CTkLabel(stats_grid, text="0%", font=ctk.CTkFont(size=20, weight="bold"), text_color="#FFD700")
        self.accuracy_label.grid(row=3, column=1, sticky="e", padx=10)
        
        self.progress_bar = ctk.CTkProgressBar(stats_card, width=250, height=15, corner_radius=7)
        self.progress_bar.pack(pady=(15, 10))
        self.progress_bar.set(0)
        
        reset_btn = ctk.CTkButton(stats_card, text="🔄 Reset Thống Kê", command=self.reset_stats, height=35, corner_radius=10, fg_color="#FF4444", hover_color="#CC0000")
        reset_btn.pack(pady=(10, 15))
        
        self.result_message = ctk.CTkLabel(stats_card, text="Chưa có dự đoán", font=ctk.CTkFont(size=11, slant="italic"), text_color="#AAAAAA")
        self.result_message.pack(pady=(0, 10))
        
        # Lịch sử
        history_frame = ctk.CTkFrame(self.main_frame, corner_radius=15)
        history_frame.pack(fill="x", pady=(20, 0))
        
        ctk.CTkLabel(history_frame, text="📜 LỊCH SỬ DỰ ĐOÁN GẦN ĐÂY", font=ctk.CTkFont(size=16, weight="bold"), text_color="#FFD700").pack(pady=(10, 5))
        
        self.history_container = ctk.CTkFrame(history_frame, fg_color="transparent")
        self.history_container.pack(fill="x", padx=15, pady=10)
        
        self.history_labels = []
        for i in range(5):
            label = ctk.CTkLabel(self.history_container, text="", font=ctk.CTkFont(size=11), anchor="w")
            label.pack(fill="x", pady=2)
            self.history_labels.append(label)
        
        # Status bar
        self.status_bar = ctk.CTkLabel(self.root, text="✅ Hệ thống đang hoạt động", font=ctk.CTkFont(size=11), fg_color="#2B2B2B", corner_radius=0)
        self.status_bar.pack(side="bottom", fill="x", pady=(5, 0))
    
    def toggle_theme(self):
        """Chuyển đổi theme"""
        current = ctk.get_appearance_mode()
        ctk.set_appearance_mode("Light" if current == "Dark" else "Dark")
    
    def countdown_loop(self):
        """Đếm ngược"""
        if self.countdown > 0:
            self.countdown -= 1
            self.time_label.configure(text=f"⏱️ Cập nhật sau: {self.countdown}s")
            self.root.after(1000, self.countdown_loop)
        else:
            self.countdown = REFRESH_INTERVAL
    
    def update_loop(self):
        """Cập nhật dữ liệu"""
        threading.Thread(target=self.fetch_data, daemon=True).start()
        self.root.after(REFRESH_INTERVAL * 1000, self.update_loop)
    
    def fetch_data(self):
        """Lấy dữ liệu từ API"""
        try:
            response = requests.get(API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            phien = data.get("phien", "---")
            tong = data.get("tong", "---")
            pattern = data.get("pattern", "---")
            ket_qua = data.get("ket_qua", "---")
            du_doan = data.get("du_doan", "---")
            so_sanh = data.get("so_sanh", "---")
            
            self.root.after(0, lambda: self.update_ui(phien, tong, pattern, ket_qua, du_doan, so_sanh))
            
            if ket_qua and du_doan and ket_qua != "---" and du_doan != "---":
                if ket_qua != self.last_ket_qua or du_doan != self.last_du_doan:
                    self.total_predictions += 1
                    is_correct = (du_doan == ket_qua)
                    
                    if is_correct:
                        self.correct_predictions += 1
                        result_text = f"✅ Dự đoán ĐÚNG! {du_doan} = {ket_qua}"
                    else:
                        result_text = f"❌ Dự đoán SAI! {du_doan} ≠ {ket_qua}"
                    
                    self.root.after(0, lambda: self.update_stats())
                    self.root.after(0, lambda: self.result_message.configure(text=result_text, text_color="#00FF00" if is_correct else "#FF4444"))
                    self.root.after(0, lambda: self.update_history(phien, ket_qua, du_doan, is_correct))
                    
                    self.last_ket_qua = ket_qua
                    self.last_du_doan = du_doan
            
            self.root.after(0, lambda: self.status_bar.configure(text=f"✅ Cập nhật lúc {datetime.now().strftime('%H:%M:%S')}"))
            
        except Exception as e:
            self.root.after(0, lambda: self.status_bar.configure(text=f"⚠️ Lỗi: {str(e)}", text_color="#FF4444"))
    
    def update_ui(self, phien, tong, pattern, ket_qua, du_doan, so_sanh):
        """Cập nhật giao diện"""
        self.phien_label.configure(text=str(phien))
        self.tong_label.configure(text=str(tong))
        self.pattern_label.configure(text=str(pattern))
        
        ket_qua_color = "#00FF00" if ket_qua == "Tài" else "#FF4444" if ket_qua == "Xỉu" else "#FFA500"
        self.ketqua_label.configure(text=ket_qua, text_color=ket_qua_color)
        
        du_doan_color = "#00FF00" if du_doan == "Tài" else "#FF4444" if du_doan == "Xỉu" else "#FFA500"
        self.dudoan_label.configure(text=du_doan, text_color=du_doan_color)
        
        self.sosanh_label.configure(text=so_sanh)
    
    def update_stats(self):
        """Cập nhật thống kê"""
        wrong = self.total_predictions - self.correct_predictions
        accuracy = (self.correct_predictions / self.total_predictions * 100) if self.total_predictions > 0 else 0
        
        self.total_label.configure(text=str(self.total_predictions))
        self.correct_label.configure(text=str(self.correct_predictions))
        self.wrong_label.configure(text=str(wrong))
        self.accuracy_label.configure(text=f"{accuracy:.1f}%")
        self.progress_bar.set(accuracy / 100)
    
    def reset_stats(self):
        """Reset thống kê"""
        self.total_predictions = 0
        self.correct_predictions = 0
        self.last_ket_qua = None
        self.last_du_doan = None
        self.history = []
        
        self.update_stats()
        self.result_message.configure(text="Đã reset thống kê!", text_color="#FFD700")
        
        for label in self.history_labels:
            label.configure(text="")
        
        self.status_bar.configure(text="🔄 Đã reset thống kê dự đoán")
    
    def update_history(self, phien, ket_qua, du_doan, is_correct):
        """Cập nhật lịch sử"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icon = "✅" if is_correct else "❌"
        history_text = f"{icon} {timestamp} | Phiên {phien} | {du_doan} → {ket_qua}"
        
        self.history.insert(0, history_text)
        if len(self.history) > 5:
            self.history.pop()
        
        for i, label in enumerate(self.history_labels):
            if i < len(self.history):
                label.configure(text=self.history[i])
            else:
                label.configure(text="")
    
    def run(self):
        """Chạy ứng dụng"""
        self.root.mainloop()


# ==================== CHẠY ====================
if __name__ == "__main__":
    app = SunLonApp()
    app.run()
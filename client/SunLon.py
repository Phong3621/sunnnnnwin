"""
SunLon Client PRO - Gọi API check key với HWID
"""

import customtkinter as ctk
import requests
import hashlib
import platform
import uuid
import json
import os
import threading
import datetime
import tkinter.messagebox as messagebox
from datetime import datetime, timedelta

# Cấu hình
API_URL = "https://apisunhpt.onrender.com/sunlon"
BOT_URL = "https://sunnnnnwin.up.railway.app"
REFRESH_INTERVAL = 5

KEY_FILE = "sunlon_key.json"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class KeyValidator:
    """Xác thực key qua API với HWID"""
    
    def __init__(self):
        self.key_code = None
        self.is_valid = False
        self.user_info = None
        self.load_key()
    
    def get_hwid(self):
        """Lấy Hardware ID duy nhất của máy tính"""
        try:
            # Kết hợp nhiều thông tin để tạo ID duy nhất
            system = platform.system()
            node = platform.node()
            processor = platform.processor()
            machine = platform.machine()
            
            # Lấy MAC address
            mac = uuid.getnode()
            
            # Lấy thông tin CPU
            try:
                import cpuinfo
                cpu = cpuinfo.get_cpu_info().get('brand_raw', '')
            except:
                cpu = ''
            
            # Lấy thông tin ổ cứng
            try:
                import psutil
                disk = psutil.disk_partitions()
                disk_info = str(disk)
            except:
                disk_info = ''
            
            unique_string = f"{system}{node}{processor}{machine}{mac}{cpu}{disk_info}"
            
            # Tạo hash
            return hashlib.sha256(unique_string.encode()).hexdigest()[:32]
        except Exception as e:
            print(f"HWID error: {e}")
            return hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:32]
    
    def get_device_name(self):
        """Lấy tên thiết bị"""
        try:
            return platform.node()
        except:
            return "Unknown"
    
    def get_device_info(self):
        """Lấy thông tin chi tiết thiết bị"""
        try:
            info = f"{platform.system()} {platform.release()} | {platform.processor()}"
            return info[:100]  # Giới hạn độ dài
        except:
            return "Unknown"
    
    def load_key(self):
        """Đọc key đã lưu"""
        if os.path.exists(KEY_FILE):
            try:
                with open(KEY_FILE, 'r') as f:
                    data = json.load(f)
                    self.key_code = data.get('key_code')
                    if self.key_code:
                        self.validate_key(self.key_code)
            except:
                pass
    
    def save_key(self, key_code):
        """Lưu key"""
        with open(KEY_FILE, 'w') as f:
            json.dump({'key_code': key_code, 'saved_at': datetime.now().isoformat()}, f)
        self.key_code = key_code
    
    def validate_key(self, key_code):
        """Gọi API để kiểm tra key với HWID"""
        try:
            hwid = self.get_hwid()
            device_name = self.get_device_name()
            device_info = self.get_device_info()
            
            response = requests.get(
                f"{BOT_URL}/checkkey",
                params={
                    'key': key_code,
                    'hwid': hwid,
                    'device_name': device_name,
                    'device_info': device_info
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('valid'):
                    self.user_info = {
                        'user_name': data.get('user'),
                        'expire_date': data.get('expire'),
                        'days_left': data.get('days_left', 0),
                        'device': data.get('device', device_name),
                        'first_time': data.get('first_time', False)
                    }
                    self.is_valid = True
                    msg = f"✅ {data.get('message')}\n👤 {data.get('user')}"
                    if data.get('first_time'):
                        msg += "\n🖥️ Thiết bị đã được đăng ký!"
                    return True, msg
                else:
                    self.is_valid = False
                    error = data.get('error', 'Key không hợp lệ')
                    # Nếu lỗi do HWID không khớp, gợi ý reset
                    if data.get('request_reset'):
                        return False, f"❌ {error}\n\n🔄 Bạn có muốn yêu cầu reset thiết bị? Liên hệ admin!"
                    return False, f"❌ {error}"
            else:
                return False, "❌ Không thể kết nối đến server"
                
        except Exception as e:
            return False, f"❌ Lỗi: {str(e)}"
    
    def request_reset(self, key_code):
        """Yêu cầu reset thiết bị"""
        try:
            hwid = self.get_hwid()
            response = requests.get(
                f"{BOT_URL}/reset_device",
                params={'key': key_code, 'hwid': hwid},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return True, data.get('message', 'Yêu cầu reset đã được gửi!')
                else:
                    return False, data.get('error', 'Không thể gửi yêu cầu reset')
            else:
                return False, "Không thể kết nối đến server"
        except Exception as e:
            return False, str(e)


class LoginDialog:
    def __init__(self, parent, validator):
        self.parent = parent
        self.validator = validator
        self.dialog = None
        
    def show(self):
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("Kích hoạt SunLon PRO")
        self.dialog.geometry("550x650")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - 275
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - 325
        self.dialog.geometry(f"+{x}+{y}")
        
        main_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        title = ctk.CTkLabel(main_frame, text="🎲 SUNLON PRO 🎲", 
                            font=ctk.CTkFont(size=36, weight="bold"), 
                            text_color="#FFD700")
        title.pack(pady=(0, 10))
        
        # Thông tin HWID
        hwid = self.validator.get_hwid()
        hwid_short = hwid[:16] + "..." if len(hwid) > 16 else hwid
        
        self.hwid_label = ctk.CTkLabel(main_frame, text=f"🖥️ HWID: {hwid_short}",
                                        font=ctk.CTkFont(size=10), text_color="#888888")
        self.hwid_label.pack(pady=(0, 10))
        
        self.status_label = ctk.CTkLabel(main_frame, text="🔄 Đang kết nối...", 
                                         font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=(0, 20))
        
        self.key_entry = ctk.CTkEntry(main_frame, placeholder_text="Nhập key của bạn",
                                       font=ctk.CTkFont(size=14), width=450, height=45)
        self.key_entry.pack(pady=(0, 15))
        
        self.message_label = ctk.CTkLabel(main_frame, text="", font=ctk.CTkFont(size=11))
        self.message_label.pack(pady=(0, 10))
        
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=(0, 10))
        
        verify_btn = ctk.CTkButton(btn_frame, text="🔑 Kích hoạt", command=self.verify_key,
                                    height=40, width=150, font=ctk.CTkFont(size=14, weight="bold"))
        verify_btn.pack(side="left", padx=5)
        
        reset_btn = ctk.CTkButton(btn_frame, text="🔄 Reset thiết bị", command=self.request_reset,
                                   height=40, width=150, font=ctk.CTkFont(size=12),
                                   fg_color="#FFA500", hover_color="#CC8400")
        reset_btn.pack(side="left", padx=5)
        
        guide_frame = ctk.CTkFrame(main_frame, corner_radius=10)
        guide_frame.pack(fill="x", pady=(20, 0))
        
        guide_text = f"""
📌 *HƯỚNG DẪN:*

1️⃣ Liên hệ Admin để được cấp key
2️⃣ Nhập key vào ô trên và nhấn "Kích hoạt"
3️⃣ Hệ thống tự động xác thực với server

🔒 *Bảo mật:* Key được gắn với HWID thiết bị
🔄 *Reset thiết bị:* Nếu muốn đổi máy, nhấn "Reset thiết bị"
📞 *Liên hệ admin:* @admin_username
        """
        
        guide = ctk.CTkLabel(guide_frame, text=guide_text, font=ctk.CTkFont(size=11),
                              justify="left", text_color="#888888")
        guide.pack(pady=15, padx=15)
        
        self.key_entry.bind('<Return>', lambda e: self.verify_key())
        self.key_entry.focus()
        
        self.check_server()
    
    def check_server(self):
        def check():
            try:
                response = requests.get(f"{BOT_URL}/health", timeout=5)
                if response.status_code == 200:
                    self.dialog.after(0, lambda: self.status_label.configure(
                        text="✅ Đã kết nối đến server", text_color="#00FF00"))
                else:
                    self.dialog.after(0, lambda: self.status_label.configure(
                        text="⚠️ Server đang offline", text_color="#FFA500"))
            except:
                self.dialog.after(0, lambda: self.status_label.configure(
                    text="❌ Không thể kết nối đến server", text_color="#FF4444"))
        
        threading.Thread(target=check, daemon=True).start()
    
    def verify_key(self):
        key_code = self.key_entry.get().strip().upper()
        if not key_code:
            self.message_label.configure(text="❌ Vui lòng nhập key", text_color="#FF4444")
            return
        
        self.message_label.configure(text="🔄 Đang xác thực...", text_color="#FFD700")
        
        def verify_thread():
            valid, message = self.validator.validate_key(key_code)
            self.dialog.after(0, lambda: self.on_result(valid, message, key_code))
        
        threading.Thread(target=verify_thread, daemon=True).start()
    
    def request_reset(self):
        key_code = self.key_entry.get().strip().upper()
        if not key_code:
            self.message_label.configure(text="❌ Vui lòng nhập key để reset", text_color="#FF4444")
            return
        
        self.message_label.configure(text="🔄 Đang gửi yêu cầu reset...", text_color="#FFD700")
        
        def reset_thread():
            success, message = self.validator.request_reset(key_code)
            self.dialog.after(0, lambda: self.on_reset_result(success, message))
        
        threading.Thread(target=reset_thread, daemon=True).start()
    
    def on_reset_result(self, success, message):
        if success:
            self.message_label.configure(text=f"✅ {message}", text_color="#00FF00")
        else:
            self.message_label.configure(text=f"❌ {message}", text_color="#FF4444")
    
    def on_result(self, valid, message, key_code):
        if valid:
            self.validator.save_key(key_code)
            self.message_label.configure(text=message, text_color="#00FF00")
            self.dialog.after(2000, self.dialog.destroy)
        else:
            self.message_label.configure(text=message, text_color="#FF4444")


class SunLonApp:
    def __init__(self):
        self.validator = KeyValidator()
        
        self.root = ctk.CTk()
        self.root.title("SunLon PRO - Cầu Tài Xỉu")
        self.root.geometry("800x700")
        self.root.resizable(False, False)
        
        self.total_predictions = 0
        self.correct_predictions = 0
        self.last_ket_qua = None
        self.last_du_doan = None
        self.countdown = REFRESH_INTERVAL
        self.history = []
        
        if not self.validator.is_valid:
            self.show_login()
        else:
            self.init_main_app()
    
    def show_login(self):
        self.login_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.login_frame.pack(fill="both", expand=True)
        
        center_frame = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        center_frame.pack(expand=True)
        
        logo = ctk.CTkLabel(center_frame, text="🎲 SUNLON PRO 🎲",
                            font=ctk.CTkFont(size=48, weight="bold"), text_color="#FFD700")
        logo.pack(pady=(0, 20))
        
        loading = ctk.CTkLabel(center_frame, text="Đang kiểm tra key...", font=ctk.CTkFont(size=14))
        loading.pack(pady=20)
        
        progress = ctk.CTkProgressBar(center_frame, width=300)
        progress.pack(pady=10)
        progress.start()
        
        def check():
            if self.validator.key_code:
                valid, msg = self.validator.validate_key(self.validator.key_code)
                if valid:
                    self.root.after(0, self.start_main_app)
                else:
                    self.root.after(0, self.show_key_dialog)
            else:
                self.root.after(1000, self.show_key_dialog)
        
        threading.Thread(target=check, daemon=True).start()
    
    def show_key_dialog(self):
        if hasattr(self, 'login_frame'):
            self.login_frame.destroy()
        dialog = LoginDialog(self.root, self.validator)
        dialog.show()
        self.check_dialog(dialog)
    
    def check_dialog(self, dialog):
        if dialog.dialog and dialog.dialog.winfo_exists():
            self.root.after(500, lambda: self.check_dialog(dialog))
        else:
            if self.validator.is_valid:
                self.start_main_app()
    
    def start_main_app(self):
        if hasattr(self, 'login_frame'):
            self.login_frame.destroy()
        
        self.init_main_app()
        
        if self.validator.user_info:
            welcome = f"Chào mừng {self.validator.user_info['user_name']}!"
            if self.validator.user_info.get('expire_date') != 'Vĩnh viễn':
                days = self.validator.user_info.get('days_left', 0)
                welcome += f" Còn {days} ngày"
            if self.validator.user_info.get('device'):
                welcome += f"\n🖥️ Thiết bị: {self.validator.user_info['device']}"
            self.root.title(f"SunLon PRO - {welcome}")
    
    def init_main_app(self):
        self.setup_ui()
        self.update_loop()
        self.countdown_loop()
    
    def setup_ui(self):
        # (Giữ nguyên phần UI từ code trước)
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        header_frame = ctk.CTkFrame(self.main_frame, corner_radius=15)
        header_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ctk.CTkLabel(header_frame, text="🎲 SUNLON - CẦU TÀI XỈU PRO 🎲",
                                    font=ctk.CTkFont(size=28, weight="bold"), text_color="#FFD700")
        title_label.pack(pady=15)
        
        control_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        control_frame.pack(pady=(0, 10))
        
        self.time_label = ctk.CTkLabel(control_frame, text="⏱️ Đang khởi tạo...", font=ctk.CTkFont(size=12))
        self.time_label.pack(side="left", padx=10)
        
        if self.validator.user_info:
            user_text = f"👤 {self.validator.user_info['user_name']}"
            if self.validator.user_info.get('expire_date') and self.validator.user_info['expire_date'] != 'Vĩnh viễn':
                user_text += f" | 📅 HSD: {self.validator.user_info['expire_date']}"
            user_label = ctk.CTkLabel(control_frame, text=user_text, font=ctk.CTkFont(size=11), text_color="#00FF00")
            user_label.pack(side="right", padx=10)
        
        theme_switch = ctk.CTkSwitch(control_frame, text="🌙 Dark Mode", command=self.toggle_theme,
                                      progress_color="#FFD700")
        theme_switch.pack(side="right", padx=10)
        theme_switch.select()
        
        columns_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        columns_frame.pack(fill="both", expand=True)
        
        left_col = ctk.CTkFrame(columns_frame, corner_radius=15)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        right_col = ctk.CTkFrame(columns_frame, corner_radius=15)
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        info_card = ctk.CTkFrame(left_col, corner_radius=15, border_width=2, border_color="#FFD700")
        info_card.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(info_card, text="📊 THÔNG TIN HIỆN TẠI", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#FFD700").pack(pady=(15, 10))
        
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
        
        stats_card = ctk.CTkFrame(right_col, corner_radius=15, border_width=2, border_color="#FFD700")
        stats_card.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(stats_card, text="📈 THỐNG KÊ DỰ ĐOÁN", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#FFD700").pack(pady=(15, 10))
        
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
        
        reset_btn = ctk.CTkButton(stats_card, text="🔄 Reset Thống Kê", command=self.reset_stats,
                                   height=35, corner_radius=10, fg_color="#FF4444", hover_color="#CC0000")
        reset_btn.pack(pady=(10, 15))
        
        self.result_message = ctk.CTkLabel(stats_card, text="Chưa có dự đoán", font=ctk.CTkFont(size=11, slant="italic"), text_color="#AAAAAA")
        self.result_message.pack(pady=(0, 10))
        
        history_frame = ctk.CTkFrame(self.main_frame, corner_radius=15)
        history_frame.pack(fill="x", pady=(20, 0))
        
        ctk.CTkLabel(history_frame, text="📜 LỊCH SỬ DỰ ĐOÁN GẦN ĐÂY", font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#FFD700").pack(pady=(10, 5))
        
        self.history_container = ctk.CTkFrame(history_frame, fg_color="transparent")
        self.history_container.pack(fill="x", padx=15, pady=10)
        
        self.history_labels = []
        for i in range(5):
            label = ctk.CTkLabel(self.history_container, text="", font=ctk.CTkFont(size=11), anchor="w")
            label.pack(fill="x", pady=2)
            self.history_labels.append(label)
        
        self.status_bar = ctk.CTkLabel(self.root, text="✅ Hệ thống đang hoạt động", font=ctk.CTkFont(size=11),
                                        fg_color="#2B2B2B", corner_radius=0)
        self.status_bar.pack(side="bottom", fill="x", pady=(5, 0))
    
    def toggle_theme(self):
        current = ctk.get_appearance_mode()
        ctk.set_appearance_mode("Light" if current == "Dark" else "Dark")
    
    def countdown_loop(self):
        if self.countdown > 0:
            self.countdown -= 1
            self.time_label.configure(text=f"⏱️ Cập nhật sau: {self.countdown}s")
            self.root.after(1000, self.countdown_loop)
        else:
            self.countdown = REFRESH_INTERVAL
    
    def update_loop(self):
        threading.Thread(target=self.fetch_data, daemon=True).start()
        self.root.after(REFRESH_INTERVAL * 1000, self.update_loop)
    
    def fetch_data(self):
        try:
            response = requests.get(API_URL, timeout=10)
            data = response.json()
            
            phien = data.get("phien", "---")
            tong = data.get("tong", "---")
            pattern = data.get("pattern", "---")
            ket_qua = data.get("ket_qua", "---")
            du_doan = data.get("du_doan", "---")
            so_sanh = data.get("so_sanh", "---")
            
            self.root.after(0, lambda: self.update_ui(phien, tong, pattern, ket_qua, du_doan, so_sanh))
            
            if ket_qua != "---" and du_doan != "---":
                if ket_qua != self.last_ket_qua or du_doan != self.last_du_doan:
                    self.total_predictions += 1
                    is_correct = (du_doan == ket_qua)
                    
                    if is_correct:
                        self.correct_predictions += 1
                        result_text = f"✅ Dự đoán ĐÚNG! {du_doan} = {ket_qua}"
                    else:
                        result_text = f"❌ Dự đoán SAI! {du_doan} ≠ {ket_qua}"
                    
                    self.root.after(0, lambda: self.update_stats())
                    self.root.after(0, lambda: self.result_message.configure(text=result_text,
                                               text_color="#00FF00" if is_correct else "#FF4444"))
                    self.root.after(0, lambda: self.update_history(phien, ket_qua, du_doan, is_correct))
                    
                    self.last_ket_qua = ket_qua
                    self.last_du_doan = du_doan
            
            self.root.after(0, lambda: self.status_bar.configure(text=f"✅ Cập nhật lúc {datetime.now().strftime('%H:%M:%S')}"))
            
        except Exception as e:
            self.root.after(0, lambda: self.status_bar.configure(text=f"⚠️ Lỗi: {str(e)}", text_color="#FF4444"))
    
    def update_ui(self, phien, tong, pattern, ket_qua, du_doan, so_sanh):
        self.phien_label.configure(text=str(phien))
        self.tong_label.configure(text=str(tong))
        self.pattern_label.configure(text=str(pattern))
        
        ket_qua_color = "#00FF00" if ket_qua == "Tài" else "#FF4444" if ket_qua == "Xỉu" else "#FFA500"
        self.ketqua_label.configure(text=ket_qua, text_color=ket_qua_color)
        
        du_doan_color = "#00FF00" if du_doan == "Tài" else "#FF4444" if du_doan == "Xỉu" else "#FFA500"
        self.dudoan_label.configure(text=du_doan, text_color=du_doan_color)
        
        self.sosanh_label.configure(text=so_sanh)
    
    def update_stats(self):
        wrong = self.total_predictions - self.correct_predictions
        accuracy = (self.correct_predictions / self.total_predictions * 100) if self.total_predictions > 0 else 0
        
        self.total_label.configure(text=str(self.total_predictions))
        self.correct_label.configure(text=str(self.correct_predictions))
        self.wrong_label.configure(text=str(wrong))
        self.accuracy_label.configure(text=f"{accuracy:.1f}%")
        self.progress_bar.set(accuracy / 100)
    
    def reset_stats(self):
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
        self.root.mainloop()


if __name__ == "__main__":
    print("=" * 50)
    print("🎲 SUNLON CLIENT PRO")
    print("🔒 Xác thực qua API với HWID")
    print("=" * 50)
    app = SunLonApp()
    app.run()

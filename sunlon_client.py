# sunlon_client.py
"""
Client GUI cho SunLon với xác thực key
"""

import customtkinter as ctk
import requests
import threading
import json
import os
from datetime import datetime
from tkinter import messagebox

# Cấu hình
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

API_URL = "https://apisunhpt.onrender.com/sunlon"
KEY_SERVER_URL = os.environ.get('KEY_SERVER_URL', 'https://localhost:5000')  # Địa chỉ server key (có thể thay đổi)
REFRESH_INTERVAL = 5

# File lưu key
KEY_FILE = "sunlon_key.json"


class KeyManager:
    """Quản lý key"""
    
    def __init__(self):
        self.key = None
        self.user_info = None
        self.load_key()
    
    def load_key(self):
        """Tải key từ file"""
        try:
            if os.path.exists(KEY_FILE):
                with open(KEY_FILE, 'r') as f:
                    data = json.load(f)
                    self.key = data.get('key')
                    self.user_info = data.get('user_info')
                    return True
        except:
            pass
        return False
    
    def save_key(self, key, user_info):
        """Lưu key vào file"""
        self.key = key
        self.user_info = user_info
        with open(KEY_FILE, 'w') as f:
            json.dump({'key': key, 'user_info': user_info}, f)
    
    def verify_key(self, key):
        """Xác thực key với server"""
        try:
            response = requests.post(
                f"{KEY_SERVER_URL}/api/verify",
                json={'key': key},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('valid'):
                    self.save_key(key, data)
                    return True, data
                else:
                    return False, data.get('message', 'Key không hợp lệ')
            else:
                return False, f"Lỗi server: {response.status_code}"
                
        except Exception as e:
            return False, f"Không thể kết nối đến server key: {str(e)}"
    
    def clear_key(self):
        """Xóa key đã lưu"""
        self.key = None
        self.user_info = None
        if os.path.exists(KEY_FILE):
            os.remove(KEY_FILE)


class LoginWindow:
    """Cửa sổ đăng nhập key"""
    
    def __init__(self, key_manager, on_success):
        self.key_manager = key_manager
        self.on_success = on_success
        self.window = ctk.CTkToplevel()
        self.window.title("SunLon - Đăng nhập")
        self.window.geometry("450x400")
        self.window.resizable(False, False)
        
        # Center window
        self.window.transient()
        self.window.grab_set()
        
        self.setup_ui()
    
    def setup_ui(self):
        """Thiết lập giao diện đăng nhập"""
        
        # Main frame
        main_frame = ctk.CTkFrame(self.window, corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Logo/Title
        title = ctk.CTkLabel(
            main_frame,
            text="🔑 XÁC THỰC KEY",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#FFD700"
        )
        title.pack(pady=(30, 10))
        
        subtitle = ctk.CTkLabel(
            main_frame,
            text="Nhập key của bạn để sử dụng ứng dụng",
            font=ctk.CTkFont(size=12),
            text_color="#AAAAAA"
        )
        subtitle.pack(pady=(0, 30))
        
        # Key input
        key_label = ctk.CTkLabel(main_frame, text="Mã Key:", font=ctk.CTkFont(size=14))
        key_label.pack(anchor="w", padx=30)
        
        self.key_entry = ctk.CTkEntry(
            main_frame,
            placeholder_text="Ví dụ: A1B2C3D4E5F6G7H8",
            width=300,
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.key_entry.pack(pady=(5, 20), padx=30)
        
        # Status
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#FFA500"
        )
        self.status_label.pack(pady=(0, 10))
        
        # Buttons
        verify_btn = ctk.CTkButton(
            main_frame,
            text="Xác thực",
            command=self.verify,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#00AA00",
            hover_color="#008800"
        )
        verify_btn.pack(pady=10, padx=30, fill="x")
        
        register_btn = ctk.CTkButton(
            main_frame,
            text="Đăng ký key mới",
            command=self.show_register,
            height=35,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color="#333333",
            border_width=1
        )
        register_btn.pack(pady=5, padx=30, fill="x")
        
        # Info
        info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        info_frame.pack(pady=(20, 10))
        
        info_text = ctk.CTkLabel(
            info_frame,
            text="💡 Hướng dẫn:\n• Liên hệ admin để nhận key\n• Key có thời hạn sử dụng\n• Key sẽ được lưu để tự động đăng nhập",
            font=ctk.CTkFont(size=10),
            text_color="#888888",
            justify="left"
        )
        info_text.pack()
    
    def verify(self):
        """Xác thực key"""
        key = self.key_entry.get().strip()
        
        if not key:
            self.status_label.configure(text="❌ Vui lòng nhập key", text_color="#FF4444")
            return
        
        self.status_label.configure(text="🔄 Đang xác thực...", text_color="#FFA500")
        
        # Gọi xác thực trong thread riêng
        threading.Thread(target=self._verify_thread, args=(key,), daemon=True).start()
    
    def _verify_thread(self, key):
        """Thread xác thực"""
        success, result = self.key_manager.verify_key(key)
        
        if success:
            self.window.after(0, lambda: self._verify_success(result))
        else:
            self.window.after(0, lambda: self.status_label.configure(
                text=f"❌ {result}",
                text_color="#FF4444"
            ))
    
    def _verify_success(self, user_info):
        """Xử lý khi xác thực thành công"""
        self.status_label.configure(
            text=f"✅ {user_info.get('message')}",
            text_color="#00FF00"
        )
        
        # Đóng cửa sổ sau 1 giây
        self.window.after(1000, self.window.destroy)
        
        # Gọi callback
        self.window.after(1000, self.on_success)
    
    def show_register(self):
        """Hiển thị form đăng ký key"""
        RegisterWindow(self.key_manager)


class RegisterWindow:
    """Cửa sổ đăng ký key mới"""
    
    def __init__(self, key_manager):
        self.key_manager = key_manager
        self.window = ctk.CTkToplevel()
        self.window.title("SunLon - Đăng ký key")
        self.window.geometry("450x450")
        self.window.resizable(False, False)
        
        self.window.transient()
        self.window.grab_set()
        
        self.setup_ui()
    
    def setup_ui(self):
        """Thiết lập giao diện đăng ký"""
        
        main_frame = ctk.CTkFrame(self.window, corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(
            main_frame,
            text="📝 ĐĂNG KÝ KEY MỚI",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#FFD700"
        )
        title.pack(pady=(30, 20))
        
        # Tên người dùng
        name_label = ctk.CTkLabel(main_frame, text="Tên người dùng:", font=ctk.CTkFont(size=14))
        name_label.pack(anchor="w", padx=30)
        
        self.name_entry = ctk.CTkEntry(main_frame, placeholder_text="Nhập tên của bạn", width=300)
        self.name_entry.pack(pady=(5, 15), padx=30)
        
        # Thời hạn
        days_label = ctk.CTkLabel(main_frame, text="Thời hạn (ngày):", font=ctk.CTkFont(size=14))
        days_label.pack(anchor="w", padx=30)
        
        self.days_var = ctk.StringVar(value="30")
        days_combo = ctk.CTkComboBox(
            main_frame,
            values=["7", "15", "30", "60", "90"],
            variable=self.days_var,
            width=300
        )
        days_combo.pack(pady=(5, 15), padx=30)
        
        # Admin key (nếu có)
        admin_label = ctk.CTkLabel(
            main_frame,
            text="Admin Key (nếu có):",
            font=ctk.CTkFont(size=14)
        )
        admin_label.pack(anchor="w", padx=30)
        
        self.admin_entry = ctk.CTkEntry(
            main_frame,
            placeholder_text="Nhập admin key để tạo key miễn phí",
            width=300,
            show="•"
        )
        self.admin_entry.pack(pady=(5, 15), padx=30)
        
        # Status
        self.status_label = ctk.CTkLabel(main_frame, text="", font=ctk.CTkFont(size=11))
        self.status_label.pack(pady=(0, 10))
        
        # Buttons
        register_btn = ctk.CTkButton(
            main_frame,
            text="Đăng ký",
            command=self.register,
            height=40,
            fg_color="#FFA500",
            hover_color="#FF8800"
        )
        register_btn.pack(pady=10, padx=30, fill="x")
        
        cancel_btn = ctk.CTkButton(
            main_frame,
            text="Hủy",
            command=self.window.destroy,
            height=35,
            fg_color="transparent",
            hover_color="#333333",
            border_width=1
        )
        cancel_btn.pack(pady=5, padx=30, fill="x")
    
    def register(self):
        """Đăng ký key mới"""
        user_name = self.name_entry.get().strip()
        days = int(self.days_var.get())
        admin_key = self.admin_entry.get().strip()
        
        if not user_name:
            self.status_label.configure(text="❌ Vui lòng nhập tên người dùng", text_color="#FF4444")
            return
        
        self.status_label.configure(text="🔄 Đang đăng ký...", text_color="#FFA500")
        
        threading.Thread(target=self._register_thread, args=(user_name, days, admin_key), daemon=True).start()
    
    def _register_thread(self, user_name, days, admin_key):
        """Thread đăng ký"""
        try:
            headers = {}
            if admin_key:
                headers['X-Admin-Key'] = admin_key
            
            response = requests.post(
                f"{KEY_SERVER_URL}/api/register",
                json={'user_name': user_name, 'days': days},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.window.after(0, lambda: self._register_success(data))
            else:
                error = response.json().get('error', 'Lỗi không xác định')
                self.window.after(0, lambda: self.status_label.configure(
                    text=f"❌ Đăng ký thất bại: {error}",
                    text_color="#FF4444"
                ))
                
        except Exception as e:
            self.window.after(0, lambda: self.status_label.configure(
                text=f"❌ Lỗi: {str(e)}",
                text_color="#FF4444"
            ))
    
    def _register_success(self, data):
        """Xử lý đăng ký thành công"""
        key = data.get('key')
        
        self.status_label.configure(
            text=f"✅ Đăng ký thành công! Key của bạn: {key}",
            text_color="#00FF00"
        )
        
        # Hiển thị key
        key_frame = ctk.CTkFrame(self.window, fg_color="#2B2B2B", corner_radius=10)
        key_frame.pack(pady=10, padx=30, fill="x")
        
        key_label = ctk.CTkLabel(
            key_frame,
            text=key,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFD700"
        )
        key_label.pack(pady=10)
        
        # Tự động đóng sau 5 giây
        self.window.after(5000, self.window.destroy)


class SunLonApp:
    """Ứng dụng chính"""
    
    def __init__(self):
        self.key_manager = KeyManager()
        self.root = None
        self.is_running = False
        
        # Kiểm tra key đã lưu chưa
        if not self.key_manager.key:
            self.show_login()
        else:
            self.verify_saved_key()
    
    def verify_saved_key(self):
        """Xác thực key đã lưu"""
        success, result = self.key_manager.verify_key(self.key_manager.key)
        
        if success:
            self.start_app()
        else:
            # Key không hợp lệ, xóa và yêu cầu đăng nhập lại
            self.key_manager.clear_key()
            messagebox.showwarning("Key hết hạn", "Key đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại.")
            self.show_login()
    
    def show_login(self):
        """Hiển thị cửa sổ đăng nhập"""
        login = LoginWindow(self.key_manager, self.start_app)
    
    def start_app(self):
        """Khởi động ứng dụng chính"""
        if self.is_running:
            return
        
        self.is_running = True
        self.root = ctk.CTk()
        self.root.title(f"SunLon - {self.key_manager.user_info.get('user_name', 'User')}")
        self.root.geometry("800x650")
        self.root.resizable(False, False)
        
        # Biến thống kê
        self.total_predictions = 0
        self.correct_predictions = 0
        self.last_ket_qua = None
        self.last_du_doan = None
        self.countdown = REFRESH_INTERVAL
        self.history = []
        
        # Setup UI
        self.setup_ui()
        
        # Bắt đầu cập nhật
        self.update_loop()
        self.countdown_loop()
        
        self.root.mainloop()
    
    def setup_ui(self):
        """Thiết lập giao diện (tương tự như version trước)"""
        # ... (giữ nguyên code UI từ version trước)
        # Thêm hiển thị thông tin user và key
        user_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        user_frame.pack(side="top", fill="x", padx=20, pady=(10, 0))
        
        user_info = ctk.CTkLabel(
            user_frame,
            text=f"👤 {self.key_manager.user_info.get('user_name')} | 🎫 Còn {self.key_manager.user_info.get('days_left', 0)} ngày",
            font=ctk.CTkFont(size=11),
            anchor="e"
        )
        user_info.pack(side="right")
        
        # ... (phần còn lại giữ nguyên)
    
    def update_ui(self, phien, tong, pattern, ket_qua, du_doan, so_sanh):
        """Cập nhật giao diện"""
        # Giữ nguyên code từ version trước
        pass
    
    def update_stats(self):
        """Cập nhật thống kê"""
        # Giữ nguyên code từ version trước
        pass
    
    def update_history(self, phien, ket_qua, du_doan, is_correct):
        """Cập nhật lịch sử"""
        # Giữ nguyên code từ version trước
        pass
    
    def fetch_data(self):
        """Lấy dữ liệu từ API"""
        # Giữ nguyên code từ version trước
        pass
    
    def countdown_loop(self):
        """Đếm ngược thời gian"""
        # Giữ nguyên code từ version trước
        pass
    
    def update_loop(self):
        """Cập nhật dữ liệu định kỳ"""
        # Giữ nguyên code từ version trước
        pass
    
    def reset_stats(self):
        """Reset thống kê"""
        # Giữ nguyên code từ version trước
        pass
    
    def toggle_theme(self):
        """Chuyển đổi Dark/Light mode"""
        # Giữ nguyên code từ version trước
        pass


# ==================== RUN ====================
if __name__ == "__main__":
    app = SunLonApp()
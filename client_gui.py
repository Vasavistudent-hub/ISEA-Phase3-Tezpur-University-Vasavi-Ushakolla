import socket
import threading
import json
import time
import os
import tkinter as tk
from tkinter import messagebox, scrolledtext

def load_config(config_path="config.json"):
    if not os.path.exists(config_path):
        return {
            "client": {
                "default_host": "127.0.0.1",
                "default_port": 5000,
                "reconnect_attempts": 3,
                "reconnect_delay": 2,
                "buffer_size": 1024
            }
        }
    with open(config_path, "r") as f:
        return json.load(f)

config = load_config()
CLIENT_CFG = config.get("client", {})
DEFAULT_HOST = CLIENT_CFG.get("default_host", "127.0.0.1")
DEFAULT_PORT = config.get("server", {}).get("port", 5000)
RECONNECT_ATTEMPTS = CLIENT_CFG.get("reconnect_attempts", 3)
RECONNECT_DELAY = CLIENT_CFG.get("reconnect_delay", 2)
MAX_MSG_SIZE = CLIENT_CFG.get("buffer_size", 1024)

class SecureChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure TCP Chat Client")
        self.root.geometry("450x550")
        self.root.configure(bg="#f0f2f5")

        self.client_socket = None
        self.username = ""
        self.password = ""
        self.host = DEFAULT_HOST
        self.port = DEFAULT_PORT
        self.running = False
        self.reconnecting = False

        self.container = tk.Frame(self.root, bg="#f0f2f5")
        self.container.pack(fill="both", expand=True)

        self.show_login_screen()

    def show_login_screen(self):
        self.login_frame = tk.Frame(self.container, bg="#ffffff", bd=2, relief="groove")
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center", width=350, height=400)

        lbl_title = tk.Label(self.login_frame, text="Secure Workspace", font=("Helvetica", 16, "bold"), bg="#ffffff", fg="#1877f2")
        lbl_title.pack(pady=20)

        tk.Label(self.login_frame, text="Server IP Address:", font=("Helvetica", 10), bg="#ffffff").pack(anchor="w", padx=30)
        self.ent_host = tk.Entry(self.login_frame, font=("Helvetica", 11), bg="#f0f2f5", bd=0)
        self.ent_host.insert(0, DEFAULT_HOST)
        self.ent_host.pack(fill="x", padx=30, pady=(5, 15), ipady=5)

        tk.Label(self.login_frame, text="Username:", font=("Helvetica", 10), bg="#ffffff").pack(anchor="w", padx=30)
        self.ent_username = tk.Entry(self.login_frame, font=("Helvetica", 11), bg="#f0f2f5", bd=0)
        self.ent_username.pack(fill="x", padx=30, pady=(5, 15), ipady=5)

        tk.Label(self.login_frame, text="Password:", font=("Helvetica", 10), bg="#ffffff").pack(anchor="w", padx=30)
        self.ent_password = tk.Entry(self.login_frame, show="•", font=("Helvetica", 11), bg="#f0f2f5", bd=0)
        self.ent_password.pack(fill="x", padx=30, pady=(5, 25), ipady=5)

        btn_login = tk.Button(self.login_frame, text="Log In", font=("Helvetica", 11, "bold"), bg="#1877f2", fg="#ffffff", activebackground="#166fe5", activeforeground="#ffffff", bd=0, command=self.attempt_login)
        btn_login.pack(fill="x", padx=30, ipady=8)

    def attempt_login(self):
        self.host = self.ent_host.get().strip()
        self.username = self.ent_username.get().strip()
        self.password = self.ent_password.get().strip()

        if not self.host or not self.username or not self.password:
            messagebox.showwarning("Missing Fields", "Please complete all registration fields.")
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5.0)
            self.client_socket.connect((self.host, self.port))
            self.client_socket.settimeout(2.0)  
        except Exception as e:
            messagebox.showerror("Connection Failed", f"Could not connect to {self.host}:{self.port}.\nError: {e}")
            return

        auth_payload = f"AUTH {self.username} {self.password}"
        try:
            self.client_socket.sendall(auth_payload.encode('utf-8'))
            response = self.client_socket.recv(MAX_MSG_SIZE).decode('utf-8').strip()
            
            self.client_socket.settimeout(None)
            
            if response == "AUTH_SUCCESS":
                self.running = True
                self.login_frame.destroy()
                self.show_chat_screen()
                threading.Thread(target=self.receive_messages, daemon=True).start()
            elif "Too many failed login attempts" in response or "blocked" in response:
                messagebox.showerror("Security Alert", response)
                self.clean_disconnect()
            else:
                messagebox.showerror("Access Denied", response)
                self.clean_disconnect()
                
        except (socket.timeout, socket.error, BrokenPipeError, ConnectionResetError):
            messagebox.showerror("Security Alert", "ERROR: Connection error during authentication.")
            self.clean_disconnect()

    def show_chat_screen(self):
        self.chat_frame = tk.Frame(self.container, bg="#f0f2f5")
        self.chat_frame.pack(fill="both", expand=True, padx=15, pady=15)

        header_frame = tk.Frame(self.chat_frame, bg="#f0f2f5")
        header_frame.pack(fill="x", pady=(0, 10))

        self.lbl_welcome = tk.Label(header_frame, text=f"Logged in as: {self.username}", font=("Helvetica", 11, "bold"), bg="#f0f2f5", fg="#333333")
        self.lbl_welcome.pack(side="left")

        btn_logout = tk.Button(header_frame, text="Log Out", font=("Helvetica", 9, "bold"), bg="#e4e6eb", fg="#050505", bd=0, padx=10, command=self.logout)
        btn_logout.pack(side="right")

        self.chat_display = scrolledtext.ScrolledText(self.chat_frame, wrap=tk.WORD, font=("Helvetica", 10), state="disabled", bg="#ffffff", bd=0)
        self.chat_display.pack(fill="both", expand=True, pady=(0, 10))

        input_frame = tk.Frame(self.chat_frame, bg="#f0f2f5")
        input_frame.pack(fill="x")

        self.ent_msg = tk.Entry(input_frame, font=("Helvetica", 11), bg="#ffffff", bd=0)
        self.ent_msg.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
        self.ent_msg.bind("<Return>", lambda event: self.send_message())

        btn_send = tk.Button(input_frame, text="Send", font=("Helvetica", 10, "bold"), bg="#1877f2", fg="#ffffff", bd=0, padx=15, command=self.send_message)
        btn_send.pack(side="right", ipady=6)

    def send_message(self):
        if not self.running:
            return

        msg = self.ent_msg.get().strip()
        if not msg:
            return

        if len(msg.encode('utf-8')) > MAX_MSG_SIZE:
            messagebox.showwarning("Oversized Message", f"Messages cannot exceed {MAX_MSG_SIZE} bytes.")
            return

        try:
            self.client_socket.sendall(msg.encode('utf-8'))
            self.append_to_display(f"[You]: {msg}")
            self.ent_msg.delete(0, tk.END)
        except Exception as e:
            self.append_to_display(f"[SYSTEM ERROR]: Failed to deliver message. {e}")

    def receive_messages(self):
        while self.running:
            try:
                data = self.client_socket.recv(MAX_MSG_SIZE).decode('utf-8')
                if not data:
                    break
                
                if "ERROR: Session timed out" in data:
                    self.append_to_display("\n[SYSTEM]: Disconnected due to inactivity.")
                    messagebox.showwarning("Session Timeout", "Your session has expired due to inactivity.")
                    break

                self.append_to_display(data.strip())
            except Exception:
                if self.running and not self.reconnecting:
                    if self.attempt_reconnect():
                        continue
                break

        if not self.reconnecting:
            self.clean_disconnect()

    def attempt_reconnect(self):
        self.reconnecting = True
        self.append_to_display("\n[SYSTEM]: Connection lost. Attempting auto-reconnection...")
        
        for attempt in range(1, RECONNECT_ATTEMPTS + 1):
            time.sleep(RECONNECT_DELAY)
            try:
                self.append_to_display(f"[SYSTEM]: Reconnecting (Attempt {attempt}/{RECONNECT_ATTEMPTS})...")
                new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                new_sock.settimeout(5.0)
                new_sock.connect((self.host, self.port))
                
                auth_payload = f"AUTH {self.username} {self.password}"
                new_sock.sendall(auth_payload.encode('utf-8'))
                res = new_sock.recv(MAX_MSG_SIZE).decode('utf-8').strip()
                
                if res == "AUTH_SUCCESS":
                    new_sock.settimeout(None)
                    self.client_socket = new_sock
                    self.reconnecting = False
                    self.append_to_display("[SYSTEM]: Reconnected successfully!")
                    return True
                else:
                    new_sock.close()
            except Exception:
                pass

        self.append_to_display("[SYSTEM]: Auto-reconnection failed.")
        self.reconnecting = False
        return False

    def append_to_display(self, message):
        def _update():
            if hasattr(self, 'chat_display') and self.chat_display.winfo_exists():
                self.chat_display.configure(state="normal")
                self.chat_display.insert(tk.END, message + "\n")
                self.chat_display.configure(state="disabled")
                self.chat_display.see(tk.END)
        self.root.after(0, _update)

    def logout(self):
        if self.client_socket and self.running:
            try:
                self.client_socket.sendall(b"LOGOUT")
            except Exception:
                pass
        self.clean_disconnect()

    def clean_disconnect(self):
        self.running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass
            self.client_socket = None

        self.root.after(0, self.reset_to_login)

    def reset_to_login(self):
        if hasattr(self, 'chat_frame') and self.chat_frame.winfo_exists():
            self.chat_frame.destroy()
        self.show_login_screen()

if __name__ == "__main__":
    root = tk.Tk()
    app = SecureChatClient(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.logout(), root.destroy()))
    root.mainloop()

import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

class ChatClientGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("ISEA Multi-Client Chat Application")
        self.root.geometry("650x480")

        self.client_socket = None
        self.username = ""

        self.login_frame = tk.Frame(self.root)
        self.login_frame.pack(pady=60)

        self.lbl_title = tk.Label(
            self.login_frame,
            text="Network Chat Login",
            font=("Arial", 14, "bold"),
        )
        self.lbl_title.pack(pady=10)

        self.lbl_user = tk.Label(self.login_frame, text="Enter Username:")
        self.lbl_user.pack()

        self.entry_username = tk.Entry(self.login_frame, font=("Arial", 11))
        self.entry_username.pack(pady=5)
        self.entry_username.bind(
            "<Return>", lambda event: self.connect_to_server()
        )

        self.btn_connect = tk.Button(
            self.login_frame,
            text="Connect",
            command=self.connect_to_server,
            bg="#2ecc71",
            fg="white",
            font=("Arial", 11, "bold"),
        )
        self.btn_connect.pack(pady=15)

        self.chat_frame = tk.Frame(self.root)

    def connect_to_server(self):
        self.username = self.entry_username.get().strip()

        if not self.username:
            messagebox.showerror("Validation Error", "Username cannot be empty!")
            return

        try:
            self.client_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
            )
            self.client_socket.connect(("10.0.0.1", 5000))
            self.client_socket.send(self.username.encode("utf-8"))

            self.login_frame.pack_forget()
            self.setup_chat_window()

            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()

        except Exception as e:
            messagebox.showerror(
                "Connection Error", f"Could not connect to server: {e}"
            )

    def setup_chat_window(self):
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.chat_frame.columnconfigure(0, weight=4)
        self.chat_frame.columnconfigure(1, weight=1)
        self.chat_frame.rowconfigure(0, weight=1)

        self.chat_area = scrolledtext.ScrolledText(
            self.chat_frame, wrap=tk.WORD, state=tk.DISABLED
        )
        self.chat_area.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.user_listbox = tk.Listbox(self.chat_frame, font=("Arial", 10))
        self.user_listbox.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        input_frame = tk.Frame(self.chat_frame)
        input_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)

        self.entry_message = tk.Entry(input_frame, font=("Arial", 11))
        self.entry_message.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.entry_message.bind("<Return>", lambda event: self.send_message())

        self.btn_send = tk.Button(
            input_frame,
            text="Send",
            command=self.send_message,
            width=10,
            bg="#3498db",
            fg="white",
        )
        self.btn_send.pack(side=tk.LEFT, padx=5)

        self.btn_disconnect = tk.Button(
            input_frame,
            text="Disconnect",
            command=self.disconnect_from_server,
            bg="#e74c3c",
            fg="white",
        )
        self.btn_disconnect.pack(side=tk.RIGHT, padx=5)

        self.lbl_status = tk.Label(
            self.chat_frame,
            text=f"Status: Connected as {self.username}",
            fg="green",
            anchor="w",
        )
        self.lbl_status.grid(row=2, column=0, columnspan=2, sticky="ew")

    def send_message(self):
        msg = self.entry_message.get().strip()
        if msg:
            try:
                self.client_socket.send(msg.encode("utf-8"))
                self.entry_message.delete(0, tk.END)
            except Exception:
                self.append_chat_log("[System Error: Server connection lost.]")

    def receive_messages(self):
        while True:
            try:
                data = self.client_socket.recv(1024).decode("utf-8")
                if not data:
                    break

                if "USERS:" in data:
                    parts = data.split("USERS:", 1)
                    chat_part = parts[0].strip()
                    users_part = parts[1].strip()

                    if chat_part:
                        self.append_chat_log(chat_part)

                    active_roster = users_part.split(",")
                    self.refresh_roster_sidebar(active_roster)
                else:
                    self.append_chat_log(data)

            except Exception:
                break

        self.append_chat_log("[Disconnected from Session]")

    def append_chat_log(self, text):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, text + "\n")
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def refresh_roster_sidebar(self, user_list):
        self.user_listbox.delete(0, tk.END)
        for user in user_list:
            if user.strip():
                self.user_listbox.insert(tk.END, user.strip())

    def disconnect_from_server(self):
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        self.root.quit()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClientGUI(root)
    root.mainloop()

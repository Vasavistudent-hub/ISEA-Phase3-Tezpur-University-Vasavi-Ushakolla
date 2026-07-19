import socket
import threading
import json
import hashlib
import time
import os

PORT = 5000
MAX_MSG_SIZE = 1024
TIMEOUT_LIMIT = 300.0
BLOCK_DURATION = 30.0
MAX_FAILED_ATTEMPTS = 3

active_clients = {}
active_usernames = set()
failed_login_attempts = {}
blocked_ips = {}


lock = threading.RLock()

def log_event(event_text):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {event_text}\n"
    with lock:
        with open("security_log.txt", "a") as f:
            f.write(log_line)

def load_user_database():
    if not os.path.exists("users.json"):
        default_users = {
            "vasavi": hashlib.sha256("sahil1212".encode()).hexdigest(),
            "sahil": hashlib.sha256("vasu1608".encode()).hexdigest(),
            "trithi": hashlib.sha256("us1612".encode()).hexdigest()
        }
        with open("users.json", "w") as f:
            json.dump(default_users, f, indent=4)
        log_event("SYSTEM: Created new users.json database.")
    
    with open("users.json", "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_user_database(database):
    with open("users.json", "w") as f:
        json.dump(database, f, indent=4)

user_db = load_user_database()

def is_blocked(ip):
    with lock:
        if ip in blocked_ips:
            if time.time() - blocked_ips[ip] < BLOCK_DURATION:
                return True
            else:
                del blocked_ips[ip]
                failed_login_attempts[ip] = 0
        return False

def record_failed_login(ip):
    with lock:
        failed_login_attempts[ip] = failed_login_attempts.get(ip, 0) + 1
        if failed_login_attempts[ip] >= MAX_FAILED_ATTEMPTS:
            blocked_ips[ip] = time.time()
            log_event(f"SECURITY ALERT: IP {ip} blocked due to excessive failed login attempts.")
            return True
        return False

def broadcast(message, sender_socket=None):
    with lock:
        for client_sock in active_clients:
            if client_sock != sender_socket:
                try:
                    client_sock.sendall(message.encode('utf-8'))
                except Exception:
                    pass

def handle_client(client_socket, client_address):
    global user_db
    ip, port = client_address
    log_event(f"CONNECTION: Incoming connection from {ip}:{port}")
    
    if is_blocked(ip):
        try:
            client_socket.sendall(b"ERROR: IP temporarily blocked due to multiple failed login attempts.")
            client_socket.shutdown(socket.SHUT_WR)
            time.sleep(0.2)
            client_socket.close()
        except Exception:
            pass
        return

    authenticated = False
    username = ""
    last_active = time.time()
    
    try:
        while not authenticated:
            if is_blocked(ip):
                try:
                    client_socket.sendall(b"ERROR: IP temporarily blocked.")
                    client_socket.shutdown(socket.SHUT_WR)
                except Exception:
                    pass
                time.sleep(0.2)
                client_socket.close()
                return

            client_socket.settimeout(TIMEOUT_LIMIT)
            data = client_socket.recv(MAX_MSG_SIZE).decode('utf-8')
            if not data:
                client_socket.close()
                return

            data = data.strip()
            if "AUTH " in data and not data.startswith("AUTH "):
                data = data[data.find("AUTH "):]

            if not data.startswith("AUTH "):
                log_event(f"PROTOCOL VIOLATION: Malformed authentication string from {ip}")
                if record_failed_login(ip):
                    try:
                        client_socket.sendall(b"ERROR: Too many failed login attempts. IP blocked.")
                        client_socket.shutdown(socket.SHUT_WR)
                    except Exception:
                        pass
                    time.sleep(0.5)
                    client_socket.close()
                    return
                else:
                    client_socket.sendall(b"ERROR: Invalid protocol. Please authenticate first.")
                continue

            parts = data.split(maxsplit=2)
            if len(parts) < 3:
                if record_failed_login(ip):
                    try:
                        client_socket.sendall(b"ERROR: Too many failed login attempts. IP blocked.")
                        client_socket.shutdown(socket.SHUT_WR)
                    except Exception:
                        pass
                    time.sleep(0.5)
                    client_socket.close()
                    return
                else:
                    client_socket.sendall(b"ERROR: Invalid credentials format. Usage: AUTH <username> <password>")
                continue

            _, input_username, input_password = parts
            input_username = input_username.strip()
            input_password = input_password.strip()

            if not input_username.isalnum() or len(input_username) < 3 or len(input_username) > 15:
                if record_failed_login(ip):
                    try:
                        client_socket.sendall(b"ERROR: Too many failed login attempts. IP blocked.")
                        client_socket.shutdown(socket.SHUT_WR)
                    except Exception:
                        pass
                    time.sleep(0.5)
                    client_socket.close()
                    return
                else:
                    client_socket.sendall(b"ERROR: Invalid username syntax. Must be alphanumeric and 3-15 chars.")
                continue

            if not input_password:
                if record_failed_login(ip):
                    try:
                        client_socket.sendall(b"ERROR: Too many failed login attempts. IP blocked.")
                        client_socket.shutdown(socket.SHUT_WR)
                    except Exception:
                        pass
                    time.sleep(0.5)
                    client_socket.close()
                    return
                else:
                    client_socket.sendall(b"ERROR: Password cannot be empty.")
                continue

            hashed_input = hashlib.sha256(input_password.encode()).hexdigest()

            with lock:
                if input_username in active_usernames:
                    client_socket.sendall(b"ERROR: This account is already logged in.")
                    log_event(f"AUTH FAILED: Duplicate login prevention for '{input_username}' from {ip}")
                    continue

            with lock:
                if input_username not in user_db:
                    user_db[input_username] = hashed_input
                    save_user_database(user_db)
                    log_event(f"REGISTRATION: Dynamically registered new user '{input_username}' from {ip}")

            if user_db[input_username] == hashed_input:
                authenticated = True
                username = input_username
                with lock:
                    active_clients[client_socket] = username
                    active_usernames.add(username)
                    if ip in failed_login_attempts:
                        failed_login_attempts[ip] = 0
                
                client_socket.sendall(b"AUTH_SUCCESS")
                log_event(f"AUTH SUCCESS: User '{username}' authenticated successfully from {ip}")
                broadcast(f"\n[SYSTEM]: {username} has joined the workspace.", client_socket)
            else:
                log_event(f"AUTH FAILED: Invalid credentials for '{input_username}' from {ip}")
                
                if record_failed_login(ip):
                    try:
                        
                        client_socket.sendall(b"ERROR: Too many failed login attempts. IP blocked.")
                        client_socket.shutdown(socket.SHUT_WR)
                    except Exception:
                        pass
                    time.sleep(0.5)
                    client_socket.close()
                    return
                else:
                    client_socket.sendall(b"ERROR: Invalid username or password.")

        while authenticated:
            try:
                client_socket.settimeout(1.0)
                data = client_socket.recv(MAX_MSG_SIZE).decode('utf-8')
                if not data:
                    break
                
                last_active = time.time()
                message = data.strip()
                
                if message == "LOGOUT":
                    log_event(f"SESSION: User '{username}' logged out gracefully.")
                    break
                
                if len(message.encode('utf-8')) > MAX_MSG_SIZE:
                    client_socket.sendall(b"ERROR: Message exceeds maximum payload limits.")
                    continue
                
                if message.startswith("/pm "):
                    parts = message.split(" ", 2)
                    if len(parts) >= 3:
                        target_user = parts[1]
                        pm_content = parts[2]
                        target_socket = None
                        
                        with lock:
                            for sock, name in active_clients.items():
                                if name == target_user:
                                    target_socket = sock
                                    break
                        
                        if target_socket:
                            try:
                                target_socket.sendall(f"[{username} (PM)]: {pm_content}\n".encode('utf-8'))
                                client_socket.sendall(f"[You (PM to {target_user})]: {pm_content}\n".encode('utf-8'))
                            except Exception:
                                client_socket.sendall(b"ERROR: Failed to deliver private message.\n")
                        else:
                            client_socket.sendall(f"ERROR: User '{target_user}' is offline.\n".encode('utf-8'))
                    else:
                        client_socket.sendall(b"ERROR: Invalid PM format. Use /pm <username> <message>\n")
                else:
                    broadcast(f"[{username}]: {message}", client_socket)
                    
            except socket.timeout:
                if time.time() - last_active > TIMEOUT_LIMIT:
                    try:
                        client_socket.sendall(b"ERROR: Session timed out due to inactivity.")
                        client_socket.shutdown(socket.SHUT_WR)
                    except Exception:
                        pass
                    log_event(f"SESSION: User '{username}' disconnected due to inactivity.")
                    break

    except Exception as e:
        log_event(f"ERROR: Connection exception occurred with {ip}. Details: {e}")
    finally:
        with lock:
            if client_socket in active_clients:
                del active_clients[client_socket]
            if username in active_usernames:
                active_usernames.remove(username)
        
        try:
            client_socket.close()
        except Exception:
            pass
            
        if authenticated:
            broadcast(f"\n[SYSTEM]: {username} has left the workspace.")

def main():
    load_user_database()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', PORT))
    server.listen(5)
    print(f"[SYSTEM READY] TCP Server running securely on 0.0.0.0:{PORT}")

    try:
        while True:
            client_socket, client_address = server.accept()
            threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[SYSTEM] Server shutting down.")
    finally:
        server.close()

if __name__ == "__main__":
    main()

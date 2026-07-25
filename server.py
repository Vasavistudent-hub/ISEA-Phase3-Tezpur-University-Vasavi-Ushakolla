import socket
import threading
import json
import hashlib
import time
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor

lock = threading.RLock()

def load_config(config_path="config.json"):
    default_config = {
        "server": {
            "host": "0.0.0.0",
            "port": 5000,
            "backlog": 15,
            "timeout": 300.0,
            "max_workers": 20
        },
        "security": {
            "max_msg_size": 1024,
            "block_duration": 30.0,
            "max_failed_attempts": 3
        }
    }
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=4)
        return default_config
    
    with open(config_path, "r") as f:
        return json.load(f)

config = load_config()
HOST = config.get("server", {}).get("host", "0.0.0.0")
PORT = config.get("server", {}).get("port", 5000)
BACKLOG = config.get("server", {}).get("backlog", 15)
TIMEOUT_LIMIT = config.get("server", {}).get("timeout", 300.0)
MAX_WORKERS = config.get("server", {}).get("max_workers", 20)

MAX_MSG_SIZE = config.get("security", {}).get("max_msg_size", 1024)
BLOCK_DURATION = config.get("security", {}).get("block_duration", 30.0)
MAX_FAILED_ATTEMPTS = config.get("security", {}).get("max_failed_attempts", 3)

active_clients = {}      
active_usernames = set()
failed_login_attempts = {}
blocked_ips = {}
server_running = True

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
            "trithi": hashlib.sha256("us1612".encode()).hexdigest(),
	    "YUVA": hashlib.sha256("pass4".encode()).hexdigest(),
	    "abhi": hashlib.sha256("pass5".encode()).hexdigest(),
	    "alica": hashlib.sha256("pass6".encode()).hexdigest(),
	    "honey": hashlib.sha256("pass7".encode()).hexdigest(),
	    "lisa": hashlib.sha256("pass8".encode()).hexdigest(),
	    "Libra": hashlib.sha256("pass9".encode()).hexdigest(),
	    "Leo": hashlib.sha256("pass10".encode()).hexdigest()	
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
        disconnected_clients = []
        for client_sock in list(active_clients.keys()):
            if client_sock != sender_socket:
                try:
                    client_sock.sendall(message.encode('utf-8'))
                except (socket.error, BrokenPipeError):
                    disconnected_clients.append(client_sock)
        for dead_sock in disconnected_clients:
            remove_client_socket(dead_sock)

def remove_client_socket(client_socket):
    with lock:
        if client_socket in active_clients:
            client_data = active_clients.pop(client_socket, {})
            username = client_data.get("username", "")
            if username and username in active_usernames:
                active_usernames.remove(username)
                broadcast(f"\n[SYSTEM]: {username} has left the workspace.")
            try:
                client_socket.close()
            except socket.error:
                pass

def handle_client(client_socket, client_address):
    global user_db, server_running
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
        
        while not authenticated and server_running:
            if is_blocked(ip):
                try:
                    client_socket.sendall(b"ERROR: IP temporarily blocked.")
                    client_socket.shutdown(socket.SHUT_WR)
                except Exception:
                    pass
                time.sleep(0.2)
                client_socket.close()
                return

            client_socket.settimeout(2.0)
            try:
                data = client_socket.recv(MAX_MSG_SIZE).decode('utf-8')
            except socket.timeout:
                continue
            except (socket.error, ConnectionResetError):
                return

            if not data:
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
                    try:
                        client_socket.sendall(b"ERROR: Invalid protocol. Please authenticate first.")
                    except socket.error:
                        return
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
                    try:
                        client_socket.sendall(b"ERROR: Invalid credentials format. Usage: AUTH <username> <password>")
                    except socket.error:
                        return
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
                    try:
                        client_socket.sendall(b"ERROR: Invalid username syntax. Must be alphanumeric and 3-15 chars.")
                    except socket.error:
                        return
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
                    try:
                        client_socket.sendall(b"ERROR: Password cannot be empty.")
                    except socket.error:
                        return
                continue

            hashed_input = hashlib.sha256(input_password.encode()).hexdigest()

            with lock:
                if input_username in active_usernames:
                    try:
                        client_socket.sendall(b"ERROR: This account is already logged in.")
                    except socket.error:
                        return
                    log_event(f"AUTH FAILED: Duplicate login prevention for '{input_username}' from {ip}")
                    continue

                if input_username not in user_db:
                    user_db[input_username] = hashed_input
                    save_user_database(user_db)
                    log_event(f"REGISTRATION: Dynamically registered new user '{input_username}' from {ip}")

            if user_db[input_username] == hashed_input:
                authenticated = True
                username = input_username
                last_active = time.time()
                with lock:
                    active_clients[client_socket] = {
                        "username": username,
                        "last_active": last_active
                    }
                    active_usernames.add(username)
                    if ip in failed_login_attempts:
                        failed_login_attempts[ip] = 0
                
                try:
                    client_socket.sendall(b"AUTH_SUCCESS")
                except socket.error:
                    remove_client_socket(client_socket)
                    return
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
                    try:
                        client_socket.sendall(b"ERROR: Invalid username or password.")
                    except socket.error:
                        return

        
        while authenticated and server_running:
            try:
                client_socket.settimeout(1.0)
                data = client_socket.recv(MAX_MSG_SIZE).decode('utf-8')
                if not data:
                    break
                
                last_active = time.time()
                with lock:
                    if client_socket in active_clients:
                        active_clients[client_socket]["last_active"] = last_active

                message = data.strip()
                
                if message == "LOGOUT":
                    log_event(f"SESSION: User '{username}' logged out gracefully.")
                    break
                
                if len(message.encode('utf-8')) > MAX_MSG_SIZE:
                    try:
                        client_socket.sendall(b"ERROR: Message exceeds maximum payload limits.")
                    except socket.error:
                        break
                    continue
                
                if message.startswith("/pm "):
                    parts = message.split(" ", 2)
                    if len(parts) >= 3:
                        target_user = parts[1]
                        pm_content = parts[2]
                        target_socket = None
                        
                        with lock:
                            for sock, info in active_clients.items():
                                if info.get("username") == target_user:
                                    target_socket = sock
                                    break
                        
                        if target_socket:
                            try:
                                target_socket.sendall(f"[{username} (PM)]: {pm_content}\n".encode('utf-8'))
                                client_socket.sendall(f"[You (PM to {target_user})]: {pm_content}\n".encode('utf-8'))
                            except Exception:
                                try:
                                    client_socket.sendall(b"ERROR: Failed to deliver private message.\n")
                                except socket.error:
                                    break
                        else:
                            try:
                                client_socket.sendall(f"ERROR: User '{target_user}' is offline.\n".encode('utf-8'))
                            except socket.error:
                                break
                    else:
                        try:
                            client_socket.sendall(b"ERROR: Invalid PM format. Use /pm <username> <message>\n")
                        except socket.error:
                            break
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
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                break

    except Exception as e:
        log_event(f"ERROR: Connection exception occurred with {ip}. Details: {e}")
    finally:
        remove_client_socket(client_socket)

def graceful_shutdown(server_socket, executor):
    global server_running
    server_running = False
    broadcast("[SYSTEM]: Server is shutting down.\n")
    with lock:
        for client_socket in list(active_clients.keys()):
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
                client_socket.close()
            except socket.error:
                pass
        active_clients.clear()
        active_usernames.clear()

    try:
        server_socket.close()
    except socket.error:
        pass

    executor.shutdown(wait=False)
    sys.exit(0)

def main():
    load_user_database()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
        server.listen(BACKLOG)
        server.settimeout(2.0)
        print(f"[SYSTEM READY] TCP Server running securely on {HOST}:{PORT}")
    except Exception as e:
        print(f"[CRITICAL] Could not start server: {e}")
        sys.exit(1)

    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    def signal_handler(sig, frame):
        graceful_shutdown(server, executor)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        while server_running:
            try:
                client_socket, client_address = server.accept()
                executor.submit(handle_client, client_socket, client_address)
            except socket.timeout:
                continue
            except Exception:
                if server_running:
                    pass
                break
    finally:
        graceful_shutdown(server, executor)

if __name__ == "__main__":
    main()

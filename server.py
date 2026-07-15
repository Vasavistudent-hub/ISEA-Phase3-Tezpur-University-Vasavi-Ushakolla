import socket
import threading


HOST = '0.0.0.0'  
PORT = 5000       

clients = {}

clients_lock = threading.Lock()

def broadcast(message, sender_socket=None):
    
    encoded_message = message.encode('utf-8')
    with clients_lock:
        for client in list(clients.keys()):
            if client != sender_socket:  
                try:
                    client.send(encoded_message)
                except Exception:
                    
                    remove_client(client)

def broadcast_user_list():
    
    with clients_lock:
        active_usernames = list(clients.values())
    
    
    user_payload = "USERS:" + ",".join(active_usernames)
    encoded_payload = user_payload.encode('utf-8')
    
    with clients_lock:
        for client in list(clients.keys()):
            try:
                client.send(encoded_payload)
            except Exception:
                remove_client(client)

def handle_private_message(sender_socket, sender_name, message_text):
    
    parts = message_text.split(' ', 2)
    if len(parts) < 3:
        try:
            sender_socket.send("[System Error]: Invalid private message format. Use /pm <username> <message>".encode('utf-8'))
        except:
            pass
        return

    recipient_name = parts[1].strip()
    private_msg = parts[2].strip()

    recipient_socket = None
    with clients_lock:
        for sock, name in clients.items():
            if name.lower() == recipient_name.lower():
                recipient_socket = sock
                break

    if recipient_socket:
        formatted_pm = f"[Private from {sender_name}]: {private_msg}"
        try:
            recipient_socket.send(formatted_pm.encode('utf-8'))
            
            sender_socket.send(f"[Private to {recipient_name}]: {private_msg}".encode('utf-8'))
        except Exception:
            remove_client(recipient_socket)
    else:
        try:
            sender_socket.send(f"[System Error]: User '{recipient_name}' is not online.".encode('utf-8'))
        except:
            pass

def remove_client(client_socket):
   
    username = None
    with clients_lock:
        if client_socket in clients:
            username = clients[client_socket]
            del clients[client_socket]
            try:
                client_socket.close()
            except:
                pass
                
    if username:
        print(f"[-] Connection closed with: {username}")
        
        broadcast(f"[System]: {username} has left the chat.")
        
        broadcast_user_list()

def handle_client(client_socket, addr):
   
    username = ""
    try:
        
        username = client_socket.recv(1024).decode('utf-8').strip()
        
        if not username:
            client_socket.close()
            return
            
        with clients_lock:
            
            if username in clients.values():
                username = f"{username}_{addr[1]}"
            clients[client_socket] = username

        print(f"[+] {username} connected from {addr[0]}:{addr[1]}")
        
        
        broadcast(f"[System]: {username} has joined the chat room.")
        
        
        broadcast_user_list()

        
        while True:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                break
            
            message = data.strip()
            
            
            if message.startswith("/pm "):
                handle_private_message(client_socket, username, message)
            else:
                
                formatted_message = f"<{username}>: {message}"
                broadcast(formatted_message, sender_socket=client_socket)
                
                client_socket.send(formatted_message.encode('utf-8'))

    except ConnectionResetError:
        pass
    except Exception as e:
        print(f"[Error] Handling client {username}: {e}")
    finally:
        remove_client(client_socket)

def start_server():
   
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(10)
        print(f"[*] Chat Server actively listening on {HOST}:{PORT}...")
    except Exception as e:
        print(f"[Critical Error] Bind failed: {e}")
        return

    while True:
        try:
            client_socket, addr = server_socket.accept()
            
            client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            client_thread.daemon = True
            client_thread.start()
        except KeyboardInterrupt:
            print("\n[*] Server shutting down.")
            break
        except Exception as e:
            print(f"[Error] Accepting connections: {e}")
            break

    server_socket.close()

if __name__ == "__main__":
    start_server()

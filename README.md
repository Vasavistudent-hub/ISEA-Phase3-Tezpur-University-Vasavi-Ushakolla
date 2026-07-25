# Assignment 8: Application Optimization, Scalability, and Reliability

**Program:** ISEA Phase III Networking Internship   
**Student Name:** Vasavi Ushakolla  
**Repository Structure:** Multi-Client Secure TCP Chat Application (`server.py`, `client_gui.py`, `config.json`)  

---

##  Project Overview
This project builds upon the Assignment 7 base architecture by systematically optimizing a multi-client secure TCP chat application. The primary focus is enhancing application **scalability**, **reliability**, **maintainability**, and **resource management** under simulated network conditions using **Mininet**.

---

##  Key Features & Optimizations

### 1. Scalability Enhancements
* **ThreadPoolExecutor:** Replaced unbounded individual thread spawning with a managed thread pool capped at 20 worker threads (`MAX_WORKERS = 20`) to eliminate context-switching overhead.
* **Non-Blocking Sockets:** Configured client handling sockets with non-blocking timeouts (`client_socket.settimeout(1.0)`) to ensure worker threads yield periodically during idle loops.
* **Thread-Safe Memory Management:** Utilized reentrant locks (`threading.RLock()`) across global client dictionaries and username tracking to prevent race conditions during concurrent client logins.

### 2. Reliability & Security Enhancements
* **Automatic Inactivity Timeouts:** The server dynamically tracks active session timestamps (`last_active`) and cleanly disconnects clients idle for longer than 300 seconds.
* **Auto-Reconnection Mechanism:** The client GUI features an exponential backoff auto-reconnect routine, attempting up to 3 automated reconnections before safely reverting to the login screen.
* **Graceful Server Shutdown:** Server captures `SIGINT` (`Ctrl+C`), broadcasts shutdown payloads to active clients, closes socket channels (`SHUT_RDWR`), and frees bound ports.
* **Brute-Force & IP Locking:** Tracks failed login attempts, automatically locking out offending IP addresses for 30 seconds after 3 consecutive authentication failures.

### 3. Configuration Management
* Decoupled all system constants and network bindings from core code files into an external **`config.json`** file for runtime parameter tuning.

---

##  Project Directory Structure

```text
├── server.py                   # Multi-threaded TCP chat server implementation
├── client_gui.py               # Tkinter-based secure chat client GUI
├── config.json                 # Externalized server, security, and client parameters
├── performance_results.csv     # Performance benchmarking dataset (Before vs After)
├── report.pdf                  # Comprehensive evaluation and technical report
├── handwritten_reflection.pdf  # Scanned physical reflection notes for Task 8
├── graphs/                     # Performance visual comparison charts (PNG)
│   ├── delay.png
│   ├── throughput.png
│   ├── cpu_usage.png
│   └── memory_usage.png
└── screenshots/                # Verification evidence and Wireshark packet captures
    ├── mininet_setup.png
    ├── 10_clients_connected.png
    ├── broadcast_and_pm.png
    ├── inactivity_timeout.png
    └── wireshark_handshake.png

```

---

##  Performance Summary (Before vs. After Optimization)

Evaluated inside a Mininet emulation environment (`sudo mn --topo single,11`) across concurrent client loads:

| Concurrent Clients | Optimization State | Avg Delay (ms) | Throughput (msg/sec) | CPU Usage (%) | Memory Usage (MB) |
| --- | --- | --- | --- | --- | --- |
| **5 Clients** | Before | 12.4 | 85.2 | 18.5% | 45.2 MB |
| **5 Clients** | After | **4.1** | **210.5** | **8.2%** | **28.4 MB** |
| **8 Clients** | Before | 28.6 | 110.1 | 35.4% | 72.1 MB |
| **8 Clients** | After | **6.8** | **340.8** | **12.1%** | **34.2 MB** |
| **10 Clients** | Before | 52.1 | 125.4 | 58.9% | 110.5 MB |
| **10 Clients** | After | **8.2** | **420.0** | **15.6%** | **39.1 MB** |

---

##  How to Run the Application

### 1. Launch Mininet Topology

```bash
sudo mn --topo single,11

```

Inside the Mininet CLI prompt, open xterm terminals for the server (`h1`) and clients (`h2` through `h11`):

```bash
xterm h1 h2 h3 h4 h5 h6 h7 h8 h9 h10 h11

```

### 2. Start the Server (`h1`)

```bash
python3 server.py

```

### 3. Start the Clients (`h2` to `h11`)

```bash
python3 client_gui.py

```

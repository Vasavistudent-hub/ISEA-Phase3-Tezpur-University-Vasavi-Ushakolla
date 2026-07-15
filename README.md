# Multi-Client GUI Chat Application over Mininet (Phase 3)

**Department:** Computer Science & Engineering, Tezpur University  
**Submitted By:** Vasavi Ushakolla  
**Roll Number:** 56

---

## 1. Project Overview
This repository contains a multi-client Desktop GUI chat application built using Python's `tkinter` library and standard TCP sockets. The system is designed to run in a simulated network topology inside **Mininet**, allowing multiple concurrent client hosts (`h2`, `h3`, `h4`, `h5`) to securely communicate through a centralized server host (`h1`) over Port 5000.

### Key Features
* **Multi-threaded Client Architecture:** A background receiver thread listens for incoming data without freezing the main GUI event loop.
* **Smart Stream Parsing:** Resolves standard TCP stream-merging behavior to keep the chat view clean and dynamically update the active user roster sidebar.
* **Private Messaging:** Route localized messages directly using `/pm <username> <message>`.
* **Validation Guards:** Prevents connection attempts with blank username configurations.

---

## 2. Directory Structure
```text
├── server.py             # Multi-threaded TCP Chat Server backend
├── client_gui.py         # Tkinter-based Desktop GUI Client application
├── ASSIGNMENT REPORT.pdf # Formatted, comprehensive phase 3 lab report
└── Screenshots/          # Folder containing network capturing and GUI test runs

```

---

## 3. Prerequisites

To run this application, make sure your Ubuntu environment has Mininet and Python's `tkinter` package installed:

```bash
# Update package list
sudo apt-get update

# Install python3-tk library for GUI support
sudo apt-get install python3-tk -y

```

---

## 4. How to Run the Project inside Mininet

### Step 1: Start the Mininet Topology

Open your primary Ubuntu terminal and run the following command to spin up a single-switch topology linking 5 hosts:

```bash
sudo mn --topo single,5

```

### Step 2: Launch Host Terminals

In the Mininet interactive CLI (`mininet>`), open graphical terminal windows (`xterm`) for the server host (`h1`) and your active clients (`h2`, `h3`, `h4`):

```bash
mininet> xterm h1 h2 h3 h4

```

### Step 3: Run the Server

Go to the **`h1` (Server)** terminal window, change directories to this project folder, and start the server:

```bash
python3 server.py

```

*The server will start listening on IP `10.0.0.1` at Port `5000`.*

### Step 4: Run the Clients

In your **`h2`, `h3`, and `h4` (Client)** terminal windows, launch the graphical client interface:

```bash
python3 client_gui.py

```

### Step 5: Connect and Interact

1. Enter your chosen **Username** in the input field and click **Connect**.
2. Type your message in the chat box and press **Send** to broadcast it to everyone.
3. Use the sidebar roster list to monitor active online users in real-time.
4. Send private messages to a specific online user using:
```text
/pm <username> <your message>

```



---

## 5. Network Traffic Analysis

You can easily trace packet exchanges using **Wireshark** on your loopback or `any` interface:

* **TCP Three-Way Handshake:** Captures `SYN` -> `SYN-ACK` -> `ACK` exchanges during connection setup.
* **Data Transmission:** Observes standard TCP data transfer payloads on port 5000 when chatting.
* **Connection Teardown:** Monitors the structured four-way handshake (`FIN-ACK` sequences) when a client closes their GUI window.

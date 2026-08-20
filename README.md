<div align="center">

# 🪟 Windows Arena AI

### Agent Middleware for Windows Control

**Let Arena AI agents see your screen, click, type, run commands, and manage files on your Windows PC.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078d4.svg)](https://microsoft.com/windows)

</div>

---

## 📖 What Is This?

**Windows Arena AI** is a middleware server that runs on your Windows PC and exposes a REST/WebSocket API. Arena AI agents (or any AI agent) can connect to this API to:

- 🖥️ **See your screen** — capture screenshots
- 🖱️ **Control the mouse** — click, drag, scroll, move
- ⌨️ **Control the keyboard** — type text, press keys, hotkeys
- 💻 **Execute commands** — run shell commands and get output
- 📁 **Browse files** — list directories, read/write files, search
- 🚀 **Manage programs** — launch apps, list/kill processes
- 🔒 **Stay secure** — approval notifications, audit logging, API keys

The server creates a **free tunnel** (Cloudflare or ngrok) so agents can reach your PC from anywhere — no port forwarding needed.

---

## ⚡ Quick Start (3 Steps)

### 1. Install

```bash
# Clone or download this repo, then:
pip install -r requirements.txt
```

Or just double-click `install.bat` on Windows.

### 2. Run

```bash
python main.py
```

Or double-click `start.bat`.

### 3. Connect

The server prints a URL. Give it to your Arena AI agent:

```
🌐 Tunnel: https://random-name.trycloudflare.com
```

The agent can now control your PC! 🎉

---

## 🔧 Installation (Detailed)

### Prerequisites

- **Windows 10/11**
- **Python 3.9+** — [Download](https://python.org/downloads/) (check "Add to PATH")

### Install Dependencies

```bash
pip install -r requirements.txt
```

<details>
<summary>📦 What gets installed</summary>

| Package | Purpose | Required? |
|---------|---------|-----------|
| `aiohttp` | HTTP/WebSocket server | ✅ Yes |
| `Pillow` | Image processing | For screenshots |
| `mss` | Fast screen capture | For screenshots |
| `pyautogui` | Mouse & keyboard control | For input |
| `pyperclip` | Clipboard (Unicode typing) | For non-ASCII text |
| `psutil` | Process management | For process listing |
| `pystray` | System tray icon | Optional |
| `win10toast` | Windows notifications | Optional |

</details>

### Install Cloudflare Tunnel (Free, No Account)

```bash
# Option A: winget
winget install Cloudflare.cloudflared

# Option B: chocolatey
choco install cloudflared

# Option C: Download from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
```

### Install ngrok (Alternative, Free Tier)

```bash
winget install ngrok.ngrok
# Then: ngrok config add-authtoken YOUR_TOKEN
```

---

## 🚀 Usage

### Basic Start

```bash
python main.py
```

### Command Line Options

```bash
python main.py --port 8080              # Custom port
python main.py --key mysecretkey         # Require API key
python main.py --unrestricted            # No approval prompts (⚠️)
python main.py --tunnel cloudflared      # Use Cloudflare tunnel
python main.py --tunnel ngrok            # Use ngrok tunnel
python main.py --no-tunnel               # Disable tunnels
python main.py --no-tray                 # No system tray icon
python main.py --settings                # Open settings GUI
```

### Settings GUI

```bash
python main.py --settings
```

Opens a window where you can configure everything visually.

---

## 🔒 Security

### Default Mode (Secure)

By default, Windows Arena AI is **secure**:

- ✅ **Read-only actions** (screenshots, file listing, process listing) are **auto-approved**
- ⚠️ **Write actions** (clicks, typing, file writes, command execution) show a **Windows notification** asking for your approval
- 📋 **All actions** are logged to `%APPDATA%\WindowsArenaAI\audit.jsonl`

### Unrestricted Mode

When enabled, the agent can do anything **without asking**. Enable via:

- CLI: `python main.py --unrestricted`
- Settings GUI: Toggle the checkbox
- API: `POST /api/settings {"unrestricted_mode": true}`
- System tray: Right-click → Toggle

> ⚠️ **Only enable unrestricted mode if you trust the agent completely.**

### API Key Authentication

Set an API key to prevent unauthorized access:

```bash
python main.py --key my-super-secret-key
```

Agents must include the key in requests:
```
Authorization: Bearer my-super-secret-key
```

Or as a query parameter: `?key=my-super-secret-key`

### Blocked Commands

These commands are always blocked regardless of mode:
- `format`, `del /s`, `rd /s`, `reg delete`, `bcdedit`

---

## 📡 API Reference

### Base URL

```
http://localhost:7770
```
Or via tunnel: `https://your-tunnel-url.com`

### Authentication

If API key is set, include in every request:
```
Authorization: Bearer YOUR_KEY
```

---

### 🖥️ System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API documentation (HTML) |
| `GET` | `/api/info` | System information |
| `GET` | `/api/settings` | Current settings |
| `POST` | `/api/settings` | Update settings |

### 📸 Screen

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/screen` | Capture screenshot (base64 JPEG) |
| `GET` | `/api/screen/info` | Monitor information |

### 💻 Commands

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/api/command` | `{"cmd": "dir"}` | Execute shell command |

### 🖱️ Mouse

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/api/mouse/click` | `{"x": 100, "y": 200}` | Click at position |
| `POST` | `/api/mouse/move` | `{"x": 100, "y": 200}` | Move cursor |
| `POST` | `/api/mouse/scroll` | `{"clicks": -5}` | Scroll wheel |
| `POST` | `/api/mouse/drag` | `{"x1":0,"y1":0,"x2":100,"y2":100}` | Drag |

### ⌨️ Keyboard

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/api/keyboard/type` | `{"text": "hello"}` | Type text |
| `POST` | `/api/keyboard/press` | `{"key": "enter"}` | Press key |
| `POST` | `/api/keyboard/hotkey` | `{"keys": ["ctrl","c"]}` | Key combo |

### 📁 Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/files/list?path=C:\\` | List directory |
| `GET` | `/api/files/drives` | List drives |
| `GET` | `/api/files/read?path=...` | Read file |
| `GET` | `/api/files/search?dir=...&pattern=*.txt` | Search files |
| `POST` | `/api/files/write` | Write file `{"path": "...", "content": "..."}` |
| `POST` | `/api/files/mkdir` | Create dir `{"path": "..."}` |
| `POST` | `/api/files/delete` | Delete `{"path": "..."}` |

### 🚀 Processes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/processes` | List processes |
| `GET` | `/api/processes?filter=chrome` | Filter by name |
| `POST` | `/api/processes/launch` | Launch `{"path": "app.exe"}` |
| `POST` | `/api/processes/kill` | Kill `{"pid": 1234}` |

### ✅ Approvals

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/approvals` | List pending approvals |
| `POST` | `/api/approvals/approve` | Approve `{"request_id": "..."}` or `{"all": true}` |
| `POST` | `/api/approvals/deny` | Deny `{"request_id": "..."}` or `{"all": true}` |

### 🌐 Tunnel

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/tunnel` | Tunnel status & URL |

---

## 🔌 WebSocket Protocol

For lower latency, connect via WebSocket:

```
ws://localhost:7770/ws
```

Send JSON messages:
```json
{"action": "command", "cmd": "dir"}
{"action": "screenshot"}
{"action": "click", "x": 100, "y": 200}
{"action": "type", "text": "hello"}
{"action": "hotkey", "keys": ["ctrl", "s"]}
{"action": "list_dir", "path": "C:\\"}
{"action": "read_file", "path": "C:\\file.txt"}
{"action": "launch", "path": "notepad.exe"}
{"action": "system_info"}
{"action": "mouse_pos"}
{"action": "screen_size"}
{"action": "scroll", "clicks": -3}
{"action": "press", "key": "enter"}
{"action": "drag", "x1": 0, "y1": 0, "x2": 100, "y2": 100}
{"action": "double_click", "x": 500, "y": 300}
{"action": "right_click", "x": 500, "y": 300}
{"action": "drives"}
{"action": "search", "dir": "C:\\", "pattern": "*.pdf"}
{"action": "file_info", "path": "C:\\file.txt"}
{"action": "processes", "filter": "chrome"}
{"action": "kill", "pid": 1234}
{"action": "write_file", "path": "...", "content": "..."}
{"action": "delete", "path": "..."}
{"action": "mkdir", "path": "..."}
```

---

## 🤖 For AI Agents

> **If you're an Arena AI agent**, read [`AGENT_PROTOCOL.md`](AGENT_PROTOCOL.md) for a concise guide on how to use this API.

### Quick Agent Workflow

```
1. GET  /api/info           → Understand the system
2. GET  /api/screen         → See what's on screen
3. POST /api/mouse/click    → Click on something
4. POST /api/keyboard/type  → Type text
5. POST /api/command        → Run a command
6. GET  /api/files/list     → Browse files
7. POST /api/processes/launch → Open a program
8. GET  /api/screen         → See the result
```

---

## 📁 Project Structure

```
windows-arena-ai/
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
├── install.bat             # Windows installer
├── start.bat               # Quick start script
├── README.md               # This file
├── AGENT_PROTOCOL.md       # Guide for AI agents
├── LICENSE                 # MIT License
└── src/
    ├── __init__.py
    ├── config.py           # Settings management
    ├── logger.py           # Logging & audit trail
    ├── server.py           # HTTP/WebSocket server
    ├── commands.py         # Shell command execution
    ├── screen.py           # Screen capture
    ├── input_control.py    # Mouse & keyboard control
    ├── filesystem.py       # File system operations
    ├── processes.py        # Process management
    ├── notifications.py    # Approval notifications
    ├── tunnel.py           # Cloudflare/ngrok tunnels
    ├── tray.py             # System tray icon
    └── gui.py              # Settings GUI
```

---

## ⚙️ Configuration

Settings are stored at `%APPDATA%\WindowsArenaAI\config.json`:

```json
{
  "host": "0.0.0.0",
  "port": 7770,
  "api_key": "",
  "unrestricted_mode": false,
  "require_approval": true,
  "approval_timeout_sec": 60,
  "tunnel_provider": "cloudflared",
  "screen_quality": 60,
  "screen_scale": 0.75,
  "max_command_timeout_sec": 30
}
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `aiohttp not found` | `pip install aiohttp` |
| `mss not found` | `pip install Pillow mss` |
| `pyautogui not found` | `pip install pyautogui` |
| Tunnel not starting | Install cloudflared: `winget install Cloudflare.cloudflared` |
| Screen capture fails | Run as administrator, or check if another app is blocking |
| Mouse/keyboard not working | Some games/apps block simulated input — run as admin |
| Port already in use | `python main.py --port 8080` |
| Unicode typing fails | `pip install pyperclip` |

---

## 📜 License

MIT License — see [LICENSE](LICENSE).

---

<div align="center">

**Made for [Arena AI](https://arena.ai) agents** 🤖

*Give your AI agent hands and eyes.*

</div>

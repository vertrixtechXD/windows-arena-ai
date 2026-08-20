# 🤖 Agent Protocol — How to Use Windows Arena AI

> **This document is written for AI agents.** If you're an Arena AI agent reading this, follow these instructions to control a Windows machine.

## Quick Start

1. The human has Windows Arena AI running on their Windows PC
2. They'll give you a URL like `https://xxxx.trycloudflare.com` or `http://192.168.1.x:7770`
3. All API calls go to that base URL
4. If an API key is set, include header: `Authorization: Bearer <key>`

## Step 1: Understand the System

```
GET /api/info
```

Returns: OS version, CPU, RAM, disk, hostname, Python version, unrestricted mode status.

## Step 2: See the Screen

```
GET /api/screen
```

Returns a base64-encoded JPEG screenshot. Decode it to see what's on the user's desktop.

```
GET /api/screen/info
```

Returns monitor layout (resolution, positions).

## Step 3: Execute Commands

```
POST /api/command
Content-Type: application/json

{"cmd": "dir C:\\Users"}
{"cmd": "ipconfig /all"}
{"cmd": "systeminfo"}
{"cmd": "tasklist | findstr chrome"}
```

Response:
```json
{
  "success": true,
  "stdout": "...",
  "stderr": "",
  "returncode": 0,
  "duration_sec": 0.123
}
```

## Step 4: Browse Files

```
GET /api/files/list?path=C:\\Users
GET /api/files/drives
GET /api/files/read?path=C:\\Users\\user\\file.txt
GET /api/files/search?dir=C:\\Users&pattern=*.docx
```

Write/create files:
```json
POST /api/files/write
{"path": "C:\\Users\\user\\Desktop\\note.txt", "content": "Hello from AI"}

POST /api/files/mkdir
{"path": "C:\\Users\\user\\Desktop\\new_folder"}

POST /api/files/delete
{"path": "C:\\Users\\user\\Desktop\\old_file.txt"}
```

## Step 5: Control the Mouse

```json
POST /api/mouse/click
{"x": 500, "y": 300, "button": "left", "clicks": 1}

POST /api/mouse/click
{"x": 500, "y": 300, "button": "right"}

POST /api/mouse/move
{"x": 800, "y": 400}

POST /api/mouse/scroll
{"clicks": -5, "x": 500, "y": 300}

POST /api/mouse/drag
{"x1": 100, "y1": 100, "x2": 500, "y2": 400}
```

## Step 6: Control the Keyboard

```json
POST /api/keyboard/type
{"text": "Hello World"}

POST /api/keyboard/type
{"text": "Привет мир", "unicode": true}

POST /api/keyboard/press
{"key": "enter"}

POST /api/keyboard/hotkey
{"keys": ["ctrl", "c"]}

POST /api/keyboard/hotkey
{"keys": ["alt", "tab"]}

POST /api/keyboard/hotkey
{"keys": ["win", "r"]}
```

Common keys: `enter`, `tab`, `escape`, `backspace`, `delete`, `space`, `up`, `down`, `left`, `right`, `home`, `end`, `pageup`, `pagedown`, `f1`-`f12`, `win`.

## Step 7: Manage Programs

```json
GET /api/processes
GET /api/processes?filter=chrome

POST /api/processes/launch
{"path": "notepad.exe"}

POST /api/processes/launch
{"path": "C:\\Program Files\\app.exe", "args": "--flag"}

POST /api/processes/kill
{"pid": 1234}
```

## Step 8: Approvals

If the user has approval mode enabled, write/delete/kill/click actions will require approval.

```
GET /api/approvals          — See pending requests
POST /api/approvals/approve — {"request_id": "req-1-..."} or {"all": true}
POST /api/approvals/deny    — {"request_id": "req-1-..."} or {"all": true}
```

## WebSocket (Real-time)

Connect to `ws://HOST:PORT/ws` for lower latency:

```json
{"action": "command", "cmd": "dir"}
{"action": "screenshot"}
{"action": "click", "x": 100, "y": 200}
{"action": "type", "text": "hello"}
{"action": "hotkey", "keys": ["ctrl", "s"]}
{"action": "list_dir", "path": "C:\\"}
{"action": "launch", "path": "notepad.exe"}
{"action": "system_info"}
{"action": "mouse_pos"}
{"action": "screen_size"}
```

## Typical Workflow

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

## Important Notes

- **Coordinates are in pixels** from top-left corner (0,0)
- **Screenshots are JPEG** encoded as base64 — decode to view
- **Unicode typing** uses clipboard (Ctrl+V) — set `"unicode": true` for non-ASCII
- **pyautogui failsafe** — move mouse to top-left corner (0,0) to abort
- **All actions are logged** in the audit trail at `%APPDATA%\WindowsArenaAI\audit.jsonl`
- **File paths use Windows format**: `C:\\Users\\...` (double backslash in JSON)
- **Max request body**: 10 MB
- **Command timeout**: 30 seconds by default

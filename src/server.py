"""
Windows Arena AI — Main HTTP/WebSocket Server
The core API server that Arena AI agents connect to.
Provides REST endpoints and WebSocket for real-time control.
"""
import asyncio
import json
import time
import base64
import os
import sys
from pathlib import Path
from typing import Optional

# Web framework
try:
    from aiohttp import web
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

from .config import Settings
from .logger import setup_logger, audit_log
from .commands import CommandEngine
from .screen import ScreenCapture
from .input_control import InputController
from .filesystem import FilesystemManager
from .processes import ProcessManager
from .notifications import NotificationManager
from .tunnel import TunnelManager


class ArenaServer:
    """Main server that exposes the Windows control API."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.load()
        self.logger = setup_logger(self.settings)

        # Initialize modules
        self.notifications = NotificationManager(self.settings, self.logger)
        self.commands = CommandEngine(self.settings, self.logger, self.notifications.request_approval)
        self.screen = ScreenCapture(self.settings, self.logger)
        self.input = InputController(self.settings, self.logger, self.notifications.request_approval)
        self.filesystem = FilesystemManager(self.settings, self.logger, self.notifications.request_approval)
        self.processes = ProcessManager(self.settings, self.logger, self.notifications.request_approval)
        self.tunnel = TunnelManager(self.settings, self.logger)

        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._start_time = time.time()

    def _check_auth(self, request: web.Request) -> bool:
        """Check API key authentication."""
        if not self.settings.api_key:
            return True  # No key configured = open access (local use)
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:] == self.settings.api_key
        key = request.query.get("key", "")
        return key == self.settings.api_key

    def _json_response(self, data: dict, status: int = 200) -> web.Response:
        return web.json_response(data, status=status, content_type="application/json")

    def _unauthorized(self) -> web.Response:
        return self._json_response({"error": "Unauthorized. Provide API key via Authorization: Bearer <key> header or ?key= param."}, 401)

    # ─── Route Handlers ───────────────────────────────────────────────

    async def handle_index(self, request: web.Request) -> web.Response:
        """API documentation / landing page."""
        if not self._check_auth(request):
            return self._unauthorized()

        uptime = int(time.time() - self._start_time)
        html = f"""<!DOCTYPE html>
<html><head><title>Windows Arena AI</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #0a0a0f; color: #e0e0e0; padding: 40px; max-width: 900px; margin: auto; }}
  h1 {{ color: #00d4ff; }} h2 {{ color: #ff6b6b; margin-top: 30px; }}
  code {{ background: #1a1a2e; padding: 2px 8px; border-radius: 4px; color: #00ff88; }}
  pre {{ background: #1a1a2e; padding: 16px; border-radius: 8px; overflow-x: auto; }}
  .endpoint {{ background: #12121f; border-left: 3px solid #00d4ff; padding: 12px; margin: 10px 0; border-radius: 4px; }}
  .method {{ font-weight: bold; color: #00ff88; }}
  .status {{ color: #00ff88; }}
  a {{ color: #00d4ff; }}
</style></head><body>
<h1>🪟 Windows Arena AI</h1>
<p class="status">✅ Server running | Uptime: {uptime}s | Unrestricted: {'ON ⚠️' if self.settings.unrestricted_mode else 'OFF 🔒'}</p>

<h2>📡 API Endpoints</h2>

<div class="endpoint"><span class="method">GET</span> <code>/api/info</code> — System information</div>
<div class="endpoint"><span class="method">POST</span> <code>/api/command</code> — Execute shell command <code>{{"cmd": "dir"}}</code></div>
<div class="endpoint"><span class="method">GET</span> <code>/api/screen</code> — Capture screenshot (base64 JPEG)</div>
<div class="endpoint"><span class="method">GET</span> <code>/api/screen/info</code> — Monitor information</div>
<div class="endpoint"><span class="method">POST</span> <code>/api/mouse/click</code> — Click <code>{{"x": 100, "y": 200}}</code></div>
<div class="endpoint"><span class="method">POST</span> <code>/api/mouse/move</code> — Move mouse <code>{{"x": 100, "y": 200}}</code></div>
<div class="endpoint"><span class="method">POST</span> <code>/api/mouse/scroll</code> — Scroll <code>{{"clicks": -3}}</code></div>
<div class="endpoint"><span class="method">POST</span> <code>/api/mouse/drag</code> — Drag <code>{{"x1":0,"y1":0,"x2":100,"y2":100}}</code></div>
<div class="endpoint"><span class="method">POST</span> <code>/api/keyboard/type</code> — Type text <code>{{"text": "hello"}}</code></div>
<div class="endpoint"><span class="method">POST</span> <code>/api/keyboard/press</code> — Press key <code>{{"key": "enter"}}</code></div>
<div class="endpoint"><span class="method">POST</span> <code>/api/keyboard/hotkey</code> — Hotkey <code>{{"keys": ["ctrl","c"]}}</code></div>
<div class="endpoint"><span class="method">GET</span> <code>/api/files/list?path=C:\\</code> — List directory</div>
<div class="endpoint"><span class="method">GET</span> <code>/api/files/read?path=C:\\file.txt</code> — Read file</div>
<div class="endpoint"><span class="method">POST</span> <code>/api/files/write</code> — Write file <code>{{"path": "...", "content": "..."}}</code></div>
<div class="endpoint"><span class="method">POST</span> <code>/api/files/delete</code> — Delete file/dir</div>
<div class="endpoint"><span class="method">POST</span> <code>/api/files/mkdir</code> — Create directory</div>
<div class="endpoint"><span class="method">GET</span> <code>/api/files/drives</code> — List drives</div>
<div class="endpoint"><span class="method">GET</span> <code>/api/files/search?dir=C:\\&pattern=*.txt</code> — Search files</div>
<div class="endpoint"><span class="method">GET</span> <code>/api/processes</code> — List processes</div>
<div class="endpoint"><span class="method">POST</span> <code>/api/processes/launch</code> — Launch program</div>
<div class="endpoint"><span class="method">POST</span> <code>/api/processes/kill</code> — Kill process <code>{{"pid": 1234}}</code></div>
<div class="endpoint"><span class="method">GET</span> <code>/api/approvals</code> — List pending approvals</div>
<div class="endpoint"><span class="method">POST</span> <code>/api/approvals/approve</code> — Approve request</div>
<div class="endpoint"><span class="method">POST</span> <code>/api/approvals/deny</code> — Deny request</div>
<div class="endpoint"><span class="method">GET</span> <code>/api/tunnel</code> — Tunnel status</div>
<div class="endpoint"><span class="method">GET</span> <code>/api/settings</code> — Current settings</div>
<div class="endpoint"><span class="method">POST</span> <code>/api/settings</code> — Update settings</div>
<div class="endpoint"><span class="method">GET</span> <code>/ws</code> — WebSocket for real-time control</div>

<h2>🔌 WebSocket Protocol</h2>
<pre>
// Connect: ws://HOST:7770/ws
// Send JSON messages:
{{"action": "command", "cmd": "dir"}}
{{"action": "screenshot"}}
{{"action": "click", "x": 100, "y": 200}}
{{"action": "type", "text": "hello world"}}
{{"action": "hotkey", "keys": ["alt", "tab"]}}
{{"action": "list_dir", "path": "C:\\\\"}}
{{"action": "read_file", "path": "C:\\\\file.txt"}}
{{"action": "launch", "path": "notepad.exe"}}
{{"action": "mouse_move", "x": 500, "y": 300}}
{{"action": "scroll", "clicks": -5}}
{{"action": "system_info"}}
</pre>

<h2>📖 For Arena AI Agents</h2>
<p>To use this Windows machine, make HTTP requests to the endpoints above.
Start with <code>GET /api/info</code> to understand the system, then use
<code>POST /api/command</code> for shell commands, <code>GET /api/screen</code>
to see the desktop, and <code>POST /api/mouse/click</code> / <code>/api/keyboard/type</code>
to interact with GUI applications.</p>
<p>All actions are logged to the audit trail. Non-read-only actions require
user approval unless unrestricted mode is enabled.</p>
</body></html>"""
        return web.Response(text=html, content_type="text/html")

    async def handle_info(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        info = await self.processes.get_system_info()
        info["server_uptime_sec"] = int(time.time() - self._start_time)
        info["unrestricted_mode"] = self.settings.unrestricted_mode
        info["tunnel_url"] = self.tunnel.tunnel_url
        info["version"] = "1.0.0"
        return self._json_response(info)

    async def handle_command(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        cmd = data.get("cmd", "")
        cwd = data.get("cwd")
        timeout = data.get("timeout")
        result = await self.commands.execute(cmd, cwd=cwd, timeout=timeout)
        return self._json_response(result)

    async def handle_screenshot(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        monitor = int(request.query.get("monitor", "0"))
        result = self.screen.capture_screen(monitor=monitor)
        return self._json_response(result)

    async def handle_screen_info(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        return self._json_response(self.screen.get_screen_info())

    async def handle_mouse_click(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        result = await self.input.mouse_click(
            x=data["x"], y=data["y"],
            button=data.get("button", "left"),
            clicks=data.get("clicks", 1),
        )
        return self._json_response(result)

    async def handle_mouse_move(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        result = await self.input.mouse_move(data["x"], data["y"])
        return self._json_response(result)

    async def handle_mouse_scroll(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        result = await self.input.mouse_scroll(
            clicks=data["clicks"],
            x=data.get("x"), y=data.get("y"),
        )
        return self._json_response(result)

    async def handle_mouse_drag(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        result = await self.input.mouse_drag(data["x1"], data["y1"], data["x2"], data["y2"])
        return self._json_response(result)

    async def handle_keyboard_type(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        text = data.get("text", "")
        unicode_mode = data.get("unicode", False)
        if unicode_mode or not text.isascii():
            result = await self.input.type_unicode(text)
        else:
            result = await self.input.type_text(text, interval=data.get("interval", 0.02))
        return self._json_response(result)

    async def handle_keyboard_press(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        result = await self.input.press_key(data["key"])
        return self._json_response(result)

    async def handle_keyboard_hotkey(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        result = await self.input.hotkey(*data["keys"])
        return self._json_response(result)

    async def handle_files_list(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        path = request.query.get("path", "C:\\")
        show_hidden = request.query.get("hidden", "false").lower() == "true"
        result = await self.filesystem.list_dir(path, show_hidden=show_hidden)
        return self._json_response(result)

    async def handle_files_read(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        path = request.query.get("path", "")
        max_bytes = int(request.query.get("max_bytes", str(1024 * 100)))
        result = await self.filesystem.read_file(path, max_bytes=max_bytes)
        return self._json_response(result)

    async def handle_files_write(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        result = await self.filesystem.write_file(data["path"], data["content"])
        return self._json_response(result)

    async def handle_files_delete(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        result = await self.filesystem.delete_file(data["path"])
        return self._json_response(result)

    async def handle_files_mkdir(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        result = await self.filesystem.create_dir(data["path"])
        return self._json_response(result)

    async def handle_files_drives(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        result = await self.filesystem.get_drives()
        return self._json_response(result)

    async def handle_files_search(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        directory = request.query.get("dir", "C:\\")
        pattern = request.query.get("pattern", "*")
        max_results = int(request.query.get("max", "50"))
        result = await self.filesystem.search_files(directory, pattern, max_results)
        return self._json_response(result)

    async def handle_processes_list(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        filter_name = request.query.get("filter")
        result = await self.processes.list_processes(filter_name=filter_name)
        return self._json_response(result)

    async def handle_processes_launch(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        result = await self.processes.launch_program(data["path"], data.get("args", ""), data.get("cwd"))
        return self._json_response(result)

    async def handle_processes_kill(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        result = await self.processes.kill_process(data["pid"])
        return self._json_response(result)

    async def handle_approvals_list(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        return self._json_response({"success": True, "pending": self.notifications.get_pending()})

    async def handle_approvals_approve(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        req_id = data.get("request_id")
        if req_id:
            ok = self.notifications.approve_request(req_id)
            return self._json_response({"success": ok})
        elif data.get("all"):
            self.notifications.approve_all()
            return self._json_response({"success": True, "action": "approved_all"})
        return self._json_response({"error": "Provide request_id or {\"all\": true}"}, 400)

    async def handle_approvals_deny(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        req_id = data.get("request_id")
        if req_id:
            ok = self.notifications.deny_request(req_id)
            return self._json_response({"success": ok})
        elif data.get("all"):
            self.notifications.deny_all()
            return self._json_response({"success": True, "action": "denied_all"})
        return self._json_response({"error": "Provide request_id or {\"all\": true}"}, 400)

    async def handle_tunnel_status(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        return self._json_response(self.tunnel.get_status())

    async def handle_settings_get(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        from dataclasses import asdict
        return self._json_response(asdict(self.settings))

    async def handle_settings_update(self, request: web.Request) -> web.Response:
        if not self._check_auth(request):
            return self._unauthorized()
        data = await request.json()
        self.settings.update(**data)
        return self._json_response({"success": True, "settings": {k: getattr(self.settings, k) for k in data if hasattr(self.settings, k)}})

    # ─── WebSocket Handler ─────────────────────────────────────────────

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)

        if not self._check_auth(request):
            await ws.send_json({"error": "Unauthorized"})
            await ws.close()
            return ws

        self.logger.info("WebSocket client connected")
        await ws.send_json({"type": "connected", "message": "Windows Arena AI WebSocket ready", "version": "1.0.0"})

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        result = await self._handle_ws_action(data)
                        await ws.send_json(result)
                    except json.JSONDecodeError:
                        await ws.send_json({"error": "Invalid JSON"})
                    except Exception as e:
                        await ws.send_json({"error": str(e)})
                elif msg.type == web.WSMsgType.ERROR:
                    self.logger.error(f"WebSocket error: {ws.exception()}")
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")

        self.logger.info("WebSocket client disconnected")
        return ws

    async def _handle_ws_action(self, data: dict) -> dict:
        """Route WebSocket action to the appropriate handler."""
        action = data.get("action", "")

        if action == "command":
            return await self.commands.execute(data.get("cmd", ""), cwd=data.get("cwd"), timeout=data.get("timeout"))
        elif action == "screenshot":
            return self.screen.capture_screen(monitor=data.get("monitor", 0))
        elif action == "screen_info":
            return self.screen.get_screen_info()
        elif action == "click":
            return await self.input.mouse_click(data["x"], data["y"], data.get("button", "left"), data.get("clicks", 1))
        elif action == "double_click":
            return await self.input.mouse_double_click(data["x"], data["y"])
        elif action == "right_click":
            return await self.input.mouse_right_click(data["x"], data["y"])
        elif action == "mouse_move":
            return await self.input.mouse_move(data["x"], data["y"])
        elif action == "scroll":
            return await self.input.mouse_scroll(data["clicks"], data.get("x"), data.get("y"))
        elif action == "drag":
            return await self.input.mouse_drag(data["x1"], data["y1"], data["x2"], data["y2"])
        elif action == "type":
            text = data.get("text", "")
            if data.get("unicode") or not text.isascii():
                return await self.input.type_unicode(text)
            return await self.input.type_text(text)
        elif action == "press":
            return await self.input.press_key(data["key"])
        elif action == "hotkey":
            return await self.input.hotkey(*data["keys"])
        elif action == "key_down":
            return await self.input.key_down(data["key"])
        elif action == "key_up":
            return await self.input.key_up(data["key"])
        elif action == "list_dir":
            return await self.filesystem.list_dir(data.get("path", "C:\\"), data.get("hidden", False))
        elif action == "read_file":
            return await self.filesystem.read_file(data["path"], data.get("max_bytes", 102400))
        elif action == "write_file":
            return await self.filesystem.write_file(data["path"], data["content"])
        elif action == "delete":
            return await self.filesystem.delete_file(data["path"])
        elif action == "mkdir":
            return await self.filesystem.create_dir(data["path"])
        elif action == "drives":
            return await self.filesystem.get_drives()
        elif action == "search":
            return await self.filesystem.search_files(data.get("dir", "C:\\"), data.get("pattern", "*"), data.get("max", 50))
        elif action == "file_info":
            return await self.filesystem.get_file_info(data["path"])
        elif action == "processes":
            return await self.processes.list_processes(data.get("filter"))
        elif action == "launch":
            return await self.processes.launch_program(data["path"], data.get("args", ""), data.get("cwd"))
        elif action == "kill":
            return await self.processes.kill_process(data["pid"])
        elif action == "system_info":
            return await self.processes.get_system_info()
        elif action == "mouse_pos":
            return self.input.get_mouse_position()
        elif action == "screen_size":
            return self.input.get_screen_size()
        elif action == "approvals":
            return {"success": True, "pending": self.notifications.get_pending()}
        elif action == "approve":
            return {"success": self.notifications.approve_request(data.get("request_id", ""))}
        elif action == "deny":
            return {"success": self.notifications.deny_request(data.get("request_id", ""))}
        elif action == "approve_all":
            self.notifications.approve_all()
            return {"success": True}
        elif action == "deny_all":
            self.notifications.deny_all()
            return {"success": True}
        else:
            return {"error": f"Unknown action: {action}"}

    # ─── Server Lifecycle ──────────────────────────────────────────────

    def _build_app(self) -> web.Application:
        app = web.Application(client_max_size=10 * 1024 * 1024)  # 10MB max body

        # CORS middleware
        @web.middleware
        async def cors_middleware(request, handler):
            if request.method == "OPTIONS":
                response = web.Response()
            else:
                try:
                    response = await handler(request)
                except web.HTTPException as ex:
                    response = ex
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

        app = web.Application(client_max_size=10 * 1024 * 1024, middlewares=[cors_middleware])

        # Routes
        app.router.add_get("/", self.handle_index)
        app.router.add_get("/api/info", self.handle_info)
        app.router.add_post("/api/command", self.handle_command)
        app.router.add_get("/api/screen", self.handle_screenshot)
        app.router.add_get("/api/screen/info", self.handle_screen_info)
        app.router.add_post("/api/mouse/click", self.handle_mouse_click)
        app.router.add_post("/api/mouse/move", self.handle_mouse_move)
        app.router.add_post("/api/mouse/scroll", self.handle_mouse_scroll)
        app.router.add_post("/api/mouse/drag", self.handle_mouse_drag)
        app.router.add_post("/api/keyboard/type", self.handle_keyboard_type)
        app.router.add_post("/api/keyboard/press", self.handle_keyboard_press)
        app.router.add_post("/api/keyboard/hotkey", self.handle_keyboard_hotkey)
        app.router.add_get("/api/files/list", self.handle_files_list)
        app.router.add_get("/api/files/read", self.handle_files_read)
        app.router.add_post("/api/files/write", self.handle_files_write)
        app.router.add_post("/api/files/delete", self.handle_files_delete)
        app.router.add_post("/api/files/mkdir", self.handle_files_mkdir)
        app.router.add_get("/api/files/drives", self.handle_files_drives)
        app.router.add_get("/api/files/search", self.handle_files_search)
        app.router.add_get("/api/processes", self.handle_processes_list)
        app.router.add_post("/api/processes/launch", self.handle_processes_launch)
        app.router.add_post("/api/processes/kill", self.handle_processes_kill)
        app.router.add_get("/api/approvals", self.handle_approvals_list)
        app.router.add_post("/api/approvals/approve", self.handle_approvals_approve)
        app.router.add_post("/api/approvals/deny", self.handle_approvals_deny)
        app.router.add_get("/api/tunnel", self.handle_tunnel_status)
        app.router.add_get("/api/settings", self.handle_settings_get)
        app.router.add_post("/api/settings", self.handle_settings_update)
        app.router.add_get("/ws", self.handle_websocket)

        return app

    async def start(self):
        """Start the server and tunnel."""
        if not HAS_AIOHTTP:
            print("ERROR: aiohttp not installed. Run: pip install aiohttp")
            sys.exit(1)

        self._app = self._build_app()
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.settings.host, self.settings.port)
        await site.start()

        self.logger.info(f"═══════════════════════════════════════════")
        self.logger.info(f"  Windows Arena AI Server v1.0.0")
        self.logger.info(f"  Listening on http://{self.settings.host}:{self.settings.port}")
        self.logger.info(f"  Unrestricted mode: {'ON ⚠️' if self.settings.unrestricted_mode else 'OFF 🔒'}")
        self.logger.info(f"═══════════════════════════════════════════")

        # Start tunnel
        if self.settings.tunnel_provider != "none":
            tunnel_result = self.tunnel.start(self.settings.port)
            if tunnel_result.get("success") and tunnel_result.get("url"):
                self.logger.info(f"  🌐 Tunnel: {tunnel_result['url']}")
            elif not tunnel_result.get("success"):
                self.logger.warning(f"  ⚠️ Tunnel failed: {tunnel_result.get('error')}")

        # Keep running
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await self.stop()

    async def stop(self):
        """Stop the server and tunnel."""
        self.tunnel.stop()
        if self._runner:
            await self._runner.cleanup()
        self.logger.info("Server stopped.")

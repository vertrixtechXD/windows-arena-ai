"""
Windows Arena AI — Window Manager
Find, focus, resize, move, minimize, maximize, close windows.
List all open windows with their titles and positions.
"""
import ctypes
import ctypes.wintypes
import subprocess
import time
import re
from typing import Optional, List
from .config import Settings
from .logger import audit_log

# Win32 constants
SW_RESTORE = 9
SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_HIDE = 0
SW_SHOW = 5
GW_OWNER = 4
GWL_STYLE = -16
WS_MINIMIZE = 0x20000000
WS_VISIBLE = 0x10000000

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def _get_window_text(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _is_window_visible(hwnd: int) -> bool:
    return bool(user32.IsWindowVisible(hwnd))


def _get_window_rect(hwnd: int) -> dict:
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return {
        "left": rect.left,
        "top": rect.top,
        "right": rect.right,
        "bottom": rect.bottom,
        "width": rect.right - rect.left,
        "height": rect.bottom - rect.top,
    }


def _get_window_process(hwnd: int) -> dict:
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    try:
        import psutil
        proc = psutil.Process(pid.value)
        return {"pid": pid.value, "name": proc.name(), "exe": proc.exe() if proc.exe() else ""}
    except Exception:
        return {"pid": pid.value, "name": "", "exe": ""}


class WindowManager:
    """Manage Windows application windows."""

    def __init__(self, settings: Settings, logger):
        self.settings = settings
        self.logger = logger

    async def list_windows(self, visible_only: bool = True, include_minimized: bool = True) -> dict:
        """List all open windows with titles, positions, and process info."""
        audit_log(self.settings, "list_windows", {})
        windows = []

        def enum_callback(hwnd, _):
            if visible_only and not _is_window_visible(hwnd):
                return True
            title = _get_window_text(hwnd)
            if not title or title in ("Default IME", "MSCTFIME UI", "DDE Server Window"]:
                return True
            if title == "Windows Arena AI":
                return True

            rect = _get_window_rect(hwnd)
            proc_info = _get_window_process(hwnd)
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            is_minimized = bool(style & WS_MINIMIZE)
            is_maximized = bool(style & 0x01000000)  # WS_MAXIMIZE

            if not include_minimized and is_minimized:
                return True

            windows.append({
                "hwnd": hwnd,
                "title": title,
                "rect": rect,
                "pid": proc_info["pid"],
                "process_name": proc_info["name"],
                "exe": proc_info.get("exe", ""),
                "is_minimized": is_minimized,
                "is_maximized": is_maximized,
                "is_foreground": hwnd == user32.GetForegroundWindow(),
            })
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
        user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

        return {"success": True, "windows": windows, "count": len(windows)}

    async def find_window(self, title_pattern: str, exact: bool = False) -> dict:
        """Find windows by title (supports regex pattern)."""
        audit_log(self.settings, "find_window", {"pattern": title_pattern})
        all_windows = await self.list_windows(visible_only=False, include_minimized=True)
        matches = []

        try:
            if exact:
                pattern = re.compile(re.escape(title_pattern), re.IGNORECASE)
            else:
                pattern = re.compile(title_pattern, re.IGNORECASE)
        except re.error:
            pattern = re.compile(re.escape(title_pattern), re.IGNORECASE)

        for w in all_windows.get("windows", []):
            if pattern.search(w["title"]):
                matches.append(w)

        return {"success": True, "pattern": title_pattern, "matches": matches, "count": len(matches)}

    async def focus_window(self, hwnd: int) -> dict:
        """Bring a window to the foreground."""
        audit_log(self.settings, "focus_window", {"hwnd": hwnd})
        try:
            # Restore if minimized
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.1)
            return {"success": True, "hwnd": hwnd, "title": _get_window_text(hwnd)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def focus_by_title(self, title_pattern: str) -> dict:
        """Find and focus a window by title pattern."""
        find_result = await self.find_window(title_pattern)
        matches = find_result.get("matches", [])
        if not matches:
            return {"success": False, "error": f"No window matching '{title_pattern}'"}
        return await self.focus_window(matches[0]["hwnd"])

    async def minimize_window(self, hwnd: int) -> dict:
        """Minimize a window."""
        audit_log(self.settings, "minimize_window", {"hwnd": hwnd})
        user32.ShowWindow(hwnd, SW_MINIMIZE)
        return {"success": True, "hwnd": hwnd, "action": "minimized"}

    async def maximize_window(self, hwnd: int) -> dict:
        """Maximize a window."""
        audit_log(self.settings, "maximize_window", {"hwnd": hwnd})
        user32.ShowWindow(hwnd, SW_MAXIMIZE)
        return {"success": True, "hwnd": hwnd, "action": "maximized"}

    async def restore_window(self, hwnd: int) -> dict:
        """Restore a window to its previous size."""
        audit_log(self.settings, "restore_window", {"hwnd": hwnd})
        user32.ShowWindow(hwnd, SW_RESTORE)
        return {"success": True, "hwnd": hwnd, "action": "restored"}

    async def close_window(self, hwnd: int) -> dict:
        """Close a window (sends WM_CLOSE)."""
        audit_log(self.settings, "close_window", {"hwnd": hwnd})
        title = _get_window_text(hwnd)
        user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE = 0x0010
        return {"success": True, "hwnd": hwnd, "title": title, "action": "close_sent"}

    async def resize_window(self, hwnd: int, width: int, height: int) -> dict:
        """Resize a window."""
        audit_log(self.settings, "resize_window", {"hwnd": hwnd, "w": width, "h": height})
        user32.MoveWindow(hwnd, 0, 0, width, height, True)
        return {"success": True, "hwnd": hwnd, "width": width, "height": height}

    async def move_window(self, hwnd: int, x: int, y: int) -> dict:
        """Move a window to a position."""
        audit_log(self.settings, "move_window", {"hwnd": hwnd, "x": x, "y": y})
        rect = _get_window_rect(hwnd)
        user32.MoveWindow(hwnd, x, y, rect["width"], rect["height"], True)
        return {"success": True, "hwnd": hwnd, "x": x, "y": y}

    async def set_window_geometry(self, hwnd: int, x: int, y: int, width: int, height: int) -> dict:
        """Set window position and size."""
        audit_log(self.settings, "set_window_geometry", {"hwnd": hwnd, "x": x, "y": y, "w": width, "h": height})
        user32.MoveWindow(hwnd, x, y, width, height, True)
        return {"success": True, "hwnd": hwnd, "x": x, "y": y, "width": width, "height": height}

    async def hide_window(self, hwnd: int) -> dict:
        """Hide a window (invisible but still running)."""
        audit_log(self.settings, "hide_window", {"hwnd": hwnd})
        user32.ShowWindow(hwnd, SW_HIDE)
        return {"success": True, "hwnd": hwnd, "action": "hidden"}

    async def show_window(self, hwnd: int) -> dict:
        """Show a hidden window."""
        audit_log(self.settings, "show_window", {"hwnd": hwnd})
        user32.ShowWindow(hwnd, SW_SHOW)
        return {"success": True, "hwnd": hwnd, "action": "shown"}

    async def get_foreground_window(self) -> dict:
        """Get info about the currently focused window."""
        hwnd = user32.GetForegroundWindow()
        title = _get_window_text(hwnd)
        rect = _get_window_rect(hwnd)
        proc = _get_window_process(hwnd)
        return {
            "success": True,
            "hwnd": hwnd,
            "title": title,
            "rect": rect,
            "pid": proc["pid"],
            "process_name": proc["name"],
        }

    async def screenshot_window(self, hwnd: int) -> dict:
        """Capture a screenshot of a specific window."""
        audit_log(self.settings, "screenshot_window", {"hwnd": hwnd})
        try:
            from PIL import Image
            import io, base64

            # Get window rect
            rect = _get_window_rect(hwnd)
            if rect["width"] <= 0 or rect["height"] <= 0:
                return {"success": False, "error": "Window has zero size (minimized?)"}

            # Use PrintWindow API
            hdc = user32.GetDC(hwnd)
            memdc = ctypes.windll.gdi32.CreateCompatibleDC(hdc)
            hbitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc, rect["width"], rect["height"])
            ctypes.windll.gdi32.SelectObject(memdc, hbitmap)

            # PrintWindow captures even partially obscured windows
            result = user32.PrintWindow(hwnd, memdc, 2)  # PW_RENDERFULLCONTENT = 2

            if result:
                # Convert to PIL Image
                bmp_info = ctypes.wintypes.BITMAPINFOHEADER()
                bmp_info.biSize = ctypes.sizeof(ctypes.wintypes.BITMAPINFOHEADER)
                bmp_info.biWidth = rect["width"]
                bmp_info.biHeight = -rect["height"]  # Top-down
                bmp_info.biPlanes = 1
                bmp_info.biBitCount = 32
                bmp_info.biCompression = 0  # BI_RGB

                buf_size = rect["width"] * rect["height"] * 4
                buf = ctypes.create_string_buffer(buf_size)
                ctypes.windll.gdi32.GetDIBits(memdc, hbitmap, 0, rect["height"], buf, ctypes.byref(bmp_info), 0)

                img = Image.frombuffer("RGBA", (rect["width"], rect["height"]), buf, "raw", "BGRA", 0, 1)
                img = img.convert("RGB")

                # Scale down
                scale = self.settings.screen_scale
                if scale < 1.0:
                    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)

                buf_out = io.BytesIO()
                img.save(buf_out, format="JPEG", quality=self.settings.screen_quality)
                frame = buf_out.getvalue()

                # Cleanup
                ctypes.windll.gdi32.DeleteObject(hbitmap)
                ctypes.windll.gdi32.DeleteDC(memdc)
                user32.ReleaseDC(hwnd, hdc)

                return {
                    "success": True,
                    "image_base64": base64.b64encode(frame).decode("ascii"),
                    "width": img.width,
                    "height": img.height,
                    "format": "jpeg",
                    "window_title": _get_window_text(hwnd),
                }
            else:
                ctypes.windll.gdi32.DeleteObject(hbitmap)
                ctypes.windll.gdi32.DeleteDC(memdc)
                user32.ReleaseDC(hwnd, hdc)
                return {"success": False, "error": "PrintWindow failed"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def tile_windows(self, hwnds: list, cols: int = 2) -> dict:
        """Tile multiple windows across the screen."""
        audit_log(self.settings, "tile_windows", {"hwnds": hwnds, "cols": cols})
        try:
            user32 = ctypes.windll.user32
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)

            rows = (len(hwnds) + cols - 1) // cols
            cell_w = screen_w // cols
            cell_h = screen_h // rows

            for i, hwnd in enumerate(hwnds):
                col = i % cols
                row = i // cols
                x = col * cell_w
                y = row * cell_h
                user32.MoveWindow(hwnd, x, y, cell_w, cell_h, True)

            return {"success": True, "tiled": len(hwnds), "cols": cols, "rows": rows}
        except Exception as e:
            return {"success": False, "error": str(e)}

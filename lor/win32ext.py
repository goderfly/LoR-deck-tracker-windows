"""
Win32 helpers that make the overlay behave like a real game HUD.

* ``WS_EX_NOACTIVATE``  - clicking the overlay never steals focus from the game.
* ``WS_EX_TRANSPARENT`` - click-through mode, clicks fall through to LoR.
* ``HWND_TOPMOST``     - keeps the panels above the fullscreen DirectX client.
"""

import ctypes

try:
    import win32con
    import win32gui
    HAS_WIN32 = True
except Exception:  # pragma: no cover - non Windows
    HAS_WIN32 = False
    win32con = win32gui = None

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000


def _hwnd(widget):
    try:
        return int(widget.winId())
    except Exception:
        return None


def enable_dpi_awareness():
    """Make the HUD crisp on high DPI displays."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def set_no_activate(widget, enabled=True):
    """Stop the window from taking keyboard focus (never interrupts the game)."""
    if not HAS_WIN32:
        return
    hwnd = _hwnd(widget)
    if not hwnd:
        return
    try:
        style = win32gui.GetWindowLong(hwnd, GWL_EXSTYLE)
        if enabled:
            style |= WS_EX_NOACTIVATE
        else:
            style &= ~WS_EX_NOACTIVATE
        win32gui.SetWindowLong(hwnd, GWL_EXSTYLE, style)
    except Exception:
        pass


def set_click_through(widget, enabled=True):
    """Enable or disable click-through (clicks pass to the game underneath)."""
    if not HAS_WIN32:
        return
    hwnd = _hwnd(widget)
    if not hwnd:
        return
    try:
        style = win32gui.GetWindowLong(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED
        if enabled:
            style |= WS_EX_TRANSPARENT
        else:
            style &= ~WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, GWL_EXSTYLE, style)
        win32gui.SetWindowPos(hwnd, None, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE |
                              win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED)
    except Exception:
        pass


def keep_topmost(widget):
    """Push the window above the game client (also works in borderless fullscreen)."""
    if not HAS_WIN32:
        return
    hwnd = _hwnd(widget)
    if not hwnd:
        return
    try:
        win32gui.SetWindowPos(
            hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
        )
    except Exception:
        pass


def hide_from_taskbar(widget):
    """Remove the window from the taskbar / alt-tab list."""
    if not HAS_WIN32:
        return
    hwnd = _hwnd(widget)
    if not hwnd:
        return
    try:
        style = win32gui.GetWindowLong(hwnd, GWL_EXSTYLE)
        style |= WS_EX_TOOLWINDOW
        style &= ~WS_EX_APPWINDOW
        win32gui.SetWindowLong(hwnd, GWL_EXSTYLE, style)
    except Exception:
        pass


def show_in_taskbar(widget):
    """Ensure the window appears on the Windows taskbar with an application button."""
    if not HAS_WIN32:
        return
    hwnd = _hwnd(widget)
    if not hwnd:
        return
    try:
        style = win32gui.GetWindowLong(hwnd, GWL_EXSTYLE)
        style &= ~WS_EX_TOOLWINDOW
        style |= WS_EX_APPWINDOW
        win32gui.SetWindowLong(hwnd, GWL_EXSTYLE, style)
    except Exception:
        pass

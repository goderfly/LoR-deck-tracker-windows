"""
Legends of Runeterra Deck Tracker
Primary executable entry point.

Handles process initialization, Windows AppUserModelID, DPI awareness,
uncaught exception logging, and application lifecycle.
"""

import argparse
import os
import sys
import time
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def install_exception_hook():
    """Install a global exception hook that writes fatal crashes to disk and alerts the user."""
    def excepthook(exctype, value, tb):
        err_msg = "".join(traceback.format_exception(exctype, value, tb))
        log_dir = os.path.join(os.environ.get("LOCALAPPDATA", BASE_DIR), "LoRDeckTracker")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "crash.log")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\nCRASH REPORT: {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}\n")
                f.write(err_msg)
        except Exception:
            pass

        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"LoR Deck Tracker encountered an unexpected error:\n\n{value}\n\nFull details written to:\n{log_file}",
                "LoR Deck Tracker - Error",
                0x10  # MB_ICONERROR
            )
        except Exception:
            pass
        sys.__excepthook__(exctype, value, tb)

    sys.excepthook = excepthook


def parse_args():
    parser = argparse.ArgumentParser(description="Legends of Runeterra Deck Tracker")
    parser.add_argument("--always-visible", action="store_true",
                        help="Force overlays visible even when outside match")
    parser.add_argument("--scale", type=float, default=None,
                        help="Override UI scale factor (e.g. 1.0, 1.25)")
    parser.add_argument("--reset-pos", action="store_true",
                        help="Reset overlay window coordinates to defaults")
    return parser.parse_args()


def main():
    install_exception_hook()

    from lor import win32ext
    win32ext.enable_dpi_awareness()

    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "LoR.DeckTracker.Community.v1")
    except Exception:
        pass

    from PyQt6 import QtCore, QtGui, QtWidgets
    from lor.manager import OverlayManager

    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        qapp = QtWidgets.QApplication(sys.argv)
    qapp.setStyle("Fusion")
    qapp.setQuitOnLastWindowClosed(False)

    # Global Hextech tooltip styling
    qapp.setStyleSheet("""
        QToolTip {
            background-color: #0A111D;
            color: #F0E6D2;
            border: 1px solid #C8AA6E;
            padding: 6px 10px;
            border-radius: 4px;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 11px;
        }
    """)

    icon_candidates = [
        os.path.join(BUNDLE_DIR, "data", "icons", "app_icon.ico"),
        os.path.join(BASE_DIR, "data", "icons", "app_icon.ico"),
        os.path.join(BUNDLE_DIR, "data", "icons", "app_icon.png"),
        os.path.join(BASE_DIR, "data", "icons", "app_icon.png"),
    ]
    for icp in icon_candidates:
        if os.path.exists(icp):
            qapp.setWindowIcon(QtGui.QIcon(icp))
            break

    args = parse_args()
    manager = OverlayManager()

    if args.always_visible:
        manager.settings["always_visible"] = True
        manager.apply_settings(manager.settings)
    if args.scale:
        manager.settings["scale"] = args.scale
        manager.apply_settings(manager.settings)
    if args.reset_pos:
        manager.reset_positions()

    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()

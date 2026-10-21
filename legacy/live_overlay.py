"""
Legends of Runeterra - Overlay Launcher.
Launches the dedicated PyQt6 multi-overlay system (Player Deck, Opponent Tracker, Settings),
with fallback to frameless Tkinter overlay if needed.
"""

import sys
import os

try:
    import pyqt_overlay
    def main():
        pyqt_overlay.main()
except ImportError:
    # Fallback to frameless Tkinter
    import tkinter as tk
    import requests
    from card_db import CardDatabase

    class FallbackFramelessOverlay:
        def __init__(self, root):
            self.root = root
            self.root.title("LoR Deck Tracker")
            self.root.overrideredirect(True) # Frameless!
            self.root.attributes("-topmost", True)
            self.root.attributes("-alpha", 0.94)
            self.root.configure(bg="#0c1017")
            
            screen_w = self.root.winfo_screenwidth()
            w, h = 320, 620
            self.root.geometry(f"{w}x{h}+{screen_w - w - 25}+60")

            # Header
            header = tk.Frame(self.root, bg="#1b2434", height=36)
            header.pack(fill=tk.X, side=tk.TOP)
            
            self.drag_x = 0
            self.drag_y = 0
            def on_down(e): self.drag_x, self.drag_y = e.x, e.y
            def on_drag(e):
                x = self.root.winfo_x() + (e.x - self.drag_x)
                y = self.root.winfo_y() + (e.y - self.drag_y)
                self.root.geometry(f"+{x}+{y}")
            
            header.bind("<Button-1>", on_down)
            header.bind("<B1-Motion>", on_drag)

            title = tk.Label(header, text="◆ LOR TRACKER", font=("Segoe UI", 10, "bold"), fg="#c89b3c", bg="#1b2434")
            title.pack(side=tk.LEFT, padx=10, pady=6)
            close = tk.Label(header, text="✕", font=("Segoe UI", 10, "bold"), fg="#94a3b8", bg="#1b2434", cursor="hand2")
            close.pack(side=tk.RIGHT, padx=10)
            close.bind("<Button-1>", lambda e: os._exit(0))

            self.status = tk.Label(self.root, text="Поиск игры...", font=("Segoe UI", 9), fg="#94a3b8", bg="#0c1017")
            self.status.pack(fill=tk.X, padx=10, pady=4)

    def main():
        root = tk.Tk()
        app = FallbackFramelessOverlay(root)
        root.mainloop()

if __name__ == "__main__":
    main()

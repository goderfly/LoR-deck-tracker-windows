"""
Native Windows Overlay for Legends of Runeterra.
Uses Tkinter with Win32 HWND_TOPMOST attributes to guarantee rendering
directly above DirectX / Unity game windows.
"""

import sys
import os
import threading
import time
import requests
import tkinter as tk
from tkinter import ttk

import win32gui
import win32con

from card_db import CardDatabase
from tracker_engine import LoRClient
from advisor_engine import get_threats_for_regions
from app import app

# Palette matching LoR
BG_COLOR = "#0c1017"
PANEL_BG = "#131b26"
CARD_BG = "#1a2536"
TEXT_COLOR = "#f0f4f8"
GOLD_COLOR = "#c89b3c"
BLUE_MANA = "#00b4d8"
RED_DANGER = "#ef4444"
MUTED_TEXT = "#94a3b8"

class NativeOverlayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LoR Deck Tracker")
        
        # Dimensions & position: floating on right side of screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = 330
        height = 600
        x = max(10, screen_w - width - 40)
        y = 60
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Windows Overlay properties
        self.root.configure(bg=BG_COLOR)
        self.root.attributes("-alpha", 0.93) # Sleek semi-transparency
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True) # Frameless HUD overlay look

        # Make it draggable
        self.drag_start_x = 0
        self.drag_start_y = 0

        self.setup_ui()
        self.ensure_topmost()

        # Polling thread
        self.running = True
        self.poll_thread = threading.Thread(target=self.poll_loop, daemon=True)
        self.poll_thread.start()

    def ensure_topmost(self):
        """Forces the window to stay on top of fullscreen/borderless DirectX games."""
        try:
            hwnd = int(self.root.frame(), 16)
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
            )
        except Exception:
            pass
        # Repeat every 2 seconds to beat game client focus grabs
        self.root.after(2000, self.ensure_topmost)

    def on_drag_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag_motion(self, event):
        deltax = event.x - self.drag_start_x
        deltay = event.y - self.drag_start_y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def setup_ui(self):
        # Header / Title Bar
        header = tk.Frame(self.root, bg="#1b2434", height=38)
        header.pack(fill=tk.X, side=tk.TOP)
        header.bind("<Button-1>", self.on_drag_start)
        header.bind("<B1-Motion>", self.on_drag_motion)

        title_lbl = tk.Label(header, text="◆ LOR COMPANION", font=("Segoe UI", 10, "bold"), fg=GOLD_COLOR, bg="#1b2434")
        title_lbl.pack(side=tk.LEFT, padx=10, pady=8)
        title_lbl.bind("<Button-1>", self.on_drag_start)
        title_lbl.bind("<B1-Motion>", self.on_drag_motion)

        # Close / Minimize buttons
        close_btn = tk.Label(header, text="✕", font=("Segoe UI", 10, "bold"), fg=MUTED_TEXT, bg="#1b2434", cursor="hand2")
        close_btn.pack(side=tk.RIGHT, padx=10)
        close_btn.bind("<Button-1>", lambda e: self.root.destroy())

        # Status Bar
        self.status_lbl = tk.Label(self.root, text="Поиск игры...", font=("Segoe UI", 9), fg=MUTED_TEXT, bg=BG_COLOR)
        self.status_lbl.pack(fill=tk.X, padx=10, pady=4)

        # Tab Selector
        tab_frame = tk.Frame(self.root, bg=BG_COLOR)
        tab_frame.pack(fill=tk.X, padx=10, pady=2)

        self.btn_deck = tk.Button(tab_frame, text="КОЛОДА", font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#38bdf8", bd=0, relief=tk.FLAT, command=lambda: self.switch_tab("deck"))
        self.btn_deck.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        self.btn_threats = tk.Button(tab_frame, text="УГРОЗЫ", font=("Segoe UI", 9, "bold"), bg="#0f172a", fg=MUTED_TEXT, bd=0, relief=tk.FLAT, command=lambda: self.switch_tab("threats"))
        self.btn_threats.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        self.btn_board = tk.Button(tab_frame, text="СТОЛ", font=("Segoe UI", 9, "bold"), bg="#0f172a", fg=MUTED_TEXT, bd=0, relief=tk.FLAT, command=lambda: self.switch_tab("board"))
        self.btn_board.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        self.current_tab = "deck"

        # Content Container (Scrollable canvas)
        self.content_frame = tk.Frame(self.root, bg=BG_COLOR)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Footer
        footer = tk.Frame(self.root, bg="#080b10", height=22)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer_lbl = tk.Label(footer, text="Always-On-Top Active | 127.0.0.1:21337", font=("Segoe UI", 8), fg="#475569", bg="#080b10")
        footer_lbl.pack(side=tk.LEFT, padx=8, pady=2)

    def switch_tab(self, tab):
        self.current_tab = tab
        for btn, name in [(self.btn_deck, "deck"), (self.btn_threats, "threats"), (self.btn_board, "board")]:
            if name == tab:
                btn.configure(bg="#1e293b", fg="#38bdf8")
            else:
                btn.configure(bg="#0f172a", fg=MUTED_TEXT)
        self.render_data(getattr(self, "last_data", None))

    def poll_loop(self):
        while self.running:
            try:
                r = requests.get("http://127.0.0.1:5000/api/state", timeout=1.0)
                if r.status_code == 200:
                    data = r.json()
                    self.root.after(0, self.render_data, data)
            except Exception:
                pass
            time.sleep(1.0)

    def render_data(self, data):
        self.last_data = data
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        if not data or data.get("status") == "offline":
            self.status_lbl.configure(text="LoR не запущен", fg=RED_DANGER)
            lbl = tk.Label(self.content_frame, text="Запусти Legends of Runeterra", font=("Segoe UI", 10), fg=MUTED_TEXT, bg=BG_COLOR)
            lbl.pack(pady=40)
            return

        if data.get("status") != "in_game":
            self.status_lbl.configure(text="В меню / лобби", fg=GOLD_COLOR)
            lbl = tk.Label(self.content_frame, text="Ожидание начала матча...", font=("Segoe UI", 10), fg=MUTED_TEXT, bg=BG_COLOR)
            lbl.pack(pady=40)
            return

        p_name = data.get("playerName", "Игрок")
        o_name = data.get("opponentName", "Оппонент")
        rem = data.get("totalRemaining", 0)
        self.status_lbl.configure(text=f"{p_name} vs {o_name} | Колода: {rem}", fg=GOLD_COLOR)

        if self.current_tab == "deck":
            self.render_deck(data.get("myDeck", []))
        elif self.current_tab == "threats":
            self.render_threats(data.get("threats", []))
        elif self.current_tab == "board":
            self.render_board(data)

    def render_deck(self, deck):
        # Canvas for scrolling if list is long
        canvas = tk.Canvas(self.content_frame, bg=BG_COLOR, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.content_frame, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG_COLOR)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=310)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for card in deck:
            is_empty = (card.get("remaining", 0) == 0)
            fg_name = "#475569" if is_empty else TEXT_COLOR
            bg_row = "#0d141f" if is_empty else CARD_BG

            row = tk.Frame(scroll_frame, bg=bg_row, height=28)
            row.pack(fill=tk.X, pady=2, padx=2)

            # Mana
            mana = tk.Label(row, text=str(card.get("cost", 0)), font=("Segoe UI", 8, "bold"), fg="#04121e", bg=BLUE_MANA, width=2)
            mana.pack(side=tk.LEFT, padx=4, pady=3)

            # Name
            name_lbl = tk.Label(row, text=card.get("name", ""), font=("Segoe UI", 9, "bold" if not is_empty else "normal"), fg=fg_name, bg=bg_row, anchor="w")
            name_lbl.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)

            # Counts & Prob
            prob_text = f"{card.get('prob', 0)}%"
            prob_lbl = tk.Label(row, text=prob_text, font=("Consolas", 8), fg="#38bdf8", bg=bg_row)
            prob_lbl.pack(side=tk.RIGHT, padx=4)

            count_text = f"{card.get('remaining', 0)}/{card.get('initial', 0)}"
            count_lbl = tk.Label(row, text=count_text, font=("Segoe UI", 8, "bold"), fg=GOLD_COLOR, bg=bg_row)
            count_lbl.pack(side=tk.RIGHT, padx=4)

    def render_threats(self, threats):
        if not threats:
            lbl = tk.Label(self.content_frame, text="Оппонент пока не показал карт региона", font=("Segoe UI", 9), fg=MUTED_TEXT, bg=BG_COLOR)
            lbl.pack(pady=30)
            return

        for t in threats[:8]:
            box = tk.Frame(self.content_frame, bg="#20111a", highlightbackground=RED_DANGER, highlightthickness=1)
            box.pack(fill=tk.X, pady=3, padx=2)

            t_top = tk.Frame(box, bg="#20111a")
            t_top.pack(fill=tk.X, padx=4, pady=2)

            tk.Label(t_top, text=f"[{t['speed']}] {t['name']}", font=("Segoe UI", 9, "bold"), fg="#fca5a5", bg="#20111a").pack(side=tk.LEFT)
            tk.Label(t_top, text=f"{t['cost']} маны", font=("Segoe UI", 8, "bold"), fg=BLUE_MANA, bg="#20111a").pack(side=tk.RIGHT)

            tk.Label(box, text=t["warning"], font=("Segoe UI", 8), fg="#cbd5e1", bg="#20111a", wraplength=290, justify="left").pack(anchor="w", padx=4, pady=2)

    def render_board(self, data):
        hand = data.get("myHand", [])
        my_b = data.get("myBoard", [])
        opp_b = data.get("opponentBoard", [])

        tk.Label(self.content_frame, text=f"Рука ({len(hand)}):", font=("Segoe UI", 9, "bold"), fg=GOLD_COLOR, bg=BG_COLOR).pack(anchor="w", pady=(4, 1))
        tk.Label(self.content_frame, text=", ".join([c["name"] for c in hand]) or "Пусто", font=("Segoe UI", 8), fg="#cbd5e1", bg=BG_COLOR, wraplength=300, justify="left").pack(anchor="w", pady=(0, 8))

        tk.Label(self.content_frame, text=f"Мой стол ({len(my_b)}):", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg=BG_COLOR).pack(anchor="w", pady=(4, 1))
        tk.Label(self.content_frame, text=", ".join([c["name"] for c in my_b]) or "Стол пуст", font=("Segoe UI", 8), fg="#cbd5e1", bg=BG_COLOR, wraplength=300, justify="left").pack(anchor="w", pady=(0, 8))

        tk.Label(self.content_frame, text=f"Стол оппонента ({len(opp_b)}):", font=("Segoe UI", 9, "bold"), fg=RED_DANGER, bg=BG_COLOR).pack(anchor="w", pady=(4, 1))
        tk.Label(self.content_frame, text=", ".join([c["name"] for c in opp_b]) or "Стол пуст", font=("Segoe UI", 8), fg="#cbd5e1", bg=BG_COLOR, wraplength=300, justify="left").pack(anchor="w")

def start_native_overlay():
    # Start flask server if not running
    threading.Thread(target=lambda: app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False), daemon=True).start()
    time.sleep(0.5)

    root = tk.Tk()
    overlay = NativeOverlayApp(root)
    root.mainloop()

if __name__ == "__main__":
    start_native_overlay()

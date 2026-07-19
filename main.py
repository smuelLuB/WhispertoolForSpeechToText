import os

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import sys
import json
import math
import time
import wave
import tempfile
import threading
import platform
import urllib.request
import urllib.error
from datetime import datetime

import tkinter as tk
from tkinter import ttk

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput import keyboard as pynput_kb
import pyperclip
import pyautogui

from text_processor import process_text

# ── Platform ────────────────────────────────────────────────────────
IS_MAC = platform.system() == "Darwin"
PASTE_KEYS = ("command", "v") if IS_MAC else ("ctrl", "v")

# ── Paths ───────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

SAMPLE_RATE = 16000
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
MAX_HISTORY = 100

# ── Version ────────────────────────────────────────────────────────
# When frozen, --add-data bundles VERSION inside the temp extraction dir
_BUNDLE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
try:
    with open(os.path.join(_BUNDLE_DIR, "VERSION")) as _vf:
        APP_VERSION = _vf.read().strip()
except FileNotFoundError:
    APP_VERSION = "dev"

PROVIDERS = ["Gemini", "OpenAI", "Claude"]

DEFAULT_CONFIG = {
    "hotkey": ["alt", "ctrl"],
    "model_size": "base",
    "language": "en",
    "remove_fillers": True,
    "backtrack": True,
    "numbered_lists": True,
    "smart_punctuation": True,
    "ai_rewrite": False,
    "ai_provider": "Gemini",
    "ai_api_keys": {"Gemini": "", "OpenAI": "", "Claude": ""},
    "ai_style": "",
}

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

# ── Key normalisation ───────────────────────────────────────────────

PYNPUT_KEY_MAP = {}
for _attr, _name in [
    ("ctrl_l", "ctrl"), ("ctrl_r", "ctrl"),
    ("alt_l", "alt"), ("alt_r", "alt"), ("alt_gr", "alt"),
    ("shift_l", "shift"), ("shift_r", "shift"),
    ("cmd", "cmd"), ("cmd_l", "cmd"), ("cmd_r", "cmd"),
]:
    _key = getattr(pynput_kb.Key, _attr, None)
    if _key is not None:
        PYNPUT_KEY_MAP[_key] = _name

TK_KEYSYM_MAP = {
    "Control_L": "ctrl", "Control_R": "ctrl",
    "Alt_L": "alt", "Alt_R": "alt",
    "Shift_L": "shift", "Shift_R": "shift",
    "Super_L": "cmd", "Super_R": "cmd",
    "Meta_L": "cmd", "Meta_R": "cmd",
}


def normalize_pynput(key):
    return PYNPUT_KEY_MAP.get(key)


def normalize_tk(keysym):
    return TK_KEYSYM_MAP.get(keysym)


def hotkey_label(keys):
    order = {"ctrl": 0, "alt": 1, "shift": 2, "cmd": 3}
    return " + ".join(
        k.capitalize() for k in sorted(keys, key=lambda k: order.get(k, 9))
    )


# ── Config ──────────────────────────────────────────────────────────

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        # Migrate old single-key config
        if "gemini_api_key" in cfg and cfg["gemini_api_key"]:
            cfg.setdefault("ai_api_keys", {})
            if not cfg["ai_api_keys"].get("Gemini"):
                cfg["ai_api_keys"]["Gemini"] = cfg["gemini_api_key"]
        for p in PROVIDERS:
            cfg["ai_api_keys"].setdefault(p, "")
        return cfg
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_CONFIG)


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


# ── AI Providers ────────────────────────────────────────────────────

DEFAULT_AI_PROMPT = (
    "Rewrite the following text to make it clear, well-structured, "
    "and free of any grammatical or language errors. "
    "Preserve the original meaning and intent. "
    "Only return the rewritten text, nothing else."
)


def _system_prompt(style=""):
    prompt = DEFAULT_AI_PROMPT
    if style.strip():
        prompt += f"\n\nAdditional style and tone instructions: {style.strip()}"
    return prompt


def rewrite_with_ai(text, provider, api_key, style=""):
    system = _system_prompt(style)
    user_content = f"Text to rewrite:\n{text}"

    if provider == "Gemini":
        # Gemini: combine system + user into a single user turn
        combined = f"{system}\n\n{user_content}"
        url = ("https://generativelanguage.googleapis.com/v1beta/"
               "models/gemini-2.0-flash:generateContent")
        body = json.dumps(
            {"contents": [{"parts": [{"text": combined}]}]}
        ).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    elif provider == "OpenAI":
        url = "https://api.openai.com/v1/chat/completions"
        body = json.dumps({
            "model": "gpt-5-nano-2025-08-07",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()

    elif provider == "Claude":
        url = "https://api.anthropic.com/v1/messages"
        body = json.dumps({
            "model": "claude-haiku-4-5",
            "max_tokens": 4096,
            "system": system,
            "messages": [{"role": "user", "content": user_content}],
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["content"][0]["text"].strip()

    raise ValueError(f"Unknown provider: {provider}")


# ── Floating Overlay (circular waveform + loading spinner) ──────────

class FloatingOverlay:
    """Circular overlay: waveform while recording, spinner while processing."""

    SIZE = 110
    BAR_COUNT = 28
    INNER_R = 20
    OUTER_R = 48
    TRANS_COLOR = "#010101"  # Transparent key colour

    # Teal gradient stops
    COLOR_BRIGHT = "#22d3ee"
    COLOR_MID = "#06b6d4"
    COLOR_DIM = "#0e7490"
    BG_CIRCLE = "#0f172a"
    BG_RING = "#1e293b"

    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-alpha", 0.95)
            self.win.attributes("-transparentcolor", self.TRANS_COLOR)
        except tk.TclError:
            pass
        if IS_MAC:
            # Mac: use built-in transparency, no transparentcolor support
            try:
                self.win.wm_attributes("-transparent", True)
                self.win.configure(bg="systemTransparent")
            except tk.TclError:
                self.win.configure(bg=self.TRANS_COLOR)
        else:
            self.win.configure(bg=self.TRANS_COLOR)

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - self.SIZE) // 2
        y = sh - self.SIZE - 120  # Higher above taskbar
        self.win.geometry(f"{self.SIZE}x{self.SIZE}+{x}+{y}")

        canvas_bg = "systemTransparent" if IS_MAC else self.TRANS_COLOR
        self.canvas = tk.Canvas(
            self.win, width=self.SIZE, height=self.SIZE,
            bg=canvas_bg, highlightthickness=0,
        )
        self.canvas.pack()

        self.visible = False
        self.mode = "idle"  # idle | recording | loading
        self.phase = 0.0
        self.audio_level = 0.0
        self._want_mode = None  # Thread-safe mode requests

    def request_recording(self):
        self._want_mode = "recording"

    def request_loading(self):
        self._want_mode = "loading"

    def request_hide(self):
        self._want_mode = "idle"

    def set_audio_level(self, level):
        self.audio_level = min(1.0, level)

    def tick(self):
        wm = self._want_mode
        if wm is not None:
            self._want_mode = None
            if wm == "idle":
                if self.visible:
                    self.visible = False
                    self.mode = "idle"
                    self.win.withdraw()
            else:
                self.mode = wm
                self.phase = 0.0
                if not self.visible:
                    self.visible = True
                    self.win.deiconify()
        if self.visible:
            self._draw()

    def _draw(self):
        self.canvas.delete("all")
        cx = cy = self.SIZE / 2
        r = self.SIZE / 2 - 4

        # Background circle
        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill=self.BG_CIRCLE, outline=self.BG_RING, width=2,
        )

        if self.mode == "recording":
            self._draw_waveform(cx, cy)
        elif self.mode == "loading":
            self._draw_spinner(cx, cy)

    def _draw_waveform(self, cx, cy):
        self.phase += 0.12
        level = max(0.2, self.audio_level)

        for i in range(self.BAR_COUNT):
            angle = 2 * math.pi * i / self.BAR_COUNT - math.pi / 2
            wave = math.sin(self.phase * 2 + i * 0.6) * 0.5 + 0.5
            bar_len = self.INNER_R + level * wave * (self.OUTER_R - self.INNER_R)

            x0 = cx + self.INNER_R * math.cos(angle)
            y0 = cy + self.INNER_R * math.sin(angle)
            x1 = cx + bar_len * math.cos(angle)
            y1 = cy + bar_len * math.sin(angle)

            # Gradient: brighter bars have more energy
            if wave > 0.6:
                color = self.COLOR_BRIGHT
            elif wave > 0.3:
                color = self.COLOR_MID
            else:
                color = self.COLOR_DIM

            self.canvas.create_line(x0, y0, x1, y1, fill=color, width=3,
                                    capstyle="round")

        # Center dot
        self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4,
                                fill=self.COLOR_BRIGHT, outline="")

    def _draw_spinner(self, cx, cy):
        self.phase += 0.08
        r = 30

        # Rotating arc
        start_deg = (self.phase * 180) % 360
        self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=start_deg, extent=90,
            style="arc", outline=self.COLOR_MID, width=3,
        )
        self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=start_deg + 180, extent=90,
            style="arc", outline=self.COLOR_DIM, width=3,
        )

        # Bouncing dots
        for i in range(3):
            offset = math.sin(self.phase * 3 + i * 1.2) * 5
            dx = (i - 1) * 12
            self.canvas.create_oval(
                cx + dx - 3, cy + offset - 3,
                cx + dx + 3, cy + offset + 3,
                fill=self.COLOR_BRIGHT, outline="",
            )


# ── Application ─────────────────────────────────────────────────────

class App:
    def __init__(self):
        self.cfg = load_config()
        self.hotkey_set = set(self.cfg["hotkey"])

        # State
        self.model = None
        self.recording = False
        self.busy = False
        self.audio_frames = []
        self.stream = None
        self.pressed_keys: set[str] = set()
        self.lock = threading.Lock()
        self.history: list[tuple[str, str]] = []

        # Hotkey capture state
        self.capturing_hotkey = False
        self._capture_keys: set[str] = set()
        self._capture_max: set[str] = set()

        # AI provider tracking (needed to correctly save key on switch)
        self._last_provider = self.cfg.get("ai_provider", "Gemini")

        # Pending UI updates from background threads
        self._pending_status = "loading"
        self._pending_history = None
        self._pending_ai_error = None  # Error text from AI call, shown in UI

        # ── Root window ──────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title(f"WhisperTool v{APP_VERSION} (by FuturMinds)")
        self.root.geometry("880x1260")
        self.root.minsize(500, 700)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._apply_dark_theme()

        # ── Variables ────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Loading model...")
        self.hotkey_var = tk.StringVar(value=hotkey_label(self.hotkey_set))
        self.filler_var = tk.BooleanVar(value=self.cfg["remove_fillers"])
        self.backtrack_var = tk.BooleanVar(value=self.cfg["backtrack"])
        self.lists_var = tk.BooleanVar(value=self.cfg["numbered_lists"])
        self.punct_var = tk.BooleanVar(value=self.cfg["smart_punctuation"])
        self.ai_var = tk.BooleanVar(value=self.cfg["ai_rewrite"])
        self.provider_var = tk.StringVar(value=self.cfg.get("ai_provider", "Gemini"))

        self._build_ui()
        self.overlay = FloatingOverlay(self.root)

        # Load model in background
        threading.Thread(target=self._load_model, daemon=True).start()

        # Global hotkey listener
        self.listener = pynput_kb.Listener(
            on_press=self._on_press, on_release=self._on_release,
        )
        self.listener.start()

        self._tick()

    # ── UI ───────────────────────────────────────────────────────────

    def _apply_dark_theme(self):
        """Apply always-on dark color scheme to all ttk and classic tk widgets."""
        # ── Color palette ─────────────────────────────────────────
        BG        = "#000000"   # pure black background
        SURFACE   = "#4a4a4a"   # grey for box elements
        HEADING   = "#FF8C00"   # dark orange for headings
        FG        = "#ffffff"   # white for small / body text
        FG_SUBTLE = "#cccccc"   # lighter grey for subtle text
        ACCENT    = "#FF8C00"   # orange accent
        BORDER    = "#666666"   # grey border
        SEL_BG    = "#FF8C00"   # orange selection
        SEL_FG    = "#000000"   # black text on orange selection
        ENTRY_BG  = "#3a3a3a"   # slightly lighter grey for input fields
        BTN_BG    = "#555555"   # button background
        BTN_HOVER = "#666666"   # button hover
        BTN_PRESS  = "#3a3a3a"   # button pressed
        DISABLED_FG = "#777777"  # disabled text

        # Store palette for use in other methods
        self.theme = {
            "bg": BG, "surface": SURFACE, "heading": HEADING,
            "fg": FG, "fg_subtle": FG_SUBTLE, "accent": ACCENT,
            "border": BORDER, "sel_bg": SEL_BG, "sel_fg": SEL_FG,
            "entry_bg": ENTRY_BG, "btn_bg": BTN_BG,
            "btn_hover": BTN_HOVER, "btn_press": BTN_PRESS,
            "disabled_fg": DISABLED_FG,
        }

        # ── Root window ───────────────────────────────────────────
        self.root.configure(bg=BG)

        # ── ttk Style ─────────────────────────────────────────────
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass  # fall back to whatever is available

        # --- Base frame surfaces ---
        style.configure("TFrame",       background=SURFACE)
        style.configure("TLabelframe",  background=SURFACE, foreground=HEADING,
                        bordercolor=BORDER, darkcolor=BORDER, lightcolor=BORDER)
        style.configure("TLabelframe.Label", background=SURFACE, foreground=HEADING,
                        font=("", 10, "bold"))

        # --- Labels ---
        style.configure("TLabel", background=SURFACE, foreground=FG)

        # --- Buttons ---
        style.configure("TButton",
            background=BTN_BG, foreground=FG,
            bordercolor=BORDER, darkcolor=BTN_PRESS, lightcolor=BTN_HOVER,
            focuscolor="none",
        )
        style.map("TButton",
            background=[("active", BTN_HOVER), ("pressed", BTN_PRESS),
                        ("disabled", BTN_PRESS)],
            foreground=[("disabled", DISABLED_FG)],
        )

        # --- Checkbuttons ---
        style.configure("TCheckbutton",
            background=SURFACE, foreground=FG,
            indicatorcolor=SURFACE, indicatorbackground=SURFACE,
        )
        style.map("TCheckbutton",
            background=[("active", SURFACE)],
            indicatorcolor=[("selected", ACCENT)],
        )

        # --- Combobox ---
        style.configure("TCombobox",
            fieldbackground=ENTRY_BG, background=ENTRY_BG,
            foreground=FG, arrowcolor=FG,
            bordercolor=BORDER, darkcolor=BORDER, lightcolor=BORDER,
        )
        style.map("TCombobox",
            fieldbackground=[("readonly", ENTRY_BG)],
            foreground=[("readonly", FG)],
            selectbackground=[("readonly", ENTRY_BG)],
            selectforeground=[("readonly", FG)],
        )
        self.root.option_add("*TCombobox*Listbox.background", ENTRY_BG)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", SEL_BG)
        self.root.option_add("*TCombobox*Listbox.selectForeground", SEL_FG)

        # --- Entry ---
        style.configure("TEntry",
            fieldbackground=ENTRY_BG, foreground=FG,
            bordercolor=BORDER, darkcolor=BORDER, lightcolor=BORDER,
            insertcolor=FG,
        )

        # --- Scrollbar ---
        style.configure("TScrollbar",
            background=SURFACE, troughcolor=BG,
            bordercolor=BG, arrowcolor=FG,
        )
        style.map("TScrollbar",
            background=[("active", BTN_HOVER)],
        )

        # --- Separator ---
        style.configure("TSeparator", background=BORDER)

        # ── Classic tk widget defaults ────────────────────────────
        self.root.option_add("*Listbox.background", ENTRY_BG)
        self.root.option_add("*Listbox.foreground", FG)
        self.root.option_add("*Listbox.selectBackground", SEL_BG)
        self.root.option_add("*Listbox.selectForeground", SEL_FG)
        self.root.option_add("*Text.background", ENTRY_BG)
        self.root.option_add("*Text.foreground", FG)
        self.root.option_add("*Text.insertBackground", FG)

    def _build_ui(self):
        px, py = 14, 6
        ipx, ipy = 12, 8
        mono = "Consolas" if not IS_MAC else "Menlo"

        # ── Status ───────────────────────────────────────────────────
        sf = ttk.LabelFrame(self.root, text="Status")
        sf.pack(fill="x", padx=px, pady=py)
        row = ttk.Frame(sf)
        row.pack(fill="x", padx=ipx, pady=ipy)
        self.status_dot = tk.Canvas(row, width=14, height=14,
                                    highlightthickness=0, bg=self.theme["surface"])
        self.status_dot.pack(side="left")
        self.status_dot.create_oval(2, 2, 12, 12, fill="gray", tags="dot")
        ttk.Label(row, textvariable=self.status_var,
                  font=("", 10)).pack(side="left", padx=8)

        # ── Hotkey ───────────────────────────────────────────────────
        hf = ttk.LabelFrame(self.root, text="Hotkey (hold to record)")
        hf.pack(fill="x", padx=px, pady=py)
        row = ttk.Frame(hf)
        row.pack(fill="x", padx=ipx, pady=ipy)
        self.hotkey_display = ttk.Label(
            row, textvariable=self.hotkey_var, font=(mono, 14, "bold"),
        )
        self.hotkey_display.pack(side="left")
        self.hotkey_btn = ttk.Button(
            row, text="Change", command=self._start_hotkey_capture,
        )
        self.hotkey_btn.pack(side="right")
        self.root.bind("<KeyPress>", self._on_tk_keypress)
        self.root.bind("<KeyRelease>", self._on_tk_keyrelease)

        # ── Features ─────────────────────────────────────────────────
        ff = ttk.LabelFrame(self.root, text="Features")
        ff.pack(fill="x", padx=px, pady=py)
        for var, label in [
            (self.filler_var, "Remove fillers (um, uh, you know...)"),
            (self.backtrack_var, 'Smart corrections ("actually", "I mean")'),
            (self.lists_var, "Format numbered lists"),
            (self.punct_var, 'Smart punctuation ("comma", "period")'),
        ]:
            ttk.Checkbutton(
                ff, text=label, variable=var, command=self._save_features,
            ).pack(anchor="w", padx=16, pady=3)
        ttk.Frame(ff).pack(pady=2)

        # ── AI Rewriting ─────────────────────────────────────────────
        self.ai_frame = ttk.LabelFrame(self.root, text="AI Rewriting")
        self.ai_frame.pack(fill="x", padx=px, pady=py)

        ttk.Checkbutton(
            self.ai_frame, text="Enable AI rewriting",
            variable=self.ai_var, command=self._toggle_ai_section,
        ).pack(anchor="w", padx=16, pady=(6, 4))

        # Collapsible details
        self.ai_details = ttk.Frame(self.ai_frame)

        # Provider row
        prov_row = ttk.Frame(self.ai_details)
        prov_row.pack(fill="x", padx=20, pady=(6, 4))
        ttk.Label(prov_row, text="Provider:").pack(side="left")
        self.provider_combo = ttk.Combobox(
            prov_row, textvariable=self.provider_var,
            values=PROVIDERS, state="readonly", width=12,
        )
        self.provider_combo.pack(side="left", padx=(8, 0))
        self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        # API Key row
        key_row = ttk.Frame(self.ai_details)
        key_row.pack(fill="x", padx=20, pady=(4, 4))
        ttk.Label(key_row, text="API Key:").pack(side="left")
        cur_provider = self.provider_var.get()
        cur_key = self.cfg.get("ai_api_keys", {}).get(cur_provider, "")
        self.api_key_var = tk.StringVar(value=cur_key)
        self.api_key_entry = ttk.Entry(
            key_row, textvariable=self.api_key_var, show="*", width=36,
        )
        self.api_key_entry.pack(side="left", padx=(8, 0), fill="x", expand=True)

        # Style / Tone
        ttk.Label(
            self.ai_details, text="Style & tone instructions (optional):",
        ).pack(anchor="w", padx=20, pady=(8, 3))

        sf2 = ttk.Frame(self.ai_details)
        sf2.pack(fill="x", padx=20, pady=(0, 4))
        self.style_text = tk.Text(sf2, height=3, wrap="word", font=(mono, 9))
        self.style_text.pack(fill="x")
        saved_style = self.cfg.get("ai_style", "")
        if saved_style:
            self.style_text.insert("1.0", saved_style)

        ttk.Label(
            self.ai_details,
            text='e.g. "Professional and concise" or "Casual, friendly tone"',
            foreground=self.theme["fg_subtle"], font=("", 8),
        ).pack(anchor="w", padx=20, pady=(2, 6))

        # Apply button + feedback row
        apply_row = ttk.Frame(self.ai_details)
        apply_row.pack(fill="x", padx=20, pady=(0, 4))
        ttk.Button(
            apply_row, text="Apply Settings", command=self._apply_ai_config,
        ).pack(side="left")
        self.ai_feedback_var = tk.StringVar()
        self.ai_feedback_lbl = ttk.Label(
            apply_row, textvariable=self.ai_feedback_var,
            font=("", 9), foreground="green",
        )
        self.ai_feedback_lbl.pack(side="left", padx=(12, 0))

        # Error display row
        self.ai_error_var = tk.StringVar()
        self.ai_error_lbl = ttk.Label(
            self.ai_details, textvariable=self.ai_error_var,
            font=("", 8), foreground="red", wraplength=700, justify="left",
        )
        self.ai_error_lbl.pack(anchor="w", padx=20, pady=(0, 6))

        if self.ai_var.get():
            self.ai_details.pack(fill="x")

        # ── History ──────────────────────────────────────────────────
        hist_frame = ttk.LabelFrame(self.root, text="Recent Transcriptions")
        hist_frame.pack(fill="both", expand=True, padx=px, pady=py)

        lc = ttk.Frame(hist_frame)
        lc.pack(fill="both", expand=True, padx=ipx, pady=ipy)
        sb = ttk.Scrollbar(lc)
        sb.pack(side="right", fill="y")
        self.history_list = tk.Listbox(
            lc, yscrollcommand=sb.set, font=(mono, 9), selectmode="browse",
        )
        self.history_list.pack(fill="both", expand=True)
        sb.config(command=self.history_list.yview)
        self.history_list.bind("<Double-1>", self._copy_history_item)

        btn_row = ttk.Frame(hist_frame)
        btn_row.pack(fill="x", padx=ipx, pady=(0, ipy))
        ttk.Button(btn_row, text="Copy Selected",
                   command=self._copy_history_item).pack(side="left")
        ttk.Button(btn_row, text="Clear",
                   command=self._clear_history).pack(side="right")

        ttk.Label(
            self.root, text="Double-click a transcription to copy it",
            foreground=self.theme["fg_subtle"],
        ).pack(pady=(0, 8))

    # ── Hotkey capture ───────────────────────────────────────────────

    def _start_hotkey_capture(self):
        self.capturing_hotkey = True
        self._capture_keys.clear()
        self._capture_max.clear()
        self.hotkey_var.set("Press & release keys (Esc to cancel)...")
        self.hotkey_btn.config(state="disabled")
        self.root.focus_force()

    def _cancel_hotkey_capture(self):
        """Cancel hotkey capture and restore previous setting."""
        self.capturing_hotkey = False
        self._capture_keys.clear()
        self._capture_max.clear()
        self.hotkey_var.set(hotkey_label(self.hotkey_set))
        self.hotkey_btn.config(state="normal")

    def _finalize_hotkey_capture(self):
        """Save the captured hotkey combination."""
        self.cfg["hotkey"] = sorted(self._capture_max)
        self.hotkey_set = set(self._capture_max)
        self.hotkey_var.set(hotkey_label(self.hotkey_set))
        save_config(self.cfg)
        self.capturing_hotkey = False
        self.hotkey_btn.config(state="normal")

    def _on_tk_keypress(self, event):
        # Capture is handled by pynput (global listener) for reliability.
        # Tk events for modifier keys can be intercepted by the OS (e.g. Alt).
        pass

    def _on_tk_keyrelease(self, event):
        pass

    # ── AI config ────────────────────────────────────────────────────

    def _toggle_ai_section(self):
        if self.ai_var.get():
            self.ai_details.pack(fill="x")
        else:
            self.ai_details.pack_forget()
        self.cfg["ai_rewrite"] = self.ai_var.get()
        save_config(self.cfg)
        self.root.update_idletasks()

    def _on_provider_change(self, _event=None):
        # 1. Save the current API key under the PREVIOUSLY shown provider
        #    (provider_var already holds the new value at this point, so we
        #     must use _last_provider to avoid key cross-contamination)
        old_prov = self._last_provider
        self.cfg.setdefault("ai_api_keys", {})[old_prov] = self.api_key_var.get()

        # 2. Switch to the new provider and load its saved key
        new_prov = self.provider_var.get()
        self._last_provider = new_prov
        self.cfg["ai_provider"] = new_prov
        key = self.cfg["ai_api_keys"].get(new_prov, "")
        self.api_key_var.set(key)

        # Clear any stale error/feedback from the previous provider
        self.ai_error_var.set("")
        self.ai_feedback_var.set("(unsaved)")
        self.ai_feedback_lbl.config(foreground=self.theme["fg_subtle"])

    def _apply_ai_config(self):
        """Explicitly save all AI settings and give visual confirmation."""
        self._save_ai_config()
        self.ai_feedback_var.set("✓ Settings applied")
        self.ai_feedback_lbl.config(foreground="green")
        self.ai_error_var.set("")
        # Clear confirmation after 3 s
        self.root.after(3000, lambda: self.ai_feedback_var.set(""))

    def _save_ai_config(self):
        provider = self.provider_var.get()
        self._last_provider = provider
        self.cfg["ai_rewrite"] = self.ai_var.get()
        self.cfg["ai_provider"] = provider
        self.cfg.setdefault("ai_api_keys", {})
        self.cfg["ai_api_keys"][provider] = self.api_key_var.get()
        self.cfg["ai_style"] = self.style_text.get("1.0", "end-1c").strip()
        save_config(self.cfg)

    def _save_features(self):
        self.cfg["remove_fillers"] = self.filler_var.get()
        self.cfg["backtrack"] = self.backtrack_var.get()
        self.cfg["numbered_lists"] = self.lists_var.get()
        self.cfg["smart_punctuation"] = self.punct_var.get()
        save_config(self.cfg)

    # ── History ──────────────────────────────────────────────────────

    def _add_history(self, text):
        ts = datetime.now().strftime("%H:%M:%S")
        self.history.append((ts, text))
        if len(self.history) > MAX_HISTORY:
            self.history.pop(0)
            self.history_list.delete(0)
        self.history_list.insert("end", f"[{ts}]  {text[:200]}")
        self.history_list.see("end")

    def _copy_history_item(self, _event=None):
        sel = self.history_list.curselection()
        if sel:
            _, text = self.history[sel[0]]
            pyperclip.copy(text)

    def _clear_history(self):
        self.history.clear()
        self.history_list.delete(0, "end")

    # ── Model ────────────────────────────────────────────────────────

    def _load_model(self):
        sz = self.cfg.get("model_size", "base")
        self.model = WhisperModel(sz, device="cpu", compute_type="int8")
        self._pending_status = "ready"

    # ── Audio & Transcription ────────────────────────────────────────

    def _audio_cb(self, indata, frames, time_info, status):
        if self.recording:
            self.audio_frames.append(indata.copy())
            level = float(np.abs(indata).mean()) * 15
            self.overlay.set_audio_level(level)

    def _start_recording(self):
        with self.lock:
            if self.recording or self.busy:
                return
            self.recording = True
            self.audio_frames = []

        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32",
            callback=self._audio_cb,
        )
        self.stream.start()
        self.overlay.request_recording()
        self._pending_status = "recording"

    def _stop_and_transcribe(self):
        with self.lock:
            if not self.recording:
                return
            self.recording = False
            self.busy = True

        # Switch overlay to loading spinner
        self.overlay.request_loading()
        self._pending_status = "transcribing"

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if not self.audio_frames:
            self.busy = False
            self.overlay.request_hide()
            self._pending_status = "ready"
            return

        audio = np.concatenate(self.audio_frames, axis=0).flatten()
        if len(audio) < SAMPLE_RATE * 0.3:
            self.busy = False
            self.overlay.request_hide()
            self._pending_status = "ready"
            return

        tmp_path = tempfile.mktemp(suffix=".wav")
        try:
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes((audio * 32767).astype(np.int16).tobytes())

            lang = self.cfg.get("language", "en") or None
            segments, _ = self.model.transcribe(
                tmp_path, beam_size=5, language=lang, vad_filter=True,
            )
            raw = " ".join(s.text for s in segments).strip()

            if raw:
                # Step 1: Local text processing
                text = process_text(
                    raw,
                    remove_fillers_on=self.cfg["remove_fillers"],
                    backtrack_on=self.cfg["backtrack"],
                    numbered_lists_on=self.cfg["numbered_lists"],
                    smart_punctuation_on=self.cfg["smart_punctuation"],
                )

                # Step 2: AI rewriting (if enabled)
                provider = self.cfg.get("ai_provider", "Gemini")
                api_key = self.cfg.get("ai_api_keys", {}).get(provider, "").strip()
                if self.cfg.get("ai_rewrite") and api_key:
                    self._pending_status = "polishing"
                    try:
                        style = self.cfg.get("ai_style", "")
                        text = rewrite_with_ai(text, provider, api_key, style)
                        self._pending_ai_error = ""  # Clear any previous error
                    except urllib.error.HTTPError as e:
                        body = e.read().decode("utf-8", errors="replace")
                        # Try to extract a clean message from JSON error body
                        try:
                            msg = json.loads(body).get("error", {}).get(
                                "message", body[:200]
                            )
                        except Exception:
                            msg = body[:200]
                        self._pending_ai_error = (
                            f"{provider} HTTP {e.code}: {msg}"
                        )
                    except Exception as e:
                        self._pending_ai_error = f"{provider} error: {e}"
                elif self.cfg.get("ai_rewrite") and not api_key:
                    self._pending_ai_error = (
                        f"No API key set for {provider}. "
                        "Enter your key and click Apply Settings."
                    )

                # Step 3: Paste at cursor
                time.sleep(0.15)
                pyperclip.copy(text)
                pyautogui.hotkey(*PASTE_KEYS)

                self._pending_history = text

        except Exception as e:
            print(f"[!] Transcription error: {e}")
        finally:
            for _ in range(5):
                try:
                    os.unlink(tmp_path)
                    break
                except (PermissionError, FileNotFoundError):
                    time.sleep(0.1)
            self.busy = False
            self.overlay.request_hide()
            self._pending_status = "ready"

    # ── Pynput handlers ──────────────────────────────────────────────

    def _on_press(self, key):
        # ── Hotkey capture mode (pynput, reliable for modifiers) ──
        if self.capturing_hotkey:
            name = normalize_pynput(key)
            if name:
                self._capture_keys.add(name)
                self._capture_max.update(self._capture_keys)
                self.hotkey_var.set(hotkey_label(self._capture_keys))
            elif key == pynput_kb.Key.esc:
                self._cancel_hotkey_capture()
            return

        # ── Normal recording mode ──
        name = normalize_pynput(key)
        if name:
            self.pressed_keys.add(name)
            if self.pressed_keys >= self.hotkey_set:
                self._start_recording()

    def _on_release(self, key):
        # ── Hotkey capture mode ──
        if self.capturing_hotkey:
            name = normalize_pynput(key)
            if name:
                self._capture_keys.discard(name)
            # Complete capture when all keys released and ≥2 modifiers captured
            if not self._capture_keys and len(self._capture_max) >= 2:
                self._finalize_hotkey_capture()
            return

        # ── Normal recording mode ──
        name = normalize_pynput(key)
        if name:
            self.pressed_keys.discard(name)
            # Only stop recording when ALL hotkey keys have been released
            if self.recording and not (self.pressed_keys & self.hotkey_set):
                threading.Thread(
                    target=self._stop_and_transcribe, daemon=True,
                ).start()

    # ── Main-thread tick ─────────────────────────────────────────────

    def _tick(self):
        st = self._pending_status
        if st:
            self._pending_status = None
            dot = self.status_dot
            dot.delete("dot")
            colours = {
                "loading": ("gray", "Loading model..."),
                "ready": ("#22c55e", "Ready"),
                "recording": ("#ef4444", "Recording..."),
                "transcribing": ("#f59e0b", "Transcribing..."),
                "polishing": ("#8b5cf6", "AI polishing..."),
            }
            c, lbl = colours.get(st, ("#22c55e", "Ready"))
            dot.create_oval(2, 2, 12, 12, fill=c, tags="dot")
            self.status_var.set(lbl)

        h = self._pending_history
        if h:
            self._pending_history = None
            self._add_history(h)

        ai_err = self._pending_ai_error
        if ai_err is not None:
            self._pending_ai_error = None
            self.ai_error_var.set(ai_err)
            if ai_err:
                self.ai_feedback_var.set("")

        self.overlay.tick()
        self.root.after(30, self._tick)

    # ── Lifecycle ────────────────────────────────────────────────────

    def _on_close(self):
        self._save_ai_config()
        self.listener.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()

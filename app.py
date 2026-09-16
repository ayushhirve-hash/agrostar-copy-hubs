import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import quote
from urllib.request import Request, urlopen

APP_NAME = "AgroStar Copy Hub"
CONFIG_PATH = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AgroStarCopyHub", "config.json")
LANGS = {
    "Hindi": ("hi", "hi-t-i0-und"),
    "Marathi": ("mr", "mr-t-i0-und"),
    "Gujarati": ("gu", "gu-t-i0-und"),
    "Telugu": ("te", "te-t-i0-und"),
    "Kannada": ("kn", "kn-t-i0-und"),
    "English": ("en", None),
}
DEFAULT_CONFIG = {"languages": list(LANGS.keys()), "shortcut": "Ctrl+Shift+A"}


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(c):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(c, f, ensure_ascii=False, indent=2)


def detect_source(text):
    counts = {"hi": 0, "gu": 0, "te": 0, "kn": 0, "mr": 0}
    for ch in text:
        o = ord(ch)
        if 0x0900 <= o <= 0x097F: counts["hi"] += 1
        elif 0x0A80 <= o <= 0x0AFF: counts["gu"] += 1
        elif 0x0C00 <= o <= 0x0C7F: counts["te"] += 1
        elif 0x0C80 <= o <= 0x0CFF: counts["kn"] += 1
    return "en" if max(counts.values()) == 0 else max(counts, key=counts.get)


def translate_text(text, target):
    text = text.strip()
    if not text: return ""
    target_code = LANGS[target][0]
    source = detect_source(text)
    if target_code == source: return text
    try:
        url = f"https://api.mymemory.translated.net/get?q={quote(text, safe='')}&langpair={source}|{target_code}"
        req = Request(url, headers={"User-Agent": "AgroStarCopyHub/2.0"})
        with urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data.get("responseData", {}).get("translatedText", "") or "Translation unavailable"
    except Exception:
        return "Translation unavailable. Check internet and retry."


def transliterate(text, lang):
    code = LANGS[lang][1]
    if not code or not text.strip(): return text
    try:
        url = f"https://inputtools.google.com/request?text={quote(text, safe='')}&itc={code}&num=5&cp=0&cs=1&ie=utf-8&oe=utf-8"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=6) as r:
            data = json.loads(r.read().decode("utf-8"))
        if isinstance(data, list) and len(data) > 1:
            candidates = data[1]
            if candidates and isinstance(candidates[0], list) and candidates[0]:
                return candidates[0][0]
    except Exception:
        pass
    return text


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.result_boxes = {}
        self.typing_after = None
        self.hotkey_thread = None
        self.hotkey_stop = False
        self.setup_dark_theme()
        self.build_ui()
        self.start_global_hotkey()

    def setup_dark_theme(self):
        self.root.configure(bg="#111315")
        style = ttk.Style(self.root)
        try: style.theme_use("clam")
        except Exception: pass
        bg, panel, field = "#111315", "#191c20", "#22262b"
        fg, muted, accent = "#F4F6F8", "#AEB6C0", "#F47B20"
        style.configure("TFrame", background=bg)
        style.configure("Card.TFrame", background=panel)
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=bg, foreground=muted, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=bg, foreground=fg, font=("Segoe UI", 19, "bold"))
        style.configure("Subtitle.TLabel", background=bg, foreground=muted, font=("Segoe UI", 10))
        style.configure("TButton", background="#292e34", foreground=fg, bordercolor="#3B424A", padding=(12, 7))
        style.map("TButton", background=[("active", "#343A42")])
        style.configure("Accent.TButton", background=accent, foreground="#111315", bordercolor=accent, padding=(14, 7), font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#FF963F")])
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", background="#20242A", foreground=muted, padding=(18, 9))
        style.map("TNotebook.Tab", background=[("selected", "#2B3037")], foreground=[("selected", fg)])
        style.configure("TLabelframe", background=panel, foreground=fg, bordercolor="#343A42")
        style.configure("TLabelframe.Label", background=panel, foreground=fg, font=("Segoe UI", 10, "bold"))
        style.configure("TCheckbutton", background=panel, foreground=fg)
        style.configure("TCombobox", fieldbackground=field, background=field, foreground=fg, arrowcolor=fg)
        self.COLORS = {"bg": bg, "panel": panel, "field": field, "fg": fg, "muted": muted, "accent": accent}

    def make_text(self, parent, height=5, font=("Segoe UI", 12)):
        c = self.COLORS
        return tk.Text(parent, height=height, font=font, wrap="word", bg=c["field"], fg=c["fg"], insertbackground=c["fg"], selectbackground=c["accent"], selectforeground="#111315", relief="flat", padx=10, pady=9, highlightthickness=1, highlightbackground="#343A42", highlightcolor=c["accent"])

    def build_ui(self):
        c = self.COLORS
        self.root.title(APP_NAME)
        self.root.geometry("1080x780")
        self.root.minsize(880, 650)

        header = ttk.Frame(self.root, padding=(18, 15))
        header.pack(fill="x")
        ttk.Label(header, text="AGROSTAR COPY HUB", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="One Copy → Multiple Languages", style="Subtitle.TLabel").pack(side="left", padx=14)
        ttk.Button(header, text="Settings", command=self.settings).pack(side="right")

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        translate_tab = ttk.Frame(nb, padding=14)
        quick_tab = ttk.Frame(nb, padding=14)
        nb.add(translate_tab, text="  Translate Copy  ")
        nb.add(quick_tab, text="  Quick Type  ")

        ttk.Label(translate_tab, text="Creative copy", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.input = self.make_text(translate_tab, height=7)
        self.input.pack(fill="x", pady=8)
        controls = ttk.Frame(translate_tab); controls.pack(fill="x")
        ttk.Button(controls, text="Translate All", style="Accent.TButton", command=self.translate_all).pack(side="left")
        ttk.Button(controls, text="Paste", command=self.paste).pack(side="left", padx=7)
        ttk.Button(controls, text="Clear", command=self.clear).pack(side="left")
        ttk.Button(controls, text="Copy All", command=self.copy_all).pack(side="right")
        self.status = ttk.Label(translate_tab, text="Ready", style="Muted.TLabel"); self.status.pack(anchor="w", pady=(7, 0))

        canvas = tk.Canvas(translate_tab, bg=c["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(translate_tab, orient="vertical", command=canvas.yview)
        self.results_frame = ttk.Frame(canvas)
        self.results_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.results_frame, anchor="nw", tags="results")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure("results", width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, pady=10); scrollbar.pack(side="right", fill="y", pady=10)
        self.build_results()

        ttk.Label(quick_tab, text="Quick Indian-language typing", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(quick_tab, text="Type in Roman English. Words convert automatically, like Google Input Tools.", style="Muted.TLabel").pack(anchor="w", pady=(3, 8))
        row = ttk.Frame(quick_tab); row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="Language:").pack(side="left")
        self.type_lang = tk.StringVar(value="Marathi")
        ttk.Combobox(row, textvariable=self.type_lang, values=list(LANGS), state="readonly", width=15).pack(side="left", padx=8)
        ttk.Button(row, text="Copy", command=self.copy_quick).pack(side="right")
        self.quick = self.make_text(quick_tab, height=18, font=("Segoe UI", 16))
        self.quick.pack(fill="both", expand=True)
        self.quick.bind("<KeyRelease>", self.schedule_transliteration)
        ttk.Label(quick_tab, text="Example:  agrostar  →  ॲग्रोस्टार    |    shetkaryansathi khas offer  →  शेतकऱ्यांसाठी खास ऑफर", style="Muted.TLabel").pack(anchor="w", pady=8)

    def build_results(self):
        for w in self.results_frame.winfo_children(): w.destroy()
        self.result_boxes = {}
        for lang in self.cfg.get("languages", list(LANGS)):
            box = ttk.LabelFrame(self.results_frame, text=lang, padding=7); box.pack(fill="x", pady=4)
            txt = self.make_text(box, height=3, font=("Segoe UI", 11)); txt.pack(side="left", fill="both", expand=True)
            ttk.Button(box, text="COPY", command=lambda t=txt: self.copy(t.get("1.0", "end-1c"))).pack(side="right", padx=6)
            self.result_boxes[lang] = txt

    def set_status(self, text): self.status.config(text=text)

    def paste(self):
        try:
            self.input.delete("1.0", "end"); self.input.insert("1.0", self.root.clipboard_get())
        except Exception: pass
        self.input.focus_set()

    def clear(self):
        self.input.delete("1.0", "end")
        for b in self.result_boxes.values(): b.delete("1.0", "end")
        self.set_status("Ready")

    def translate_all(self):
        text = self.input.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning(APP_NAME, "Paste or type some copy first."); return
        self.set_status("Translating…")
        for b in self.result_boxes.values(): b.delete("1.0", "end")
        def work():
            for lang, box in self.result_boxes.items():
                result = translate_text(text, lang)
                self.root.after(0, lambda b=box, r=result: b.insert("1.0", r))
            self.root.after(0, lambda: self.set_status("Done"))
        threading.Thread(target=work, daemon=True).start()

    def copy(self, text):
        if text:
            self.root.clipboard_clear(); self.root.clipboard_append(text); self.root.update()

    def copy_all(self):
        parts=[]
        for lang, box in self.result_boxes.items():
            v=box.get("1.0", "end-1c").strip()
            if v: parts.append(f"{lang}:\n{v}")
        self.copy("\n\n".join(parts))

    def copy_quick(self): self.copy(self.quick.get("1.0", "end-1c"))

    def schedule_transliteration(self, event=None):
        if self.typing_after:
            try: self.root.after_cancel(self.typing_after)
            except Exception: pass
        # Convert on space/enter immediately; also convert the current word after a short pause.
        delay = 80 if event and event.keysym in ("space", "Return", "KP_Enter", ".", ",", "!", "?", ";", ":") else 550
        self.typing_after = self.root.after(delay, self.do_transliteration)

    def do_transliteration(self):
        self.typing_after = None
        text = self.quick.get("1.0", "end-1c")
        if not text.strip(): return
        # Work on only the final Roman word so earlier converted words remain untouched.
        pos = self.quick.index("insert")
        line = self.quick.get("1.0", pos)
        import re
        m = re.search(r"([A-Za-z][A-Za-z0-9'_-]*)$", line)
        if not m: return
        word = m.group(1)
        start = f"1.0+{m.start(1)}c"
        lang = self.type_lang.get()
        result = transliterate(word, lang)
        if result != word and result.strip():
            self.quick.delete(start, pos)
            self.quick.insert(start, result)
            self.quick.mark_set("insert", f"{start}+{len(result)}c")

    def start_global_hotkey(self):
        # A real Windows message loop is required for RegisterHotKey. It runs in a daemon thread,
        # so Ctrl+Shift+A works even when another app has focus and without admin rights.
        if os.name != "nt": return
        def worker():
            try:
                import ctypes
                from ctypes import wintypes
                user32 = ctypes.windll.user32
                MOD_CONTROL, MOD_SHIFT, VK_A = 0x0002, 0x0004, 0x41
                hotkey_id = 777
                if not user32.RegisterHotKey(None, hotkey_id, MOD_CONTROL | MOD_SHIFT, VK_A):
                    return
                msg = wintypes.MSG()
                while not self.hotkey_stop:
                    result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                    if result <= 0: break
                    if msg.message == 0x0312 and msg.wParam == hotkey_id:
                        self.root.after(0, self.show_from_hotkey)
                user32.UnregisterHotKey(None, hotkey_id)
            except Exception:
                pass
        self.hotkey_thread = threading.Thread(target=worker, daemon=True)
        self.hotkey_thread.start()

    def show_from_hotkey(self):
        try:
            self.root.deiconify(); self.root.lift(); self.root.attributes("-topmost", True); self.root.after(250, lambda: self.root.attributes("-topmost", False)); self.root.focus_force(); self.quick.focus_set()
        except Exception: pass

    def on_close(self):
        self.hotkey_stop = True
        try: self.root.destroy()
        except Exception: pass

    def settings(self):
        win=tk.Toplevel(self.root); win.title("Settings"); win.geometry("420x460"); win.configure(bg=self.COLORS["panel"])
        ttk.Label(win,text="Languages",font=("Segoe UI",12,"bold")).pack(anchor="w",padx=18,pady=12)
        checks={}
        for l in LANGS:
            v=tk.BooleanVar(value=l in self.cfg.get("languages", list(LANGS))); checks[l]=v
            ttk.Checkbutton(win,text=l,variable=v).pack(anchor="w",padx=30,pady=3)
        ttk.Label(win,text="Global shortcut",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=18,pady=(18,5))
        sh=tk.StringVar(value=self.cfg.get("shortcut","Ctrl+Shift+A"))
        ttk.Entry(win,textvariable=sh).pack(fill="x",padx=18)
        ttk.Label(win,text="Default: Ctrl+Shift+A",style="Muted.TLabel").pack(anchor="w",padx=18,pady=5)
        def save():
            self.cfg["languages"]=[l for l,v in checks.items() if v.get()] or list(LANGS)
            self.cfg["shortcut"]=sh.get(); save_config(self.cfg); self.build_results(); win.destroy()
        ttk.Button(win,text="Save",style="Accent.TButton",command=save).pack(pady=18)

if __name__ == "__main__":
    root=tk.Tk()
    app=App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

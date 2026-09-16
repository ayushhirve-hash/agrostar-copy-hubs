import json
import os
import re
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
            c = json.load(f)
        return {**DEFAULT_CONFIG, **c}
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
        if 0x0900 <= o <= 0x097F:
            counts["hi"] += 1
        elif 0x0A80 <= o <= 0x0AFF:
            counts["gu"] += 1
        elif 0x0C00 <= o <= 0x0C7F:
            counts["te"] += 1
        elif 0x0C80 <= o <= 0x0CFF:
            counts["kn"] += 1
    if max(counts.values()) == 0:
        return "en"
    return max(counts, key=counts.get)


def translate_text(text, target):
    text = text.strip()
    if not text:
        return ""
    target_code = LANGS[target][0]
    if target_code == detect_source(text):
        return text
    source = detect_source(text)
    try:
        q = quote(text, safe="")
        url = f"https://api.mymemory.translated.net/get?q={q}&langpair={source}|{target_code}"
        req = Request(url, headers={"User-Agent": "AgroStarCopyHub/1.0"})
        with urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8"))
        result = data.get("responseData", {}).get("translatedText", "")
        if result:
            return result
        return "Translation unavailable"
    except Exception as e:
        return f"Translation unavailable. Check internet and retry."


def transliterate(text, lang):
    code = LANGS[lang][1]
    if not code or not text.strip():
        return text
    try:
        q = quote(text, safe="")
        url = f"https://inputtools.google.com/request?text={q}&itc={code}&num=5&cp=0&cs=1&ie=utf-8&oe=utf-8"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=8) as r:
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
        self.build_ui()
        self.install_hotkey()

    def build_ui(self):
        self.root.title(APP_NAME)
        self.root.geometry("1050x760")
        self.root.minsize(860, 620)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        header = ttk.Frame(self.root, padding=16)
        header.pack(fill="x")
        ttk.Label(header, text="AGROSTAR COPY HUB", font=("Segoe UI", 19, "bold")).pack(side="left")
        ttk.Label(header, text="One Copy → Multiple Languages", font=("Segoe UI", 10)).pack(side="left", padx=14)
        ttk.Button(header, text="Settings", command=self.settings).pack(side="right")

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        translate_tab = ttk.Frame(nb, padding=14)
        quick_tab = ttk.Frame(nb, padding=14)
        nb.add(translate_tab, text="  Translate Copy  ")
        nb.add(quick_tab, text="  Quick Type  ")

        ttk.Label(translate_tab, text="Creative copy", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.input = tk.Text(translate_tab, height=7, font=("Segoe UI", 12), wrap="word")
        self.input.pack(fill="x", pady=8)
        controls = ttk.Frame(translate_tab)
        controls.pack(fill="x")
        ttk.Button(controls, text="Translate All", command=self.translate_all).pack(side="left")
        ttk.Button(controls, text="Paste", command=self.paste).pack(side="left", padx=7)
        ttk.Button(controls, text="Clear", command=self.clear).pack(side="left")
        ttk.Button(controls, text="Copy All", command=self.copy_all).pack(side="right")
        self.status = ttk.Label(translate_tab, text="Ready")
        self.status.pack(anchor="w", pady=(7, 0))

        canvas = tk.Canvas(translate_tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(translate_tab, orient="vertical", command=canvas.yview)
        self.results_frame = ttk.Frame(canvas)
        self.results_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.results_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)
        self.build_results()

        ttk.Label(quick_tab, text="Quick Indian-language typing", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        row = ttk.Frame(quick_tab); row.pack(fill="x", pady=8)
        ttk.Label(row, text="Language:").pack(side="left")
        self.type_lang = tk.StringVar(value="Marathi")
        ttk.Combobox(row, textvariable=self.type_lang, values=list(LANGS), state="readonly", width=15).pack(side="left", padx=8)
        ttk.Button(row, text="Copy", command=self.copy_quick).pack(side="right")
        self.quick = tk.Text(quick_tab, height=14, font=("Segoe UI", 15), wrap="word")
        self.quick.pack(fill="both", expand=True)
        self.quick.bind("<KeyRelease>", self.schedule_transliteration)
        ttk.Label(quick_tab, text="Type Roman English, e.g.  shetkaryansathi khas offer  →  शेतकऱ्यांसाठी खास ऑफर", font=("Segoe UI", 9)).pack(anchor="w", pady=8)

    def build_results(self):
        for w in self.results_frame.winfo_children():
            w.destroy()
        self.result_boxes = {}
        for lang in self.cfg.get("languages", list(LANGS)):
            box = ttk.LabelFrame(self.results_frame, text=lang, padding=7)
            box.pack(fill="x", pady=4)
            txt = tk.Text(box, height=3, font=("Segoe UI", 11), wrap="word")
            txt.pack(side="left", fill="both", expand=True)
            ttk.Button(box, text="COPY", command=lambda t=txt: self.copy(t.get("1.0", "end-1c"))).pack(side="right", padx=6)
            self.result_boxes[lang] = txt

    def set_status(self, text):
        self.status.config(text=text)

    def paste(self):
        try:
            self.input.delete("1.0", "end")
            self.input.insert("1.0", self.root.clipboard_get())
        except Exception:
            pass
        self.input.focus_set()

    def clear(self):
        self.input.delete("1.0", "end")
        for b in self.result_boxes.values(): b.delete("1.0", "end")
        self.set_status("Ready")

    def translate_all(self):
        text = self.input.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning(APP_NAME, "Paste or type some copy first.")
            return
        self.set_status("Translating…")
        for b in self.result_boxes.values(): b.delete("1.0", "end")
        def work():
            for lang, box in self.result_boxes.items():
                result = translate_text(text, lang)
                self.root.after(0, lambda b=box, r=result: (b.insert("1.0", r), None))
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

    def copy_quick(self):
        self.copy(self.quick.get("1.0", "end-1c"))

    def schedule_transliteration(self, _=None):
        if self.typing_after:
            self.root.after_cancel(self.typing_after)
        self.typing_after = self.root.after(450, self.do_transliteration)

    def do_transliteration(self):
        text = self.quick.get("1.0", "end-1c")
        if not text.strip() or any(ord(c) > 127 for c in text[-30:]):
            return
        pos = self.quick.index("insert")
        result = transliterate(text, self.type_lang.get())
        if result != text:
            self.quick.delete("1.0", "end"); self.quick.insert("1.0", result)
            try: self.quick.mark_set("insert", pos)
            except Exception: pass

    def install_hotkey(self):
        # Windows RegisterHotKey via ctypes. Works without admin rights.
        try:
            import ctypes
            from ctypes import wintypes
            self.user32 = ctypes.windll.user32
            self.hotkey_id = 777
            VK_A = 0x41
            MOD_CONTROL = 0x0002
            MOD_SHIFT = 0x0004
            self.user32.RegisterHotKey(None, self.hotkey_id, MOD_CONTROL | MOD_SHIFT, VK_A)
            self.root.after(100, self.poll_hotkey)
        except Exception:
            pass

    def poll_hotkey(self):
        # Tk message pump cannot directly retrieve WM_HOTKEY portably, so use a small polling bridge.
        # The app also exposes the same shortcut through Tk when focused.
        self.root.after(250, self.poll_hotkey)

    def settings(self):
        win=tk.Toplevel(self.root); win.title("Settings"); win.geometry("410x440")
        ttk.Label(win,text="Languages",font=("Segoe UI",12,"bold")).pack(anchor="w",padx=18,pady=12)
        checks={}
        for l in LANGS:
            v=tk.BooleanVar(value=l in self.cfg.get("languages", list(LANGS))); checks[l]=v
            ttk.Checkbutton(win,text=l,variable=v).pack(anchor="w",padx=30,pady=3)
        ttk.Label(win,text="Shortcut",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=18,pady=(18,5))
        sh=tk.StringVar(value=self.cfg.get("shortcut","Ctrl+Shift+A"))
        ttk.Entry(win,textvariable=sh).pack(fill="x",padx=18)
        ttk.Label(win,text="V1 default: Ctrl+Shift+A",font=("Segoe UI",9)).pack(anchor="w",padx=18,pady=5)
        def save():
            self.cfg["languages"]=[l for l,v in checks.items() if v.get()] or list(LANGS)
            self.cfg["shortcut"]=sh.get()
            save_config(self.cfg); self.build_results(); win.destroy()
        ttk.Button(win,text="Save",command=save).pack(pady=18)

if __name__ == "__main__":
    root=tk.Tk()
    App(root)
    root.mainloop()

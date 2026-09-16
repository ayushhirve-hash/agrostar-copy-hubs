import json, os, re, queue, threading, tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import quote
from urllib.request import Request, urlopen

APP_NAME="AgroStar Copy Hub"
CONFIG_PATH=os.path.join(os.environ.get("APPDATA",os.path.expanduser("~")),"AgroStarCopyHub","config.json")
LANGS={"Hindi":("hi","hi-t-i0-und"),"Marathi":("mr","mr-t-i0-und"),"Gujarati":("gu","gu-t-i0-und"),"Telugu":("te","te-t-i0-und"),"Kannada":("kn","kn-t-i0-und"),"English":("en",None)}
DEFAULT_CONFIG={"languages":list(LANGS),"shortcut":"Ctrl+Shift+A"}

def load_config():
    try:
        with open(CONFIG_PATH,"r",encoding="utf-8") as f:return {**DEFAULT_CONFIG,**json.load(f)}
    except Exception:return DEFAULT_CONFIG.copy()

def save_config(c):
    os.makedirs(os.path.dirname(CONFIG_PATH),exist_ok=True)
    with open(CONFIG_PATH,"w",encoding="utf-8") as f:json.dump(c,f,ensure_ascii=False,indent=2)

def detect_source(text):
    counts={"hi":0,"gu":0,"te":0,"kn":0,"mr":0}
    for ch in text:
        o=ord(ch)
        if 0x0900<=o<=0x097F:counts["hi"]+=1
        elif 0x0A80<=o<=0x0AFF:counts["gu"]+=1
        elif 0x0C00<=o<=0x0C7F:counts["te"]+=1
        elif 0x0C80<=o<=0x0CFF:counts["kn"]+=1
    return "en" if max(counts.values())==0 else max(counts,key=counts.get)

def translate_text(text,target):
    text=text.strip(); code=LANGS[target][0]; source=detect_source(text)
    if not text:return ""
    if code==source:return text
    try:
        url=f"https://api.mymemory.translated.net/get?q={quote(text,safe='')}&langpair={source}|{code}"
        with urlopen(Request(url,headers={"User-Agent":"AgroStarCopyHub/3.0"}),timeout=12) as r:
            d=json.loads(r.read().decode("utf-8"))
        return d.get("responseData",{}).get("translatedText","") or "Translation unavailable"
    except Exception:return "Translation unavailable. Check internet and retry."

def candidates_for(word,lang):
    code=LANGS[lang][1]
    if not code or not word:return []
    try:
        url=f"https://inputtools.google.com/request?text={quote(word,safe='')}&itc={code}&num=8&cp=0&cs=1&ie=utf-8&oe=utf-8"
        with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=6) as r:
            d=json.loads(r.read().decode("utf-8"))
        if isinstance(d,list) and len(d)>1 and isinstance(d[1],list) and d[1] and isinstance(d[1][0],list):return [str(x) for x in d[1][0][:8]]
    except Exception:pass
    return []

class App:
    def __init__(self,root,background=False):
        self.root=root; self.cfg=load_config(); self.result_boxes={}; self.quick_after=None
        self.candidates=[]; self.candidate_box=None; self.hotkey_stop=False; self.hotkey_thread=None
        self.setup_theme(); self.build_ui(); self.start_global_hotkey()
        if background:self.root.withdraw()

    def setup_theme(self):
        self.root.configure(bg="#101214"); s=ttk.Style(self.root)
        try:s.theme_use("clam")
        except Exception:pass
        bg="#101214"; panel="#181b1f"; field="#22262b"; fg="#F3F5F7"; muted="#AAB2BC"; accent="#F47B20"
        s.configure("TFrame",background=bg); s.configure("TLabel",background=bg,foreground=fg)
        s.configure("Muted.TLabel",background=bg,foreground=muted,font=("Segoe UI",9)); s.configure("Title.TLabel",background=bg,foreground=fg,font=("Segoe UI",19,"bold"))
        s.configure("Subtitle.TLabel",background=bg,foreground=muted,font=("Segoe UI",10)); s.configure("TButton",background="#292e34",foreground=fg,padding=(12,7))
        s.map("TButton",background=[("active","#343a42")]); s.configure("Accent.TButton",background=accent,foreground="#111315",padding=(14,7),font=("Segoe UI",10,"bold"))
        s.configure("TNotebook",background=bg,borderwidth=0); s.configure("TNotebook.Tab",background="#20242a",foreground=muted,padding=(18,9))
        s.map("TNotebook.Tab",background=[("selected","#2b3037")],foreground=[("selected",fg)])
        s.configure("TLabelframe",background=panel,foreground=fg,bordercolor="#343a42"); s.configure("TLabelframe.Label",background=panel,foreground=fg,font=("Segoe UI",10,"bold"))
        s.configure("TCheckbutton",background=panel,foreground=fg); s.configure("TCombobox",fieldbackground=field,background=field,foreground="#111315",arrowcolor="#111315")
        self.C={"bg":bg,"panel":panel,"field":field,"fg":fg,"muted":muted,"accent":accent}

    def text(self,parent,height=5,font=("Segoe UI",12)):
        c=self.C; return tk.Text(parent,height=height,font=font,wrap="word",bg=c["field"],fg=c["fg"],insertbackground=c["fg"],selectbackground="#3b82f6",relief="flat",padx=10,pady=9,highlightthickness=1,highlightbackground="#343a42",highlightcolor=c["accent"])

    def build_ui(self):
        c=self.C; self.root.title(APP_NAME); self.root.geometry("1080x780"); self.root.minsize(880,650)
        h=ttk.Frame(self.root,padding=(18,15)); h.pack(fill="x"); ttk.Label(h,text="AGROSTAR COPY HUB",style="Title.TLabel").pack(side="left"); ttk.Label(h,text="One Copy → Multiple Languages",style="Subtitle.TLabel").pack(side="left",padx=14); ttk.Button(h,text="Settings",command=self.settings).pack(side="right")
        nb=ttk.Notebook(self.root); nb.pack(fill="both",expand=True,padx=16,pady=(0,16)); t=ttk.Frame(nb,padding=14); q=ttk.Frame(nb,padding=14); nb.add(t,text="  Translate Copy  "); nb.add(q,text="  Quick Type  ")
        ttk.Label(t,text="Creative copy",font=("Segoe UI",11,"bold")).pack(anchor="w"); self.input=self.text(t,7); self.input.pack(fill="x",pady=8)
        ctl=ttk.Frame(t); ctl.pack(fill="x"); ttk.Button(ctl,text="Translate All",style="Accent.TButton",command=self.translate_all).pack(side="left"); ttk.Button(ctl,text="Paste",command=self.paste).pack(side="left",padx=7); ttk.Button(ctl,text="Clear",command=self.clear).pack(side="left"); ttk.Button(ctl,text="Copy All",command=self.copy_all).pack(side="right")
        self.status=ttk.Label(t,text="Ready",style="Muted.TLabel"); self.status.pack(anchor="w",pady=(7,0)); canvas=tk.Canvas(t,bg=c["bg"],highlightthickness=0); sb=ttk.Scrollbar(t,orient="vertical",command=canvas.yview); self.results_frame=ttk.Frame(canvas); self.results_frame.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all"))); canvas.create_window((0,0),window=self.results_frame,anchor="nw",tags="results"); canvas.bind("<Configure>",lambda e:canvas.itemconfigure("results",width=e.width)); canvas.configure(yscrollcommand=sb.set); canvas.pack(side="left",fill="both",expand=True,pady=10); sb.pack(side="right",fill="y",pady=10); self.build_results()
        ttk.Label(q,text="Quick Indian-language typing",font=("Segoe UI",11,"bold")).pack(anchor="w"); ttk.Label(q,text="Google Input Tools-style: type Roman English, choose a suggestion, press Space/Enter to commit.",style="Muted.TLabel").pack(anchor="w",pady=(3,8))
        row=ttk.Frame(q); row.pack(fill="x",pady=(0,8)); ttk.Label(row,text="Language:").pack(side="left"); self.type_lang=tk.StringVar(value="Marathi"); cb=ttk.Combobox(row,textvariable=self.type_lang,values=list(LANGS),state="readonly",width=15); cb.pack(side="left",padx=8); cb.bind("<<ComboboxSelected>>",lambda e:self.refresh_candidates()); ttk.Button(row,text="Copy",command=self.copy_quick).pack(side="right")
        self.quick=self.text(q,18,("Segoe UI",16)); self.quick.pack(fill="both",expand=True); self.quick.bind("<KeyRelease>",self.quick_key_release); self.quick.bind("<KeyPress>",self.quick_key_press)
        ttk.Label(q,text="Example: agrostar → ॲग्रोस्टार   |   shetkaryansathi → शेतकऱ्यांसाठी",style="Muted.TLabel").pack(anchor="w",pady=8)

    def build_results(self):
        for w in self.results_frame.winfo_children():w.destroy()
        self.result_boxes={}
        for lang in self.cfg.get("languages",list(LANGS)):
            box=ttk.LabelFrame(self.results_frame,text=lang,padding=7); box.pack(fill="x",pady=4); txt=self.text(box,3,("Segoe UI",11)); txt.pack(side="left",fill="both",expand=True); ttk.Button(box,text="COPY",command=lambda x=txt:self.copy(x.get("1.0","end-1c"))).pack(side="right",padx=6); self.result_boxes[lang]=txt

    def translate_all(self):
        text=self.input.get("1.0","end-1c").strip()
        if not text:messagebox.showwarning(APP_NAME,"Paste or type some copy first.");return
        self.status.config(text="Translating…")
        for b in self.result_boxes.values():b.delete("1.0","end")
        def work():
            for lang,b in self.result_boxes.items():
                r=translate_text(text,lang); self.root.after(0,lambda x=b,v=r:x.insert("1.0",v))
            self.root.after(0,lambda:self.status.config(text="Done"))
        threading.Thread(target=work,daemon=True).start()
    def paste(self):
        try:self.input.delete("1.0","end");self.input.insert("1.0",self.root.clipboard_get())
        except Exception:pass
        self.input.focus_set()
    def clear(self):
        self.input.delete("1.0","end")
        for b in self.result_boxes.values():b.delete("1.0","end")
        self.status.config(text="Ready")
    def copy(self,x):
        if x:self.root.clipboard_clear();self.root.clipboard_append(x);self.root.update()
    def copy_all(self):
        self.copy("\n\n".join(f"{l}:\n{b.get('1.0','end-1c').strip()}" for l,b in self.result_boxes.items() if b.get("1.0","end-1c").strip()))
    def copy_quick(self):self.copy(self.quick.get("1.0","end-1c"))

    def current_word_range(self):
        pos=self.quick.index("insert"); before=self.quick.get("1.0",pos); m=re.search(r"([A-Za-z][A-Za-z0-9'_-]*)$",before)
        if not m:return None,None,""
        return f"1.0+{m.start(1)}c",pos,m.group(1)

    def quick_key_press(self,e):
        if self.candidates and e.keysym in ("space","Return","KP_Enter","Tab"):
            idx=self.selected_candidate(); self.commit_candidate(idx,add_space=e.keysym!="Tab"); return "break"
        if self.candidates and e.char in "12345678":
            i=int(e.char)-1
            if i<len(self.candidates):self.commit_candidate(i,add_space=True);return "break"
        if self.candidates and e.keysym=="Down":self.move_candidate(1);return "break"
        if self.candidates and e.keysym=="Up":self.move_candidate(-1);return "break"
        if e.keysym=="Escape":self.hide_candidates()

    def quick_key_release(self,e):
        if e.keysym in ("space","Return","KP_Enter","Tab","Up","Down","Escape"):return
        self.refresh_candidates()

    def refresh_candidates(self):
        if self.quick_after:
            try:self.root.after_cancel(self.quick_after)
            except Exception:pass
        self.quick_after=self.root.after(180,self.fetch_candidates)

    def fetch_candidates(self):
        self.quick_after=None; start,end,word=self.current_word_range(); lang=self.type_lang.get()
        if not word or lang=="English":self.hide_candidates();return
        def work():
            items=candidates_for(word,lang); self.root.after(0,lambda:self.show_candidates(items))
        threading.Thread(target=work,daemon=True).start()

    def show_candidates(self,items):
        self.hide_candidates(); self.candidates=items
        if not items:return
        box=tk.Toplevel(self.root); self.candidate_box=box; box.overrideredirect(True); box.attributes("-topmost",True)
        lb=tk.Listbox(box,font=("Segoe UI",12),bg="#171a1e",fg="#f2f4f6",selectbackground="#F47B20",selectforeground="#111315",relief="flat",height=min(8,len(items)),width=max(28,min(48,max(len(x) for x in items)+5))); lb.pack(padx=1,pady=1); self.candidate_list=lb
        for i,x in enumerate(items):lb.insert("end",f"{i+1}.  {x}")
        lb.selection_set(0); lb.activate(0)
        try:
            b=self.quick.bbox("insert"); x=self.quick.winfo_rootx()+b[0]; y=self.quick.winfo_rooty()+b[1]+b[3]+4
        except Exception:x=self.quick.winfo_rootx()+10;y=self.quick.winfo_rooty()+40
        box.geometry(f"+{x}+{y}")

    def selected_candidate(self):
        if not self.candidates:return 0
        s=self.candidate_list.curselection() if self.candidate_box else ()
        return s[0] if s else 0
    def move_candidate(self,d):
        if not self.candidate_box:return
        i=max(0,min(len(self.candidates)-1,self.selected_candidate()+d)); self.candidate_list.selection_clear(0,"end"); self.candidate_list.selection_set(i); self.candidate_list.activate(i)
    def commit_candidate(self,i,add_space=True):
        start,end,word=self.current_word_range()
        if not word or not self.candidates:return
        chosen=self.candidates[max(0,min(i,len(self.candidates)-1))]; self.quick.delete(start,end); self.quick.insert(start,chosen+(" " if add_space else "")); self.quick.mark_set("insert",f"{start}+{len(chosen)+(1 if add_space else 0)}c"); self.hide_candidates(); self.quick.focus_set()
    def hide_candidates(self):
        if self.candidate_box:
            try:self.candidate_box.destroy()
            except Exception:pass
        self.candidate_box=None; self.candidates=[]

    def start_global_hotkey(self):
        if os.name!="nt":return
        def worker():
            try:
                import ctypes
                from ctypes import wintypes
                u=ctypes.windll.user32; MOD_CONTROL=2; MOD_SHIFT=4; VK_A=0x41; ID=7731
                if not u.RegisterHotKey(None,ID,MOD_CONTROL|MOD_SHIFT,VK_A):return
                msg=wintypes.MSG()
                while not self.hotkey_stop:
                    r=u.GetMessageW(ctypes.byref(msg),None,0,0)
                    if r<=0:break
                    if msg.message==0x0312 and msg.wParam==ID:self.root.after(0,self.show_hotkey)
                u.UnregisterHotKey(None,ID)
            except Exception:pass
        self.hotkey_thread=threading.Thread(target=worker,daemon=True);self.hotkey_thread.start()
    def show_hotkey(self):
        self.root.deiconify();self.root.state("normal");self.root.lift();self.root.attributes("-topmost",True);self.root.after(250,lambda:self.root.attributes("-topmost",False));self.root.focus_force();self.quick.focus_set()

    def settings(self):
        w=tk.Toplevel(self.root);w.title("Settings");w.geometry("420x430");w.configure(bg=self.C["panel"]);ttk.Label(w,text="Languages",font=("Segoe UI",12,"bold")).pack(anchor="w",padx=18,pady=12);checks={}
        for l in LANGS:
            v=tk.BooleanVar(value=l in self.cfg.get("languages",list(LANGS)));checks[l]=v;ttk.Checkbutton(w,text=l,variable=v).pack(anchor="w",padx=30,pady=3)
        ttk.Label(w,text="Global shortcut: Ctrl + Shift + A",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=18,pady=(18,5));ttk.Label(w,text="AgroStar Copy Hub runs in the background after Windows starts, so the shortcut can open it anytime.",style="Muted.TLabel",wraplength=360).pack(anchor="w",padx=18,pady=5)
        def save():
            self.cfg["languages"]=[l for l,v in checks.items() if v.get()] or list(LANGS);save_config(self.cfg);self.build_results();w.destroy()
        ttk.Button(w,text="Save",style="Accent.TButton",command=save).pack(pady=18)

if __name__=="__main__":
    root=tk.Tk();app=App(root,"--background" in os.sys.argv);root.protocol("WM_DELETE_WINDOW",lambda:(setattr(app,"hotkey_stop",True),root.destroy()));root.mainloop()

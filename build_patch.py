from pathlib import Path

p = Path("app.py")
s = p.read_text(encoding="utf-8")

needle = 'ttk.Label(q,text="Example: agrostar → ॲग्रोस्टार   |   shetkaryansathi → शेतकऱ्यांसाठी",style="Muted.TLabel").pack(anchor="w",pady=8)'
footer = needle + '\n        footer=ttk.Frame(self.root,padding=(18,0,18,10)); footer.pack(fill="x")\n        ttk.Label(footer,text="◆  Powered by Ayush Hirve",style="Muted.TLabel").pack(side="right")'
if 'Powered by Ayush Hirve' not in s:
    if needle not in s:
        raise SystemExit("Footer insertion point not found")
    s = s.replace(needle, footer, 1)

p.write_text(s, encoding="utf-8")
print("Footer applied")

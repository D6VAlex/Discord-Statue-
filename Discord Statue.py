import customtkinter as ctk
from pypresence import Presence
import time
import threading
import queue

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Status")
        self.geometry("440x720")
        self.minsize(420, 680)
        self.configure(fg_color="#2f3136")

        self.RPC = None
        self.running = False
        self.connecting = False
        self.q = queue.Queue()

        self.app_id_entry = self._field("App ID", "1234567890")
        self.details_entry = self._field("Details", "Playing Minecraft")
        self.state_entry = self._field("State", "Since 3 AM")
        self.image_key_entry = self._field("Large Image Key", "minecraft")
        self.image_text_entry = self._field("Large Image Text", "Survival Mode")

        ctk.CTkLabel(self, text="Time", font=("", 13),
                     text_color="#b9bbbe", anchor="w").pack(fill="x", padx=20, pady=(10, 2))
        trow = ctk.CTkFrame(self, fg_color="transparent")
        trow.pack(fill="x", padx=20, pady=(0, 12))
        self.h_entry = self._time(trow, "0", "h")
        self.m_entry = self._time(trow, "0", "m")
        self.s_entry = self._time(trow, "0", "s")

        brow = ctk.CTkFrame(self, fg_color="transparent")
        brow.pack(fill="x", padx=20, pady=(6, 0))
        self.go_btn = ctk.CTkButton(brow, text="Start", height=46, corner_radius=8,
                                    fg_color="#5865F2", hover_color="#4752c4",
                                    font=("", 14, "bold"), command=self.start)
        self.go_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self.stop_btn = ctk.CTkButton(brow, text="Stop", height=46, corner_radius=8,
                                      fg_color="#40444b", hover_color="#4f545c",
                                      text_color="#ed4245", font=("", 14, "bold"),
                                      command=self.stop_presence)
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=(6, 0))

        self.status_label = ctk.CTkLabel(self, text="Ready", font=("", 12),
                                         text_color="#b9bbbe")
        self.status_label.pack(pady=14)

        self.entries = [self.app_id_entry, self.details_entry, self.state_entry,
                        self.image_key_entry, self.image_text_entry,
                        self.h_entry, self.m_entry, self.s_entry]
        self._bind_paste()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._poll)

    def _field(self, label, ph):
        ctk.CTkLabel(self, text=label, font=("", 13),
                     text_color="#b9bbbe", anchor="w").pack(fill="x", padx=20, pady=(10, 2))
        e = ctk.CTkEntry(self, height=42, corner_radius=6, border_width=0,
                         fg_color="#40444b", text_color="#ffffff",
                         font=("", 13), placeholder_text=ph,
                         placeholder_text_color="#72767d")
        e.pack(fill="x", padx=20)
        return e

    def _time(self, parent, d, unit):
        e = ctk.CTkEntry(parent, width=64, height=42, corner_radius=6,
                         border_width=0, fg_color="#40444b", text_color="#ffffff",
                         font=("", 13), justify="center")
        e.pack(side="left")
        e.insert(0, d)
        ctk.CTkLabel(parent, text=unit, text_color="#b9bbbe",
                     font=("", 13)).pack(side="left", padx=(4, 18))
        return e

    def _inner(self, e):
        for a in ("_entry", "_textbox", "entry", "_tkinter_entry"):
            w = getattr(e, a, None)
            if w is not None and hasattr(w, "insert"):
                return w
        return e

    def _bind_paste(self):
        for e in self.entries:
            inner = self._inner(e)
            for seq in ("<Control-v>", "<Control-V>", "<Command-v>",
                        "<Command-V>", "<Shift-Insert>"):
                inner.bind(seq, lambda ev, w=inner: self._paste(w))

    def _clip(self):
        if HAS_PYPERCLIP:
            try:
                t = pyperclip.paste()
                if t:
                    return t
            except Exception:
                pass
        for ct in (None, "STRING", "UTF8_STRING"):
            try:
                t = self.clipboard_get(type=ct) if ct else self.clipboard_get()
                if t:
                    return t
            except Exception:
                continue
        return None

    def _paste(self, w):
        t = self._clip()
        if not t:
            return "break"
        try:
            w.delete("sel.first", "sel.last")
        except Exception:
            pass
        w.insert("insert", t)
        return "break"

    def _poll(self):
        try:
            while True:
                kind, msg = self.q.get_nowait()
                if kind == "ok":
                    self.go_btn.configure(state="normal", text="Start")
                    self.stop_btn.configure(state="normal")
                    self.status_label.configure(text="Running", text_color="#3ba55c")
                else:
                    self.go_btn.configure(state="normal", text="Start")
                    self.stop_btn.configure(state="normal")
                    self.status_label.configure(text=msg, text_color="#ed4245")
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def start(self):
        if self.connecting:
            return
        cid = self.app_id_entry.get().strip()
        if not cid:
            self.status_label.configure(text="Enter your App ID first", text_color="#ed4245")
            return
        if not cid.isdigit():
            self.status_label.configure(text="App ID must be numbers", text_color="#ed4245")
            return
        if self.running:
            self.stop_presence()

        data = {
            "id": cid,
            "details": self.details_entry.get().strip(),
            "state": self.state_entry.get().strip(),
            "image": self.image_key_entry.get().strip(),
            "image_text": self.image_text_entry.get().strip(),
            "h": self.h_entry.get().strip(),
            "m": self.m_entry.get().strip(),
            "s": self.s_entry.get().strip(),
        }

        self.connecting = True
        self.go_btn.configure(state="disabled", text="Connecting…")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="Connecting…", text_color="#b9bbbe")

        threading.Thread(target=self._work, args=(data,), daemon=True).start()

    def _work(self, d):
        try:
            h = int(d["h"] or 0)
            m = int(d["m"] or 0)
            s = int(d["s"] or 0)
        except Exception:
            h = m = s = 0
        total = min(h * 3600 + m * 60 + s, 360000000)
        start_ts = max(int(time.time() - total), 0)

        p = {
            "details": d["details"] or None,
            "state": d["state"] or None,
            "large_image": d["image"] or None,
            "large_text": d["image_text"] or None,
            "start": start_ts,
        }
        p = {k: v for k, v in p.items() if v is not None}

        try:
            rpc = Presence(d["id"])
            rpc.connect()
            rpc.update(**p)
            self.RPC = rpc
            self.running = True
            self.connecting = False
            self.q.put(("ok", None))
        except Exception as e:
            self.RPC = None
            self.running = False
            self.connecting = False
            raw = str(e).lower()
            if "could not find" in raw or "pipe" in raw:
                msg = "Discord isn't open"
            elif "invalid" in raw or "not found" in raw:
                msg = "Wrong App ID"
            else:
                msg = "Something broke — try again"
            self.q.put(("err", msg))

    def stop_presence(self):
        if self.RPC:
            r = self.RPC
            self.RPC = None
            try:
                r.clear()
                r.close()
            except Exception:
                pass
        self.running = False
        self.connecting = False
        self.go_btn.configure(state="normal", text="Start")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text="Stopped", text_color="#b9bbbe")

    def _close(self):
        self.stop_presence()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
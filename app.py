"""Audiomnesis — local transcription & report drafting. 100% local processing."""
import queue
import threading
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import (Tk, Canvas, Frame, Label, Text, StringVar, PhotoImage,
                     filedialog, messagebox, DISABLED, NORMAL, END, ttk)
import tkinter.font as tkfont

from anamnese import config
from anamnese.docx_filler import fill_report
from anamnese.generator import generate_report
from anamnese.ollama_client import OllamaClient
from anamnese.prompts import STYLE_SKELETONS
from anamnese.recorder import Recorder
from anamnese.transcriber import to_whisper_wav, transcribe

POLL_MS = 200

# Audiomnesis design tokens (assets/tokens.css)
INK = "#1F2A26"
INK2 = "#2E3F39"
PAPER = "#F4EFE6"
PAPER2 = "#E9E1D2"
PAPER3 = "#FBF8F1"     # text-editor field
TOOLBAR = "#EFE9DC"    # toolbar / field wells
LINE = "#D6CDB8"
MUTE = "#7B8580"
SAGE = "#2D5249"
SAGE2 = "#4F8B7A"
CLAY = "#C97B5C"
NEGATIVE = "#B85847"
INFO_BG = "#EAF0EC"    # status callout bg
INFO_LINE = "#CFE0D6"  # status callout border
PLACEHOLDER = "#A79F8C"

PLACEHOLDER_TEXT = ("La transcription apparaîtra ici. Démarrez un enregistrement "
                    "ou ouvrez un fichier audio pour commencer…")


def _pick(families, *candidates, default="TkDefaultFont"):
    for name in candidates:
        if name in families:
            return name
    return default


class App:
    def __init__(self, root):
        self.root = root
        root.title("Audiomnesis — session locale")
        root.geometry("900x760")
        root.configure(bg=PAPER)
        self.events = queue.Queue()
        self.recorder = None
        self.audio_path = None
        self._placeholder = False
        self._pulse = False

        families = set(tkfont.families())
        serif = _pick(families, "Newsreader", "Iowan Old Style", "Georgia")
        sans = _pick(families, "DM Sans", "Helvetica Neue", "Helvetica")
        mono = _pick(families, "JetBrains Mono", "Menlo", "Courier")
        self.F = {
            "display": (serif, 30),
            "eyebrow": (mono, 11, "bold"),
            "mono": (mono, 12),
            "timer": (mono, 22, "bold"),
            "body": (sans, 13),
            "btn": (sans, 13, "bold"),
            "seg": (sans, 12, "bold"),
            "editor": (serif, 15),
            "italic": (serif, 12, "italic"),
        }

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(".", background=PAPER, foreground=INK,
                        font=self.F["body"], borderwidth=0)
        style.configure("Record.TButton", background=CLAY, foreground=PAPER,
                        font=self.F["btn"], padding=(18, 10))
        style.map("Record.TButton", background=[("active", "#B56A4D")])
        style.configure("Recording.TButton", background=NEGATIVE,
                        foreground=PAPER, font=self.F["btn"], padding=(18, 10))
        style.map("Recording.TButton", background=[("active", "#A84C3D")])
        style.configure("Primary.TButton", background=SAGE, foreground=PAPER,
                        font=self.F["btn"], padding=(20, 11))
        style.map("Primary.TButton",
                  background=[("active", "#26463E"), ("disabled", LINE)],
                  foreground=[("disabled", MUTE)])
        style.configure("Ghost.TButton", background=PAPER, foreground=INK2,
                        font=self.F["body"], padding=(13, 8),
                        bordercolor=LINE, borderwidth=1, relief="solid")
        style.map("Ghost.TButton", background=[("active", PAPER2)])
        style.configure("Browse.TButton", background=PAPER2, foreground=MUTE,
                        font=self.F["body"], padding=(10, 8))
        style.map("Browse.TButton", background=[("active", LINE)])
        style.configure("SegOn.TButton", background=SAGE, foreground=PAPER,
                        font=self.F["seg"], padding=(14, 6))
        style.map("SegOn.TButton", background=[("active", SAGE)])
        style.configure("SegOff.TButton", background=PAPER, foreground=MUTE,
                        font=self.F["seg"], padding=(14, 6))
        style.map("SegOff.TButton", background=[("active", PAPER2)])
        style.configure("TEntry", fieldbackground=PAPER, foreground=INK2,
                        bordercolor=LINE, lightcolor=LINE, darkcolor=LINE,
                        insertcolor=SAGE, padding=8)

        # ----- header / brand -----
        header = Frame(root, bg=PAPER)
        header.pack(fill="x", padx=28, pady=(22, 18))
        try:
            self._mark_img = PhotoImage(
                file=str(config.APP_DIR / "assets" / "mark.png")).subsample(2)
            Label(header, image=self._mark_img, bg=PAPER).pack(
                side="left", padx=(0, 14))
        except Exception:
            pass  # missing asset must never block the clinic
        titles = Frame(header, bg=PAPER)
        titles.pack(side="left")
        Label(titles, text="Audiomnesis", font=self.F["display"], bg=PAPER,
              fg=INK).pack(anchor="w")
        sub = Frame(titles, bg=PAPER)
        sub.pack(anchor="w", pady=(4, 0))
        Label(sub, text="TRANSCRIPTION & PRÉ-RÉDACTION · ",
              font=self.F["eyebrow"], bg=PAPER, fg=MUTE).pack(side="left")
        Label(sub, text="100 % LOCAL", font=self.F["eyebrow"], bg=PAPER,
              fg=SAGE).pack(side="left")

        # ----- transport toolbar (well) -----
        bar = Frame(root, bg=TOOLBAR, highlightbackground=LINE,
                    highlightthickness=1)
        bar.pack(fill="x", padx=28, pady=(0, 12))
        inner = Frame(bar, bg=TOOLBAR)
        inner.pack(fill="x", padx=12, pady=10)
        self.record_btn = ttk.Button(inner, text="●  Enregistrer",
                                     style="Record.TButton",
                                     command=self.toggle_record)
        self.record_btn.pack(side="left")
        self.timer_var = StringVar(value="00:00")
        self.timer_lbl = Label(inner, textvariable=self.timer_var,
                               font=self.F["timer"], bg=TOOLBAR, fg=INK)
        self.timer_lbl.pack(side="left", padx=14)
        Frame(inner, bg=LINE, width=1, height=30).pack(side="left", padx=(0, 12))
        ttk.Button(inner, text="♪  Ouvrir un audio…", style="Ghost.TButton",
                   command=self.open_audio).pack(side="left", padx=(0, 8))
        ttk.Button(inner, text="🗎  Ouvrir un texte…", style="Ghost.TButton",
                   command=self.open_text).pack(side="left")
        seg = Frame(inner, bg=PAPER, highlightbackground=LINE,
                    highlightthickness=1)
        seg.pack(side="right")
        self.title_var = StringVar(value="Monsieur XXX")
        self.seg_m = ttk.Button(seg, text="Monsieur", style="SegOn.TButton",
                                command=lambda: self._set_civ("M"))
        self.seg_m.pack(side="left", padx=2, pady=2)
        self.seg_f = ttk.Button(seg, text="Madame", style="SegOff.TButton",
                                command=lambda: self._set_civ("F"))
        self.seg_f.pack(side="left", padx=(0, 2), pady=2)

        # ----- path fields -----
        paths = Frame(root, bg=PAPER)
        paths.pack(fill="x", padx=28)
        paths.columnconfigure(1, weight=1)
        Label(paths, text="MODÈLE", font=self.F["eyebrow"], bg=PAPER,
              fg=MUTE).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.template_var = StringVar(value=str(config.DEFAULT_TEMPLATE))
        ttk.Entry(paths, textvariable=self.template_var,
                  font=self.F["mono"]).grid(row=0, column=1, sticky="ew", pady=3)
        ttk.Button(paths, text="…", style="Browse.TButton", width=2,
                   command=self.pick_template).grid(row=0, column=2, padx=(8, 0))
        Label(paths, text="SORTIE", font=self.F["eyebrow"], bg=PAPER,
              fg=MUTE).grid(row=1, column=0, sticky="w", padx=(0, 10))
        default_out = Path.home() / "Documents" / "CR-anamnese"
        self.outdir_var = StringVar(value=str(default_out))
        ttk.Entry(paths, textvariable=self.outdir_var,
                  font=self.F["mono"]).grid(row=1, column=1, sticky="ew", pady=3)
        ttk.Button(paths, text="…", style="Browse.TButton", width=2,
                   command=self.pick_outdir).grid(row=1, column=2, padx=(8, 0))

        # ----- status callout -----
        callout = Frame(root, bg=INFO_BG, highlightbackground=INFO_LINE,
                        highlightthickness=1)
        callout.pack(fill="x", padx=28, pady=(14, 16))
        dot = Canvas(callout, width=10, height=10, bg=INFO_BG,
                     highlightthickness=0)
        dot.create_oval(1, 1, 9, 9, fill=SAGE2, outline="")
        dot.pack(side="left", padx=(12, 8), pady=10)
        self.status_var = StringVar(
            value="Prêt. Rappel : le patient doit avoir consenti à l'enregistrement.")
        Label(callout, textvariable=self.status_var, anchor="w", bg=INFO_BG,
              fg=INK2, font=self.F["body"]).pack(
            side="left", fill="x", expand=True, pady=8, padx=(0, 12))

        # ----- transcription -----
        head = Frame(root, bg=PAPER)
        head.pack(fill="x", padx=28)
        Label(head, text="TRANSCRIPTION — RELISEZ ET CORRIGEZ AVANT DE GÉNÉRER",
              font=self.F["eyebrow"], bg=PAPER, fg=SAGE).pack(side="left")
        self.words_var = StringVar(value="0 mots")
        Label(head, textvariable=self.words_var, font=self.F["eyebrow"],
              bg=PAPER, fg=MUTE).pack(side="right")
        self.transcript = Text(root, wrap="word", height=12, bg=PAPER3,
                               fg=INK, insertbackground=SAGE,
                               selectbackground="#DDE7E2", selectforeground=INK,
                               font=self.F["editor"], relief="flat",
                               highlightthickness=1, highlightbackground=LINE,
                               highlightcolor=SAGE2, padx=16, pady=14,
                               spacing2=4)
        self.transcript.pack(fill="both", expand=True, padx=28, pady=(6, 0))
        self.transcript.bind("<<Modified>>", self.on_text_modified)
        self.transcript.bind("<FocusIn>", self._clear_placeholder)
        self.transcript.bind("<FocusOut>", self._maybe_placeholder)
        self._show_placeholder()

        # ----- footer -----
        footer = Frame(root, bg=PAPER)
        footer.pack(fill="x", padx=28, pady=14)
        Label(footer, text="Traitement effectué localement — aucune donnée ne "
                           "quitte cet appareil.", font=self.F["italic"],
              bg=PAPER, fg=MUTE).pack(side="left")
        self.generate_btn = ttk.Button(footer, text="✎  Générer le compte-rendu",
                                       style="Primary.TButton", state=DISABLED,
                                       command=self.generate)
        self.generate_btn.pack(side="right")

        root.after(POLL_MS, self.poll)

    # ---------- placeholder handling ----------
    def _show_placeholder(self):
        if not self.transcript.get("1.0", END).strip():
            self._placeholder = True
            self.transcript.insert("1.0", PLACEHOLDER_TEXT)
            self.transcript.config(fg=PLACEHOLDER)
            self.transcript.edit_modified(False)

    def _clear_placeholder(self, _event=None):
        if self._placeholder:
            self._placeholder = False
            self.transcript.delete("1.0", END)
            self.transcript.config(fg=INK)
            self.transcript.edit_modified(False)

    def _maybe_placeholder(self, _event=None):
        if not self._placeholder and not self.transcript.get("1.0", END).strip():
            self._show_placeholder()

    def _real_text(self):
        return "" if self._placeholder else self.transcript.get("1.0", END).strip()

    # ---------- UI helpers ----------
    def _set_civ(self, civ):
        self.title_var.set("Monsieur XXX" if civ == "M" else "Madame XXX")
        self.seg_m.config(style="SegOn.TButton" if civ == "M" else "SegOff.TButton")
        self.seg_f.config(style="SegOn.TButton" if civ == "F" else "SegOff.TButton")

    def set_status(self, msg):
        self.events.put(("status", msg))

    def poll(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "status":
                    self.status_var.set(payload)
                elif kind == "transcript":
                    self._clear_placeholder()
                    self.transcript.delete("1.0", END)
                    self.transcript.insert("1.0", payload)
                    self.transcript.config(fg=INK)
                    self.generate_btn.config(state=NORMAL)
                    self.status_var.set("Transcription terminée. Relisez, "
                                        "corrigez, puis générez le compte-rendu.")
                elif kind == "done":
                    self.generate_btn.config(state=NORMAL)
                    messagebox.showinfo("Terminé", payload)
                elif kind == "error":
                    self.generate_btn.config(state=NORMAL)
                    messagebox.showerror("Erreur", payload)
        except queue.Empty:
            pass
        if self.recorder is not None:
            s = self.recorder.elapsed_seconds()
            self.timer_var.set(f"{s // 60:02d}:{s % 60:02d}")
            self._pulse = not self._pulse
            self.record_btn.config(
                text=("●  Arrêter" if self._pulse else "○  Arrêter"))
        self.root.after(POLL_MS, self.poll)

    def run_bg(self, fn):
        def wrapper():
            try:
                fn()
            except Exception:
                self.events.put(("error", traceback.format_exc(limit=3)))
        threading.Thread(target=wrapper, daemon=True).start()

    # ---------- actions ----------
    def pick_template(self):
        p = filedialog.askopenfilename(filetypes=[("Word", "*.docx")])
        if p:
            self.template_var.set(p)

    def pick_outdir(self):
        p = filedialog.askdirectory()
        if p:
            self.outdir_var.set(p)

    def toggle_record(self):
        if self.recorder is None:
            try:
                self.recorder = Recorder()
                self.audio_path = self.recorder.start()
            except Exception as e:
                self.recorder = None
                messagebox.showerror(
                    "Micro indisponible",
                    "Impossible d'accéder au micro. Vérifiez :\nRéglages Système"
                    " → Confidentialité et sécurité → Microphone,\npuis autorisez"
                    f" Audiomnesis.\n\nDétail : {e}")
                return
            self.record_btn.config(text="●  Arrêter", style="Recording.TButton")
            self.timer_lbl.config(fg=NEGATIVE)
            self.set_status(f"Enregistrement en cours → {self.audio_path.name}")
        else:
            rec, self.recorder = self.recorder, None
            wav = rec.stop()
            self.record_btn.config(text="●  Enregistrer", style="Record.TButton")
            self.timer_lbl.config(fg=INK)
            self.transcribe_file(wav, already_16k=True)

    def open_audio(self):
        p = filedialog.askopenfilename(
            filetypes=[("Audio", "*.wav *.mp3 *.m4a *.aiff *.aac *.ogg *.flac")])
        if p:
            self.transcribe_file(Path(p), already_16k=False)

    def open_text(self):
        """Third input mode: an existing transcript/notes text file."""
        p = filedialog.askopenfilename(
            filetypes=[("Texte", "*.txt *.md"), ("Tous", "*.*")])
        if not p:
            return
        try:
            content = Path(p).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = Path(p).read_text(encoding="latin-1")
        self.events.put(("transcript", content))

    def on_text_modified(self, _event):
        self.transcript.edit_modified(False)  # reset the flag or it fires once
        text = self._real_text()
        self.words_var.set(f"{len(text.split())} mots" if text else "0 mots")
        self.generate_btn.config(state=NORMAL if text else DISABLED)

    def transcribe_file(self, path, already_16k):
        self.set_status("Transcription en cours… (plusieurs minutes pour une "
                        "consultation complète)")
        self.generate_btn.config(state=DISABLED)
        def job():
            config.RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
            wav = path if already_16k else to_whisper_wav(path, config.RECORDINGS_DIR)
            self.events.put(("transcript", transcribe(wav)))
        self.run_bg(job)

    def generate(self):
        text = self._real_text()
        if not text:
            messagebox.showwarning("Vide", "Aucune transcription à traiter.")
            return
        template = Path(self.template_var.get())
        if not template.exists():
            messagebox.showerror("Modèle introuvable", str(template))
            return
        outdir = Path(self.outdir_var.get())
        outdir.mkdir(parents=True, exist_ok=True)
        title = self.title_var.get()
        self.generate_btn.config(state=DISABLED)

        def job():
            stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            report_dir = outdir / f"CR_{stamp}"
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / f"CR_{stamp}_transcript.txt").write_text(
                text, encoding="utf-8")
            self.set_status("Démarrage du modèle local (Ollama)…")
            client = OllamaClient()
            client.ensure_running()
            try:
                result = generate_report(text, client, STYLE_SKELETONS, title,
                                         progress_cb=self.set_status)
            finally:
                client.unload()  # free ~3 GB of RAM immediately
            out_docx = report_dir / f"CR_{stamp}.docx"
            fill_report(template, out_docx, result.intro_text,
                        result.section_texts, result.header_fields)
            msg = f"Compte-rendu écrit :\n{out_docx}"
            if result.no_info:
                msg += "\n\nSections sans information dans l'entretien :\n- " \
                       + "\n- ".join(result.no_info)
            if result.failed:
                msg += "\n\nSections en échec (à rédiger à la main) :\n- " \
                       + "\n- ".join(result.failed)
            self.events.put(("done", msg))
        self.run_bg(job)


if __name__ == "__main__":
    root = Tk()
    App(root)
    root.mainloop()

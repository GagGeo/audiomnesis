"""Audiomnesis — local transcription & report drafting. 100% local processing."""
import queue
import threading
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import (Tk, Frame, Label, Text, StringVar, PhotoImage,
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

# Psykick design tokens (design_handoff_psykick_brand/tokens.css)
INK = "#1F2A26"
INK2 = "#2E3F39"
PAPER = "#F4EFE6"
PAPER2 = "#E9E1D2"
LINE = "#D6CDB8"
MUTE = "#7B8580"
SAGE = "#2D5249"
SAGE2 = "#4F8B7A"
SAGE_TINT = "#DDE7E2"
CLAY = "#C97B5C"


def _pick(families, *candidates, default="TkDefaultFont"):
    for name in candidates:
        if name in families:
            return name
    return default


class App:
    def __init__(self, root):
        self.root = root
        root.title("Audiomnesis — transcription locale")
        root.geometry("860x680")
        root.configure(bg=PAPER)
        self.events = queue.Queue()
        self.recorder = None
        self.audio_path = None

        families = set(tkfont.families())
        serif = _pick(families, "Newsreader", "Iowan Old Style", "Georgia")
        sans = _pick(families, "DM Sans", "Helvetica Neue", "Helvetica")
        self._fonts = {
            "title": (serif, 24),
            "eyebrow": (sans, 10, "bold"),
            "body": (sans, 12),
            "label": (sans, 10, "bold"),
            "btn": (sans, 12, "bold"),
            "timer": (sans, 16, "bold"),
        }

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(".", background=PAPER, foreground=INK,
                        font=self._fonts["body"], borderwidth=0)
        style.configure("Record.TButton", background=CLAY, foreground=PAPER,
                        font=self._fonts["btn"], padding=(18, 10))
        style.map("Record.TButton", background=[("active", "#B56A4D")])
        style.configure("Primary.TButton", background=SAGE, foreground=PAPER,
                        font=self._fonts["btn"], padding=(18, 10))
        style.map("Primary.TButton",
                  background=[("active", SAGE2), ("disabled", LINE)],
                  foreground=[("disabled", MUTE)])
        style.configure("Ghost.TButton", background=PAPER2, foreground=INK2,
                        font=self._fonts["body"], padding=(12, 8))
        style.map("Ghost.TButton", background=[("active", SAGE_TINT)])
        style.configure("TRadiobutton", background=PAPER, foreground=INK)
        style.map("TRadiobutton", background=[("active", PAPER)])
        style.configure("TEntry", fieldbackground=PAPER, foreground=INK,
                        bordercolor=LINE, lightcolor=LINE, darkcolor=LINE,
                        padding=6)

        # --- header: mark + wordmark ---
        header = Frame(root, bg=PAPER)
        header.pack(fill="x", padx=20, pady=(16, 4))
        try:
            self._mark = PhotoImage(file=str(config.APP_DIR / "assets" / "mark.png"))
            Label(header, image=self._mark, bg=PAPER).pack(side="left", padx=(0, 12))
        except Exception:
            pass  # missing asset must never block the clinic
        titles = Frame(header, bg=PAPER)
        titles.pack(side="left")
        Label(titles, text="Audiomnesis", font=self._fonts["title"],
              bg=PAPER, fg=INK2).pack(anchor="w")
        Label(titles, text="TRANSCRIPTION & PRÉ-RÉDACTION — 100 % LOCAL",
              font=self._fonts["eyebrow"], bg=PAPER, fg=MUTE).pack(anchor="w")

        # --- actions row ---
        top = Frame(root, bg=PAPER)
        top.pack(fill="x", padx=20, pady=8)
        self.record_btn = ttk.Button(top, text="●  Enregistrer",
                                     style="Record.TButton",
                                     command=self.toggle_record)
        self.record_btn.pack(side="left")
        self.timer_var = StringVar(value="00:00")
        Label(top, textvariable=self.timer_var, font=self._fonts["timer"],
              bg=PAPER, fg=INK).pack(side="left", padx=12)
        ttk.Button(top, text="Ouvrir un audio…", style="Ghost.TButton",
                   command=self.open_audio).pack(side="left", padx=(12, 4))
        ttk.Button(top, text="Ouvrir un texte…", style="Ghost.TButton",
                   command=self.open_text).pack(side="left")
        self.title_var = StringVar(value="Monsieur XXX")
        ttk.Radiobutton(top, text="Monsieur", variable=self.title_var,
                        value="Monsieur XXX").pack(side="left", padx=(24, 4))
        ttk.Radiobutton(top, text="Madame", variable=self.title_var,
                        value="Madame XXX").pack(side="left")

        # --- paths ---
        paths = Frame(root, bg=PAPER)
        paths.pack(fill="x", padx=20)
        paths.columnconfigure(1, weight=1)
        Label(paths, text="MODÈLE", font=self._fonts["label"], bg=PAPER,
              fg=MUTE).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.template_var = StringVar(value=str(config.DEFAULT_TEMPLATE))
        ttk.Entry(paths, textvariable=self.template_var).grid(
            row=0, column=1, sticky="ew", pady=2)
        ttk.Button(paths, text="…", style="Ghost.TButton", width=2,
                   command=self.pick_template).grid(row=0, column=2, padx=(6, 0))
        Label(paths, text="SORTIE", font=self._fonts["label"], bg=PAPER,
              fg=MUTE).grid(row=1, column=0, sticky="w", padx=(0, 8))
        default_out = Path.home() / "Documents" / "CR-anamnese"
        self.outdir_var = StringVar(value=str(default_out))
        ttk.Entry(paths, textvariable=self.outdir_var).grid(
            row=1, column=1, sticky="ew", pady=2)
        ttk.Button(paths, text="…", style="Ghost.TButton", width=2,
                   command=self.pick_outdir).grid(row=1, column=2, padx=(6, 0))

        self.status_var = StringVar(
            value="Prêt. Rappel : le patient doit avoir consenti à l'enregistrement.")
        Label(root, textvariable=self.status_var, anchor="w", bg=PAPER,
              fg=MUTE, font=self._fonts["body"]).pack(fill="x", padx=20, pady=6)

        Label(root, text="TRANSCRIPTION — RELISEZ ET CORRIGEZ AVANT DE GÉNÉRER",
              font=self._fonts["eyebrow"], bg=PAPER, fg=MUTE
              ).pack(anchor="w", padx=20)
        self.transcript = Text(root, wrap="word", height=16, bg=PAPER,
                               fg=INK, insertbackground=SAGE,
                               selectbackground=SAGE_TINT, selectforeground=INK,
                               font=(self._fonts["body"][0], 13), relief="flat",
                               highlightthickness=1, highlightbackground=LINE,
                               highlightcolor=SAGE, padx=12, pady=10)
        self.transcript.pack(fill="both", expand=True, padx=20, pady=(4, 8))
        self.transcript.bind("<<Modified>>", self.on_text_modified)

        self.generate_btn = ttk.Button(root, text="Générer le compte-rendu",
                                       style="Primary.TButton", state=DISABLED,
                                       command=self.generate)
        self.generate_btn.pack(pady=(0, 16))
        root.after(POLL_MS, self.poll)

    # ---------- UI helpers ----------
    def set_status(self, msg):
        self.events.put(("status", msg))

    def poll(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "status":
                    self.status_var.set(payload)
                elif kind == "transcript":
                    self.transcript.delete("1.0", END)
                    self.transcript.insert("1.0", payload)
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
            self.record_btn.config(text="■  Stop")
            self.set_status(f"Enregistrement en cours → {self.audio_path.name}")
        else:
            rec, self.recorder = self.recorder, None
            wav = rec.stop()
            self.record_btn.config(text="●  Enregistrer")
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
        has_text = bool(self.transcript.get("1.0", END).strip())
        self.generate_btn.config(state=NORMAL if has_text else DISABLED)

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
        text = self.transcript.get("1.0", END).strip()
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

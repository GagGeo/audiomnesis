"""Anamnèse — local transcription & report drafting. 100% local processing."""
import queue
import threading
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import (Tk, Frame, Button, Label, Entry, Text, StringVar,
                     Radiobutton, filedialog, messagebox, DISABLED, NORMAL, END)

from anamnese import config
from anamnese.docx_filler import fill_report
from anamnese.examples import extract_examples
from anamnese.generator import generate_report
from anamnese.ollama_client import OllamaClient
from anamnese.recorder import Recorder
from anamnese.transcriber import to_whisper_wav, transcribe

POLL_MS = 200


class App:
    def __init__(self, root):
        self.root = root
        root.title("Anamnèse — transcription locale")
        root.geometry("820x640")
        self.events = queue.Queue()
        self.recorder = None
        self.audio_path = None

        top = Frame(root); top.pack(fill="x", padx=12, pady=8)
        self.record_btn = Button(top, text="●  Enregistrer", fg="red",
                                 font=("Helvetica", 16, "bold"),
                                 command=self.toggle_record)
        self.record_btn.pack(side="left")
        self.timer_var = StringVar(value="00:00")
        Label(top, textvariable=self.timer_var,
              font=("Helvetica", 16)).pack(side="left", padx=10)
        Button(top, text="Ouvrir un audio…",
               command=self.open_audio).pack(side="left", padx=10)
        self.title_var = StringVar(value="Monsieur XXX")
        Radiobutton(top, text="Monsieur", variable=self.title_var,
                    value="Monsieur XXX").pack(side="left", padx=(20, 0))
        Radiobutton(top, text="Madame", variable=self.title_var,
                    value="Madame XXX").pack(side="left")

        paths = Frame(root); paths.pack(fill="x", padx=12)
        Label(paths, text="Modèle :").grid(row=0, column=0, sticky="w")
        self.template_var = StringVar(value=str(config.DEFAULT_TEMPLATE))
        Entry(paths, textvariable=self.template_var, width=70).grid(row=0, column=1)
        Button(paths, text="…", command=self.pick_template).grid(row=0, column=2)
        Label(paths, text="Sortie :").grid(row=1, column=0, sticky="w")
        default_out = Path.home() / "Documents" / "CR-anamnese"
        self.outdir_var = StringVar(value=str(default_out))
        Entry(paths, textvariable=self.outdir_var, width=70).grid(row=1, column=1)
        Button(paths, text="…", command=self.pick_outdir).grid(row=1, column=2)

        self.status_var = StringVar(
            value="Prêt. Rappel : le patient doit avoir consenti à l'enregistrement.")
        Label(root, textvariable=self.status_var, anchor="w",
              fg="gray25").pack(fill="x", padx=12, pady=4)

        Label(root, text="Transcription (relisez et corrigez avant de générer) :"
              ).pack(anchor="w", padx=12)
        self.transcript = Text(root, wrap="word", height=18)
        self.transcript.pack(fill="both", expand=True, padx=12, pady=4)

        self.generate_btn = Button(root, text="Générer le compte-rendu",
                                   font=("Helvetica", 14, "bold"),
                                   state=DISABLED, command=self.generate)
        self.generate_btn.pack(pady=8)
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
                    f" Terminal/Python.\n\nDétail : {e}")
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
            (outdir / f"CR_{stamp}_transcript.txt").write_text(
                text, encoding="utf-8")
            self.set_status("Démarrage du modèle local (Ollama)…")
            client = OllamaClient()
            client.ensure_running()
            examples = extract_examples(config.STYLE_EXAMPLE_DOCX)
            result = generate_report(text, client, examples, title,
                                     progress_cb=self.set_status)
            out_docx = outdir / f"CR_{stamp}.docx"
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

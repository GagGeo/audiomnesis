"""Audiomnesis — local transcription & report drafting. 100% local processing.

The FR/EN switch in the header translates the INTERFACE (anamnese/i18n.py).
The REPORT language is chosen separately (Auto/FR/EN) and may differ: Auto
detects it from the transcript. See anamnese/lang.py.
"""
import queue
import threading
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import (Tk, Canvas, Frame, Label, Text, StringVar, PhotoImage,
                     filedialog, messagebox, DISABLED, NORMAL, END, ttk)
import tkinter.font as tkfont

from anamnese import config, i18n, lang as lang_mod, settings, style_examples
from anamnese.docx_filler import fill_report
from anamnese.generator import generate_report
from anamnese.ollama_client import OllamaClient
from anamnese.prompts import skeletons
from anamnese.recorder import Recorder
from anamnese.transcriber import to_whisper_wav, transcribe
from anamnese.ui_widgets import RoundButton, Segmented

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
SAGE_DARK = "#26463E"
CLAY = "#C97B5C"
CLAY_HOVER = "#B56A4D"
NEGATIVE = "#B85847"
NEG_HOVER = "#A84C3D"
INFO_BG = "#EAF0EC"    # status callout bg
INFO_LINE = "#CFE0D6"  # status callout border
PLACEHOLDER = "#A79F8C"


def _pick(families, *candidates, default="TkDefaultFont"):
    for name in candidates:
        if name in families:
            return name
    return default


class App:
    def __init__(self, root, lang=None):
        self.root = root
        self.lang = lang or i18n.load_lang()
        self.T = i18n.STRINGS[self.lang]
        root.title(self.T["app_title"])
        root.geometry("920x780")
        root.configure(bg=PAPER)
        self.events = queue.Queue()
        self.recorder = None
        self.audio_path = None
        self.civ = "M"               # "M" | "F" — report patient designation
        self.report_lang = "auto"    # "auto" | "fr" | "en"
        self._placeholder = False
        self._pulse = False
        self._after_id = None

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
        Label(sub, text=self.T["subtitle_prefix"], font=self.F["eyebrow"],
              bg=PAPER, fg=MUTE).pack(side="left")
        Label(sub, text=self.T["subtitle_local"], font=self.F["eyebrow"],
              bg=PAPER, fg=SAGE).pack(side="left")
        Segmented(header, values=[("fr", "FR"), ("en", "EN")],
                  on_change=self._switch_lang, active=self.lang,
                  parent_bg=PAPER, bg=PAPER, active_bg=SAGE, fg=MUTE,
                  active_fg=PAPER, line=LINE, font=self.F["seg"],
                  padx=10, pady=4).pack(side="right", anchor="n")

        # ----- transport toolbar (well) -----
        bar = Frame(root, bg=TOOLBAR, highlightbackground=LINE,
                    highlightthickness=1)
        bar.pack(fill="x", padx=28, pady=(0, 12))
        inner = Frame(bar, bg=TOOLBAR)
        inner.pack(fill="x", padx=12, pady=10)
        stop_labels = ("●  " + self.T["stop"], "○  " + self.T["stop"])
        self.record_btn = RoundButton(
            inner, text=self.T["record"], command=self.toggle_record,
            bg=CLAY, fg=PAPER, hover_bg=CLAY_HOVER, parent_bg=TOOLBAR,
            font=self.F["btn"], reserve=stop_labels)
        self.record_btn.pack(side="left")
        self.timer_var = StringVar(value="00:00")
        self.timer_lbl = Label(inner, textvariable=self.timer_var,
                               font=self.F["timer"], bg=TOOLBAR, fg=INK)
        self.timer_lbl.pack(side="left", padx=14)
        Frame(inner, bg=LINE, width=1, height=30).pack(side="left", padx=(0, 12))
        RoundButton(inner, text=self.T["open_audio"], command=self.open_audio,
                    bg=PAPER, fg=INK2, hover_bg=PAPER2, parent_bg=TOOLBAR,
                    font=self.F["body"], outline=LINE, padx=14,
                    ).pack(side="left", padx=(0, 8))
        RoundButton(inner, text=self.T["open_text"], command=self.open_text,
                    bg=PAPER, fg=INK2, hover_bg=PAPER2, parent_bg=TOOLBAR,
                    font=self.F["body"], outline=LINE, padx=14,
                    ).pack(side="left")
        self.civ_seg = Segmented(
            inner, values=[("M", self.T["monsieur"]), ("F", self.T["madame"])],
            on_change=self._set_civ, active="M", parent_bg=TOOLBAR, bg=PAPER,
            active_bg=SAGE, fg=MUTE, active_fg=PAPER, line=LINE,
            font=self.F["seg"])
        self.civ_seg.pack(side="right")

        # ----- path fields -----
        paths = Frame(root, bg=PAPER)
        paths.pack(fill="x", padx=28)
        paths.columnconfigure(1, weight=1)
        Label(paths, text=self.T["template_label"], font=self.F["eyebrow"],
              bg=PAPER, fg=MUTE).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.template_var = StringVar(value=str(config.DEFAULT_TEMPLATE))
        ttk.Entry(paths, textvariable=self.template_var,
                  font=self.F["mono"]).grid(row=0, column=1, sticky="ew", pady=3)
        RoundButton(paths, text="…", command=self.pick_template, bg=PAPER2,
                    fg=MUTE, hover_bg=LINE, parent_bg=PAPER,
                    font=self.F["body"], padx=12, pady=7, radius=9
                    ).grid(row=0, column=2, padx=(8, 0))
        Label(paths, text=self.T["output_label"], font=self.F["eyebrow"],
              bg=PAPER, fg=MUTE).grid(row=1, column=0, sticky="w", padx=(0, 10))
        default_out = Path.home() / "Documents" / "CR-anamnese"
        self.outdir_var = StringVar(value=str(default_out))
        ttk.Entry(paths, textvariable=self.outdir_var,
                  font=self.F["mono"]).grid(row=1, column=1, sticky="ew", pady=3)
        RoundButton(paths, text="…", command=self.pick_outdir, bg=PAPER2,
                    fg=MUTE, hover_bg=LINE, parent_bg=PAPER,
                    font=self.F["body"], padx=12, pady=7, radius=9
                    ).grid(row=1, column=2, padx=(8, 0))

        # report language (Auto / FR / EN) — separate from the interface switch
        Label(paths, text=self.T["report_lang_label"], font=self.F["eyebrow"],
              bg=PAPER, fg=MUTE).grid(row=2, column=0, sticky="w",
                                      padx=(0, 10), pady=(6, 0))
        Segmented(paths, values=[("auto", self.T["report_lang_auto"]),
                                 ("fr", "FR"), ("en", "EN")],
                  on_change=self._set_report_lang, active=self.report_lang,
                  parent_bg=PAPER, bg=PAPER2, active_bg=SAGE, fg=MUTE,
                  active_fg=PAPER, line=LINE, font=self.F["seg"]).grid(
            row=2, column=1, sticky="w", pady=(6, 0))

        # style examples folder (feature: learn the clinician's writing style)
        Label(paths, text=self.T["examples_label"], font=self.F["eyebrow"],
              bg=PAPER, fg=MUTE).grid(row=3, column=0, sticky="w", padx=(0, 10))
        self.examples_var = StringVar(value=settings.get("examples_dir", ""))
        ttk.Entry(paths, textvariable=self.examples_var,
                  font=self.F["mono"]).grid(row=3, column=1, sticky="ew", pady=3)
        RoundButton(paths, text="…", command=self.pick_examples, bg=PAPER2,
                    fg=MUTE, hover_bg=LINE, parent_bg=PAPER,
                    font=self.F["body"], padx=12, pady=7, radius=9
                    ).grid(row=3, column=2, padx=(8, 0))
        Label(paths, text=self.T["examples_warn"], font=self.F["italic"],
              bg=PAPER, fg=CLAY, wraplength=820, justify="left").grid(
            row=4, column=1, columnspan=2, sticky="w", pady=(0, 2))

        # ----- status callout -----
        callout = Frame(root, bg=INFO_BG, highlightbackground=INFO_LINE,
                        highlightthickness=1)
        callout.pack(fill="x", padx=28, pady=(14, 16))
        dot = Canvas(callout, width=10, height=10, bg=INFO_BG,
                     highlightthickness=0)
        dot.create_oval(1, 1, 9, 9, fill=SAGE2, outline="")
        dot.pack(side="left", padx=(12, 8), pady=10)
        self.status_var = StringVar(value=self.T["status_ready"])
        Label(callout, textvariable=self.status_var, anchor="w", bg=INFO_BG,
              fg=INK2, font=self.F["body"]).pack(
            side="left", fill="x", expand=True, pady=8, padx=(0, 12))

        # ----- transcription -----
        head = Frame(root, bg=PAPER)
        head.pack(fill="x", padx=28)
        Label(head, text=self.T["transcript_head"], font=self.F["eyebrow"],
              bg=PAPER, fg=SAGE).pack(side="left")
        self.words_var = StringVar(value=f"0 {self.T['words']}")
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
        Label(footer, text=self.T["privacy_note"], font=self.F["italic"],
              bg=PAPER, fg=MUTE).pack(side="left")
        self.generate_btn = RoundButton(
            footer, text=self.T["generate"], command=self.generate,
            bg=SAGE, fg=PAPER, hover_bg=SAGE_DARK, parent_bg=PAPER,
            font=self.F["btn"], padx=20, pady=10,
            disabled_bg=LINE, disabled_fg=MUTE)
        self.generate_btn.set_enabled(False)
        self.generate_btn.pack(side="right")

        self._after_id = root.after(POLL_MS, self.poll)

    # ---------- language ----------
    def _switch_lang(self, lang):
        if self.recorder is not None:
            return  # never rebuild the UI mid-recording
        i18n.save_lang(lang)
        if self._after_id:
            self.root.after_cancel(self._after_id)
        for w in self.root.winfo_children():
            w.destroy()
        App(self.root, lang)

    # ---------- placeholder handling ----------
    def _show_placeholder(self):
        if not self.transcript.get("1.0", END).strip():
            self._placeholder = True
            self.transcript.insert("1.0", self.T["placeholder"])
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
        self.civ = civ

    def _set_report_lang(self, key):
        self.report_lang = key

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
                    self.generate_btn.set_enabled(True)
                    self.status_var.set(self.T["status_transcribed"])
                elif kind == "done":
                    self.generate_btn.set_enabled(True)
                    messagebox.showinfo(self.T["done_title"], payload)
                elif kind == "error":
                    self.generate_btn.set_enabled(True)
                    messagebox.showerror(self.T["error_title"], payload)
        except queue.Empty:
            pass
        if self.recorder is not None:
            s = self.recorder.elapsed_seconds()
            self.timer_var.set(f"{s // 60:02d}:{s % 60:02d}")
            self._pulse = not self._pulse
            dot = "●" if self._pulse else "○"
            self.record_btn.set_text(f"{dot}  {self.T['stop']}")
        self._after_id = self.root.after(POLL_MS, self.poll)

    def run_bg(self, fn):
        def wrapper():
            try:
                fn()
            except Exception:
                self.events.put(("error", traceback.format_exc(limit=3)))
        threading.Thread(target=wrapper, daemon=True).start()

    # ---------- actions ----------
    def pick_template(self):
        p = filedialog.askopenfilename(
            filetypes=[(self.T["filter_word"], "*.docx")])
        if p:
            self.template_var.set(p)

    def pick_outdir(self):
        p = filedialog.askdirectory()
        if p:
            self.outdir_var.set(p)

    def pick_examples(self):
        p = filedialog.askdirectory()
        if p:
            self.examples_var.set(p)
            settings.set("examples_dir", p)

    def toggle_record(self):
        if self.recorder is None:
            try:
                self.recorder = Recorder()
                self.audio_path = self.recorder.start()
            except Exception as e:
                self.recorder = None
                messagebox.showerror(self.T["err_mic_title"],
                                     self.T["err_mic"].format(error=e))
                return
            self.record_btn.set_text("●  " + self.T["stop"])
            self.record_btn.set_colors(bg=NEGATIVE, hover_bg=NEG_HOVER)
            self.timer_lbl.config(fg=NEGATIVE)
            self.set_status(
                self.T["status_recording"].format(name=self.audio_path.name))
        else:
            rec, self.recorder = self.recorder, None
            wav = rec.stop()
            self.record_btn.set_text(self.T["record"])
            self.record_btn.set_colors(bg=CLAY, hover_bg=CLAY_HOVER)
            self.timer_lbl.config(fg=INK)
            self.transcribe_file(wav, already_16k=True)

    def open_audio(self):
        p = filedialog.askopenfilename(
            filetypes=[(self.T["filter_audio"],
                        "*.wav *.mp3 *.m4a *.aiff *.aac *.ogg *.flac")])
        if p:
            self.transcribe_file(Path(p), already_16k=False)

    def open_text(self):
        """Third input mode: an existing transcript/notes text file."""
        p = filedialog.askopenfilename(
            filetypes=[(self.T["filter_text"], "*.txt *.md"),
                       (self.T["filter_all"], "*.*")])
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
        n = len(text.split()) if text else 0
        self.words_var.set(f"{n} {self.T['words']}")
        self.generate_btn.set_enabled(bool(text))

    def transcribe_file(self, path, already_16k):
        self.set_status(self.T["status_transcribing"])
        self.generate_btn.set_enabled(False)
        def job():
            config.RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
            wav = path if already_16k else to_whisper_wav(path, config.RECORDINGS_DIR)
            self.events.put(("transcript", transcribe(wav)))
        self.run_bg(job)

    def generate(self):
        text = self._real_text()
        if not text:
            messagebox.showwarning(self.T["warn_empty_title"],
                                   self.T["warn_empty"])
            return
        rlang = lang_mod.resolve(self.report_lang, text)   # auto -> detected
        template = (config.DEFAULT_TEMPLATE_EN if rlang == "en"
                    else Path(self.template_var.get()))
        if not template.exists():
            messagebox.showerror(self.T["err_template_title"], str(template))
            return
        outdir = Path(self.outdir_var.get())
        outdir.mkdir(parents=True, exist_ok=True)
        title = lang_mod.patient_title(self.civ, rlang)
        examples_dir = self.examples_var.get().strip()
        self.generate_btn.set_enabled(False)

        def job():
            stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            report_dir = outdir / f"CR_{stamp}"
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / f"CR_{stamp}_transcript.txt").write_text(
                text, encoding="utf-8")
            self.set_status(self.T["status_ollama"])
            # Real anonymized reports override the generic skeletons where found.
            real = style_examples.load(examples_dir, rlang)
            examples = {**skeletons(rlang), **real}
            client = OllamaClient()
            client.ensure_running()
            try:
                result = generate_report(text, client, examples, title,
                                         progress_cb=self.set_status, lang=rlang,
                                         example_is_real=bool(real))
            finally:
                client.unload()  # free ~3 GB of RAM immediately
            out_docx = report_dir / f"CR_{stamp}.docx"
            fill_report(template, out_docx, result.intro_text,
                        result.section_texts, result.header_fields, rlang)
            msg = self.T["done_msg"].format(path=out_docx)
            if result.no_info:
                msg += "\n\n" + self.T["done_no_info"] + "\n- " \
                       + "\n- ".join(result.no_info)
            if result.failed:
                msg += "\n\n" + self.T["done_failed"] + "\n- " \
                       + "\n- ".join(result.failed)
            self.events.put(("done", msg))
        self.run_bg(job)


if __name__ == "__main__":
    root = Tk()
    App(root)
    root.mainloop()

"""Canvas-based rounded widgets — Tk's native buttons cannot be rounded."""
import tkinter.font as tkfont
from tkinter import Canvas


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Draw a rounded rectangle as a smoothed polygon; returns the item id."""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class RoundButton(Canvas):
    """Pill button with hover/press feedback and a disabled state.

    reserve: optional list of alternative labels; the button is sized for the
    widest one so later set_text() calls never clip.
    """

    def __init__(self, parent, text, command, bg, fg, hover_bg,
                 parent_bg, font, radius=10, padx=18, pady=9,
                 outline="", disabled_bg=None, disabled_fg=None, reserve=()):
        self._font = tkfont.Font(font=font)
        widths = [self._font.measure(t) for t in (text, *reserve)]
        w = max(widths) + 2 * padx
        h = self._font.metrics("linespace") + 2 * pady
        super().__init__(parent, width=w, height=h, bg=parent_bg,
                         highlightthickness=0, cursor="pointinghand")
        self._colors = {"bg": bg, "fg": fg, "hover": hover_bg,
                        "disabled_bg": disabled_bg or bg,
                        "disabled_fg": disabled_fg or fg}
        self._command = command
        self._enabled = True
        self._rect = round_rect(self, 1, 1, w - 1, h - 1, radius,
                                fill=bg, outline=outline)
        self._label = self.create_text(w // 2, h // 2, text=text,
                                       font=font, fill=fg)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    # -- interaction ------------------------------------------------------
    def _on_enter(self, _e):
        if self._enabled:
            self.itemconfig(self._rect, fill=self._colors["hover"])

    def _on_leave(self, _e):
        fill = self._colors["bg" if self._enabled else "disabled_bg"]
        self.itemconfig(self._rect, fill=fill)

    def _on_press(self, _e):
        if self._enabled:
            self.move(self._label, 0, 1)

    def _on_release(self, e):
        if not self._enabled:
            return
        self.move(self._label, 0, -1)
        inside = 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height()
        if inside and self._command:
            self._command()

    # -- state ------------------------------------------------------------
    def set_text(self, text):
        self.itemconfig(self._label, text=text)

    def set_colors(self, bg=None, fg=None, hover_bg=None):
        if bg:
            self._colors["bg"] = bg
        if fg:
            self._colors["fg"] = fg
        if hover_bg:
            self._colors["hover"] = hover_bg
        if self._enabled:
            self.itemconfig(self._rect, fill=self._colors["bg"])
            self.itemconfig(self._label, fill=self._colors["fg"])

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)
        key = "" if self._enabled else "disabled_"
        self.itemconfig(self._rect, fill=self._colors[key + "bg"
                                                      if key else "bg"])
        self.itemconfig(self._label, fill=self._colors[key + "fg"
                                                       if key else "fg"])
        self.configure(cursor="pointinghand" if self._enabled else "arrow")

    @property
    def enabled(self):
        return self._enabled


class Segmented(Canvas):
    """Rounded segmented control (e.g. Monsieur | Madame, FR | EN).

    values: list of (key, label). on_change(key) fires on selection change;
    the active segment always repaints, so every click gives feedback.
    """

    def __init__(self, parent, values, on_change, active, parent_bg,
                 bg, active_bg, fg, active_fg, line, font,
                 radius=9, padx=14, pady=6, gap=3):
        self._font = tkfont.Font(font=font)
        self._values = list(values)
        self._on_change = on_change
        self.active = active
        seg_w = [self._font.measure(lbl) + 2 * padx for _, lbl in self._values]
        h = self._font.metrics("linespace") + 2 * pady + 2 * gap
        w = sum(seg_w) + gap * (len(self._values) + 1)
        super().__init__(parent, width=w, height=h, bg=parent_bg,
                         highlightthickness=0, cursor="pointinghand")
        self._c = {"bg": bg, "active_bg": active_bg, "fg": fg,
                   "active_fg": active_fg}
        round_rect(self, 1, 1, w - 1, h - 1, radius, fill=bg, outline=line)
        self._segments = []
        x = gap
        for (key, lbl), sw in zip(self._values, seg_w):
            rect = round_rect(self, x, gap, x + sw, h - gap, radius - 2,
                              fill="", outline="")
            txt = self.create_text(x + sw // 2, h // 2, text=lbl, font=font)
            self._segments.append((key, rect, txt, x, x + sw))
            x += sw + gap
        self.bind("<Button-1>", self._click)
        self._paint()

    def _paint(self):
        for key, rect, txt, _x1, _x2 in self._segments:
            on = key == self.active
            self.itemconfig(rect, fill=self._c["active_bg"] if on else "")
            self.itemconfig(txt, fill=self._c["active_fg"] if on
                            else self._c["fg"])

    def _click(self, e):
        for key, _rect, _txt, x1, x2 in self._segments:
            if x1 <= e.x <= x2:
                changed = key != self.active
                self.active = key
                self._paint()
                if changed and self._on_change:
                    self._on_change(key)
                return

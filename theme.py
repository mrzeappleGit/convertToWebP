"""
Synthetic Atelier Design System -- Centralized design tokens and ttk style configuration.

All surface colors, accent colors, typography, and spacing values are defined here.
Every UI module imports from this file so the design language is consistent.
"""

import tkinter as tk
from tkinter import ttk

# ═══════════════════════════════════════════════════════════════════
# Color Scheme Definitions
# ═══════════════════════════════════════════════════════════════════

COLOR_SCHEMES = {
    "Synthetic Atelier": {
        "surface":                  "#111317",
        "surface_container_lowest": "#0d0f12",
        "surface_container_low":    "#1a1c1f",
        "surface_container":        "#1e2023",
        "surface_container_high":   "#282a2e",
        "surface_container_highest":"#333539",
        "surface_bright":           "#3a3d42",
        "primary":                  "#6cdba4",
        "primary_container":        "#3caf7c",
        "secondary":                "#55d8e1",
        "secondary_container":      "#1a3a3d",
        "tertiary":                 "#ffb68d",
        "on_primary":               "#0d0f12",
        "on_surface":               "#e2e2e7",
        "on_surface_variant":       "#8a8d93",
        "outline_variant":          "#3c494a",
        "error":                    "#f2726f",
    },
    "Midnight Blue": {
        "surface":                  "#0b0e18",
        "surface_container_lowest": "#070a12",
        "surface_container_low":    "#111624",
        "surface_container":        "#161b2a",
        "surface_container_high":   "#1e2438",
        "surface_container_highest":"#283046",
        "surface_bright":           "#344058",
        "primary":                  "#5b9cf5",
        "primary_container":        "#3a6ec4",
        "secondary":                "#f5c45b",
        "secondary_container":      "#3d3520",
        "tertiary":                 "#f59b5b",
        "on_primary":               "#070a12",
        "on_surface":               "#dce2f0",
        "on_surface_variant":       "#7e8ba0",
        "outline_variant":          "#2e3a52",
        "error":                    "#f2726f",
    },
    "Obsidian Purple": {
        "surface":                  "#13111a",
        "surface_container_lowest": "#0e0c14",
        "surface_container_low":    "#1c1924",
        "surface_container":        "#211e2a",
        "surface_container_high":   "#2b2735",
        "surface_container_highest":"#363241",
        "surface_bright":           "#413c4e",
        "primary":                  "#b07cf5",
        "primary_container":        "#8352c9",
        "secondary":                "#f07cc3",
        "secondary_container":      "#3d1e35",
        "tertiary":                 "#7cc3f0",
        "on_primary":               "#0e0c14",
        "on_surface":               "#e4e0ec",
        "on_surface_variant":       "#918d9e",
        "outline_variant":          "#3e394d",
        "error":                    "#f2726f",
    },
    "Carbon Ember": {
        "surface":                  "#141210",
        "surface_container_lowest": "#0f0d0b",
        "surface_container_low":    "#1d1a17",
        "surface_container":        "#221f1b",
        "surface_container_high":   "#2d2924",
        "surface_container_highest":"#38342e",
        "surface_bright":           "#454038",
        "primary":                  "#f57a4a",
        "primary_container":        "#c45a2e",
        "secondary":                "#f5c94a",
        "secondary_container":      "#3d3518",
        "tertiary":                 "#4ac9f5",
        "on_primary":               "#0f0d0b",
        "on_surface":               "#ede8e2",
        "on_surface_variant":       "#9e9890",
        "outline_variant":          "#4a4439",
        "error":                    "#f25252",
    },
    "Deep Ocean": {
        "surface":                  "#0c1315",
        "surface_container_lowest": "#080f11",
        "surface_container_low":    "#131d20",
        "surface_container":        "#172225",
        "surface_container_high":   "#1f2d31",
        "surface_container_highest":"#29393e",
        "surface_bright":           "#35474d",
        "primary":                  "#4adce2",
        "primary_container":        "#2ba8ae",
        "secondary":                "#f58472",
        "secondary_container":      "#3d2420",
        "tertiary":                 "#72f5a8",
        "on_primary":               "#080f11",
        "on_surface":               "#dde8ea",
        "on_surface_variant":       "#7e9498",
        "outline_variant":          "#2e4448",
        "error":                    "#f2726f",
    },
    "Monochrome Luxe": {
        "surface":                  "#121212",
        "surface_container_lowest": "#0a0a0a",
        "surface_container_low":    "#1a1a1a",
        "surface_container":        "#1e1e1e",
        "surface_container_high":   "#282828",
        "surface_container_highest":"#333333",
        "surface_bright":           "#404040",
        "primary":                  "#e040fb",
        "primary_container":        "#a020c0",
        "secondary":                "#e040fb",
        "secondary_container":      "#351a3d",
        "tertiary":                 "#fb40a0",
        "on_primary":               "#0a0a0a",
        "on_surface":               "#e8e8e8",
        "on_surface_variant":       "#909090",
        "outline_variant":          "#404040",
        "error":                    "#f2726f",
    },
    "Cyberpunk": {
        "surface":                  "#0a0a12",
        "surface_container_lowest": "#06060e",
        "surface_container_low":    "#111119",
        "surface_container":        "#15151f",
        "surface_container_high":   "#1e1e2c",
        "surface_container_highest":"#28283a",
        "surface_bright":           "#353548",
        "primary":                  "#f0e030",
        "primary_container":        "#b8a820",
        "secondary":                "#ff2a6d",
        "secondary_container":      "#3d0a1e",
        "tertiary":                 "#05d9e8",
        "on_primary":               "#06060e",
        "on_surface":               "#d1f7ff",
        "on_surface_variant":       "#7a8899",
        "outline_variant":          "#2a2a40",
        "error":                    "#ff2a6d",
    },
}

# ═══════════════════════════════════════════════════════════════════
# Active color variables (module-level, updated by set_color_scheme)
# ═══════════════════════════════════════════════════════════════════

_active_scheme_name = "Synthetic Atelier"
_s = COLOR_SCHEMES[_active_scheme_name]

SURFACE                   = _s["surface"]
SURFACE_CONTAINER_LOWEST  = _s["surface_container_lowest"]
SURFACE_CONTAINER_LOW     = _s["surface_container_low"]
SURFACE_CONTAINER         = _s["surface_container"]
SURFACE_CONTAINER_HIGH    = _s["surface_container_high"]
SURFACE_CONTAINER_HIGHEST = _s["surface_container_highest"]
SURFACE_BRIGHT            = _s["surface_bright"]

PRIMARY            = _s["primary"]
PRIMARY_CONTAINER  = _s["primary_container"]
SECONDARY          = _s["secondary"]
SECONDARY_CONTAINER = _s["secondary_container"]
TERTIARY           = _s["tertiary"]
ON_PRIMARY         = _s["on_primary"]
ON_SURFACE         = _s["on_surface"]
ON_SURFACE_VARIANT = _s["on_surface_variant"]
OUTLINE_VARIANT    = _s["outline_variant"]
ERROR              = _s["error"]


def set_color_scheme(name):
    """Update all module-level color variables to the given scheme."""
    global _active_scheme_name
    global SURFACE, SURFACE_CONTAINER_LOWEST, SURFACE_CONTAINER_LOW
    global SURFACE_CONTAINER, SURFACE_CONTAINER_HIGH, SURFACE_CONTAINER_HIGHEST
    global SURFACE_BRIGHT
    global PRIMARY, PRIMARY_CONTAINER, SECONDARY, SECONDARY_CONTAINER
    global TERTIARY, ON_PRIMARY, ON_SURFACE, ON_SURFACE_VARIANT
    global OUTLINE_VARIANT, ERROR

    if name not in COLOR_SCHEMES:
        return
    _active_scheme_name = name
    s = COLOR_SCHEMES[name]
    SURFACE                   = s["surface"]
    SURFACE_CONTAINER_LOWEST  = s["surface_container_lowest"]
    SURFACE_CONTAINER_LOW     = s["surface_container_low"]
    SURFACE_CONTAINER         = s["surface_container"]
    SURFACE_CONTAINER_HIGH    = s["surface_container_high"]
    SURFACE_CONTAINER_HIGHEST = s["surface_container_highest"]
    SURFACE_BRIGHT            = s["surface_bright"]
    PRIMARY            = s["primary"]
    PRIMARY_CONTAINER  = s["primary_container"]
    SECONDARY          = s["secondary"]
    SECONDARY_CONTAINER = s["secondary_container"]
    TERTIARY           = s["tertiary"]
    ON_PRIMARY         = s["on_primary"]
    ON_SURFACE         = s["on_surface"]
    ON_SURFACE_VARIANT = s["on_surface_variant"]
    OUTLINE_VARIANT    = s["outline_variant"]
    ERROR              = s["error"]


def get_active_scheme_name():
    return _active_scheme_name


# ═══════════════════════════════════════════════════════════════════
# Typography  (Section 3 -- Inter with Segoe UI fallback)
# ═══════════════════════════════════════════════════════════════════

FONT_FAMILY   = "Inter"
_FALLBACK     = "Segoe UI"

DISPLAY_SM    = (FONT_FAMILY, 18, "bold")
TITLE_LG      = (FONT_FAMILY, 15, "bold")
TITLE_MD      = (FONT_FAMILY, 13, "bold")
TITLE_SM      = (FONT_FAMILY, 11, "bold")
BODY          = (FONT_FAMILY, 10)
BODY_SM       = (FONT_FAMILY, 9)
LABEL_SM      = (FONT_FAMILY, 9)
LABEL_SM_MONO = ("Consolas", 9)

# ═══════════════════════════════════════════════════════════════════
# Spacing Scale  (Section 5/6 -- rem-based, converted to px)
# ═══════════════════════════════════════════════════════════════════

SP_1  = 4    # 0.4rem  -- tight internal
SP_2  = 8    # intra-row
SP_4  = 16   # standard padding
SP_6  = 22   # comfortable section padding
SP_8  = 28   # 1.75rem -- between list groups / sections
SP_10 = 36   # 2.25rem -- between major functional blocks

# Corner radius token (used where tk allows it, e.g. Canvas rounded rects)
RADIUS_MD = 4


def apply_atelier_theme(root, scheme_name=None):
    """
    Configure every ttk widget style to match the Synthetic Atelier design system.
    Call once after creating the root window and its Style instance.
    If scheme_name is given, activates that color scheme first.
    """
    if scheme_name:
        set_color_scheme(scheme_name)

    # Read current module-level colors
    import theme as _t
    S   = _t.SURFACE
    SCL = _t.SURFACE_CONTAINER_LOWEST
    SCLo= _t.SURFACE_CONTAINER_LOW
    SC  = _t.SURFACE_CONTAINER
    SCH = _t.SURFACE_CONTAINER_HIGH
    SCHi= _t.SURFACE_CONTAINER_HIGHEST
    SB  = _t.SURFACE_BRIGHT
    P   = _t.PRIMARY
    PC  = _t.PRIMARY_CONTAINER
    Se  = _t.SECONDARY
    SeC = _t.SECONDARY_CONTAINER
    Te  = _t.TERTIARY
    OP  = _t.ON_PRIMARY
    OS  = _t.ON_SURFACE
    OSV = _t.ON_SURFACE_VARIANT
    OV  = _t.OUTLINE_VARIANT
    ER  = _t.ERROR

    style = ttk.Style(root)
    style.theme_use("clam")

    # ── Global: kill the dotted focus rectangle on every widget ───
    style.configure(".", focuscolor="", focusthickness=0)

    # ── Frames ────────────────────────────────────────────────────
    style.configure("TFrame", background=SC)
    style.configure("Surface.TFrame", background=S)
    style.configure("Low.TFrame", background=SCLo)
    style.configure("High.TFrame", background=SCH)
    style.configure("Lowest.TFrame", background=SCL)

    # ── Labels ────────────────────────────────────────────────────
    style.configure("TLabel", background=SC, foreground=OS, font=BODY)
    style.configure("Low.TLabel", background=SCLo, foreground=OS, font=BODY)
    style.configure("High.TLabel", background=SCH, foreground=OS, font=BODY)
    style.configure("SectionHeader.TLabel", background=SC, foreground=OSV, font=LABEL_SM)
    style.configure("Dim.TLabel", background=SC, foreground=OSV, font=LABEL_SM)
    style.configure("Title.TLabel", background=SC, foreground=OS, font=TITLE_MD)
    style.configure("DisplaySm.TLabel", background=SCH, foreground=OS, font=DISPLAY_SM)
    style.configure("TabInactive.TLabel", background=SCLo, foreground=OSV, font=BODY)
    style.configure("TabActive.TLabel", background=SCLo, foreground=OS, font=TITLE_SM)
    style.configure("TabHover.TLabel", background=SCH, foreground=OS, font=BODY)
    style.configure("Link.TLabel", background=SCH, foreground=Se, font=BODY_SM)

    # ── LabelFrame (tonal shift, no visible border) ──────────────
    style.configure("TLabelframe", background=SCLo, borderwidth=0, relief="flat")
    style.configure("TLabelframe.Label", background=SCLo, foreground=OSV, font=LABEL_SM)
    style.configure("Card.TLabelframe", background=SCLo, borderwidth=0, relief="flat")
    style.configure("Card.TLabelframe.Label", background=SCLo, foreground=OSV, font=LABEL_SM)

    # ── Buttons ───────────────────────────────────────────────────
    for sname, bg, fg, fnt, pad, abg, dbg in [
        ("TButton",          SCH, Se,  BODY,    (SP_2 + SP_1, SP_1), SCHi, SC),
        ("Primary.TButton",  P,   OP,  BODY,    (SP_2 + SP_1, SP_1), PC,  SCH),
        ("Tertiary.TButton", SC,  OSV, BODY,    (SP_2 + SP_1, SP_1), SCH, SC),
        ("Menu.TButton",     SCLo,OSV, BODY,    (SP_2, SP_1),        SCH, SC),
    ]:
        style.configure(sname, background=bg, foreground=fg, font=fnt, borderwidth=0,
                        relief="flat", padding=pad, lightcolor=bg, darkcolor=bg, bordercolor=bg)
        style.map(sname,
                  background=[("active", abg), ("disabled", dbg)],
                  foreground=[("disabled", OSV)],
                  lightcolor=[("active", abg), ("disabled", dbg)],
                  darkcolor=[("active", abg), ("disabled", dbg)],
                  bordercolor=[("active", abg), ("disabled", dbg)])

    # ── Entry (Obsidian Input) ────────────────────────────────────
    style.configure("TEntry", fieldbackground=SCL, background=SCL, foreground=OS,
                    insertcolor=OS, borderwidth=0, font=BODY,
                    bordercolor=SCL, lightcolor=SCL, darkcolor=SCL,
                    selectbackground=SeC, selectforeground=OS, padding=(SP_2, SP_1))
    style.map("TEntry",
              fieldbackground=[("focus", SCL), ("disabled", SC)],
              background=[("focus", SCL), ("disabled", SC)],
              bordercolor=[("focus", SCL)], lightcolor=[("focus", SCL)], darkcolor=[("focus", SCL)])
    style.layout("TEntry", [
        ("Entry.padding", {"sticky": "nsew", "children": [
            ("Entry.textarea", {"sticky": "nsew"})
        ]})
    ])

    # ── Combobox ──────────────────────────────────────────────────
    style.configure("TCombobox", fieldbackground=SCL, background=SCL, foreground=OS,
                    arrowcolor=OSV, borderwidth=0, font=BODY,
                    bordercolor=SCL, lightcolor=SCL, darkcolor=SCL,
                    arrowsize=14, padding=(SP_2, SP_1))
    style.map("TCombobox",
              fieldbackground=[("readonly", SCL), ("disabled", SC)],
              background=[("readonly", SCL), ("disabled", SC)],
              foreground=[("disabled", OSV)],
              bordercolor=[("focus", SCL)], lightcolor=[("focus", SCL)], darkcolor=[("focus", SCL)])

    # ── Checkbutton ───────────────────────────────────────────────
    style.configure("TCheckbutton", background=SCLo, foreground=OS, font=BODY,
                    indicatorcolor=SCL, indicatorbackground=SCL, borderwidth=0,
                    indicatormargin=4, focuscolor="",
                    bordercolor=SCLo, lightcolor=SCLo, darkcolor=SCLo,
                    upperbordercolor=OSV, lowerbordercolor=OSV)
    style.map("TCheckbutton",
              background=[("active", SCLo)],
              indicatorcolor=[("selected", P), ("active", SCH)],
              upperbordercolor=[("selected", P)], lowerbordercolor=[("selected", P)])

    # ── Radiobutton ───────────────────────────────────────────────
    style.configure("TRadiobutton", background=SCLo, foreground=OS, font=BODY,
                    indicatorcolor=SCL, indicatorbackground=SCL, borderwidth=0,
                    indicatormargin=4, focuscolor="",
                    bordercolor=SCLo, lightcolor=SCLo, darkcolor=SCLo,
                    upperbordercolor=OSV, lowerbordercolor=OSV)
    style.map("TRadiobutton",
              background=[("active", SCLo)],
              indicatorcolor=[("selected", Se), ("active", SCH)],
              upperbordercolor=[("selected", Se)], lowerbordercolor=[("selected", Se)])

    # ── Scale / Slider ────────────────────────────────────────────
    style.configure("TScale", background=SB, troughcolor=SCL, borderwidth=0, relief="flat",
                    lightcolor=SCL, darkcolor=SCL, bordercolor=SCL, focuscolor="",
                    sliderlength=16, sliderthickness=16)
    style.configure("Horizontal.TScale", background=SB, troughcolor=SCL,
                    lightcolor=SCL, darkcolor=SCL, bordercolor=SCL)
    style.map("TScale", background=[("active", OSV)])
    style.layout("Horizontal.TScale", [
        ("Horizontal.Scale.trough", {"sticky": "nsew", "children": [
            ("Horizontal.Scale.slider", {"side": "left", "sticky": ""})
        ]})
    ])

    # ── Progressbar ───────────────────────────────────────────────
    style.configure("TProgressbar", troughcolor=SCLo, background=P, borderwidth=0, relief="flat",
                    lightcolor=SCLo, darkcolor=SCLo, bordercolor=SCLo)
    style.configure("Horizontal.TProgressbar", troughcolor=SCLo, background=P,
                    lightcolor=SCLo, darkcolor=SCLo, bordercolor=SCLo)

    # ── Notebook (Licenses dialog) ────────────────────────────────
    style.configure("TNotebook", background=SC, borderwidth=0,
                    lightcolor=SC, darkcolor=SC, bordercolor=SC)
    style.configure("TNotebook.Tab", background=SCLo, foreground=OSV, font=BODY,
                    padding=(SP_4, SP_2), borderwidth=0,
                    lightcolor=SCLo, darkcolor=SCLo, bordercolor=SCLo)
    style.map("TNotebook.Tab",
              background=[("selected", SC), ("active", SCH)],
              foreground=[("selected", OS)],
              lightcolor=[("selected", SC), ("active", SCH)],
              darkcolor=[("selected", SC), ("active", SCH)],
              bordercolor=[("selected", SC), ("active", SCH)])

    # ── Scrollbar ─────────────────────────────────────────────────
    style.configure("TScrollbar", background=SCH, troughcolor=SC, borderwidth=0, relief="flat",
                    arrowcolor=OSV, lightcolor=SC, darkcolor=SC, bordercolor=SC)
    style.map("TScrollbar", background=[("active", SCHi)])

    # ── Separator (hidden -- design says no structural lines) ─────
    style.configure("TSeparator", background=SC)

    # ── Pill-shaped chip ──────────────────────────────────────────
    style.configure("Chip.TLabel", background=SCH, foreground=OSV, font=BODY_SM,
                    padding=(SP_2 + SP_1, SP_1))
    style.configure("ActiveChip.TLabel", background=SeC, foreground=Se, font=BODY_SM,
                    padding=(SP_2 + SP_1, SP_1))

    # ── Mono label for data values ────────────────────────────────
    style.configure("Mono.TLabel", background=SCLo, foreground=OS, font=LABEL_SM_MONO)
    style.configure("MonoDim.TLabel", background=SCLo, foreground=OSV, font=LABEL_SM_MONO)

    # ── Root window background ────────────────────────────────────
    root.configure(bg=S)

    # ── Kill focus highlight rings globally ──────────────────────
    root.option_add("*TEntry*highlightThickness", 0)
    root.option_add("*TCombobox*highlightThickness", 0)
    root.option_add("*highlightThickness", 0)
    root.option_add("*borderWidth", 0)

    # ── Combobox popdown colors ─────────────────────────────────
    root.option_add("*TCombobox*Listbox.background", SCL)
    root.option_add("*TCombobox*Listbox.foreground", OS)
    root.option_add("*TCombobox*Listbox.selectBackground", SCH)
    root.option_add("*TCombobox*Listbox.selectForeground", OS)
    root.option_add("*TCombobox*Listbox.highlightThickness", 0)
    root.option_add("*TCombobox*Listbox.borderWidth", 0)

    return style


# ═══════════════════════════════════════════════════════════════════
# Shared UI Components
# ═══════════════════════════════════════════════════════════════════

def create_section(parent, title):
    """Tonal section: uppercase label + recessed body frame.  No borders."""
    wrapper = tk.Frame(parent, bg=SURFACE_CONTAINER)
    tk.Label(
        wrapper, text=title, font=LABEL_SM, fg=ON_SURFACE_VARIANT,
        bg=SURFACE_CONTAINER, anchor="w",
    ).pack(fill="x", padx=SP_1, pady=(0, SP_1))
    body = tk.Frame(wrapper, bg=SURFACE_CONTAINER_LOW, padx=SP_4, pady=SP_2 + SP_1)
    body.pack(fill="x")
    return wrapper, body


class PillSelector(tk.Frame):
    """Horizontal row of pill-shaped toggle buttons. Returns selected value via callback."""

    def __init__(self, parent, options, default=None, command=None, bg=SURFACE_CONTAINER_LOW, **kw):
        super().__init__(parent, bg=bg, **kw)
        self._buttons = {}
        self._selected = None
        self._command = command
        self._bg = bg

        for value, label in options:
            btn = tk.Label(
                self, text=label, font=BODY, cursor="hand2",
                padx=SP_4, pady=SP_1 + 2,
                bg=SURFACE_CONTAINER_HIGH, fg=ON_SURFACE_VARIANT,
            )
            btn.pack(side="left", padx=(0, SP_1))
            btn.bind("<Button-1>", lambda e, v=value: self.select(v))
            btn.bind("<Enter>", lambda e, b=btn: self._on_enter(b))
            btn.bind("<Leave>", lambda e, b=btn: self._on_leave(b))
            self._buttons[value] = btn

        if default and default in self._buttons:
            self.select(default, _silent=True)
        elif options:
            self.select(options[0][0], _silent=True)

    def _on_enter(self, btn):
        if btn != self._buttons.get(self._selected):
            btn.configure(bg=SURFACE_CONTAINER_HIGHEST, fg=ON_SURFACE)

    def _on_leave(self, btn):
        if btn != self._buttons.get(self._selected):
            btn.configure(bg=SURFACE_CONTAINER_HIGH, fg=ON_SURFACE_VARIANT)

    def select(self, value, _silent=False):
        if value not in self._buttons:
            return
        self._selected = value
        for v, btn in self._buttons.items():
            if v == value:
                btn.configure(bg=PRIMARY, fg=ON_PRIMARY, font=TITLE_SM)
            else:
                btn.configure(bg=SURFACE_CONTAINER_HIGH, fg=ON_SURFACE_VARIANT, font=BODY)
        if self._command and not _silent:
            self._command(value)

    def get(self):
        return self._selected


class StatusDot(tk.Canvas):
    """Small colored status indicator dot."""

    def __init__(self, parent, color=PRIMARY, size=8, bg=SURFACE_CONTAINER_LOW, **kw):
        super().__init__(parent, width=size, height=size, bg=bg,
                         highlightthickness=0, **kw)
        self._size = size
        self._color = color
        self.create_oval(1, 1, size - 1, size - 1, fill=color, outline="")

    def set_color(self, color):
        self._color = color
        self.delete("all")
        self.create_oval(1, 1, self._size - 1, self._size - 1, fill=color, outline="")


class Tooltip:
    """Hover tooltip in surface-container-highest."""

    _DELAY_MS = 350

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self._tip = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._cancel, add="+")
        widget.bind("<Button>", self._cancel, add="+")

    def _schedule(self, event=None):
        self._cancel()
        self._after_id = self.widget.after(self._DELAY_MS, self._show)

    def _cancel(self, event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        self._hide()

    def _show(self):
        if self._tip:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 6
        y = self.widget.winfo_rooty() + (self.widget.winfo_height() - 24) // 2
        self._tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.configure(bg=SURFACE_CONTAINER_HIGHEST)
        tk.Label(
            tw, text=self.text,
            bg=SURFACE_CONTAINER_HIGHEST, fg=ON_SURFACE,
            font=BODY, padx=SP_2 + SP_1, pady=SP_1,
        ).pack()

    def _hide(self):
        if self._tip:
            self._tip.destroy()
            self._tip = None

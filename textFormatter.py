import tkinter as tk
from tkinter import ttk, messagebox
import re

from theme import (
    SURFACE, SURFACE_CONTAINER, SURFACE_CONTAINER_LOW, SURFACE_CONTAINER_HIGH,
    SURFACE_CONTAINER_HIGHEST, SURFACE_CONTAINER_LOWEST,
    PRIMARY, PRIMARY_CONTAINER, SECONDARY, SECONDARY_CONTAINER,
    ON_PRIMARY, ON_SURFACE, ON_SURFACE_VARIANT, OUTLINE_VARIANT,
    TERTIARY, ERROR,
    FONT_FAMILY, DISPLAY_SM, TITLE_LG, TITLE_MD, TITLE_SM, BODY, BODY_SM, LABEL_SM, LABEL_SM_MONO,
    SP_1, SP_2, SP_4, SP_6, SP_8, SP_10,
    apply_atelier_theme, Tooltip, create_section, PillSelector,
)


FORMAT_OPTIONS = [
    ("slug", "slug"),
    ("lower", "lowercase"),
    ("upper", "UPPERCASE"),
    ("title", "Title Case"),
    ("camel", "camelCase"),
    ("kebab", "kebab-case"),
    ("snake", "snake_case"),
]


class TextFormatterGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self._debounce_id = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = tk.Frame(self, bg=SURFACE_CONTAINER)
        card.grid(row=0, column=0, sticky="n")

        # ── Input section ─────────────────────────────────────────
        in_wrap, inp = create_section(card, "INPUT")
        in_wrap.pack(fill="x", pady=(0, SP_8))

        self.input_text = tk.Text(
            inp, height=6, wrap="word",
            bg=SURFACE_CONTAINER_LOWEST, fg=ON_SURFACE,
            insertbackground=ON_SURFACE,
            font=BODY, bd=0, highlightthickness=0,
            padx=SP_2, pady=SP_2,
        )
        self.input_text.pack(fill="x")

        # Placeholder
        self._placeholder = "Enter text to format..."
        self._placeholder_active = True
        self.input_text.insert("1.0", self._placeholder)
        self.input_text.config(fg=ON_SURFACE_VARIANT)
        self.input_text.bind("<FocusIn>", self._on_focus_in)
        self.input_text.bind("<FocusOut>", self._on_focus_out)

        # Live conversion bindings
        self.input_text.bind("<KeyRelease>", self._on_input_change)
        self.input_text.bind("<Return>", self._on_enter)

        # ── Format section ────────────────────────────────────────
        fmt_wrap, fmt = create_section(card, "FORMAT")
        fmt_wrap.pack(fill="x", pady=(0, SP_8))

        self.pill_selector = PillSelector(
            fmt, FORMAT_OPTIONS, default="slug",
            command=self._on_format_change,
        )
        self.pill_selector.pack(anchor="w")

        # ── Result section ────────────────────────────────────────
        res_wrap, res = create_section(card, "RESULT")
        res_wrap.pack(fill="x", pady=(0, SP_8))

        self.output_text = tk.Text(
            res, height=6, wrap="word",
            bg=SURFACE_CONTAINER_LOWEST, fg=PRIMARY,
            font=BODY, bd=0, highlightthickness=0,
            padx=SP_2, pady=SP_2,
            state="disabled",
        )
        self.output_text.pack(fill="x")

        # ── Bottom row: Copy button + counts ──────────────────────
        bottom = tk.Frame(card, bg=SURFACE_CONTAINER)
        bottom.pack(fill="x")

        ttk.Button(bottom, text="Copy", command=self.copy_to_clipboard).pack(side="left")

        self.count_label = tk.Label(
            bottom, text="0 chars \u00b7 0 words",
            font=LABEL_SM_MONO, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER,
        )
        self.count_label.pack(side="right")

    # ── Placeholder handling ──────────────────────────────────────

    def _on_focus_in(self, event=None):
        if self._placeholder_active:
            self.input_text.delete("1.0", "end")
            self.input_text.config(fg=ON_SURFACE)
            self._placeholder_active = False

    def _on_focus_out(self, event=None):
        content = self.input_text.get("1.0", "end-1c")
        if not content.strip():
            self._placeholder_active = True
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", self._placeholder)
            self.input_text.config(fg=ON_SURFACE_VARIANT)

    # ── Live conversion with debounce ─────────────────────────────

    def _on_input_change(self, event=None):
        if self._debounce_id is not None:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(200, self._convert)

    def _on_enter(self, event=None):
        """Enter key triggers immediate conversion."""
        if self._debounce_id is not None:
            self.after_cancel(self._debounce_id)
            self._debounce_id = None
        self._convert()

    def _on_format_change(self, value):
        self._convert()

    # ── Format implementations ────────────────────────────────────

    def _format_slug(self, text):
        t = re.sub(r'[^\w\s-]', '', text).lower().replace(' ', '-')
        t = re.sub(r'[-_]+', '-', t)
        t = re.sub(r'^-|-$', '', t)
        return t

    def _format_lower(self, text):
        return text.lower()

    def _format_upper(self, text):
        return text.upper()

    def _format_title(self, text):
        return text.title()

    def _format_camel(self, text):
        parts = re.split(r'[\s\-_]+', text)
        parts = [p for p in parts if p]
        if not parts:
            return ""
        return parts[0].lower() + "".join(w.capitalize() for w in parts[1:])

    def _format_kebab(self, text):
        t = text.lower()
        t = re.sub(r'[\s_]+', '-', t)
        t = re.sub(r'-+', '-', t)
        t = t.strip('-')
        return t

    def _format_snake(self, text):
        t = text.lower()
        t = re.sub(r'[\s\-]+', '_', t)
        t = re.sub(r'_+', '_', t)
        t = t.strip('_')
        return t

    _FORMATTERS = {
        "slug": _format_slug,
        "lower": _format_lower,
        "upper": _format_upper,
        "title": _format_title,
        "camel": _format_camel,
        "kebab": _format_kebab,
        "snake": _format_snake,
    }

    # ── Core conversion ───────────────────────────────────────────

    def _convert(self):
        self._debounce_id = None

        if self._placeholder_active:
            raw = ""
        else:
            raw = self.input_text.get("1.0", "end-1c")

        fmt = self.pill_selector.get()
        formatter = self._FORMATTERS.get(fmt, self._format_slug)
        result = formatter(self, raw) if raw.strip() else ""

        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", result)
        self.output_text.config(state="disabled")

        # Update counts
        char_count = len(result)
        word_count = len(result.split()) if result.strip() else 0
        self.count_label.config(text=f"{char_count} chars \u00b7 {word_count} words")

    # ── Clipboard ─────────────────────────────────────────────────

    def copy_to_clipboard(self):
        try:
            result = self.output_text.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(result)
            messagebox.showinfo("Copied", "Formatted text copied to clipboard.")
        except tk.TclError:
            messagebox.showerror("Error", "Failed to copy to clipboard.")

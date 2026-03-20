import re
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

from theme import (
    SURFACE, SURFACE_CONTAINER, SURFACE_CONTAINER_LOW, SURFACE_CONTAINER_HIGH,
    SURFACE_CONTAINER_HIGHEST, SURFACE_CONTAINER_LOWEST,
    PRIMARY, PRIMARY_CONTAINER, SECONDARY, SECONDARY_CONTAINER,
    ON_PRIMARY, ON_SURFACE, ON_SURFACE_VARIANT, OUTLINE_VARIANT,
    TERTIARY, ERROR,
    FONT_FAMILY, DISPLAY_SM, TITLE_LG, TITLE_MD, TITLE_SM, BODY, BODY_SM, LABEL_SM, LABEL_SM_MONO,
    SP_1, SP_2, SP_4, SP_6, SP_8, SP_10,
    apply_atelier_theme, Tooltip, create_section, PillSelector, StatusDot,
)


class FileRenamerGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self.folder_path = tk.StringVar()
        self.single_file_path = tk.StringVar()
        self.prefix_var = tk.StringVar()
        self.suffix_var = tk.StringVar()
        self.slug_var = tk.BooleanVar(value=True)
        self.case_mode = "original"

        # Preview data: list of (original_path, new_path) tuples
        self._preview_items = []
        self._error_count = 0

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = tk.Frame(self, bg=SURFACE_CONTAINER)
        card.grid(row=0, column=0, sticky="nsew")

        # ── Rename Options section ──────────────────────────────────
        opt_wrap, opt = create_section(card, "RENAME OPTIONS")
        opt_wrap.pack(fill="x", pady=(0, SP_8))
        opt.grid_columnconfigure(1, weight=1)

        # Prefix
        tk.Label(opt, text="Prefix", font=BODY, fg=ON_SURFACE, bg=SURFACE_CONTAINER_LOW).grid(
            row=0, column=0, sticky="w", padx=(0, SP_2), pady=SP_1)
        ttk.Entry(opt, width=20, textvariable=self.prefix_var).grid(
            row=0, column=1, sticky="ew", pady=SP_1)

        # Suffix
        tk.Label(opt, text="Suffix", font=BODY, fg=ON_SURFACE, bg=SURFACE_CONTAINER_LOW).grid(
            row=1, column=0, sticky="w", padx=(0, SP_2), pady=SP_1)
        ttk.Entry(opt, width=20, textvariable=self.suffix_var).grid(
            row=1, column=1, sticky="ew", pady=SP_1)

        # Slug checkbox
        ttk.Checkbutton(opt, text="Slug formatting (remove special chars, hyphens for spaces)",
                         variable=self.slug_var).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(SP_2, SP_1))

        # Case conversion pill selector
        tk.Label(opt, text="Case", font=BODY, fg=ON_SURFACE, bg=SURFACE_CONTAINER_LOW).grid(
            row=3, column=0, sticky="w", padx=(0, SP_2), pady=SP_1)
        self.case_pill = PillSelector(
            opt,
            options=[
                ("original", "Original"),
                ("lower", "lowercase"),
                ("upper", "UPPERCASE"),
                ("title", "Title Case"),
            ],
            default="original",
            command=self._on_case_change,
        )
        self.case_pill.grid(row=3, column=1, sticky="w", pady=SP_1)

        # ── Source section ──────────────────────────────────────────
        src_wrap, src = create_section(card, "SOURCE")
        src_wrap.pack(fill="x", pady=(0, SP_8))
        src.grid_columnconfigure(1, weight=1)

        tk.Label(src, text="Folder", font=BODY, fg=ON_SURFACE, bg=SURFACE_CONTAINER_LOW).grid(
            row=0, column=0, sticky="w", padx=(0, SP_2), pady=SP_1)
        ttk.Entry(src, width=40, textvariable=self.folder_path).grid(
            row=0, column=1, sticky="ew", pady=SP_1)
        ttk.Button(src, text="Browse\u2026", command=self.select_folder, style="Tertiary.TButton").grid(
            row=0, column=2, padx=(SP_2, 0), pady=SP_1)

        tk.Label(src, text="Single File", font=BODY, fg=ON_SURFACE, bg=SURFACE_CONTAINER_LOW).grid(
            row=1, column=0, sticky="w", padx=(0, SP_2), pady=SP_1)
        ttk.Entry(src, width=40, textvariable=self.single_file_path).grid(
            row=1, column=1, sticky="ew", pady=SP_1)
        ttk.Button(src, text="Browse\u2026", command=self.select_file, style="Tertiary.TButton").grid(
            row=1, column=2, padx=(SP_2, 0), pady=SP_1)

        # ── Preview button ──────────────────────────────────────────
        ttk.Button(card, text="Preview", command=self._refresh_preview, style="TButton").pack(
            anchor="w", pady=(0, SP_8))

        # ── Preview section ─────────────────────────────────────────
        prev_wrap, prev = create_section(card, "PREVIEW")
        prev_wrap.pack(fill="both", expand=True, pady=(0, SP_8))
        prev.grid_rowconfigure(0, weight=1)
        prev.grid_columnconfigure(0, weight=1)

        # Scrollable preview area
        self._preview_canvas = tk.Canvas(prev, bg=SURFACE_CONTAINER_LOW, highlightthickness=0,
                                          height=200)
        self._preview_scrollbar = ttk.Scrollbar(prev, orient="vertical",
                                                  command=self._preview_canvas.yview)
        self._preview_inner = tk.Frame(self._preview_canvas, bg=SURFACE_CONTAINER_LOW)

        self._preview_inner.bind("<Configure>",
                                  lambda e: self._preview_canvas.configure(
                                      scrollregion=self._preview_canvas.bbox("all")))
        self._preview_canvas_window = self._preview_canvas.create_window(
            (0, 0), window=self._preview_inner, anchor="nw")
        self._preview_canvas.configure(yscrollcommand=self._preview_scrollbar.set)

        self._preview_canvas.grid(row=0, column=0, sticky="nsew")
        self._preview_scrollbar.grid(row=0, column=1, sticky="ns")

        # Make the inner frame expand to canvas width
        self._preview_canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel scrolling
        self._preview_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._preview_inner.bind("<MouseWheel>", self._on_mousewheel)

        # ── Rename button (primary CTA) ─────────────────────────────
        ttk.Button(card, text="\u270F  Rename Files", command=self.rename_files,
                   style="Primary.TButton").pack(anchor="w", pady=(0, SP_8))

        # ── Status bar ──────────────────────────────────────────────
        status_frame = tk.Frame(card, bg=SURFACE_CONTAINER_LOW, padx=SP_4, pady=SP_2)
        status_frame.pack(fill="x")

        # Ready count
        self._dot_ready = StatusDot(status_frame, color=PRIMARY)
        self._dot_ready.pack(side="left", padx=(0, SP_1))
        self._lbl_ready = tk.Label(status_frame, text="Ready: 0", font=LABEL_SM,
                                    fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW)
        self._lbl_ready.pack(side="left", padx=(0, SP_4))

        # Modified count
        self._dot_modified = StatusDot(status_frame, color=SECONDARY)
        self._dot_modified.pack(side="left", padx=(0, SP_1))
        self._lbl_modified = tk.Label(status_frame, text="Modified: 0", font=LABEL_SM,
                                       fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW)
        self._lbl_modified.pack(side="left", padx=(0, SP_4))

        # Error count
        self._dot_error = StatusDot(status_frame, color=ERROR)
        self._dot_error.pack(side="left", padx=(0, SP_1))
        self._lbl_error = tk.Label(status_frame, text="Errors: 0", font=LABEL_SM,
                                    fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW)
        self._lbl_error.pack(side="left")

    # ── Callbacks ───────────────────────────────────────────────────

    def _on_canvas_configure(self, event):
        self._preview_canvas.itemconfig(self._preview_canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self._preview_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_case_change(self, value):
        self.case_mode = value

    def select_folder(self):
        d = filedialog.askdirectory(title="Select folder containing files")
        if d:
            self.folder_path.set(d)

    def select_file(self):
        f = filedialog.askopenfilename(title="Select a file")
        if f:
            self.single_file_path.set(f)

    # ── Slug / rename logic ─────────────────────────────────────────

    def _compute_new_name(self, filepath):
        """Compute the new filename for a given path based on current options."""
        basename = os.path.basename(filepath)
        name, ext = os.path.splitext(basename)

        # Slug conversion
        if self.slug_var.get():
            name = re.sub(r'[^\w\s-]', '', name)
            name = name.replace(' ', '-')
            name = re.sub(r'[-_]+', '-', name)
            name = re.sub(r'^-|-$', '', name)

        # Case conversion
        case = self.case_mode
        if case == "lower":
            name = name.lower()
        elif case == "upper":
            name = name.upper()
        elif case == "title":
            name = name.replace('-', ' ').title().replace(' ', '-')
        else:
            # "original" with slug still lowercases (preserving original behavior)
            if self.slug_var.get():
                name = name.lower()

        # Prefix / suffix
        prefix = self.prefix_var.get()
        suffix = self.suffix_var.get()
        if prefix:
            name = prefix + name
        if suffix:
            name = name + suffix

        return name + ext

    def _gather_files(self):
        """Gather files from folder path and/or single file path."""
        files = []
        folder_path = self.folder_path.get()
        single_file_path = self.single_file_path.get()

        if folder_path:
            for root, _, filenames in os.walk(folder_path):
                for fn in filenames:
                    files.append(os.path.join(root, fn))
        if single_file_path:
            files.append(single_file_path)
        return files

    # ── Preview ─────────────────────────────────────────────────────

    def _refresh_preview(self):
        """Populate the preview table with original/new name pairs."""
        # Clear previous preview rows
        for widget in self._preview_inner.winfo_children():
            widget.destroy()
        self._preview_items = []

        files = self._gather_files()
        if not files:
            messagebox.showerror("Error", "Please select a source folder or a file.")
            return

        self._preview_inner.grid_columnconfigure(0, weight=1)
        self._preview_inner.grid_columnconfigure(1, weight=1)

        # Header row
        tk.Label(self._preview_inner, text="Original", font=LABEL_SM,
                 fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW).grid(
            row=0, column=0, sticky="w", padx=(SP_2, SP_4), pady=(SP_1, SP_2))
        tk.Label(self._preview_inner, text="New", font=LABEL_SM,
                 fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW).grid(
            row=0, column=1, sticky="w", padx=(SP_4, SP_2), pady=(SP_1, SP_2))

        ready_count = 0
        modified_count = 0

        for i, filepath in enumerate(files):
            original_name = os.path.basename(filepath)
            new_name = self._compute_new_name(filepath)
            new_path = os.path.join(os.path.dirname(filepath), new_name)
            self._preview_items.append((filepath, new_path))

            row_idx = i + 1
            row_bg = SURFACE_CONTAINER_LOW if i % 2 == 0 else SURFACE_CONTAINER

            # Determine if file will actually change
            changed = original_name != new_name
            if changed:
                modified_count += 1
            else:
                ready_count += 1

            # Original name (dim)
            tk.Label(self._preview_inner, text=original_name, font=LABEL_SM_MONO,
                     fg=ON_SURFACE_VARIANT, bg=row_bg, anchor="w").grid(
                row=row_idx, column=0, sticky="ew", padx=(SP_2, SP_4), pady=1)

            # New name (primary green if changed, else dim)
            new_fg = PRIMARY if changed else ON_SURFACE_VARIANT
            tk.Label(self._preview_inner, text=new_name, font=LABEL_SM_MONO,
                     fg=new_fg, bg=row_bg, anchor="w").grid(
                row=row_idx, column=1, sticky="ew", padx=(SP_4, SP_2), pady=1)

        # Update status counts
        self._lbl_ready.config(text=f"Ready: {ready_count}")
        self._lbl_modified.config(text=f"Modified: {modified_count}")
        self._lbl_error.config(text="Errors: 0")
        self._error_count = 0

    # ── Rename ──────────────────────────────────────────────────────

    def rename_files(self):
        """Execute the rename operation."""
        # If no preview yet, generate it first
        if not self._preview_items:
            self._refresh_preview()
        if not self._preview_items:
            return

        error_count = 0
        modified_count = 0
        ready_count = 0

        for old_path, new_path in self._preview_items:
            if old_path == new_path:
                ready_count += 1
                continue
            try:
                os.rename(old_path, new_path)
                modified_count += 1
            except Exception as e:
                error_count += 1

        self._error_count = error_count

        # Update status
        self._lbl_ready.config(text=f"Ready: {ready_count}")
        self._lbl_modified.config(text=f"Modified: {modified_count}")
        self._lbl_error.config(text=f"Errors: {error_count}")

        if error_count > 0:
            messagebox.showwarning("Partial Success",
                                   f"Renamed {modified_count} files with {error_count} error(s).")
        else:
            messagebox.showinfo("Success", "All files have been renamed.")

        # Clear preview data so next run re-scans
        self._preview_items = []

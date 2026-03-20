import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from sys import platform
import fitz
from PIL import Image, ImageTk, ImageChops

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


class pdfToImageGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self.pdf_file_path = tk.StringVar()
        self.include_margins = tk.BooleanVar(value=True)
        self.output_format = tk.StringVar(value="webp")
        self.quality = tk.IntVar(value=85)
        self.preview_image = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Left Panel ──────────────────────────────────────────────
        left = tk.Frame(self, bg=SURFACE_CONTAINER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, SP_4))

        # ── PDF Source ──────────────────────────────────────────────
        src_wrap, src = create_section(left, "PDF SOURCE")
        src_wrap.pack(fill="x", pady=(0, SP_8))
        src.grid_columnconfigure(1, weight=1)

        tk.Label(
            src, text="PDF File", font=BODY, fg=ON_SURFACE, bg=SURFACE_CONTAINER_LOW,
        ).grid(row=0, column=0, sticky="w", padx=(0, SP_2), pady=SP_1)
        ttk.Entry(src, width=36, textvariable=self.pdf_file_path).grid(
            row=0, column=1, sticky="ew", pady=SP_1,
        )
        ttk.Button(src, text="Browse\u2026", command=self.select_pdf, style="Tertiary.TButton").grid(
            row=0, column=2, padx=(SP_2, 0), pady=SP_1,
        )

        # ── Output ──────────────────────────────────────────────────
        out_wrap, out = create_section(left, "OUTPUT")
        out_wrap.pack(fill="x", pady=(0, SP_8))

        tk.Label(
            out, text="Format", font=BODY, fg=ON_SURFACE, bg=SURFACE_CONTAINER_LOW,
        ).pack(anchor="w", pady=(0, SP_1))

        self.format_selector = PillSelector(
            out,
            options=[("webp", "WebP"), ("png", "PNG"), ("jpeg", "JPEG")],
            default="webp",
            command=self._on_format_change,
        )
        self.format_selector.pack(anchor="w", pady=(0, SP_4))

        # Quality slider row
        quality_row = tk.Frame(out, bg=SURFACE_CONTAINER_LOW)
        quality_row.pack(fill="x", pady=(0, SP_1))
        quality_row.grid_columnconfigure(1, weight=1)

        tk.Label(
            quality_row, text="Quality", font=BODY, fg=ON_SURFACE, bg=SURFACE_CONTAINER_LOW,
        ).grid(row=0, column=0, sticky="w", padx=(0, SP_2))

        self.quality_scale = ttk.Scale(
            quality_row, from_=0, to=100, orient="horizontal",
            variable=self.quality, command=self._on_quality_change,
        )
        self.quality_scale.grid(row=0, column=1, sticky="ew", padx=(0, SP_2))

        self.quality_label = tk.Label(
            quality_row, text="85", font=LABEL_SM_MONO, fg=ON_SURFACE_VARIANT,
            bg=SURFACE_CONTAINER_LOW, width=4, anchor="e",
        )
        self.quality_label.grid(row=0, column=2, sticky="e")

        # ── Options ─────────────────────────────────────────────────
        opt_wrap, opt = create_section(left, "OPTIONS")
        opt_wrap.pack(fill="x", pady=(0, SP_8))
        ttk.Checkbutton(
            opt, text="Include Margins", variable=self.include_margins,
            command=self.update_preview,
        ).pack(anchor="w", pady=SP_1)

        # ── Action ──────────────────────────────────────────────────
        ttk.Button(
            left, text="\u2B07  Convert PDF", command=self.convert_pdf_to_image,
            style="Primary.TButton",
        ).pack(anchor="w")

        # ── Output Path ─────────────────────────────────────────────
        self.output_path_label = tk.Label(
            left, text="", font=LABEL_SM_MONO, fg=ON_SURFACE_VARIANT,
            bg=SURFACE_CONTAINER, anchor="w", wraplength=360, justify="left",
        )
        self.output_path_label.pack(anchor="w", fill="x", pady=(SP_4, 0))

        # ── Right Panel / Preview ───────────────────────────────────
        right = tk.Frame(self, bg=SURFACE_CONTAINER)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        preview_wrap = tk.Frame(right, bg=SURFACE_CONTAINER_LOW, padx=SP_4, pady=SP_4)
        preview_wrap.grid(row=0, column=0, sticky="nsew")
        preview_wrap.grid_rowconfigure(1, weight=1)
        preview_wrap.grid_columnconfigure(0, weight=1)

        tk.Label(
            preview_wrap, text="PREVIEW", font=LABEL_SM, fg=ON_SURFACE_VARIANT,
            bg=SURFACE_CONTAINER_LOW, anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, SP_1))

        self.preview_label = tk.Label(
            preview_wrap, text="Select a PDF to preview", font=BODY,
            fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW,
            anchor="center", justify="center",
        )
        self.preview_label.grid(row=1, column=0, sticky="nsew")

    # ── Format / Quality callbacks ──────────────────────────────────

    def _on_format_change(self, value):
        self.output_format.set(value)
        if value == "png":
            self.quality_scale.state(["disabled"])
            self.quality_label.configure(fg=OUTLINE_VARIANT)
        else:
            self.quality_scale.state(["!disabled"])
            self.quality_label.configure(fg=ON_SURFACE_VARIANT)

    def _on_quality_change(self, value):
        self.quality.set(int(float(value)))
        self.quality_label.configure(text=str(self.quality.get()))

    # ── PDF logic (unchanged) ───────────────────────────────────────

    def select_pdf(self):
        f = filedialog.askopenfilename(
            title="Select a PDF file",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*")),
        )
        if f:
            self.pdf_file_path.set(f)
            self.update_preview()

    def update_preview(self):
        pdf_path = self.pdf_file_path.get()
        if not pdf_path or not pdf_path.lower().endswith(".pdf"):
            return
        with fitz.open(pdf_path) as doc:
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(1, 1))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        if not self.include_margins.get():
            img = self.crop_to_content(img)
        self.display_preview(img)

    def display_preview(self, image):
        image.thumbnail((300, 400))
        self.preview_image = ImageTk.PhotoImage(image)
        self.preview_label.config(image=self.preview_image, text="")
        self.preview_label.image = self.preview_image

    def convert_pdf_to_image(self):
        pdf_path = self.pdf_file_path.get()
        if not pdf_path or not pdf_path.lower().endswith(".pdf"):
            messagebox.showerror("Error", "Please select a valid PDF file.")
            return

        with fitz.open(pdf_path) as doc:
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        if not self.include_margins.get():
            img = self.crop_to_content(img)

        fmt = self.output_format.get()
        quality = self.quality.get()
        base = os.path.splitext(pdf_path)[0] + "-thumbnail"

        if fmt == "webp":
            out = base + ".webp"
            img.save(out, "WEBP", quality=quality)
        elif fmt == "png":
            out = base + ".png"
            img.save(out, "PNG")
        elif fmt == "jpeg":
            out = base + ".jpeg"
            img = img.convert("RGB")
            img.save(out, "JPEG", quality=quality)
        else:
            out = base + ".webp"
            img.save(out, "WEBP", quality=quality)

        self.output_path_label.configure(text=f"Saved: {out}")
        messagebox.showinfo("Success", f"PDF converted to {fmt.upper()}:\n{out}")

    def crop_to_content(self, image, threshold=10):
        bg = Image.new(image.mode, image.size, image.getpixel((0, 0)))
        diff = ImageChops.difference(image, bg).convert("L").point(lambda x: 255 if x > threshold else 0)
        bbox = diff.getbbox()
        return image.crop(bbox) if bbox else image

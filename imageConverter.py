import re
import time
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk
Image.MAX_IMAGE_PIXELS = None  # disable decompression bomb check for local desktop use
import concurrent.futures
from sys import platform
import pillow_avif
import threading
import queue
import io

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


class ImageViewerWindow(tk.Toplevel):
    def __init__(self, master, image_path):
        super().__init__(master, bg=SURFACE_CONTAINER)
        self.title("Image Preview")
        self.geometry("800x600")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, bg=SURFACE_CONTAINER_LOWEST, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.original_image = Image.open(image_path)
        self.image = self.original_image.copy()
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.image_on_canvas = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.center_image()
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.pan)
        self.bind("<Configure>", self.center_image)

    def center_image(self, event=None):
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.coords(self.image_on_canvas, (cw - self.image.width) / 2, (ch - self.image.height) / 2)

    def zoom(self, event):
        factor = 1.1 if event.delta > 0 else 0.9
        self.image = self.original_image.copy().resize(
            (int(self.image.width * factor), int(self.image.height * factor)), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.itemconfig(self.image_on_canvas, image=self.tk_image)
        self.center_image()

    def start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)
        self.canvas.config(cursor="fleur")

    def pan(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)


class ImageConverterGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self.folder_path = tk.StringVar()
        self.destination_folder_path = tk.StringVar()
        self.quality = tk.IntVar(value=100)
        self.progress = tk.DoubleVar(value=0)
        self.overide_images = tk.BooleanVar()
        self.rename = tk.BooleanVar()
        self.convert = tk.BooleanVar()
        self.compress = tk.BooleanVar()
        self.fileOut = tk.StringVar()
        self.extension = tk.StringVar()
        self.start_time = None
        self.end_time = None
        self.new_width_percentage = tk.IntVar(value=100)
        self.source_preview_path = None
        self.preview_photo_image = None
        self.preview_queue = queue.Queue()
        self.scheduled_preview_update = None

        # File queue tracking
        self.file_queue_items = []       # list of dicts: {path, frame, status_dot, name_label, dims_label, thumb_label}
        self.file_queue_thumbnails = []  # keep references to prevent GC

        # Conversion stats tracking
        self.total_input_size = 0
        self.total_output_size = 0
        self.files_completed = 0
        self.files_total = 0

        # ── Two-column layout ─────────────────────────────────────
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left_panel = tk.Frame(self, bg=SURFACE_CONTAINER)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, SP_4))

        right_panel = tk.Frame(self, bg=SURFACE_CONTAINER)
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_rowconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        # ── Source ────────────────────────────────────────────────
        src_wrap, src = create_section(left_panel, "SOURCE")
        src_wrap.pack(fill="x", pady=(0, SP_8))

        tk.Label(src, text="Image / Folder", font=BODY, fg=ON_SURFACE, bg=SURFACE_CONTAINER_LOW).grid(
            row=0, column=0, sticky="w", pady=(0, SP_1))
        ttk.Entry(src, width=36, textvariable=self.folder_path).grid(row=1, column=0, sticky="ew", pady=(0, SP_2))
        src.grid_columnconfigure(0, weight=1)

        btn_row = tk.Frame(src, bg=SURFACE_CONTAINER_LOW)
        btn_row.grid(row=2, column=0, sticky="w")
        ttk.Button(btn_row, text="Browse Folder\u2026", command=self.select_folder, style="Tertiary.TButton").pack(side="left", padx=(0, SP_2))
        ttk.Button(btn_row, text="Browse File\u2026", command=self.select_file, style="Tertiary.TButton").pack(side="left")

        # ── Destination ───────────────────────────────────────────
        dst_wrap, dst = create_section(left_panel, "DESTINATION")
        dst_wrap.pack(fill="x", pady=(0, SP_8))

        tk.Label(dst, text="Output Folder", font=BODY, fg=ON_SURFACE, bg=SURFACE_CONTAINER_LOW).grid(
            row=0, column=0, sticky="w", pady=(0, SP_1))
        ttk.Entry(dst, width=36, textvariable=self.destination_folder_path).grid(row=1, column=0, sticky="ew", pady=(0, SP_2))
        dst.grid_columnconfigure(0, weight=1)
        ttk.Button(dst, text="Browse\u2026", command=self.destination_select_folder, style="Tertiary.TButton").grid(row=2, column=0, sticky="w")

        # ── Output Format ─────────────────────────────────────────
        out_wrap, out = create_section(left_panel, "OUTPUT")
        out_wrap.pack(fill="x", pady=(0, SP_8))

        self.image_format = tk.StringVar(value="webp")
        self.format_pill = PillSelector(
            out,
            options=[("webp", "WebP"), ("png", "PNG"), ("jpeg", "JPEG"), ("jpegli", "JPEGLI"), ("avif", "AVIF")],
            default="webp",
            command=self._on_format_pill_change,
            bg=SURFACE_CONTAINER_LOW,
        )
        self.format_pill.pack(anchor="w", pady=(0, SP_1))
        self.format_pill2 = PillSelector(
            out,
            options=[("tiff", "TIFF"), ("bmp", "BMP"), ("gif", "GIF"), ("ico", "ICO")],
            default=None,
            command=self._on_format_pill2_change,
            bg=SURFACE_CONTAINER_LOW,
        )
        self.format_pill2.pack(anchor="w")
        # Deselect row 2 initially (row 1 has the default)
        for btn in self.format_pill2._buttons.values():
            btn.configure(bg=SURFACE_CONTAINER_HIGH, fg=ON_SURFACE_VARIANT, font=BODY)

        # ── Options ───────────────────────────────────────────────
        opt_wrap, opt = create_section(left_panel, "OPTIONS")
        opt_wrap.pack(fill="x", pady=(0, SP_8))
        opt.grid_columnconfigure(1, weight=1)

        ttk.Checkbutton(opt, text="Convert", variable=self.convert, command=self.request_preview_update).grid(row=0, column=0, columnspan=2, sticky="w", pady=SP_1)

        ttk.Checkbutton(opt, text="Compress", variable=self.compress, command=self.request_preview_update).grid(row=1, column=0, sticky="w", pady=SP_1)
        q_row = tk.Frame(opt, bg=SURFACE_CONTAINER_LOW)
        q_row.grid(row=1, column=1, sticky="ew", padx=(SP_2, 0), pady=SP_1)
        self.quality_slider = ttk.Scale(q_row, length=130, orient="horizontal", from_=0, to=100, variable=self.quality, command=self.request_preview_update, state=tk.DISABLED)
        self.quality_slider.pack(side="left")
        self.quality_label = tk.Label(q_row, text="100%", width=5, font=LABEL_SM, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW)
        self.quality_label.pack(side="left", padx=(SP_2, 0))

        ttk.Checkbutton(opt, text="Rename files to slug", variable=self.rename).grid(row=2, column=0, columnspan=2, sticky="w", pady=SP_1)

        self.resize_checkbox = tk.BooleanVar()
        ttk.Checkbutton(opt, text="Resize", variable=self.resize_checkbox, command=self.request_preview_update).grid(row=3, column=0, sticky="w", pady=SP_1)
        r_row = tk.Frame(opt, bg=SURFACE_CONTAINER_LOW)
        r_row.grid(row=3, column=1, sticky="ew", padx=(SP_2, 0), pady=SP_1)
        self.resize_slider = ttk.Scale(r_row, length=130, from_=1, to=100, orient="horizontal", variable=self.new_width_percentage, command=self.request_preview_update, state=tk.DISABLED)
        self.resize_slider.pack(side="left")
        self.resize_label = tk.Label(r_row, text="100%", width=5, font=LABEL_SM, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW)
        self.resize_label.pack(side="left", padx=(SP_2, 0))

        # ── Action area ──────────────────────────────────────────
        act_wrap, act = create_section(left_panel, "ACTION")
        act_wrap.pack(fill="x", pady=(0, SP_8))

        act_top = tk.Frame(act, bg=SURFACE_CONTAINER_LOW)
        act_top.pack(fill="x", pady=(0, SP_2))
        ttk.Button(act_top, text="\u25B6  Run", command=self.convert_images, style="Primary.TButton").pack(side="left")
        self.time_label = tk.Label(act_top, text="", font=LABEL_SM, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW)
        self.time_label.pack(side="right")

        # File count label
        self.file_count_label = tk.Label(act, text="", font=LABEL_SM, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW)
        self.file_count_label.pack(fill="x", pady=(0, SP_1))

        # Progress bar with percentage
        prog_row = tk.Frame(act, bg=SURFACE_CONTAINER_LOW)
        prog_row.pack(fill="x", pady=(0, SP_1))
        prog_row.grid_columnconfigure(0, weight=1)
        ttk.Progressbar(prog_row, orient="horizontal", mode="determinate", variable=self.progress).grid(row=0, column=0, sticky="ew")
        self.progress_pct_label = tk.Label(prog_row, text="", width=5, font=LABEL_SM, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW, anchor="e")
        self.progress_pct_label.grid(row=0, column=1, padx=(SP_2, 0))

        # Estimated savings label
        self.savings_label = tk.Label(act, text="", font=LABEL_SM, fg=PRIMARY, bg=SURFACE_CONTAINER_LOW)
        self.savings_label.pack(fill="x", pady=(SP_1, 0))

        # ── Preview (recessed right panel, top half) ──────────────
        preview_wrap = tk.Frame(right_panel, bg=SURFACE_CONTAINER_LOW, padx=SP_4, pady=SP_4)
        preview_wrap.grid(row=0, column=0, sticky="nsew", pady=(0, SP_2))
        preview_wrap.grid_rowconfigure(1, weight=1)
        preview_wrap.grid_columnconfigure(0, weight=1)

        tk.Label(preview_wrap, text="PREVIEW", font=LABEL_SM, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, SP_1))

        self.preview_label = tk.Label(
            preview_wrap, text="Select a single image\nto see a preview",
            font=BODY, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW,
            anchor="center", justify="center",
        )
        self.preview_label.grid(row=1, column=0, sticky="nsew")
        self.preview_label.bind("<Button-1>", self.open_image_viewer)
        self.preview_label.bind("<Enter>", lambda e: self.preview_label.config(cursor="hand2" if self.source_preview_path else ""))
        self.preview_label.bind("<Leave>", lambda e: self.preview_label.config(cursor=""))

        self.resolution_label = tk.Label(
            preview_wrap, text="", font=LABEL_SM, fg=ON_SURFACE_VARIANT,
            bg=SURFACE_CONTAINER_LOW, anchor="e",
        )
        self.resolution_label.grid(row=2, column=0, sticky="e", pady=(SP_1, 0))

        # ── File Queue (right panel, bottom half) ─────────────────
        queue_wrap = tk.Frame(right_panel, bg=SURFACE_CONTAINER_LOW, padx=SP_4, pady=SP_4)
        queue_wrap.grid(row=1, column=0, sticky="nsew")
        queue_wrap.grid_rowconfigure(1, weight=1)
        queue_wrap.grid_columnconfigure(0, weight=1)

        tk.Label(queue_wrap, text="FILE QUEUE", font=LABEL_SM, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, SP_1))

        # Scrollable canvas for file queue
        queue_canvas_frame = tk.Frame(queue_wrap, bg=SURFACE_CONTAINER_LOWEST)
        queue_canvas_frame.grid(row=1, column=0, sticky="nsew")
        queue_canvas_frame.grid_rowconfigure(0, weight=1)
        queue_canvas_frame.grid_columnconfigure(0, weight=1)

        self.queue_canvas = tk.Canvas(queue_canvas_frame, bg=SURFACE_CONTAINER_LOWEST, highlightthickness=0)
        self.queue_scrollbar = ttk.Scrollbar(queue_canvas_frame, orient="vertical", command=self.queue_canvas.yview)
        self.queue_canvas.configure(yscrollcommand=self.queue_scrollbar.set)

        self.queue_canvas.grid(row=0, column=0, sticky="nsew")
        self.queue_scrollbar.grid(row=0, column=1, sticky="ns")

        self.queue_inner = tk.Frame(self.queue_canvas, bg=SURFACE_CONTAINER_LOWEST)
        self.queue_window_id = self.queue_canvas.create_window((0, 0), window=self.queue_inner, anchor="nw")

        self.queue_inner.bind("<Configure>", self._on_queue_inner_configure)
        self.queue_canvas.bind("<Configure>", self._on_queue_canvas_configure)
        self.queue_canvas.bind("<Enter>", lambda e: self.queue_canvas.bind_all("<MouseWheel>", self._on_queue_mousewheel))
        self.queue_canvas.bind("<Leave>", lambda e: self.queue_canvas.unbind_all("<MouseWheel>"))

        self.queue_placeholder = tk.Label(
            self.queue_inner, text="No files queued",
            font=BODY, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOWEST,
            anchor="center", justify="center",
        )
        self.queue_placeholder.pack(fill="x", pady=SP_8)

        # ── Traces ────────────────────────────────────────────────
        self.new_width_percentage.trace_add('write', self.validate_resize_percentage)
        self.quality.trace_add('write', self.validate_quality_percentage)

        self.toggle_convert()
        self.toggle_compress()
        self.toggle_resize_slider()
        self.process_preview_queue()

    # ── Queue canvas helpers ──────────────────────────────────────

    def _on_queue_inner_configure(self, event=None):
        self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))

    def _on_queue_canvas_configure(self, event=None):
        self.queue_canvas.itemconfig(self.queue_window_id, width=event.width)

    def _on_queue_mousewheel(self, event):
        self.queue_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── Format pill callback ──────────────────────────────────────

    def _on_format_pill_change(self, value):
        # Deselect row 2 when row 1 is selected
        self.format_pill2._selected = None
        for btn in self.format_pill2._buttons.values():
            btn.configure(bg=SURFACE_CONTAINER_HIGH, fg=ON_SURFACE_VARIANT, font=BODY)
        display_map = {"webp": "WebP", "png": "PNG", "jpeg": "JPEG", "jpegli": "JPEGLI", "avif": "AVIF"}
        self.image_format.set(display_map.get(value, "WebP"))
        self.request_preview_update()

    def _on_format_pill2_change(self, value):
        # Deselect row 1 when row 2 is selected
        self.format_pill._selected = None
        for btn in self.format_pill._buttons.values():
            btn.configure(bg=SURFACE_CONTAINER_HIGH, fg=ON_SURFACE_VARIANT, font=BODY)
        display_map = {"tiff": "TIFF", "bmp": "BMP", "gif": "GIF", "ico": "ICO"}
        self.image_format.set(display_map.get(value, "TIFF"))
        self.request_preview_update()

    # ── File queue management ─────────────────────────────────────

    def _clear_file_queue(self):
        for item in self.file_queue_items:
            item["frame"].destroy()
        self.file_queue_items.clear()
        self.file_queue_thumbnails.clear()

    def _populate_file_queue(self, file_paths):
        self._clear_file_queue()

        if self.queue_placeholder.winfo_exists():
            self.queue_placeholder.pack_forget()

        if not file_paths:
            self.queue_placeholder.pack(fill="x", pady=SP_8)
            return

        for fp in file_paths:
            row = tk.Frame(self.queue_inner, bg=SURFACE_CONTAINER_LOW, padx=SP_2, pady=SP_1)
            row.pack(fill="x", padx=SP_1, pady=(0, SP_1))

            # Thumbnail
            thumb_label = tk.Label(row, bg=SURFACE_CONTAINER_LOW, width=32, height=32)
            thumb_label.pack(side="left", padx=(0, SP_2))

            # Generate thumbnail in background
            self._generate_thumbnail(fp, thumb_label)

            # File info column
            info_frame = tk.Frame(row, bg=SURFACE_CONTAINER_LOW)
            info_frame.pack(side="left", fill="x", expand=True)

            name_label = tk.Label(info_frame, text=os.path.basename(fp), font=LABEL_SM_MONO,
                                  fg=ON_SURFACE, bg=SURFACE_CONTAINER_LOW, anchor="w")
            name_label.pack(fill="x")

            # Dimensions
            dims_label = tk.Label(info_frame, text="", font=LABEL_SM,
                                  fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW, anchor="w")
            dims_label.pack(fill="x")

            # Load dimensions in background
            self._load_dimensions(fp, dims_label)

            # Status dot
            status_dot = StatusDot(row, color=PRIMARY, size=8, bg=SURFACE_CONTAINER_LOW)
            status_dot.pack(side="right", padx=(SP_2, 0))

            item = {
                "path": fp,
                "frame": row,
                "status_dot": status_dot,
                "name_label": name_label,
                "dims_label": dims_label,
                "thumb_label": thumb_label,
            }
            self.file_queue_items.append(item)

    def _generate_thumbnail(self, file_path, label):
        def _worker():
            try:
                with Image.open(file_path) as img:
                    img.thumbnail((32, 32))
                    photo = ImageTk.PhotoImage(img)
                    self.file_queue_thumbnails.append(photo)
                    self.after(0, lambda: label.config(image=photo))
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    def _load_dimensions(self, file_path, label):
        def _worker():
            try:
                with Image.open(file_path) as img:
                    w, h = img.size
                    self.after(0, lambda: label.config(text=f"{w}\u00D7{h}"))
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    def _update_queue_item_status(self, file_path, status):
        """Update the status dot for a file in the queue.
        status: 'ready' | 'converting' | 'done' | 'error'
        """
        color_map = {
            "ready": PRIMARY,
            "converting": SECONDARY,
            "done": PRIMARY_CONTAINER,
            "error": ERROR,
        }
        color = color_map.get(status, PRIMARY)
        for item in self.file_queue_items:
            if item["path"] == file_path:
                self.after(0, lambda c=color, d=item["status_dot"]: d.set_color(c))
                break

    # ── Preview pipeline ──────────────────────────────────────────

    def request_preview_update(self, *args):
        if self.scheduled_preview_update:
            self.after_cancel(self.scheduled_preview_update)
        self.toggle_convert()
        self.toggle_compress()
        self.toggle_resize_slider()
        self.scheduled_preview_update = self.after(400, self.start_preview_generation_thread)

    def start_preview_generation_thread(self):
        if not self.source_preview_path:
            return
        self.preview_label.config(image='', text="Loading preview\u2026")
        self.resolution_label.config(text="")
        settings = {
            "source_path": self.source_preview_path,
            "quality": self.quality.get() if self.compress.get() else 100,
            "width_percent": self.new_width_percentage.get() if self.resize_checkbox.get() else 100,
            "convert_format": self.image_format.get().lower() if self.convert.get() else None,
        }
        threading.Thread(target=self._preview_worker, kwargs=settings, daemon=True).start()

    def _preview_worker(self, source_path, quality, width_percent, convert_format):
        try:
            with Image.open(source_path) as image:
                nw = int(image.width * (width_percent / 100))
                nh = int(image.height * (nw / image.width))
                if image.width != nw or image.height != nh:
                    image = image.resize((nw, nh), Image.LANCZOS)

                fmt = 'JPEG'
                ext = os.path.splitext(source_path)[1].lower()[1:]
                if convert_format:
                    fmt = {
                        'webp': 'WEBP', 'png': 'PNG', 'jpeg': 'JPEG', 'jpegli': 'JPEG',
                        'avif': 'AVIF', 'tiff': 'TIFF', 'bmp': 'BMP', 'gif': 'GIF', 'ico': 'ICO',
                    }.get(convert_format, 'JPEG')
                else:
                    fmt = {'png': 'PNG', 'webp': 'WEBP', 'avif': 'AVIF'}.get(ext, 'JPEG')

                if image.mode == 'RGBA' and fmt in ('JPEG', 'BMP', 'ICO'):
                    bg = Image.new('RGB', image.size, (255, 255, 255))
                    bg.paste(image, mask=image.split()[3])
                    image = bg

                if fmt == 'ICO' and (image.width > 256 or image.height > 256):
                    image.thumbnail((256, 256), Image.LANCZOS)

                mem = io.BytesIO()
                params = {'format': fmt}
                if fmt in ('JPEG', 'WEBP', 'AVIF'):
                    params['quality'] = quality
                elif fmt == 'PNG':
                    params['compress_level'] = 6
                # BMP, TIFF, GIF, ICO use defaults
                image.save(mem, **params)
                mem.seek(0)
                self.preview_queue.put((mem, nw, nh))
        except Exception as e:
            self.preview_queue.put((f"Error: {e}", None, None))

    def process_preview_queue(self):
        try:
            result, w, h = self.preview_queue.get(block=False)
            if isinstance(result, io.BytesIO):
                image = Image.open(result)
                pw, ph = self.preview_label.winfo_width(), self.preview_label.winfo_height()
                if pw > 1 and ph > 1:
                    image.thumbnail((pw - 10, ph - 10))
                self.preview_photo_image = ImageTk.PhotoImage(image)
                self.preview_label.config(image=self.preview_photo_image, text="")
                self.resolution_label.config(text=f"{w} \u00D7 {h} px")
            elif isinstance(result, str):
                self.preview_label.config(image='', text=result)
                self.resolution_label.config(text="")
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_preview_queue)

    # ── File selection ────────────────────────────────────────────

    def select_file(self):
        f = filedialog.askopenfilename(title="Select an image file", filetypes=(("Image files", "*.jpg *.png *.webp *.jpeg *.avif"), ("All files", "*.*")))
        if f:
            self.folder_path.set(f)
            self.source_preview_path = f
            self._populate_file_queue([f])
            self.request_preview_update()

    def select_folder(self):
        d = filedialog.askdirectory(title="Select folder containing images")
        if d:
            self.folder_path.set(d)
            self.clear_preview()
            # Scan folder for images and populate queue
            files = []
            for root, _, filenames in os.walk(d):
                for fn in filenames:
                    if re.search(r"\.(jpg|jpeg|png|bmp|tiff|webp|avif)$", fn, re.IGNORECASE):
                        files.append(os.path.join(root, fn))
            self._populate_file_queue(files)
            # If only one image found, set it as preview source
            if len(files) == 1:
                self.source_preview_path = files[0]
                self.request_preview_update()

    def clear_preview(self):
        if self.scheduled_preview_update:
            self.after_cancel(self.scheduled_preview_update)
        self.preview_label.config(image='', text="Select a single image\nto see a preview")
        self.resolution_label.config(text="")
        self.preview_photo_image = None
        self.source_preview_path = None

    def open_image_viewer(self, event=None):
        if self.source_preview_path:
            try:
                ImageViewerWindow(self.master, self.source_preview_path)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open preview:\n{e}")

    # ── Toggle helpers ────────────────────────────────────────────

    def toggle_resize_slider(self):
        en = self.resize_checkbox.get()
        self.resize_slider.config(state=tk.NORMAL if en else tk.DISABLED)

    def toggle_compress(self):
        en = self.compress.get()
        self.quality_slider.config(state=tk.NORMAL if en else tk.DISABLED)

    def toggle_convert(self):
        # PillSelector doesn't have a disabled state, but we keep the method
        # for compatibility with request_preview_update flow
        pass

    def validate_quality_percentage(self, *args):
        try:
            v = round(float(self.quality.get()))
            if v < 1: self.quality.set(1)
            elif v > 100: self.quality.set(100)
            else: self.quality.set(v)
        except (ValueError, tk.TclError):
            self.quality.set(0)
        self.quality_label.configure(text=f"{self.quality.get()}%")

    def validate_resize_percentage(self, *args):
        try:
            v = round(float(self.new_width_percentage.get()))
            if v < 1: self.new_width_percentage.set(1)
            elif v > 100: self.new_width_percentage.set(100)
            else: self.new_width_percentage.set(v)
        except (ValueError, tk.TclError):
            self.new_width_percentage.set(0)
        self.resize_label.configure(text=f"{self.new_width_percentage.get()}%")

    def destination_select_folder(self):
        d = filedialog.askdirectory(title="Select destination folder")
        if d:
            self.destination_folder_path.set(d)

    # ── Conversion ────────────────────────────────────────────────

    @staticmethod
    def format_time(seconds):
        return f"{round(seconds / 60)} minute(s)" if seconds >= 60 else f"{round(seconds, 2)} seconds"

    @staticmethod
    def format_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    @staticmethod
    def adjust_ppi(image, desired_ppi):
        dpi = image.info.get('dpi', (72, 72))
        if dpi[0] > desired_ppi:
            image = image.copy()
            image.info['dpi'] = (desired_ppi, desired_ppi)
        return image

    def convert_images(self):
        if not self.folder_path.get() or not self.destination_folder_path.get():
            messagebox.showerror("Error", "Please select source and destination folders.")
            return
        self.start_time = time.time()
        path = self.folder_path.get()

        files = []
        if os.path.isdir(path):
            for root, _, filenames in os.walk(path):
                for fn in filenames:
                    if re.search(r"\.(jpg|jpeg|png|bmp|tiff|webp|avif)$", fn, re.IGNORECASE):
                        files.append(os.path.join(root, fn))
        elif os.path.isfile(path):
            files.append(path)
        else:
            messagebox.showerror("Error", "Invalid path.")
            return
        if not files:
            messagebox.showerror("Error", "No image files found.")
            return

        dest = self.destination_folder_path.get()
        if not dest:
            self.destination_folder_path.set(path)
            self.overide_images.set(True)
        else:
            self.overide_images.set(False)

        total = len(files)
        self.files_total = total
        self.files_completed = 0
        self.total_input_size = 0
        self.total_output_size = 0
        self.progress.set(0)
        self.progress_pct_label.config(text="0%")
        self.file_count_label.config(text=f"0 of {total} files")
        self.savings_label.config(text="")
        self.time_label.config(text="")

        # Calculate total input size
        for f in files:
            try:
                self.total_input_size += os.path.getsize(f)
            except OSError:
                pass

        # Set all queue items to ready
        for item in self.file_queue_items:
            self._update_queue_item_status(item["path"], "ready")

        all_args = []
        for f in files:
            a = {
                "file_path": f, "rename": self.rename.get(),
                "quality": self.quality.get() if self.compress.get() else 100,
                "overide_image": self.overide_images.get(),
                "folder_path": self.folder_path.get(),
                "destination_folder_path": self.destination_folder_path.get(),
                "new_width_percentage": self.new_width_percentage.get() if self.resize_checkbox.get() else 100,
                "single_file_selected": os.path.isfile(path),
            }
            if self.convert.get():
                a["extension"] = {
                    "WebP": "webp", "PNG": "png", "JPEG": "jpeg", "JPEGLI": "jpeg",
                    "AVIF": "avif", "TIFF": "tiff", "BMP": "bmp", "GIF": "gif", "ICO": "ico",
                }.get(self.image_format.get(), "webp")
            else:
                a["extension"] = os.path.splitext(f)[1][1:].lower()
            all_args.append(a)

        def _run():
            done = 0
            output_size_acc = 0
            with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as ex:
                future_to_args = {}
                for a in all_args:
                    fut = ex.submit(ImageConverterGUI.convert_file, **a)
                    future_to_args[fut] = a
                    self._update_queue_item_status(a["file_path"], "converting")

                for future in concurrent.futures.as_completed(future_to_args):
                    a = future_to_args[future]
                    result_path = future.result()
                    done += 1

                    # Track output file size
                    if result_path and os.path.exists(result_path):
                        try:
                            output_size_acc += os.path.getsize(result_path)
                        except OSError:
                            pass
                        self._update_queue_item_status(a["file_path"], "done")
                    else:
                        self._update_queue_item_status(a["file_path"], "error")

                    pct = done / total * 100
                    current_done = done
                    current_output = output_size_acc
                    self.after(0, lambda p=pct, d=current_done, o=current_output: self._update_progress(p, d, total, o))

            elapsed = time.time() - self.start_time
            self.total_output_size = output_size_acc
            self.after(0, lambda: self._on_conversion_complete(elapsed))

        threading.Thread(target=_run, daemon=True).start()

    def _update_progress(self, pct, done, total, output_size):
        self.progress.set(pct)
        self.progress_pct_label.config(text=f"{int(pct)}%")
        self.file_count_label.config(text=f"{done} of {total} files")
        self.files_completed = done
        self.total_output_size = output_size

    def _on_conversion_complete(self, elapsed):
        self.time_label.config(text=f"Completed in {ImageConverterGUI.format_time(elapsed)}")
        # Show savings
        if self.total_input_size > 0:
            saved_pct = (1 - self.total_output_size / self.total_input_size) * 100
            in_str = ImageConverterGUI.format_size(self.total_input_size)
            out_str = ImageConverterGUI.format_size(self.total_output_size)
            if saved_pct > 0:
                self.savings_label.config(text=f"Saved ~{saved_pct:.0f}% ({in_str} \u2192 {out_str})", fg=PRIMARY)
            else:
                self.savings_label.config(text=f"Size increased ({in_str} \u2192 {out_str})", fg=TERTIARY)

    @staticmethod
    def convert_file(file_path, rename, quality, overide_image, extension, folder_path, destination_folder_path, new_width_percentage, single_file_selected):
        try:
            with Image.open(file_path) as image:
                if new_width_percentage != 100:
                    wp = new_width_percentage / 100
                    nw = int(image.width * wp)
                    nh = int(image.height * (nw / image.width))
                    image = image.resize((nw, nh), Image.LANCZOS)
                image = ImageConverterGUI.adjust_ppi(image, 72)
                if image.mode == 'RGBA' and extension in ('jpeg', 'jpg', 'bmp', 'ico'):
                    bg = Image.new('RGB', image.size, (255, 255, 255))
                    bg.paste(image, mask=image.split()[3])
                    image = bg
                if single_file_selected:
                    new_file_path = os.path.join(destination_folder_path, os.path.basename(file_path))
                else:
                    new_file_path = os.path.join(destination_folder_path, os.path.relpath(file_path, folder_path))
                name = os.path.splitext(os.path.basename(new_file_path))[0]
                if rename:
                    name = re.sub(r'[^\w\s-]', '', name).lower().replace(' ', '-')
                    name = re.sub(r'[-_]+', '-', name)
                    name = re.sub(r'^-|-$', '', name)
                new_file_path = os.path.join(os.path.dirname(new_file_path), name + '.' + extension)
                os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
                sp = {}
                if extension == "jpeg": sp = {"format": "JPEG", "quality": quality}
                elif extension == "png": sp = {"format": "PNG", "compress_level": 6}
                elif extension == "avif": sp = {"format": "AVIF", "quality": quality}
                elif extension == "webp": sp = {"format": "WEBP", "quality": quality}
                elif extension == "tiff": sp = {"format": "TIFF"}
                elif extension == "bmp": sp = {"format": "BMP"}
                elif extension == "gif": sp = {"format": "GIF"}
                elif extension == "ico":
                    # ICO requires specific sizes; resize to 256x256 max
                    if image.width > 256 or image.height > 256:
                        image.thumbnail((256, 256), Image.LANCZOS)
                    sp = {"format": "ICO"}
                if sp:
                    image.save(new_file_path, **sp)
            if overide_image and new_file_path != file_path:
                os.remove(file_path)
            return new_file_path
        except Exception as e:
            print(f"Failed to convert {file_path}: {e}")
            return None

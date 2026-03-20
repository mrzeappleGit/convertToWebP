import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from tkinter import ttk
from sys import platform
import os


class ImageManipulationGUI(ttk.Frame):
    """Image manipulation tool with interactive crop, magic wand selection,
    rotate/flip transforms, undo/redo, zoom/pan, and save/export."""

    TOOL_NONE = "none"
    TOOL_CROP = "crop"
    TOOL_WAND = "wand"

    def __init__(self, master=None):
        super().__init__(master)
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"

        # --- State ---
        self.current_image = None
        self.selection_mask = None
        self.file_path = None
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.current_tool = self.TOOL_NONE
        self._tk_image = None
        self._canvas_image_id = None

        # Undo / Redo
        self.history = []
        self.future = []
        self._max_history = 20

        # Crop state
        self._crop_rect_id = None
        self._crop_start = None
        self._crop_end = None
        self._crop_dim_ids = []

        # Pan state
        self._pan_start = None

        # --- Toolbar row 1 ---
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        ttk.Button(toolbar, text="Load", command=self.load_image, cursor=cursor_point).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save As", command=self.save_image, cursor=cursor_point).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        self._crop_btn = ttk.Button(toolbar, text="Crop", command=self._activate_crop, cursor=cursor_point)
        self._crop_btn.pack(side=tk.LEFT, padx=2)
        self._wand_btn = ttk.Button(toolbar, text="Magic Select", command=self._activate_wand, cursor=cursor_point)
        self._wand_btn.pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        ttk.Button(toolbar, text="Remove Selected", command=self.remove_selection, cursor=cursor_point).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Feather", command=self.feather_selection, cursor=cursor_point).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Clear Selection", command=self.clear_selection, cursor=cursor_point).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        ttk.Button(toolbar, text="\u21bb 90\u00b0", command=lambda: self.rotate_image(90), cursor=cursor_point).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="\u21ba 90\u00b0", command=lambda: self.rotate_image(-90), cursor=cursor_point).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Flip H", command=lambda: self.flip_image("h"), cursor=cursor_point).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Flip V", command=lambda: self.flip_image("v"), cursor=cursor_point).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

        ttk.Button(toolbar, text="Undo", command=self.undo, cursor=cursor_point).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Redo", command=self.redo, cursor=cursor_point).pack(side=tk.LEFT, padx=2)

        # --- Toolbar row 2: wand settings + tool indicator ---
        toolbar2 = ttk.Frame(self)
        toolbar2.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        ttk.Label(toolbar2, text="Tolerance:").pack(side=tk.LEFT, padx=(5, 2))
        self.tolerance_var = tk.IntVar(value=32)
        ttk.Scale(toolbar2, from_=0, to=128, variable=self.tolerance_var,
                  orient="horizontal", length=120).pack(side=tk.LEFT, padx=2)
        self._tolerance_label = ttk.Label(toolbar2, text="32", width=4)
        self._tolerance_label.pack(side=tk.LEFT)
        self.tolerance_var.trace_add("write", self._on_tolerance_change)

        self._tool_label = ttk.Label(toolbar2, text="", foreground="gray")
        self._tool_label.pack(side=tk.LEFT, padx=20)

        # --- Canvas ---
        self.canvas = tk.Canvas(self, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<ButtonPress-2>", self._on_pan_start)
        self.canvas.bind("<B2-Motion>", self._on_pan_drag)
        self.canvas.bind("<ButtonPress-1>", self._on_left_press)
        self.canvas.bind("<B1-Motion>", self._on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_release)
        self.canvas.bind("<ButtonPress-3>", self._on_right_press)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Escape>", self._on_escape)
        self.canvas.bind("<Return>", self._on_enter)

        # --- Status bar ---
        self._status_var = tk.StringVar(value="Load an image to begin")
        ttk.Label(self, textvariable=self._status_var, relief="sunken",
                  anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)

    # ---------------------------------------------------------------
    # Coordinate conversion
    # ---------------------------------------------------------------

    def _canvas_to_image(self, cx, cy):
        ix = (cx - self.offset_x) / self.zoom
        iy = (cy - self.offset_y) / self.zoom
        return ix, iy

    def _image_to_canvas(self, ix, iy):
        return ix * self.zoom + self.offset_x, iy * self.zoom + self.offset_y

    def _clamp_to_image(self, ix, iy):
        if self.current_image is None:
            return 0, 0
        w, h = self.current_image.size
        return max(0, min(w, ix)), max(0, min(h, iy))

    # ---------------------------------------------------------------
    # Display
    # ---------------------------------------------------------------

    def _fit_to_canvas(self):
        if self.current_image is None:
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 2 or ch < 2:
            return
        iw, ih = self.current_image.size
        self.zoom = min(cw / iw, ch / ih, 1.0)
        dw = iw * self.zoom
        dh = ih * self.zoom
        self.offset_x = (cw - dw) / 2
        self.offset_y = (ch - dh) / 2

    def _refresh_display(self):
        if self.current_image is None:
            self.canvas.delete("all")
            self._canvas_image_id = None
            return

        iw, ih = self.current_image.size
        dw = max(1, int(iw * self.zoom))
        dh = max(1, int(ih * self.zoom))

        display = self.current_image.resize((dw, dh), Image.LANCZOS)

        # Selection overlay: semi-transparent magenta on selected pixels
        if self.selection_mask is not None and np.any(self.selection_mask):
            display_arr = np.array(display.convert("RGBA"))
            mask_resized = cv2.resize(self.selection_mask, (dw, dh),
                                      interpolation=cv2.INTER_NEAREST)
            selected = mask_resized > 0
            magenta = np.array([255, 0, 255], dtype=np.float32)
            display_arr[selected, :3] = (
                display_arr[selected, :3].astype(np.float32) * 0.5 + magenta * 0.5
            ).astype(np.uint8)
            display = Image.fromarray(display_arr, "RGBA")

        self._tk_image = ImageTk.PhotoImage(display)

        if self._canvas_image_id:
            self.canvas.itemconfig(self._canvas_image_id, image=self._tk_image)
            self.canvas.coords(self._canvas_image_id, self.offset_x, self.offset_y)
        else:
            self._canvas_image_id = self.canvas.create_image(
                self.offset_x, self.offset_y, anchor=tk.NW, image=self._tk_image)

        self._update_status()

    def _on_canvas_configure(self, event=None):
        if self.current_image is not None:
            self._fit_to_canvas()
            self._refresh_display()

    def _on_tolerance_change(self, *args):
        try:
            self._tolerance_label.config(text=str(self.tolerance_var.get()))
        except tk.TclError:
            pass

    def _update_status(self):
        if self.current_image is None:
            self._status_var.set("Load an image to begin")
            return
        w, h = self.current_image.size
        zoom_pct = int(self.zoom * 100)
        sel = ""
        if self.selection_mask is not None and np.any(self.selection_mask):
            sel = f" | Selection: {int(np.count_nonzero(self.selection_mask)):,} px"
        tool = self.current_tool if self.current_tool != self.TOOL_NONE else "None"
        self._status_var.set(f"{w}x{h} {self.current_image.mode} | Zoom: {zoom_pct}%{sel} | Tool: {tool}")

    # ---------------------------------------------------------------
    # File operations
    # ---------------------------------------------------------------

    def load_image(self):
        path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff *.avif"),
                       ("All Files", "*.*")])
        if not path:
            return
        try:
            img = Image.open(path)
            img.load()
            self.current_image = img
            self.file_path = path
            self.selection_mask = None
            self.history.clear()
            self.future.clear()
            self._deactivate_tools()
            self._fit_to_canvas()
            self._refresh_display()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image:\n{e}")

    def save_image(self):
        if self.current_image is None:
            messagebox.showinfo("Info", "No image to save.")
            return
        path = filedialog.asksaveasfilename(
            title="Save image as", defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("WebP", "*.webp"),
                       ("JPEG", "*.jpg"), ("BMP", "*.bmp"), ("All Files", "*.*")])
        if not path:
            return
        try:
            save_img = self.current_image
            ext = os.path.splitext(path)[1].lower()
            if ext in ('.jpg', '.jpeg') and save_img.mode == 'RGBA':
                bg = Image.new('RGB', save_img.size, (255, 255, 255))
                bg.paste(save_img, mask=save_img.split()[3])
                save_img = bg
            save_img.save(path)
            messagebox.showinfo("Saved", f"Image saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image:\n{e}")

    # ---------------------------------------------------------------
    # Tool activation
    # ---------------------------------------------------------------

    def _activate_crop(self):
        self._deactivate_tools()
        self.current_tool = self.TOOL_CROP
        self.canvas.config(cursor="crosshair")
        self._tool_label.config(text="Crop: drag to select, Enter/double-click to apply, Esc to cancel",
                                foreground="green")
        self._update_status()

    def _activate_wand(self):
        self._deactivate_tools()
        self.current_tool = self.TOOL_WAND
        self.canvas.config(cursor="crosshair")
        self._tool_label.config(text="Magic Wand: left-click to add, right-click to remove",
                                foreground="blue")
        self._update_status()

    def _deactivate_tools(self):
        self.current_tool = self.TOOL_NONE
        self.canvas.config(cursor="")
        self._tool_label.config(text="", foreground="gray")
        self._clear_crop_overlay()
        self._crop_start = None
        self._crop_end = None

    # ---------------------------------------------------------------
    # Mouse / keyboard handlers
    # ---------------------------------------------------------------

    def _on_left_press(self, event):
        self.canvas.focus_set()
        if self.current_image is None:
            return
        if self.current_tool == self.TOOL_CROP:
            self._crop_start = (event.x, event.y)
            self._crop_end = (event.x, event.y)
            self._clear_crop_overlay()
        elif self.current_tool == self.TOOL_WAND:
            self._do_magic_wand(event.x, event.y, add=True)

    def _on_left_drag(self, event):
        if self.current_tool == self.TOOL_CROP and self._crop_start:
            self._crop_end = (event.x, event.y)
            self._draw_crop_rect()

    def _on_left_release(self, event):
        if self.current_tool == self.TOOL_CROP and self._crop_start:
            self._crop_end = (event.x, event.y)
            self._draw_crop_rect()

    def _on_right_press(self, event):
        if self.current_image is None:
            return
        if self.current_tool == self.TOOL_WAND:
            self._do_magic_wand(event.x, event.y, add=False)

    def _on_double_click(self, event):
        if self.current_tool == self.TOOL_CROP and self._crop_start and self._crop_end:
            self._apply_crop()

    def _on_escape(self, event):
        self._deactivate_tools()
        self._refresh_display()

    def _on_enter(self, event):
        if self.current_tool == self.TOOL_CROP and self._crop_start and self._crop_end:
            self._apply_crop()

    def _on_scroll(self, event):
        if self.current_image is None:
            return
        ix, iy = self._canvas_to_image(event.x, event.y)
        factor = 1.1 if event.delta > 0 else 1 / 1.1
        self.zoom = max(0.05, min(10.0, self.zoom * factor))
        self.offset_x = event.x - ix * self.zoom
        self.offset_y = event.y - iy * self.zoom
        self._refresh_display()
        if self._crop_start and self._crop_end:
            self._draw_crop_rect()

    def _on_pan_start(self, event):
        self._pan_start = (event.x, event.y)

    def _on_pan_drag(self, event):
        if self._pan_start:
            self.offset_x += event.x - self._pan_start[0]
            self.offset_y += event.y - self._pan_start[1]
            self._pan_start = (event.x, event.y)
            self._refresh_display()

    # ---------------------------------------------------------------
    # Crop tool
    # ---------------------------------------------------------------

    def _clear_crop_overlay(self):
        for item_id in self._crop_dim_ids:
            self.canvas.delete(item_id)
        self._crop_dim_ids.clear()
        if self._crop_rect_id:
            self.canvas.delete(self._crop_rect_id)
            self._crop_rect_id = None

    def _draw_crop_rect(self):
        self._clear_crop_overlay()
        if not self._crop_start or not self._crop_end:
            return

        x1, y1 = self._crop_start
        x2, y2 = self._crop_end
        left, right = min(x1, x2), max(x1, x2)
        top, bottom = min(y1, y2), max(y1, y2)

        # Dashed selection rectangle
        self._crop_rect_id = self.canvas.create_rectangle(
            left, top, right, bottom, outline="cyan", width=2, dash=(4, 4))

        # Dim outside the crop area
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        stipple = "gray50"
        dim = "#000000"
        self._crop_dim_ids = [
            self.canvas.create_rectangle(0, 0, cw, top, fill=dim, stipple=stipple, outline=""),
            self.canvas.create_rectangle(0, bottom, cw, ch, fill=dim, stipple=stipple, outline=""),
            self.canvas.create_rectangle(0, top, left, bottom, fill=dim, stipple=stipple, outline=""),
            self.canvas.create_rectangle(right, top, cw, bottom, fill=dim, stipple=stipple, outline=""),
        ]

    def _apply_crop(self):
        if not self._crop_start or not self._crop_end or not self.current_image:
            return

        ix1, iy1 = self._canvas_to_image(*self._crop_start)
        ix2, iy2 = self._canvas_to_image(*self._crop_end)
        ix1, iy1 = self._clamp_to_image(ix1, iy1)
        ix2, iy2 = self._clamp_to_image(ix2, iy2)

        left, right = int(min(ix1, ix2)), int(max(ix1, ix2))
        top, bottom = int(min(iy1, iy2)), int(max(iy1, iy2))

        if right - left < 2 or bottom - top < 2:
            return

        self._save_state()
        self.current_image = self.current_image.crop((left, top, right, bottom))
        if self.selection_mask is not None:
            self.selection_mask = self.selection_mask[top:bottom, left:right].copy()

        self._deactivate_tools()
        self._fit_to_canvas()
        self._refresh_display()

    # ---------------------------------------------------------------
    # Magic Wand
    # ---------------------------------------------------------------

    def _do_magic_wand(self, cx, cy, add=True):
        if self.current_image is None:
            return
        ix, iy = self._canvas_to_image(cx, cy)
        ix, iy = int(ix), int(iy)
        w, h = self.current_image.size
        if ix < 0 or ix >= w or iy < 0 or iy >= h:
            return

        self._save_state()

        image_array = np.array(self.current_image.convert('RGB'))
        tolerance = self.tolerance_var.get()

        mask = np.zeros((h + 2, w + 2), np.uint8)
        flags = cv2.FLOODFILL_FIXED_RANGE | cv2.FLOODFILL_MASK_ONLY | (255 << 8)
        cv2.floodFill(image_array, mask, (ix, iy), None,
                      (tolerance, tolerance, tolerance),
                      (tolerance, tolerance, tolerance), flags)

        adjusted_mask = mask[1:-1, 1:-1]

        if self.selection_mask is None:
            self.selection_mask = np.zeros((h, w), dtype=np.uint8)

        if add:
            self.selection_mask = cv2.bitwise_or(self.selection_mask, adjusted_mask)
        else:
            self.selection_mask = cv2.bitwise_and(
                self.selection_mask, cv2.bitwise_not(adjusted_mask))

        self._refresh_display()

    # ---------------------------------------------------------------
    # Selection operations
    # ---------------------------------------------------------------

    def remove_selection(self):
        if self.current_image is None or self.selection_mask is None:
            return
        if not np.any(self.selection_mask):
            return
        self._save_state()
        rgba = self.current_image.convert('RGBA')
        arr = np.array(rgba)
        arr[self.selection_mask > 0] = [0, 0, 0, 0]
        self.current_image = Image.fromarray(arr, 'RGBA')
        self.selection_mask = None
        self._refresh_display()

    def feather_selection(self):
        if self.selection_mask is None or not np.any(self.selection_mask):
            return
        radius = simpledialog.askinteger(
            "Feather Radius", "Enter feather radius (1-50):",
            minvalue=1, maxvalue=50)
        if radius is None:
            return
        self._save_state()
        k = radius * 2 + 1
        self.selection_mask = cv2.GaussianBlur(self.selection_mask, (k, k), 0)
        self._refresh_display()

    def clear_selection(self):
        if self.selection_mask is not None:
            self._save_state()
            self.selection_mask = None
            self._refresh_display()

    # ---------------------------------------------------------------
    # Transform
    # ---------------------------------------------------------------

    def rotate_image(self, degrees):
        if self.current_image is None:
            return
        self._save_state()
        if degrees == 90:
            self.current_image = self.current_image.transpose(Image.ROTATE_270)
            if self.selection_mask is not None:
                self.selection_mask = np.rot90(self.selection_mask, k=-1)
        elif degrees == -90:
            self.current_image = self.current_image.transpose(Image.ROTATE_90)
            if self.selection_mask is not None:
                self.selection_mask = np.rot90(self.selection_mask, k=1)
        self._fit_to_canvas()
        self._refresh_display()

    def flip_image(self, direction):
        if self.current_image is None:
            return
        self._save_state()
        if direction == "h":
            self.current_image = self.current_image.transpose(Image.FLIP_LEFT_RIGHT)
            if self.selection_mask is not None:
                self.selection_mask = np.fliplr(self.selection_mask)
        elif direction == "v":
            self.current_image = self.current_image.transpose(Image.FLIP_TOP_BOTTOM)
            if self.selection_mask is not None:
                self.selection_mask = np.flipud(self.selection_mask)
        self._refresh_display()

    # ---------------------------------------------------------------
    # Undo / Redo
    # ---------------------------------------------------------------

    def _save_state(self):
        if self.current_image is None:
            return
        img_copy = self.current_image.copy()
        mask_copy = self.selection_mask.copy() if self.selection_mask is not None else None
        self.history.append((img_copy, mask_copy))
        self.future.clear()
        if len(self.history) > self._max_history:
            self.history.pop(0)

    def undo(self):
        if not self.history:
            return
        img_copy = self.current_image.copy() if self.current_image else None
        mask_copy = self.selection_mask.copy() if self.selection_mask is not None else None
        self.future.append((img_copy, mask_copy))

        self.current_image, self.selection_mask = self.history.pop()
        self._fit_to_canvas()
        self._refresh_display()

    def redo(self):
        if not self.future:
            return
        img_copy = self.current_image.copy() if self.current_image else None
        mask_copy = self.selection_mask.copy() if self.selection_mask is not None else None
        self.history.append((img_copy, mask_copy))

        self.current_image, self.selection_mask = self.future.pop()
        self._fit_to_canvas()
        self._refresh_display()

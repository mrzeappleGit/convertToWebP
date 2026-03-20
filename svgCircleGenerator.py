import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, StringVar, colorchooser
from PIL import Image, ImageTk
import os
import math
from sys import platform

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


class SVGCircleGeneratorGUI(ttk.Frame):
    """Draw circles, polygons, or rectangles on an image and generate SVG path data."""

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master

        self.POLYGON_CLOSING_THRESHOLD = 15
        self.image_path = None
        self.tk_image = None
        self.original_image = None
        self.display_image = None
        self.canvas_image_id = None
        self.image_display_rect = None
        self.shape_drawn = False
        self.current_mode = StringVar(value="circle")
        self.center_original_coords = None
        self.center_canvas_coords = None
        self.radius_var = StringVar(value="20")
        self.polygon_original_points = []
        self.polygon_canvas_points = []
        self.is_polygon_closed = False
        self.generated_svg_path = ""
        self.drawn_canvas_items = []

        # Rectangle state
        self.rect_first_original = None
        self.rect_first_canvas = None
        self.rect_second_original = None
        self.rect_second_canvas = None

        # Stroke width
        self.stroke_width_var = tk.DoubleVar(value=2.0)

        # Color
        self.color_var = StringVar(value=SECONDARY)

        # Zoom
        self.zoom_level = 1.0
        self.zoom_min = 0.5
        self.zoom_max = 3.0

        # All generated SVG elements (for export)
        self.all_svg_elements = []

        # ── Main split layout ──────────────────────────────────────
        main_pane = tk.Frame(self, bg=SURFACE_CONTAINER)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # Left side: canvas area (~60%)
        left_frame = tk.Frame(main_pane, bg=SURFACE_CONTAINER)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Load image button row at top of canvas area
        top_bar = tk.Frame(left_frame, bg=SURFACE_CONTAINER)
        top_bar.pack(fill=tk.X, padx=SP_4, pady=(SP_4, SP_2))
        ttk.Button(top_bar, text="Load Image\u2026", command=self.load_image, style="Tertiary.TButton").pack(side=tk.LEFT)

        # Canvas container with relative positioning for zoom overlay
        canvas_container = tk.Frame(left_frame, bg=SURFACE_CONTAINER_LOWEST)
        canvas_container.pack(fill=tk.BOTH, expand=True, padx=SP_4, pady=(0, SP_2))

        self.canvas = tk.Canvas(canvas_container, width=600, height=400, highlightthickness=0, bg=SURFACE_CONTAINER_LOWEST)
        self.canvas.pack(expand=True, fill=tk.BOTH)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Floating zoom controls (placed after canvas so we can overlay)
        self._zoom_frame = tk.Frame(canvas_container, bg=SURFACE_CONTAINER_HIGH)
        self._zoom_frame.place(relx=0.0, rely=1.0, anchor="sw", x=SP_4, y=-SP_4)

        zoom_out_btn = tk.Label(
            self._zoom_frame, text="\u2212", font=TITLE_MD, cursor="hand2",
            bg=SURFACE_CONTAINER_HIGH, fg=ON_SURFACE, padx=SP_2, pady=SP_1,
        )
        zoom_out_btn.pack(side=tk.LEFT)
        zoom_out_btn.bind("<Button-1>", lambda e: self._zoom(-0.25))

        self._zoom_label = tk.Label(
            self._zoom_frame, text="100%", font=LABEL_SM_MONO,
            bg=SURFACE_CONTAINER_HIGH, fg=ON_SURFACE_VARIANT, padx=SP_2, pady=SP_1,
        )
        self._zoom_label.pack(side=tk.LEFT)

        zoom_in_btn = tk.Label(
            self._zoom_frame, text="+", font=TITLE_MD, cursor="hand2",
            bg=SURFACE_CONTAINER_HIGH, fg=ON_SURFACE, padx=SP_2, pady=SP_1,
        )
        zoom_in_btn.pack(side=tk.LEFT)
        zoom_in_btn.bind("<Button-1>", lambda e: self._zoom(0.25))

        # Instruction label below canvas
        self.instruction_label = tk.Label(
            left_frame, text="Load an image to begin.", font=BODY,
            fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER, anchor="w",
        )
        self.instruction_label.pack(fill="x", padx=SP_4, pady=(0, SP_4))

        # ── Right side: controls panel (~40%) ──────────────────────
        right_frame = tk.Frame(main_pane, bg=SURFACE_CONTAINER, width=320)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, SP_4), pady=SP_4)
        right_frame.pack_propagate(False)

        # ── Section: SHAPE ─────────────────────────────────────────
        shape_wrap, shape_body = create_section(right_frame, "SHAPE")
        shape_wrap.pack(fill=tk.X, pady=(0, SP_4))

        self._pill_selector = PillSelector(
            shape_body,
            options=[("circle", "Circle"), ("polygon", "Polygon"), ("rectangle", "Rectangle")],
            default="circle",
            command=self._on_pill_mode_change,
            bg=SURFACE_CONTAINER_LOW,
        )
        self._pill_selector.pack(fill=tk.X)

        # ── Section: PROPERTIES ────────────────────────────────────
        props_wrap, props_body = create_section(right_frame, "PROPERTIES")
        props_wrap.pack(fill=tk.X, pady=(0, SP_4))

        # Radius entry (circle mode only)
        self.radius_frame = tk.Frame(props_body, bg=SURFACE_CONTAINER_LOW)
        self.radius_frame.pack(fill=tk.X, pady=(0, SP_2))
        tk.Label(self.radius_frame, text="Radius", font=LABEL_SM, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW).pack(side=tk.LEFT)
        vcmd = (self.register(self._validate_radius), '%P')
        self.radius_entry = ttk.Entry(self.radius_frame, textvariable=self.radius_var, width=8, validate='key', validatecommand=vcmd)
        self.radius_entry.pack(side=tk.RIGHT)
        self.radius_entry.bind("<FocusOut>", self._on_radius_change)
        self.radius_entry.bind("<Return>", self._on_radius_change)

        # Stroke width slider
        stroke_frame = tk.Frame(props_body, bg=SURFACE_CONTAINER_LOW)
        stroke_frame.pack(fill=tk.X, pady=(0, SP_2))
        tk.Label(stroke_frame, text="Stroke Width", font=LABEL_SM, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW).pack(side=tk.LEFT)
        self._stroke_value_label = tk.Label(stroke_frame, text="2.0", font=LABEL_SM_MONO, fg=ON_SURFACE, bg=SURFACE_CONTAINER_LOW)
        self._stroke_value_label.pack(side=tk.RIGHT)

        stroke_slider_frame = tk.Frame(props_body, bg=SURFACE_CONTAINER_LOW)
        stroke_slider_frame.pack(fill=tk.X, pady=(0, SP_4))
        self._stroke_scale = ttk.Scale(
            stroke_slider_frame, from_=0.5, to=10.0,
            variable=self.stroke_width_var, orient=tk.HORIZONTAL,
            command=self._on_stroke_change,
        )
        self._stroke_scale.pack(fill=tk.X)

        # Color picker
        color_frame = tk.Frame(props_body, bg=SURFACE_CONTAINER_LOW)
        color_frame.pack(fill=tk.X, pady=(0, SP_2))
        tk.Label(color_frame, text="Color", font=LABEL_SM, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW).pack(side=tk.LEFT)

        color_input_frame = tk.Frame(color_frame, bg=SURFACE_CONTAINER_LOW)
        color_input_frame.pack(side=tk.RIGHT)

        self._color_swatch = tk.Canvas(
            color_input_frame, width=20, height=20,
            highlightthickness=0, bg=SURFACE_CONTAINER_LOW, cursor="hand2",
        )
        self._color_swatch.pack(side=tk.LEFT, padx=(0, SP_1))
        self._swatch_rect = self._color_swatch.create_rectangle(0, 0, 20, 20, fill=self.color_var.get(), outline="")
        self._color_swatch.bind("<Button-1>", self._pick_color)

        self._color_entry = ttk.Entry(color_input_frame, textvariable=self.color_var, width=9)
        self._color_entry.pack(side=tk.LEFT)
        self._color_entry.bind("<Return>", self._on_color_entry_change)
        self._color_entry.bind("<FocusOut>", self._on_color_entry_change)

        # ── Section: SVG OUTPUT ────────────────────────────────────
        svg_wrap, svg_body = create_section(right_frame, "SVG OUTPUT")
        svg_wrap.pack(fill=tk.BOTH, expand=True, pady=(0, SP_4))

        self.output_text = scrolledtext.ScrolledText(
            svg_body, height=6, wrap=tk.WORD, relief=tk.FLAT, borderwidth=0,
            bg=SURFACE_CONTAINER_LOWEST, fg=ON_SURFACE, font=LABEL_SM_MONO,
            insertbackground=ON_SURFACE, selectbackground=SECONDARY,
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)
        self.output_text.config(state=tk.DISABLED)
        self.output_text.bind("<Configure>", self._manage_scrollbar_visibility)

        # ── Button row ─────────────────────────────────────────────
        btn_row = tk.Frame(right_frame, bg=SURFACE_CONTAINER)
        btn_row.pack(fill=tk.X, pady=(0, SP_2))

        self.clear_button = ttk.Button(btn_row, text="Clear Shape", command=self.clear_shapes, state=tk.DISABLED)
        self.clear_button.pack(side=tk.LEFT, padx=(0, SP_2))

        ttk.Button(btn_row, text="Copy SVG", command=self._copy_svg).pack(side=tk.LEFT, padx=(0, SP_2))

        ttk.Button(btn_row, text="Export SVG", command=self._export_svg, style="Primary.TButton").pack(side=tk.RIGHT)

        self._update_mode()

    # ── Mode / UI ─────────────────────────────────────────────────

    def _on_pill_mode_change(self, value):
        self.current_mode.set(value)
        self._update_mode()

    def _update_mode(self):
        mode = self.current_mode.get()
        self.clear_shapes()
        if mode == "circle":
            self.radius_frame.pack(fill=tk.X, pady=(0, SP_2))
            self.clear_button.config(text="Clear Circle")
            self.canvas.config(cursor="crosshair")
        elif mode == "polygon":
            self.radius_frame.pack_forget()
            self.clear_button.config(text="Clear Polygon")
            self.canvas.config(cursor="crosshair")
        elif mode == "rectangle":
            self.radius_frame.pack_forget()
            self.clear_button.config(text="Clear Rectangle")
            self.canvas.config(cursor="crosshair")
        self._update_instructions()

    def _update_instructions(self):
        if not self.original_image:
            self.instruction_label.config(text="Load an image to begin.")
            return
        mode = self.current_mode.get()
        if mode == "circle":
            self.instruction_label.config(
                text="Circle generated. Clear to draw another." if self.shape_drawn
                else "Click on the image to define the circle center."
            )
        elif mode == "polygon":
            if self.is_polygon_closed:
                self.instruction_label.config(text=f"Polygon closed ({len(self.polygon_original_points)} pts). Clear to restart.")
            elif not self.polygon_original_points:
                self.instruction_label.config(text="Click to add the first polygon point.")
            elif len(self.polygon_original_points) < 3:
                self.instruction_label.config(text=f"Click to add points ({len(self.polygon_original_points)} so far).")
            else:
                self.instruction_label.config(text=f"Click near the first point to close. ({len(self.polygon_original_points)} pts)")
        elif mode == "rectangle":
            if self.rect_second_original:
                self.instruction_label.config(text="Rectangle drawn. Clear to draw another.")
            elif self.rect_first_original:
                self.instruction_label.config(text="Click to set the opposite corner.")
            else:
                self.instruction_label.config(text="Click to set the first corner of the rectangle.")

    # ── Image ─────────────────────────────────────────────────────

    def load_image(self):
        f = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff"), ("All Files", "*.*")],
            parent=self.master,
        )
        if not f:
            return
        try:
            self.original_image = Image.open(f)
            self.image_path = f
            self.zoom_level = 1.0
            self._update_zoom_label()
            self.clear_shapes()
            self.canvas.config(cursor="crosshair")
            self._display_loaded_image()
            self.clear_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}", parent=self.master)
            self._reset_image_state()

    def _on_canvas_resize(self, event=None):
        if self.original_image and self.canvas.winfo_width() > 1 and self.canvas.winfo_height() > 1:
            self._display_loaded_image()

    def _display_loaded_image(self):
        if not self.original_image:
            return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return
        iw, ih = self.original_image.size
        # Base scale factor to fit image in canvas, then apply zoom
        base_sf = min(cw / iw, ch / ih)
        sf = base_sf * self.zoom_level
        dw, dh = int(iw * sf), int(ih * sf)
        self.display_image = self.original_image.resize((dw, dh), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.display_image)
        dx, dy = (cw - dw) / 2, (ch - dh) / 2
        self.image_display_rect = (dx, dy, dw, dh)
        if self.canvas_image_id:
            self.canvas.delete(self.canvas_image_id)
        self.canvas_image_id = self.canvas.create_image(dx, dy, anchor=tk.NW, image=self.tk_image)
        self.canvas.tag_raise("drawn_shape")
        self._redraw_feedback_shapes()
        self._update_instructions()

    def _reset_image_state(self):
        self.image_path = self.original_image = self.display_image = self.tk_image = None
        if self.canvas_image_id:
            self.canvas.delete(self.canvas_image_id)
            self.canvas_image_id = None
        self.image_display_rect = None
        self.clear_button.config(state=tk.DISABLED)
        self.canvas.config(cursor="")
        self.clear_shapes()
        self._update_instructions()

    # ── Zoom ──────────────────────────────────────────────────────

    def _zoom(self, delta):
        new_zoom = round(self.zoom_level + delta, 2)
        if new_zoom < self.zoom_min or new_zoom > self.zoom_max:
            return
        self.zoom_level = new_zoom
        self._update_zoom_label()
        if self.original_image:
            self._display_loaded_image()

    def _update_zoom_label(self):
        pct = int(self.zoom_level * 100)
        self._zoom_label.config(text=f"{pct}%")

    # ── Coords ────────────────────────────────────────────────────

    def _canvas_to_original_coords(self, cx, cy):
        if not self.image_display_rect or not self.original_image:
            return None
        dx, dy, dw, dh = self.image_display_rect
        ow, oh = self.original_image.size
        if not (dx <= cx < dx + dw and dy <= cy < dy + dh) or dw == 0 or dh == 0:
            return None
        return (max(0, min(ow, ((cx - dx) / dw) * ow)), max(0, min(oh, ((cy - dy) / dh) * oh)))

    def _original_to_canvas_coords(self, ox, oy):
        if not self.image_display_rect or not self.original_image:
            return None
        dx, dy, dw, dh = self.image_display_rect
        ow, oh = self.original_image.size
        if ow == 0 or oh == 0:
            return None
        return ((ox / ow) * dw + dx, (oy / oh) * dh + dy)

    # ── Click ─────────────────────────────────────────────────────

    def on_canvas_click(self, event):
        if not self.original_image or not self.image_display_rect:
            messagebox.showwarning("No Image", "Load an image first.", parent=self.master)
            return
        oc = self._canvas_to_original_coords(event.x, event.y)
        if oc is None:
            return
        mode = self.current_mode.get()
        if mode == "circle":
            self._handle_circle_click(event.x, event.y, oc)
        elif mode == "polygon":
            self._handle_polygon_click(event.x, event.y, oc)
        elif mode == "rectangle":
            self._handle_rectangle_click(event.x, event.y, oc)
        if (
            (mode == "circle" and self.center_original_coords)
            or (mode == "polygon" and self.polygon_original_points)
            or (mode == "rectangle" and self.rect_first_original)
        ):
            self.shape_drawn = True
            self._update_instructions()

    def _handle_circle_click(self, cx, cy, oc):
        self.clear_shapes(keep_mode=True)
        r = self._get_circle_radius()
        if r is None:
            return
        self.center_original_coords = oc
        self.center_canvas_coords = (cx, cy)
        self._draw_circle_feedback()
        self._generate_circle_svg()

    def _handle_polygon_click(self, cx, cy, oc):
        if self.is_polygon_closed:
            messagebox.showinfo("Closed", "Polygon closed. Clear to start new.", parent=self.master)
            return
        if len(self.polygon_canvas_points) >= 3:
            fx, fy = self.polygon_canvas_points[0]
            if (cx - fx)**2 + (cy - fy)**2 < self.POLYGON_CLOSING_THRESHOLD**2:
                self.is_polygon_closed = True
                self._draw_polygon_feedback()
                self._generate_polygon_svg()
                self._update_instructions()
                return
        self.polygon_original_points.append(oc)
        self.polygon_canvas_points.append((cx, cy))
        self._draw_polygon_feedback()
        self._generate_polygon_svg()

    def _handle_rectangle_click(self, cx, cy, oc):
        if self.rect_second_original:
            # Already drawn, ignore
            messagebox.showinfo("Drawn", "Rectangle already drawn. Clear to start new.", parent=self.master)
            return
        if self.rect_first_original is None:
            # First corner
            self.rect_first_original = oc
            self.rect_first_canvas = (cx, cy)
            self._draw_rectangle_feedback()
        else:
            # Second corner
            self.rect_second_original = oc
            self.rect_second_canvas = (cx, cy)
            self._draw_rectangle_feedback()
            self._generate_rectangle_svg()

    # ── Drawing feedback ──────────────────────────────────────────

    def _get_draw_color(self):
        """Return the current drawing color from the color picker."""
        c = self.color_var.get()
        # Validate it's a usable color string
        try:
            self.canvas.winfo_rgb(c)
            return c
        except Exception:
            return SECONDARY

    def _get_draw_width(self):
        """Return the current stroke width for canvas feedback."""
        return max(1, self.stroke_width_var.get())

    def _clear_drawn_feedback(self):
        for i in self.drawn_canvas_items:
            self.canvas.delete(i)
        self.drawn_canvas_items = []

    def _redraw_feedback_shapes(self):
        self._clear_drawn_feedback()
        if not self.original_image:
            return
        mode = self.current_mode.get()
        if mode == "circle" and self.center_original_coords:
            cc = self._original_to_canvas_coords(*self.center_original_coords)
            if cc:
                self.center_canvas_coords = cc
                self._draw_circle_feedback()
        elif mode == "polygon" and self.polygon_original_points:
            self.polygon_canvas_points = [c for c in (self._original_to_canvas_coords(*p) for p in self.polygon_original_points) if c]
            if self.polygon_canvas_points:
                self._draw_polygon_feedback()
        elif mode == "rectangle" and self.rect_first_original:
            fc = self._original_to_canvas_coords(*self.rect_first_original)
            if fc:
                self.rect_first_canvas = fc
            if self.rect_second_original:
                sc = self._original_to_canvas_coords(*self.rect_second_original)
                if sc:
                    self.rect_second_canvas = sc
            self._draw_rectangle_feedback()

    def _draw_circle_feedback(self):
        if not self.center_canvas_coords:
            return
        r = self._get_circle_radius()
        if r is None or not self.image_display_rect or self.image_display_rect[2] == 0 or self.original_image.size[0] == 0:
            return
        rc = r * (self.image_display_rect[2] / self.original_image.size[0])
        cx, cy = self.center_canvas_coords
        color = self._get_draw_color()
        width = self._get_draw_width()
        self._clear_drawn_feedback()
        self.drawn_canvas_items.append(
            self.canvas.create_oval(cx - rc, cy - rc, cx + rc, cy + rc, outline=color, width=width, tags="drawn_shape")
        )
        mr = 3
        self.drawn_canvas_items.append(
            self.canvas.create_oval(cx - mr, cy - mr, cx + mr, cy + mr, fill=ERROR, outline=ERROR, tags="drawn_shape")
        )
        self.canvas.tag_raise("drawn_shape")

    def _draw_polygon_feedback(self):
        if not self.polygon_canvas_points:
            return
        self._clear_drawn_feedback()
        color = self._get_draw_color()
        width = self._get_draw_width()
        mr = 3
        for i, (px, py) in enumerate(self.polygon_canvas_points):
            c = SECONDARY if i == 0 else ERROR
            self.drawn_canvas_items.append(
                self.canvas.create_oval(px - mr, py - mr, px + mr, py + mr, fill=c, outline=c, tags="drawn_shape")
            )
        if len(self.polygon_canvas_points) > 1:
            for i in range(len(self.polygon_canvas_points) - 1):
                x1, y1 = self.polygon_canvas_points[i]
                x2, y2 = self.polygon_canvas_points[i + 1]
                self.drawn_canvas_items.append(
                    self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width, tags="drawn_shape")
                )
            if self.is_polygon_closed:
                x1, y1 = self.polygon_canvas_points[-1]
                x2, y2 = self.polygon_canvas_points[0]
                self.drawn_canvas_items.append(
                    self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width, tags="drawn_shape")
                )
        self.canvas.tag_raise("drawn_shape")

    def _draw_rectangle_feedback(self):
        self._clear_drawn_feedback()
        color = self._get_draw_color()
        width = self._get_draw_width()
        mr = 3
        if self.rect_first_canvas:
            fx, fy = self.rect_first_canvas
            if self.rect_second_canvas:
                sx, sy = self.rect_second_canvas
                # Draw dashed rectangle
                self.drawn_canvas_items.append(
                    self.canvas.create_rectangle(
                        fx, fy, sx, sy,
                        outline=color, width=width, dash=(6, 4), tags="drawn_shape",
                    )
                )
                # Corner markers
                for mx, my in [(fx, fy), (sx, sy)]:
                    self.drawn_canvas_items.append(
                        self.canvas.create_oval(mx - mr, my - mr, mx + mr, my + mr, fill=ERROR, outline=ERROR, tags="drawn_shape")
                    )
            else:
                # Just the first corner marker
                self.drawn_canvas_items.append(
                    self.canvas.create_oval(fx - mr, fy - mr, fx + mr, fy + mr, fill=ERROR, outline=ERROR, tags="drawn_shape")
                )
        self.canvas.tag_raise("drawn_shape")

    # ── SVG generation ────────────────────────────────────────────

    def _svg_stroke_attr(self):
        """Return the stroke-width attribute string."""
        sw = round(self.stroke_width_var.get(), 1)
        sw_s = f"{int(sw)}" if sw == int(sw) else f"{sw}"
        return f' stroke-width="{sw_s}"'

    def _generate_circle_svg(self):
        if not self.center_original_coords:
            self.generated_svg_path = ""
            self._update_output_text()
            return
        r = self._get_circle_radius()
        if r is None:
            return
        cx, cy = self.center_original_coords
        r_r = round(r, 2)
        r_s = f"{int(r_r)}" if r_r == int(r_r) else f"{r_r:.2f}"
        sy = round(round(cy, 2) - r_r, 2)
        dy1 = round(2 * r_r, 2)
        dy2 = round(-2 * r_r, 2)
        dy1s = f"{int(dy1)}" if dy1 == int(dy1) else f"{dy1:.2f}"
        dy2s = f"{int(dy2)}" if dy2 == int(dy2) else f"{dy2:.2f}"
        path_d = f"M{round(cx, 2):.2f} {sy:.2f}a{r_s},{r_s} 0 1 0 0,{dy1s}a{r_s},{r_s} 0 1 0 0,{dy2s}Z"
        sw_attr = self._svg_stroke_attr()
        color = self._get_draw_color()
        self.generated_svg_path = f'<path d="{path_d}" fill="none" stroke="{color}"{sw_attr} />'
        self._store_svg_element(self.generated_svg_path)
        self._update_output_text()

    def _generate_polygon_svg(self):
        if not self.polygon_original_points:
            self.generated_svg_path = ""
            self._update_output_text()
            return
        segs = [f"{'M' if i == 0 else 'L'}{round(ox, 2):.2f} {round(oy, 2):.2f}" for i, (ox, oy) in enumerate(self.polygon_original_points)]
        d = " ".join(segs)
        if self.is_polygon_closed or len(self.polygon_original_points) > 2:
            d += " Z"
        sw_attr = self._svg_stroke_attr()
        color = self._get_draw_color()
        self.generated_svg_path = f'<path d="{d}" fill="none" stroke="{color}"{sw_attr} />'
        self._store_svg_element(self.generated_svg_path)
        self._update_output_text()

    def _generate_rectangle_svg(self):
        if not self.rect_first_original or not self.rect_second_original:
            self.generated_svg_path = ""
            self._update_output_text()
            return
        x1, y1 = self.rect_first_original
        x2, y2 = self.rect_second_original
        rx = round(min(x1, x2), 2)
        ry = round(min(y1, y2), 2)
        rw = round(abs(x2 - x1), 2)
        rh = round(abs(y2 - y1), 2)
        sw_attr = self._svg_stroke_attr()
        color = self._get_draw_color()
        self.generated_svg_path = f'<rect x="{rx:.2f}" y="{ry:.2f}" width="{rw:.2f}" height="{rh:.2f}" fill="none" stroke="{color}"{sw_attr} />'
        self._store_svg_element(self.generated_svg_path)
        self._update_output_text()

    def _store_svg_element(self, element):
        """Store the latest SVG element for export. Replace last if same shape is being refined."""
        # For polygon, keep replacing until closed; for circle/rect always replace last
        mode = self.current_mode.get()
        if mode == "polygon" and not self.is_polygon_closed:
            # Update the in-progress polygon element
            if self.all_svg_elements and self.all_svg_elements[-1].startswith('<path d="M') and 'polygon-wip' in (getattr(self, '_last_tag', '') or ''):
                self.all_svg_elements[-1] = element
            else:
                self.all_svg_elements.append(element)
                self._last_tag = 'polygon-wip'
        elif mode == "polygon" and self.is_polygon_closed:
            # Finalize
            if self.all_svg_elements and getattr(self, '_last_tag', '') == 'polygon-wip':
                self.all_svg_elements[-1] = element
            else:
                self.all_svg_elements.append(element)
            self._last_tag = 'polygon-done'
        else:
            self.all_svg_elements.append(element)
            self._last_tag = ''

    def _update_output_text(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, self.generated_svg_path)
        self.output_text.config(state=tk.DISABLED)
        self._manage_scrollbar_visibility()

    def _manage_scrollbar_visibility(self, event=None):
        if not hasattr(self.output_text, 'vbar') or not self.output_text.vbar:
            return
        self.output_text.update_idletasks()
        first, last = self.output_text.yview()
        if first == 0.0 and last == 1.0:
            if self.output_text.vbar.winfo_ismapped():
                self.output_text.vbar.pack_forget()
        else:
            if not self.output_text.vbar.winfo_ismapped():
                self.output_text.vbar.pack(side=tk.RIGHT, fill=tk.Y)

    # ── Stroke width callback ─────────────────────────────────────

    def _on_stroke_change(self, value=None):
        sw = round(self.stroke_width_var.get(), 1)
        self._stroke_value_label.config(text=f"{sw}")
        # Redraw feedback and regenerate SVG
        self._redraw_feedback_shapes()
        mode = self.current_mode.get()
        if mode == "circle" and self.center_original_coords:
            self._generate_circle_svg()
        elif mode == "polygon" and self.polygon_original_points:
            self._generate_polygon_svg()
        elif mode == "rectangle" and self.rect_second_original:
            self._generate_rectangle_svg()

    # ── Color callbacks ───────────────────────────────────────────

    def _pick_color(self, event=None):
        result = colorchooser.askcolor(color=self.color_var.get(), title="Pick Stroke Color", parent=self.master)
        if result and result[1]:
            self.color_var.set(result[1])
            self._apply_color_change()

    def _on_color_entry_change(self, event=None):
        self._apply_color_change()

    def _apply_color_change(self):
        color = self.color_var.get()
        try:
            self.canvas.winfo_rgb(color)
        except Exception:
            return
        self._color_swatch.itemconfig(self._swatch_rect, fill=color)
        # Redraw feedback and regenerate SVG
        self._redraw_feedback_shapes()
        mode = self.current_mode.get()
        if mode == "circle" and self.center_original_coords:
            self._generate_circle_svg()
        elif mode == "polygon" and self.polygon_original_points:
            self._generate_polygon_svg()
        elif mode == "rectangle" and self.rect_second_original:
            self._generate_rectangle_svg()

    # ── Copy / Export ─────────────────────────────────────────────

    def _copy_svg(self):
        text = self.generated_svg_path.strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)

    def _export_svg(self):
        if not self.all_svg_elements:
            messagebox.showinfo("Nothing to Export", "Draw at least one shape first.", parent=self.master)
            return
        if not self.original_image:
            messagebox.showinfo("No Image", "Load an image first.", parent=self.master)
            return
        path = filedialog.asksaveasfilename(
            title="Export SVG",
            defaultextension=".svg",
            filetypes=[("SVG Files", "*.svg"), ("All Files", "*.*")],
            parent=self.master,
        )
        if not path:
            return
        ow, oh = self.original_image.size
        elements = "\n  ".join(self.all_svg_elements)
        svg_content = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ow} {oh}">\n'
            f'  {elements}\n'
            f'</svg>\n'
        )
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to write SVG: {e}", parent=self.master)

    # ── Utilities ─────────────────────────────────────────────────

    def _validate_radius(self, P):
        if P == "":
            return True
        try:
            return P.count('.') <= 1 and float(P) is not None
        except ValueError:
            return False

    def _get_circle_radius(self):
        try:
            s = self.radius_var.get()
            if not s:
                self.radius_var.set("20")
                return 20.0
            v = float(s)
            if v <= 0:
                self.radius_var.set("20")
                return 20.0
            return v
        except ValueError:
            self.radius_var.set("20")
            return 20.0

    def _on_radius_change(self, event=None):
        self._get_circle_radius()
        if self.current_mode.get() == "circle" and self.center_original_coords:
            self._draw_circle_feedback()
            self._generate_circle_svg()

    def clear_shapes(self, keep_mode=False):
        self._clear_drawn_feedback()
        self.center_original_coords = self.center_canvas_coords = None
        self.polygon_original_points = []
        self.polygon_canvas_points = []
        self.is_polygon_closed = False
        self.rect_first_original = self.rect_first_canvas = None
        self.rect_second_original = self.rect_second_canvas = None
        self.shape_drawn = False
        self.generated_svg_path = ""
        self._update_output_text()
        if self.original_image:
            self._update_instructions()

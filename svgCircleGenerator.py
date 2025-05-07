import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, StringVar
from PIL import Image, ImageTk
import os
import math
from sys import platform

class SVGCircleGeneratorGUI(ttk.Frame):
    """
    A Tkinter Frame for loading an image, allowing the user to draw
    either a circle (by clicking center and defining radius) or a polygon
    (by clicking vertices), and generating the corresponding SVG path data.
    """
    def __init__(self, master=None, **kwargs):
        """
        Initializes the Frame and its widgets.
        """
        super().__init__(master, **kwargs)
        self.master = master # Store master window reference

        # --- Constants ---
        self.POLYGON_CLOSING_THRESHOLD = 15 # Max distance in canvas pixels to close polygon

        # --- State Variables ---
        self.image_path = None
        self.tk_image = None
        self.original_image = None
        self.display_image = None
        self.canvas_image_id = None
        self.image_display_rect = None # Stores (x, y, width, height) of the image on the canvas
        self.shape_drawn = False       # Flag to indicate if any shape element exists

        # Drawing Mode
        self.current_mode = StringVar(value="circle") # Modes: "circle", "polygon"

        # Circle Specific State
        self.center_original_coords = None   # Stores (original_x, original_y) of the center
        self.center_canvas_coords = None     # Stores (canvas_x, canvas_y) for drawing
        self.radius_var = StringVar(value="20") # Default radius value

        # Polygon Specific State
        self.polygon_original_points = [] # List of (original_x, original_y) tuples for SVG
        self.polygon_canvas_points = []   # List of (canvas_x, canvas_y) tuples for drawing
        self.is_polygon_closed = False

        # Shared State / Output
        self.generated_svg_path = ""
        self.drawn_canvas_items = [] # Keep track of drawn feedback shapes (markers, lines)

        # Determine cursor type based on platform
        self.cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        self.cursor_crosshair = "crosshair"

        # --- Widgets ---
        # Frame for top controls
        self.control_frame = ttk.Frame(self)
        self.control_frame.pack(pady=10, padx=10, fill=tk.X)

        # Load Image Button
        self.load_button = ttk.Button(self.control_frame, text="Load Image", command=self.load_image, cursor=self.cursor_point)
        self.load_button.grid(row=0, column=0, padx=5)

        # Mode Selector Frame
        self.mode_frame = ttk.LabelFrame(self.control_frame, text="Shape Type")
        self.mode_frame.grid(row=0, column=1, padx=10)
        self.circle_radio = ttk.Radiobutton(self.mode_frame, text="Circle", variable=self.current_mode, value="circle", command=self._update_mode, cursor=self.cursor_point)
        self.circle_radio.pack(side=tk.LEFT, padx=5)
        self.polygon_radio = ttk.Radiobutton(self.mode_frame, text="Polygon", variable=self.current_mode, value="polygon", command=self._update_mode, cursor=self.cursor_point)
        self.polygon_radio.pack(side=tk.LEFT, padx=5)

        # Clear Shape Button
        self.clear_button = ttk.Button(self.control_frame, text="Clear Shape", command=self.clear_shapes, cursor=self.cursor_point)
        self.clear_button.grid(row=0, column=2, padx=5)
        self.clear_button.config(state=tk.DISABLED)

        # Radius Input (conditionally shown)
        self.radius_frame = ttk.Frame(self.control_frame)
        self.radius_frame.grid(row=0, column=3, padx=(10, 5)) # Initially place it
        self.radius_label = ttk.Label(self.radius_frame, text="Radius:")
        self.radius_label.pack(side=tk.LEFT)
        # Validate command to allow only numbers and one decimal point
        vcmd = (self.register(self._validate_radius), '%P')
        self.radius_entry = ttk.Entry(self.radius_frame, textvariable=self.radius_var, width=5, validate='key', validatecommand=vcmd)
        self.radius_entry.pack(side=tk.LEFT, padx=(2,0))
        self.radius_entry.bind("<FocusOut>", self._on_radius_change)
        self.radius_entry.bind("<Return>", self._on_radius_change)

        # Canvas for Image Display
        # Set initial size, will be adjusted by image loading
        self.canvas = tk.Canvas(self, width=600, height=400, highlightthickness=0) # Removed bg
        self.canvas.pack(pady=10, padx=10, expand=True, fill=tk.BOTH)
        self.canvas.bind("<Button-1>", self.on_canvas_click) # Bind left mouse click
        self.canvas.bind("<Configure>", self._on_canvas_resize) # Handle window resize

        # Label for instructions
        self.instruction_label = ttk.Label(self, text="Load an image to begin.")
        self.instruction_label.pack(pady=(0,5), padx=10, anchor=tk.W) # Adjusted padding

        # Text Area for SVG Output
        self.output_label = ttk.Label(self, text="Generated SVG Path Data:")
        self.output_label.pack(padx=10, anchor=tk.W)
        self.output_text = scrolledtext.ScrolledText(self, height=4, wrap=tk.WORD, bg="#5A6268", fg="#333333", relief=tk.SOLID, borderwidth=1)
        self.output_text.pack(pady=(0,10), padx=10, fill=tk.X)
        self.output_text.config(state=tk.DISABLED) # Read-only
        
        # --- Manage scrollbar visibility for output_text ---
        # Bind to <Configure> event of the Text component of ScrolledText
        # to re-evaluate scrollbar visibility if its size changes (e.g., due to window resize and fill=X)
        self.output_text.bind("<Configure>", self._manage_scrollbar_visibility)
        # Initial check will be triggered by _update_mode -> clear_shapes -> _update_output_text

        # Initial UI setup based on mode
        self._update_mode()

    # --- Mode and UI Update ---

    def _update_mode(self):
        """Updates UI elements based on the selected drawing mode."""
        mode = self.current_mode.get()
        self.clear_shapes() # Clear existing shapes when mode changes

        if mode == "circle":
            # Show radius input
            self.radius_frame.grid() # Make visible by placing in grid
            self.clear_button.config(text="Clear Circle")
            self.canvas.config(cursor=self.cursor_crosshair)
        elif mode == "polygon":
            # Hide radius input
            self.radius_frame.grid_remove() # Hide without losing grid config
            self.clear_button.config(text="Clear Polygon")
            self.canvas.config(cursor=self.cursor_crosshair)
        else:
             self.canvas.config(cursor="") # Default cursor if no image

        self._update_instructions()

    def _update_instructions(self):
        """Sets the instruction label text based on current state."""
        if not self.original_image:
            self.instruction_label.config(text="Load an image to begin.")
            return

        mode = self.current_mode.get()
        if mode == "circle":
            if self.shape_drawn:
                self.instruction_label.config(text="Circle generated. Click 'Clear Circle' to draw another.")
            else:
                self.instruction_label.config(text="Click on the image to define the circle's center.")
        elif mode == "polygon":
            if self.is_polygon_closed:
                self.instruction_label.config(text=f"Polygon closed ({len(self.polygon_original_points)} points). Click 'Clear Polygon' to start over.")
            elif not self.polygon_original_points:
                self.instruction_label.config(text="Click on the image to add the first point of the polygon.")
            elif len(self.polygon_original_points) < 3:
                 self.instruction_label.config(text=f"Click to add more points. Current points: {len(self.polygon_original_points)}.")
            else:
                 self.instruction_label.config(text=f"Click to add more points, or click near the first point (<{self.POLYGON_CLOSING_THRESHOLD}px) to close. Points: {len(self.polygon_original_points)}.")

    # --- Image Loading and Handling ---

    def load_image(self):
        """
        Opens a file dialog, loads image, displays it scaled to fit,
        calculates display metrics, and resets state.
        """
        file_path = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff"), ("All Files", "*.*")],
            parent=self.master # Specify parent for dialog
        )
        if not file_path: return

        try:
            # Load the original image
            self.original_image = Image.open(file_path)
            self.image_path = file_path

            # Reset state before displaying
            self.clear_shapes()
            self.canvas.config(cursor=self.cursor_crosshair) # Set appropriate cursor

            # Display the image (this will trigger _on_canvas_resize -> _display_loaded_image)
            self._display_loaded_image()

            self.clear_button.config(state=tk.NORMAL)


        except Exception as e:
            messagebox.showerror("Error Loading Image", f"Failed to load image: {e}", parent=self.master)
            self._reset_image_state()

    def _on_canvas_resize(self, event=None):
        """Handles canvas resize events to redraw the image scaled correctly."""
        # This check prevents errors during initial setup or if image is cleared
        if self.original_image and self.canvas.winfo_width() > 1 and self.canvas.winfo_height() > 1:
            self._display_loaded_image()


    def _display_loaded_image(self):
        """
        Scales the original image to fit the current canvas size,
        displays it, and calculates the image's position and scale.
        Also redraws any existing shapes.
        """
        if not self.original_image:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Prevent division by zero if canvas is too small initially
        if canvas_width <= 1 or canvas_height <= 1:
            return # Wait for a proper size

        img_width, img_height = self.original_image.size

        # Calculate scaling factor to fit image within canvas while maintaining aspect ratio
        width_ratio = canvas_width / img_width
        height_ratio = canvas_height / img_height
        scale_factor = min(width_ratio, height_ratio)

        # Calculate the dimensions of the displayed image
        display_width = int(img_width * scale_factor)
        display_height = int(img_height * scale_factor)

        # Resize the image using LANCZOS for better quality
        self.display_image = self.original_image.resize((display_width, display_height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.display_image)

        # Calculate the top-left corner (x, y) to center the image on the canvas
        display_x = (canvas_width - display_width) / 2
        display_y = (canvas_height - display_height) / 2

        # Store the display rectangle and scale factor
        self.image_display_rect = (display_x, display_y, display_width, display_height)

        # Clear previous image and draw the new one
        if self.canvas_image_id:
            self.canvas.delete(self.canvas_image_id)
        self.canvas_image_id = self.canvas.create_image(display_x, display_y, anchor=tk.NW, image=self.tk_image)

        # Bring drawn shapes to the front if they exist
        self.canvas.tag_raise("drawn_shape")

        # Recalculate canvas coordinates for existing shapes and redraw them
        self._redraw_feedback_shapes()
        self._update_instructions() # Update instructions as image is now loaded

    def _reset_image_state(self):
        """Resets all image-related state variables."""
        self.image_path = None
        self.original_image = None
        self.display_image = None
        self.tk_image = None
        if self.canvas_image_id:
            self.canvas.delete(self.canvas_image_id)
            self.canvas_image_id = None
        self.image_display_rect = None
        self.clear_button.config(state=tk.DISABLED)
        self.canvas.config(cursor="") # Reset cursor
        self.clear_shapes() # Also clear any drawing state
        self._update_instructions()


    # --- Coordinate Conversion ---

    def _canvas_to_original_coords(self, canvas_x, canvas_y):
        """Converts canvas coordinates to original image coordinates."""
        if not self.image_display_rect or not self.original_image:
            return None

        disp_x, disp_y, disp_w, disp_h = self.image_display_rect
        orig_w, orig_h = self.original_image.size

        # Check if click is within the displayed image bounds
        if not (disp_x <= canvas_x < disp_x + disp_w and disp_y <= canvas_y < disp_y + disp_h):
            # print("Click outside displayed image bounds.") # Optional debug
            return None

        # Calculate coordinates relative to the displayed image's top-left corner
        x_in_display = canvas_x - disp_x
        y_in_display = canvas_y - disp_y

        # Scale back up to original image coordinates
        # Prevent division by zero if display width/height is somehow zero
        if disp_w == 0 or disp_h == 0: return None
        original_x = (x_in_display / disp_w) * orig_w
        original_y = (y_in_display / disp_h) * orig_h

        # Clamp to ensure coordinates are within the original image dimensions
        original_x = max(0, min(orig_w, original_x))
        original_y = max(0, min(orig_h, original_y))

        return (original_x, original_y)

    def _original_to_canvas_coords(self, original_x, original_y):
        """Converts original image coordinates to canvas coordinates."""
        if not self.image_display_rect or not self.original_image:
            return None

        disp_x, disp_y, disp_w, disp_h = self.image_display_rect
        orig_w, orig_h = self.original_image.size

        # Prevent division by zero
        if orig_w == 0 or orig_h == 0: return None

        # Scale down to displayed image coordinates
        x_in_display = (original_x / orig_w) * disp_w
        y_in_display = (original_y / orig_h) * disp_h

        # Add the display offset to get canvas coordinates
        canvas_x = x_in_display + disp_x
        canvas_y = y_in_display + disp_y

        return (canvas_x, canvas_y)

    # --- Click Handling ---

    def on_canvas_click(self, event):
        """Handles mouse clicks on the canvas based on the current mode."""
        if not self.original_image or not self.image_display_rect:
            messagebox.showwarning("No Image", "Please load an image first.", parent=self.master)
            return

        canvas_x, canvas_y = event.x, event.y
        original_coords = self._canvas_to_original_coords(canvas_x, canvas_y)

        if original_coords is None:
            # Click was outside the image area on the canvas
            return

        mode = self.current_mode.get()

        if mode == "circle":
            self._handle_circle_click(canvas_x, canvas_y, original_coords)
        elif mode == "polygon":
            self._handle_polygon_click(canvas_x, canvas_y, original_coords)

        # Mark that some shape element now exists (or is being drawn)
        if (mode == "circle" and self.center_original_coords) or \
           (mode == "polygon" and self.polygon_original_points):
             self.shape_drawn = True
             self._update_instructions()


    def _handle_circle_click(self, canvas_x, canvas_y, original_coords):
        """Handles click logic for Circle mode."""
        # In circle mode, each click defines a new center
        self.clear_shapes(keep_mode=True) # Clear previous circle before drawing new

        radius_original = self._get_circle_radius()
        if radius_original is None: return # Validation failed

        self.center_original_coords = original_coords
        self.center_canvas_coords = (canvas_x, canvas_y)

        self._draw_circle_feedback()
        self._generate_circle_svg()

    def _handle_polygon_click(self, canvas_x, canvas_y, original_coords):
        """Handles click logic for Polygon mode."""
        if self.is_polygon_closed:
            messagebox.showinfo("Polygon Closed", "Polygon is already closed. Click 'Clear Polygon' to start a new one.", parent=self.master)
            return

        # Check for closing click (if enough points exist)
        if len(self.polygon_canvas_points) >= 3:
            first_canvas_x, first_canvas_y = self.polygon_canvas_points[0]
            dist_sq = (canvas_x - first_canvas_x)**2 + (canvas_y - first_canvas_y)**2
            if dist_sq < self.POLYGON_CLOSING_THRESHOLD**2:
                self.is_polygon_closed = True
                print("Polygon closed by clicking near start.") # Debug info
                # Don't add the closing click as a new point
                self._draw_polygon_feedback() # Redraw to show the closed line
                self._generate_polygon_svg() # Generate final SVG with 'Z'
                self._update_instructions()
                return # Stop processing this click

        # If not closing, add the new point
        self.polygon_original_points.append(original_coords)
        self.polygon_canvas_points.append((canvas_x, canvas_y))

        self._draw_polygon_feedback()
        self._generate_polygon_svg() # Update SVG as points are added

    # --- Drawing Feedback ---

    def _clear_drawn_feedback(self):
        """Removes all feedback shapes (markers, lines) from the canvas."""
        for item_id in self.drawn_canvas_items:
            self.canvas.delete(item_id)
        self.drawn_canvas_items = []

    def _redraw_feedback_shapes(self):
        """Clears existing feedback and redraws based on current state and mode."""
        self._clear_drawn_feedback()
        if not self.original_image: return # No image, nothing to draw on

        mode = self.current_mode.get()
        if mode == "circle" and self.center_original_coords:
            # Recalculate canvas coords for center
            canvas_coords = self._original_to_canvas_coords(*self.center_original_coords)
            if canvas_coords:
                self.center_canvas_coords = canvas_coords
                self._draw_circle_feedback()
        elif mode == "polygon" and self.polygon_original_points:
            # Recalculate canvas coords for all polygon points
            self.polygon_canvas_points = []
            for orig_pt in self.polygon_original_points:
                canvas_pt = self._original_to_canvas_coords(*orig_pt)
                if canvas_pt:
                    self.polygon_canvas_points.append(canvas_pt)
                else:
                    # Handle case where a point might be off-canvas after resize (unlikely with clamping)
                    print(f"Warning: Original point {orig_pt} could not be converted to canvas coordinates.")
                    # Decide how to handle this - skip point, clear shape? For now, just skip.
                    pass
            # Only draw if we still have points
            if self.polygon_canvas_points:
                 self._draw_polygon_feedback()


    def _draw_circle_feedback(self):
        """Draws the circle outline and center marker on the canvas."""
        if not self.center_canvas_coords: return

        radius_original = self._get_circle_radius()
        if radius_original is None: return

        # Calculate radius for canvas display (scaled)
        # Use the width scale factor for radius scaling
        if not self.image_display_rect or self.image_display_rect[2] == 0 or self.original_image.size[0] == 0:
             return # Cannot calculate scale
        radius_canvas = radius_original * (self.image_display_rect[2] / self.original_image.size[0])


        canvas_x, canvas_y = self.center_canvas_coords

        # Clear previous feedback first (important if only radius changes)
        self._clear_drawn_feedback()

        # Draw Circle outline
        circle_id = self.canvas.create_oval(
            canvas_x - radius_canvas, canvas_y - radius_canvas,
            canvas_x + radius_canvas, canvas_y + radius_canvas,
            outline="cyan", width=2, tags="drawn_shape" # Use tag for layering
        )
        self.drawn_canvas_items.append(circle_id)

        # Draw Center marker
        marker_radius = 3
        marker_id = self.canvas.create_oval(
            canvas_x - marker_radius, canvas_y - marker_radius,
            canvas_x + marker_radius, canvas_y + marker_radius,
            fill="red", outline="red", tags="drawn_shape"
        )
        self.drawn_canvas_items.append(marker_id)
        self.canvas.tag_raise("drawn_shape") # Ensure feedback is on top of image


    def _draw_polygon_feedback(self):
        """Draws polygon vertices and connecting lines on the canvas."""
        if not self.polygon_canvas_points: return

        # Clear previous feedback first
        self._clear_drawn_feedback()

        marker_radius = 3
        # Draw markers for each vertex
        for i, (px, py) in enumerate(self.polygon_canvas_points):
            fill_color = "blue" if i == 0 else "red" # First point blue, others red
            marker_id = self.canvas.create_oval(
                px - marker_radius, py - marker_radius,
                px + marker_radius, py + marker_radius,
                fill=fill_color, outline=fill_color, tags="drawn_shape"
            )
            self.drawn_canvas_items.append(marker_id)

        # Draw lines connecting vertices
        if len(self.polygon_canvas_points) > 1:
            for i in range(len(self.polygon_canvas_points) - 1):
                x1, y1 = self.polygon_canvas_points[i]
                x2, y2 = self.polygon_canvas_points[i+1]
                line_id = self.canvas.create_line(x1, y1, x2, y2, fill="yellow", width=2, tags="drawn_shape")
                self.drawn_canvas_items.append(line_id)

            # Draw the closing line if the polygon is closed
            if self.is_polygon_closed and len(self.polygon_canvas_points) > 1:
                x1, y1 = self.polygon_canvas_points[-1]
                x2, y2 = self.polygon_canvas_points[0]
                line_id = self.canvas.create_line(x1, y1, x2, y2, fill="yellow", width=2, tags="drawn_shape")
                self.drawn_canvas_items.append(line_id)

        self.canvas.tag_raise("drawn_shape") # Ensure feedback is on top of image

    # --- SVG Generation ---

    def _generate_circle_svg(self):
        """Generates the SVG path data for the circle."""
        if not self.center_original_coords:
            self.generated_svg_path = ""
            self._update_output_text()
            return

        radius_original = self._get_circle_radius()
        if radius_original is None: return # Validation failed

        cx, cy = self.center_original_coords
        r = radius_original

        # Round coordinates and radius for SVG output
        cx_r = round(cx, 2)
        cy_r = round(cy, 2)
        r_r = round(r, 2)

        # Format radius to avoid unnecessary decimals if it's an integer
        r_str = f"{int(r_r)}" if r_r == int(r_r) else f"{r_r:.2f}"

        # Move to the top point of the circle
        start_x = cx_r
        start_y = round(cy_r - r_r, 2)

        # Calculate endpoint y-coordinates relative to start_y for arcs
        # Use 2*r for the relative move, ensuring precision
        dy1_r = round(2 * r_r, 2)
        dy2_r = round(-2 * r_r, 2)

        # Format relative moves
        dy1_str = f"{int(dy1_r)}" if dy1_r == int(dy1_r) else f"{dy1_r:.2f}"
        dy2_str = f"{int(dy2_r)}" if dy2_r == int(dy2_r) else f"{dy2_r:.2f}"


        # First arc: from top to bottom (180 degrees) - relative move
        arc1 = f"a{r_str},{r_str} 0 1 0 0,{dy1_str}" # large-arc=1, sweep=0

        # Second arc: from bottom back to top (180 degrees) - relative move
        arc2 = f"a{r_str},{r_str} 0 1 0 0,{dy2_str}" # large-arc=1, sweep=0

        # Construct the full path string
        self.generated_svg_path = f"M{start_x:.2f} {start_y:.2f}{arc1}{arc2}Z"
        self._update_output_text()

    def _generate_polygon_svg(self):
        """Generates the SVG path data for the polygon."""
        if not self.polygon_original_points:
            self.generated_svg_path = ""
            self._update_output_text()
            return

        # Build path segments
        path_segments = []
        for i, (ox, oy) in enumerate(self.polygon_original_points):
            prefix = "M" if i == 0 else "L"
            # Round original coordinates for SVG
            ox_r = round(ox, 2)
            oy_r = round(oy, 2)
            path_segments.append(f"{prefix}{ox_r:.2f} {oy_r:.2f}")

        path_data = " ".join(path_segments)

        # Add 'Z' to close the path if it's marked as closed or has enough points
        # Swift adds Z if count > 2, let's match that logic for implicit closing view
        # But also explicitly add if is_polygon_closed is True
        if self.is_polygon_closed or len(self.polygon_original_points) > 2:
            path_data += " Z"

        self.generated_svg_path = path_data
        self._update_output_text()


    def _update_output_text(self):
        """Updates the SVG output text area."""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, self.generated_svg_path)
        self.output_text.config(state=tk.DISABLED)
        self._manage_scrollbar_visibility() # Update scrollbar based on new content

    def _manage_scrollbar_visibility(self, event=None):
        """Shows or hides the scrollbar for output_text based on content."""
        if not hasattr(self.output_text, 'vbar') or not self.output_text.vbar:
            return # Should not happen with ScrolledText

        # Force Tkinter to update layout and pending tasks to get accurate yview
        self.output_text.update_idletasks()

        first, last = self.output_text.yview()

        # If first is 0.0 and last is 1.0, all content is visible
        if first == 0.0 and last == 1.0:
            # Content fits, hide scrollbar if it's currently visible
            if self.output_text.vbar.winfo_ismapped():
                self.output_text.vbar.pack_forget()
        else:
            # Content overflows, show scrollbar if it's currently hidden
            if not self.output_text.vbar.winfo_ismapped():
                # Re-pack the scrollbar. ScrolledText internally packs the Text widget
                # to the LEFT and the Scrollbar to the RIGHT within its internal frame.
                # We replicate the original packing for the scrollbar.
                self.output_text.vbar.pack(side=tk.RIGHT, fill=tk.Y)



    # --- Utility and State Management ---

    def _validate_radius(self, P):
        """Validation function for radius entry: allows only numbers and one dot."""
        if P == "": return True # Allow empty string (e.g., during deletion)
        try:
            if P.count('.') <= 1:
                float(P) # Check if it's a valid float representation
                return True # Allow if it's a number or partial number
            else:
                return False # Disallow more than one dot
        except ValueError:
            # Handle cases like "-" or "." at the beginning if needed,
            # but for radius, we usually want positive numbers.
            # Let's disallow anything that doesn't form a valid number start.
            return False

    def _get_circle_radius(self):
        """Gets and validates the circle radius from the entry field."""
        try:
            radius_str = self.radius_var.get()
            if not radius_str: # Handle empty case
                 messagebox.showwarning("Invalid Radius", "Radius cannot be empty. Using default (20).", parent=self.master)
                 self.radius_var.set("20")
                 return 20.0
            radius = float(radius_str)
            if radius <= 0:
                messagebox.showwarning("Invalid Radius", "Radius must be a positive number. Using default (20).", parent=self.master)
                self.radius_var.set("20")
                return 20.0
            return radius # Return the valid float
        except ValueError:
            messagebox.showwarning("Invalid Radius", "Radius must be a valid number. Using default (20).", parent=self.master)
            self.radius_var.set("20")
            return 20.0

    def _on_radius_change(self, event=None):
        """Callback when radius entry loses focus or Enter is pressed."""
        # Validate the final value
        valid_radius = self._get_circle_radius()
        # If in circle mode and a center exists, redraw feedback and regenerate SVG
        if self.current_mode.get() == "circle" and self.center_original_coords:
            self._draw_circle_feedback()
            self._generate_circle_svg()


    def clear_shapes(self, keep_mode=False):
        """
        Removes drawn shapes, clears output, and resets drawing state.
        Optionally keeps the current mode selected.
        """
        self._clear_drawn_feedback() # Remove visuals from canvas

        # Reset state variables
        self.center_original_coords = None
        self.center_canvas_coords = None
        self.polygon_original_points = []
        self.polygon_canvas_points = []
        self.is_polygon_closed = False
        self.shape_drawn = False
        self.generated_svg_path = ""

        self._update_output_text() # Clear the output text area

        if self.original_image: # Only update instructions if image is loaded
            self._update_instructions()

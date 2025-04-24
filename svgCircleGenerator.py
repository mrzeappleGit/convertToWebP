import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, StringVar
from PIL import Image, ImageTk
import os
import math # Keep for potential future use
from sys import platform # Import platform for cursor handling

class SVGCircleGeneratorGUI(ttk.Frame):
    """
    A Tkinter Frame for loading an image, allowing the user to click a
    center point, input a radius, draw a visual representation of the
    circle, and generate a single SVG path string for that circle.
    Integrated as a module for the main application.
    """
    def __init__(self, master=None, **kwargs):
        """
        Initializes the Frame and its widgets.
        """
        super().__init__(master, **kwargs)

        # --- State Variables ---
        self.image_path = None
        self.tk_image = None
        self.original_image = None
        self.display_image = None
        self.canvas_image_id = None
        self.center_coords = None       # Stores (original_x, original_y) of the center
        self.center_canvas_coords = None # Stores (canvas_x, canvas_y) for drawing
        self.drawn_items = []           # Keep track of shapes drawn on canvas
        self.shape_drawn = False        # Flag to indicate if the circle has been drawn
        self.scale_factor = 1.0         # Initialize scale factor

        # Determine cursor type based on platform
        self.cursor_point = "hand2" if platform != "darwin" else "pointinghand"

        # --- Widgets ---
        # Frame for top controls (buttons and radius)
        self.control_frame = ttk.Frame(self)
        self.control_frame.pack(pady=10)

        # Load Image Button
        self.load_button = ttk.Button(self.control_frame, text="Load Image", command=self.load_image, cursor=self.cursor_point)
        self.load_button.grid(row=0, column=0, padx=5)

        # Clear Shape Button
        self.clear_button = ttk.Button(self.control_frame, text="Clear Circle", command=self.clear_shapes, cursor=self.cursor_point)
        self.clear_button.grid(row=0, column=1, padx=5)
        self.clear_button.config(state=tk.DISABLED)

        # Radius Input
        self.radius_label = ttk.Label(self.control_frame, text="Circle Radius:")
        self.radius_label.grid(row=0, column=2, padx=(10, 2))
        self.radius_var = StringVar(value="20") # Default radius value
        self.radius_entry = ttk.Entry(self.control_frame, textvariable=self.radius_var, width=5)
        self.radius_entry.grid(row=0, column=3, padx=(0, 5))

        # Canvas for Image Display
        self.canvas = tk.Canvas(self, bg="grey", width=600, height=400) # Use a neutral background
        self.canvas.pack(pady=10, padx=10, expand=True, fill=tk.BOTH)
        self.canvas.bind("<Button-1>", self.on_canvas_click) # Bind left mouse click

        # Label for instructions
        self.instruction_label = ttk.Label(self, text="Load an image, then click one point to define the circle's center.")
        self.instruction_label.pack(pady=5)

        # Text Area for SVG Output
        self.output_label = ttk.Label(self, text="Generated SVG Path Data:")
        self.output_label.pack()
        # Use standard tk ScrolledText as ttk doesn't have a direct equivalent easily styled here
        self.output_text = scrolledtext.ScrolledText(self, height=4, wrap=tk.WORD, bg="#2b2b2b", fg="white", insertbackground="white")
        self.output_text.pack(pady=10, padx=10, fill=tk.X)
        self.output_text.config(state=tk.DISABLED) # Read-only

    def get_circle_radius(self):
        """Gets and validates the circle radius from the entry field."""
        try:
            radius = float(self.radius_var.get())
            if radius <= 0:
                messagebox.showwarning("Invalid Radius", "Radius must be a positive number. Using default (20).", parent=self) # Specify parent
                self.radius_var.set("20") # Reset entry field too
                return 20.0
            return round(radius, 2)
        except ValueError:
            messagebox.showwarning("Invalid Radius", "Radius must be a number. Using default (20).", parent=self) # Specify parent
            self.radius_var.set("20") # Reset entry field too
            return 20.0

    def load_image(self):
        """
        Opens a file dialog, loads image, displays it, and resets state.
        """
        file_path = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff"), ("All Files", "*.*")],
            parent=self # Specify parent for dialog
        )
        if not file_path: return

        self.clear_shapes() # Clear previous state

        try:
            self.original_image = Image.open(file_path)
            self.image_path = file_path

            # --- Dynamically determine max dimensions based on current frame size ---
            self.update_idletasks() # Ensure frame dimensions are calculated
            max_width = self.winfo_width() - 40  # Account for padding
            max_height = self.winfo_height() - 200 # Account for controls/output area
            if max_width < 100: max_width = 500 # Minimum sensible defaults
            if max_height < 100: max_height = 300

            img_width, img_height = self.original_image.size
            self.scale_factor = 1.0

            # Calculate scale factor
            if img_width > max_width or img_height > max_height:
                ratio = min(max_width / img_width, max_height / img_height)
                self.scale_factor = ratio
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                # Use LANCZOS for resizing
                self.display_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                self.display_image = self.original_image.copy()

            self.tk_image = ImageTk.PhotoImage(self.display_image)

            # Update canvas and display image
            self.canvas.config(width=self.display_image.width, height=self.display_image.height)
            if self.canvas_image_id:
                self.canvas.delete(self.canvas_image_id)
            self.canvas_image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

            self.clear_button.config(state=tk.NORMAL)
            self.instruction_label.config(text="Click one point to define the circle's center.")
            self.shape_drawn = False

        except Exception as e:
            messagebox.showerror("Error Loading Image", f"Failed to load image: {e}", parent=self) # Specify parent
            # Reset state thoroughly on error
            self.image_path = None
            self.original_image = None
            self.display_image = None
            self.tk_image = None
            if self.canvas_image_id:
                self.canvas.delete(self.canvas_image_id)
            self.canvas.config(width=600, height=400) # Reset canvas size
            self.clear_button.config(state=tk.DISABLED)
            self.instruction_label.config(text="Load an image to begin.")
            self.shape_drawn = False


    def on_canvas_click(self, event):
        """
        Handles a single mouse click on the canvas to define the circle center.
        """
        if not self.tk_image:
            messagebox.showwarning("No Image", "Please load an image first.", parent=self)
            return
        #if self.shape_drawn:
        #     messagebox.showinfo("Shape Limit", "One circle already drawn. Click 'Clear Circle' to draw a new one.", parent=self)
        #     return

        # Clear any previous markers immediately
        for item_id in self.drawn_items:
            self.canvas.delete(item_id)
        self.drawn_items = []

        # Get click coordinates
        canvas_x, canvas_y = event.x, event.y
        # Ensure scale_factor is not zero before division
        if self.scale_factor == 0:
             messagebox.showerror("Error", "Image scaling factor is zero.", parent=self)
             return
        original_x = round(canvas_x / self.scale_factor) # Use original coords for SVG
        original_y = round(canvas_y / self.scale_factor)

        # Validate click is within bounds
        if not self.original_image: return # Should not happen if tk_image exists, but safety check
        img_width, img_height = self.original_image.size
        if not (0 <= original_x < img_width and 0 <= original_y < img_height):
             print("Click outside image bounds.") # Keep console print for debugging
             return

        # Store coordinates
        self.center_coords = (original_x, original_y)
        self.center_canvas_coords = (canvas_x, canvas_y)

        # Get radius
        radius_original = self.get_circle_radius()
        if radius_original is None: return # Validation failed

        # Calculate radius for canvas display (scaled)
        radius_canvas = radius_original * self.scale_factor

        # Draw visual feedback on the canvas (center marker and circle outline)
        # Center marker
        marker_id = self.canvas.create_oval(canvas_x-3, canvas_y-3, canvas_x+3, canvas_y+3, fill="red", outline="red")
        self.drawn_items.append(marker_id)
        # Circle outline (using canvas coordinates and radius)
        circle_id = self.canvas.create_oval(
            canvas_x - radius_canvas, canvas_y - radius_canvas,
            canvas_x + radius_canvas, canvas_y + radius_canvas,
            outline="cyan", width=2 # Changed color for visibility
        )
        self.drawn_items.append(circle_id)

        # --- Generate the SVG path for a circle using two arcs ---
        cx, cy = self.center_coords
        r = radius_original

        # Format radius to avoid unnecessary decimals if it's an integer
        r_str = f"{int(r)}" if r == int(r) else f"{r:.2f}"

        # Move to the top point of the circle (absolute coordinates)
        start_x = round(cx, 2) # Round final coordinates
        start_y = round(cy - r, 2)

        # Calculate endpoint y-coordinates relative to start_y for arcs
        dy1 = round(2 * r, 2)
        dy2 = round(-2 * r, 2)

        # First arc: from top to bottom (180 degrees)
        arc1 = f"a{r_str},{r_str} 0 1 0 0,{dy1}" # large-arc=1, sweep=0

        # Second arc: from bottom back to top (180 degrees)
        arc2 = f"a{r_str},{r_str} 0 1 0 0,{dy2}" # large-arc=1, sweep=0

        # Construct the full path string
        svg_path = f"M{start_x} {start_y}{arc1}{arc2}Z"

        # Display the path
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, svg_path)
        self.output_text.config(state=tk.DISABLED)

        # Mark shape as drawn and update instructions
        self.shape_drawn = True
        self.instruction_label.config(text="Circle generated. Click 'Clear Circle' to draw another.")


    def clear_shapes(self):
        """
        Removes drawn shapes, clears output, and resets state for a new circle.
        """
        for item_id in self.drawn_items:
            self.canvas.delete(item_id)
        self.drawn_items = []
        self.center_coords = None
        self.center_canvas_coords = None
        self.shape_drawn = False # Allow drawing again

        # Clear the output text area
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.config(state=tk.DISABLED)

        if self.tk_image:
            self.instruction_label.config(text="Click one point to define the circle's center.")
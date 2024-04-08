import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from tkinter import simpledialog

class ImageManipulationGUI(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.history = []  # To store past states
        self.future = []   # To store undone states for redo functionality

        # Toolbar for buttons
        self.toolbar = tk.Frame(self)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Load and Crop buttons
        self.load_button = ttk.Button(self.toolbar, text="Load Image", command=self.load_image)
        self.load_button.pack(side=tk.LEFT, padx=2, pady=2)

        self.crop_button = ttk.Button(self.toolbar, text="Crop", command=self.crop_image)
        self.crop_button.pack(side=tk.LEFT, padx=2, pady=2)

        # Selection tools frame
        self.selection_tools_frame = tk.Frame(self.toolbar)
        self.selection_tools_frame.pack(side=tk.LEFT, padx=5)

        self.pick_color_button = ttk.Button(self.selection_tools_frame, text="Magic Selection", command=self.pick_color)
        self.pick_color_button.pack(side=tk.LEFT, padx=2, pady=2)

        self.remove_selection_button = ttk.Button(self.selection_tools_frame, text="Remove Selection", command=self.remove_selection)
        self.remove_selection_button.pack(side=tk.LEFT, padx=2, pady=2)

        self.feather_button = ttk.Button(self.selection_tools_frame, text="Feather Selection", command=self.feather_selection)
        self.feather_button.pack(side=tk.LEFT, padx=2, pady=2)

        # Undo and Redo buttons
        self.undo_button = ttk.Button(self.toolbar, text="Undo", command=self.undo)
        self.undo_button.pack(side=tk.LEFT, padx=2, pady=2)

        self.redo_button = ttk.Button(self.toolbar, text="Redo", command=self.redo)
        self.redo_button.pack(side=tk.LEFT, padx=2, pady=2)

        # Image display label
        self.image_label = ttk.Label(self)
        self.image_label.pack(pady=5)

        self.original_image = None
        self.display_image = None

    def load_image(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.original_image = Image.open(file_path)
            self.display_image = ImageTk.PhotoImage(self.original_image)
            self.image_label.config(image=self.display_image)
            
    def pick_color(self):
        if self.original_image:
            # Bind a mouse click event to the image label
            self.image_label.bind("<Button-1>", lambda e: self.on_image_click(e, add=True))  # Left-click for selection
            self.image_label.bind("<Button-3>", lambda e: self.on_image_click(e, add=False))  # Right-click for deselection

    def on_image_click(self, event, add=True):
        self.save_state()
        # Convert the PIL image to a NumPy array for color extraction
        image_array = np.array(self.original_image.convert('RGB'))
        clicked_color = image_array[event.y, event.x]

        # Prompt user for tolerance value
        tolerance = simpledialog.askinteger("Tolerance", "Enter tolerance value (0-255):", minvalue=0, maxvalue=255)
        if tolerance is None: return  # Cancelled dialog

        # Prepare for floodFill
        h, w = image_array.shape[:2]
        mask = np.zeros((h+2, w+2), np.uint8)  # Note: mask is larger than the image
        lower_diff = upper_diff = [tolerance, tolerance, tolerance]
        seed_point = (event.x, event.y)

        # Flood fill algorithm
        flags = cv2.FLOODFILL_FIXED_RANGE | (255 << 8)
        if not add:
            flags |= cv2.FLOODFILL_MASK_ONLY  # Only update the mask for deselection
        cv2.floodFill(image_array, mask, seed_point, (255, 0, 0), tuple(lower_diff), tuple(upper_diff), flags)

        # Adjust mask size to match the image size
        adjusted_mask = mask[1:-1, 1:-1]  # Crop the mask to the size of the image

        # Ensure the selection mask is initialized
        if not hasattr(self, 'selection_mask'):
            self.selection_mask = np.zeros_like(adjusted_mask)

        # Update the selection mask with bitwise operations
        if add:
            self.selection_mask = cv2.bitwise_or(self.selection_mask, adjusted_mask)
        else:
            self.selection_mask = cv2.bitwise_and(self.selection_mask, cv2.bitwise_not(adjusted_mask))

        # Show selection on image
        self.show_selection()

    def remove_selection(self):
        self.save_state()
        if self.original_image and hasattr(self, 'selection_mask'):
            # Convert the original image to a format that includes an alpha channel (RGBA)
            rgba_image = self.original_image.convert('RGBA')
            
            # Prepare a blank (transparent) image with the same size
            new_image = Image.new("RGBA", rgba_image.size)
            
            # Get the data from both images
            rgba_data = rgba_image.getdata()
            mask_data = self.selection_mask
            
            new_data = []
            for i, pixel in enumerate(rgba_data):
                x, y = i % rgba_image.width, i // rgba_image.width
                if mask_data[y, x]:
                    # If the pixel is selected (mask is white), make it transparent
                    new_data.append((0, 0, 0, 0))
                else:
                    # Otherwise, copy the pixel from the original image
                    new_data.append(pixel)
            
            # Update the new image with the modified data
            new_image.putdata(new_data)

            # Update the original image and display image
            self.original_image = new_image
            self.display_image = ImageTk.PhotoImage(new_image)
            self.image_label.config(image=self.display_image)
            
    def feather_selection(self):
        self.save_state()
        if hasattr(self, 'selection_mask'):
            # Ask user for the feathering radius
            radius = simpledialog.askinteger("Feather Radius", "Enter feather radius (1-50):", minvalue=1, maxvalue=50)
            if radius is None: return  # Cancelled dialog
            
            # Apply Gaussian blur to the selection mask
            self.selection_mask = cv2.GaussianBlur(self.selection_mask, (radius*2+1, radius*2+1), 0)

            # Update the image display
            self.show_selection()
        
    def update_mask(self, lower_bound, upper_bound, add=True):
        open_cv_image = np.array(self.original_image)[:, :, ::-1]  # Convert to OpenCV format
        new_mask = cv2.inRange(open_cv_image, lower_bound, upper_bound)

        if not hasattr(self, 'selection_mask'):
            self.selection_mask = np.zeros(open_cv_image.shape[:2], dtype="uint8")

        if add:
            self.selection_mask = cv2.bitwise_or(self.selection_mask, new_mask)
        else:
            self.selection_mask = cv2.bitwise_and(self.selection_mask, cv2.bitwise_not(new_mask))
            
    def show_selection(self, mask_color=(255, 0, 255)):  # Example high-contrast color: magenta
        open_cv_image = np.array(self.original_image.convert('RGB'))[:, :, ::-1]  # Convert to OpenCV format

        if hasattr(self, 'selection_mask') and self.selection_mask.shape[:2] == open_cv_image.shape[:2]:
            # Create a color mask
            color_mask = np.full(open_cv_image.shape, mask_color, dtype=np.uint8)

            # Apply the color mask where the selection mask is
            display_image = np.where(self.selection_mask[:, :, None], color_mask, open_cv_image)
        else:
            display_image = open_cv_image  # Fallback to original if the mask is not correctly set

        # Convert back to PIL format and display
        self.display_image = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)))
        self.image_label.config(image=self.display_image)

    def save_state(self):
        if self.original_image:
            # Copy the image
            image_copy = self.original_image.copy()

            # Check if selection_mask exists and is not None before copying
            mask_copy = None
            if hasattr(self, 'selection_mask') and self.selection_mask is not None:
                mask_copy = self.selection_mask.copy()

            self.history.append((image_copy, mask_copy))
            self.future.clear()  # Clear future states on new action
 
    def undo(self):
        if self.history:
            self.future.append((self.original_image.copy(), self.selection_mask.copy() if hasattr(self, 'selection_mask') else None))
            self.original_image, self.selection_mask = self.history.pop()
            self.update_display()

    def redo(self):
        print("Future states available:", len(self.future))
        print("Contents of future:", self.future)

        if len(self.future) > 0:
            self.save_state()
            state = self.future.pop()
            if state:
                self.original_image, self.selection_mask = state
                if self.selection_mask is not None:
                    # Ensure the selection mask is correctly applied
                    self.apply_selection_mask()
                self.update_display()
        else:
            print("No actions to redo")
            
    def apply_selection_mask(self):
        if self.selection_mask is not None:
            # Logic to apply the selection mask to the image
            # This could involve blending the mask with the image, etc.
            pass
        # Update the display after applying the mask
        self.update_display()

    def update_display(self):
        # Update the image display
        self.display_image = ImageTk.PhotoImage(self.original_image)
        self.image_label.config(image=self.display_image)

        # Update the selection mask display
        if self.selection_mask is not None:
            self.show_selection()



    def crop_image(self):
        if self.original_image:
            # Example crop: top-left quarter of the image
            width, height = self.original_image.size
            cropped_image = self.original_image.crop((0, 0, width // 2, height // 2))

            self.display_image = ImageTk.PhotoImage(cropped_image)
            self.image_label.config(image=self.display_image)

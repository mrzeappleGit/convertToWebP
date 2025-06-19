from multiprocessing import Process, Queue, cpu_count
import multiprocessing
from multiprocessing.dummy import Pool
import re
import subprocess
import sys
import time
import os
import tkinter as tk
from tkinter import  filedialog
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import concurrent.futures
# import sv_ttk # No longer setting theme here
import time
import shutil
from sys import platform
import pillow_avif
import threading
import queue
import io


class ImageViewerWindow(tk.Toplevel):
    """
    A new window to display an image with zoom and pan capabilities.
    """
    def __init__(self, master, image_path):
        super().__init__(master)
        self.title("Image Preview")
        self.geometry("800x600")

        # Configure the grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create canvas
        self.canvas = tk.Canvas(self, bg="gray")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Load image
        self.original_image = Image.open(image_path)
        self.image = self.original_image.copy()
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.image_on_canvas = self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        
        # Center the image
        self.center_image()

        # Bind events
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.pan)
        self.bind("<Configure>", self.center_image) # Recenter on window resize

    def center_image(self, event=None):
        """Centers the image on the canvas."""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        self.canvas.coords(self.image_on_canvas, (canvas_width - self.image.width) / 2, (canvas_height - self.image.height) / 2)

    def zoom(self, event):
        """Zooms the image in or out based on the mouse wheel movement."""
        factor = 1.1 if event.delta > 0 else 0.9
        
        new_width = int(self.image.width * factor)
        new_height = int(self.image.height * factor)

        # Use the higher-quality resampling filter for resizing
        self.image = self.original_image.copy().resize((new_width, new_height), Image.LANCZOS)
        
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.itemconfig(self.image_on_canvas, image=self.tk_image)
        self.center_image() # Recenter after zoom

    def start_pan(self, event):
        """Records the starting position for panning."""
        self.canvas.scan_mark(event.x, event.y)
        self.canvas.config(cursor="fleur")

    def pan(self, event):
        """Moves the canvas based on mouse movement."""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        
class ImageConverterGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"

        # --- Grid Configuration ---
        self.grid_columnconfigure(2, weight=1) # Make the preview column expandable

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
        self.source_preview_path = None # Path of the original file selected for preview
        self.preview_photo_image = None # To prevent garbage collection
        
        # For live preview threading and debouncing
        self.preview_queue = queue.Queue()
        self.scheduled_preview_update = None

        folder_label = ttk.Label(self, text="Image/Folder:")
        folder_label.grid(column=0, row=0, padx=10, pady=10, sticky=tk.W)

        folder_entry = ttk.Entry(self, width=30, textvariable=self.folder_path)
        folder_entry.grid(column=1, row=0, padx=10, pady=10, sticky=tk.W)
        
        folder_button = ttk.Button(self, text="Select Folder", command=self.select_folder, cursor=cursor_point)
        folder_button.grid(column=0, row=1, padx=10, pady=10, sticky=tk.W)
        
        file_button = ttk.Button(self, text="Select File", command=self.select_file, cursor=cursor_point)
        file_button.grid(column=1, row=1, padx=10, pady=10, sticky=tk.W)
        
        destination_folder_label = ttk.Label(self, text="Destination Folder:")
        destination_folder_label.grid(column=0, row=2, padx=10, pady=10, sticky=tk.W)

        destination_folder_entry = ttk.Entry(self, width=30, textvariable=self.destination_folder_path)
        destination_folder_entry.grid(column=1, row=2, padx=10, pady=10, sticky=tk.W)
        
        destination_folder_button = ttk.Button(self, text="Select Folder", command=self.destination_select_folder, cursor=cursor_point)
        destination_folder_button.grid(column=0, row=3, padx=10, pady=10, sticky=tk.W)
        
        # --- Controls that trigger preview update ---
        separator1 = ttk.Separator(self, orient='horizontal')
        separator1.grid(row=4, column=0, columnspan=2, sticky='ew', pady=10)

        convert_checkbox = ttk.Checkbutton(self, text="Convert", variable=self.convert, cursor=cursor_point, command=self.request_preview_update)
        convert_checkbox.grid(column=0, row=5, padx=10, pady=10, sticky=tk.W)
        
        self.image_format = tk.StringVar()
        image_formats = ["WebP", "PNG", "JPEGLI", "AVIF"]
        self.format_dropdown = ttk.Combobox(self, textvariable=self.image_format, values=image_formats, state=tk.DISABLED, width=10)
        self.format_dropdown.set("WebP")
        self.format_dropdown.grid(column=1, row=5, padx=10, pady=10, sticky=tk.W)
        self.format_dropdown.bind("<<ComboboxSelected>>", self.request_preview_update)
        
        compress_checkbox = ttk.Checkbutton(self, text="Compress", variable=self.compress, command=self.request_preview_update, cursor=cursor_point)
        compress_checkbox.grid(column=0, row=6, padx=10, pady=10, sticky=tk.W)

        rename_checkbox = ttk.Checkbutton(self, text="Rename", variable=self.rename, cursor=cursor_point)
        rename_checkbox.grid(column=1, row=6, padx=10, pady=10, sticky=tk.W)

        separator2 = ttk.Separator(self, orient='horizontal')
        separator2.grid(row=7, column=0, columnspan=2, sticky='ew', pady=10)

        quality_label_text = ttk.Label(self, text="Quality:")
        quality_label_text.grid(column=0, row=8, padx=10, pady=10, sticky=tk.W)
        
        self.quality_slider = ttk.Scale(self, length=150, orient="horizontal", from_=0, to=100, variable=self.quality, command=self.request_preview_update, state=tk.DISABLED, cursor="arrow")
        self.quality_slider.grid(column=1, row=8, padx=10, pady=10, sticky=tk.W)

        self.quality_label = ttk.Label(self, text="{}%".format(self.quality.get()), state=tk.DISABLED, width=5)
        self.quality_label.grid(column=1, row=8, padx=(170,0), pady=10, sticky=tk.W)
        
        self.resize_checkbox = tk.BooleanVar()
        resize_checkbox = ttk.Checkbutton(self, text="Enable Resizing", variable=self.resize_checkbox, command=self.request_preview_update, cursor=cursor_point)
        resize_checkbox.grid(column=0, row=9, padx=10, pady=10, sticky=tk.W)
        
        self.resize_slider = ttk.Scale(self, length=150, from_=1, to=100, orient="horizontal", variable=self.new_width_percentage, command=self.request_preview_update, state=tk.DISABLED, cursor="arrow")
        self.resize_slider.grid(column=1, row=9, padx=10, pady=10, sticky=tk.W)

        self.resize_label = ttk.Label(self, text="{}%".format(self.new_width_percentage.get()), state=tk.DISABLED, width=5)
        self.resize_label.grid(column=1, row=9, padx=(170,0), pady=10, sticky=tk.W)
        
        separator3 = ttk.Separator(self, orient='horizontal')
        separator3.grid(row=10, column=0, columnspan=2, sticky='ew', pady=10)

        # --- End of preview-triggering controls ---
        
        # --- Bottom Controls ---
        run_button_frame = ttk.Frame(self)
        run_button_frame.grid(row=11, column=0, columnspan=2, pady=10, sticky='ew')
        run_button_frame.grid_columnconfigure(0, weight=1)

        convert_button = ttk.Button(run_button_frame, text="Run", command=self.convert_images, cursor=cursor_point)
        convert_button.pack(side=tk.LEFT, padx=10)

        self.time_label = tk.Label(run_button_frame, text="", font=("Helvetica", 12))
        self.time_label.pack(side=tk.RIGHT, padx=10)

        progress_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate", variable=self.progress, style="green.Horizontal.TProgressbar")
        progress_bar.grid(column=0, row=12, columnspan=2, padx=10, pady=10, sticky=tk.W+tk.E)

        # --- Image Preview (on the right) ---
        self.preview_label = ttk.Label(self, text="Select a single image to see a preview", relief="solid", borderwidth=1, anchor="center")
        self.preview_label.grid(row=0, column=2, rowspan=12, padx=20, pady=10, sticky="nsew") # Adjusted rowspan
        self.preview_label.bind("<Button-1>", self.open_image_viewer)
        self.preview_label.bind("<Enter>", lambda e: self.preview_label.config(cursor=cursor_point if self.source_preview_path else ""))
        self.preview_label.bind("<Leave>", lambda e: self.preview_label.config(cursor=""))
        
        # --- New Resolution Label ---
        self.resolution_label = ttk.Label(self, text="", anchor="center")
        self.resolution_label.grid(row=12, column=2, padx=20, pady=(0, 10), sticky="ew")

        
        self.new_width_percentage.trace('w', self.validate_resize_percentage)
        self.quality.trace('w', self.validate_quality_percentage)
        
        self.toggle_convert() # Set initial state
        self.toggle_compress()
        self.toggle_resize_slider()
        self.process_preview_queue() # Start the queue checker

    def request_preview_update(self, *args):
        """Debounces requests to update the preview."""
        if self.scheduled_preview_update:
            self.after_cancel(self.scheduled_preview_update)
        
        # Also trigger the dependent UI updates immediately
        self.toggle_convert()
        self.toggle_compress()
        self.toggle_resize_slider()
        
        self.scheduled_preview_update = self.after(400, self.start_preview_generation_thread)

    def start_preview_generation_thread(self):
        """Starts a background thread to generate the image preview."""
        if not self.source_preview_path:
            return

        self.preview_label.config(image='', text="Loading preview...")
        self.resolution_label.config(text="") # Clear old resolution
        
        # Gather settings for the thread
        settings = {
            "source_path": self.source_preview_path,
            "quality": self.quality.get() if self.compress.get() else 100,
            "width_percent": self.new_width_percentage.get() if self.resize_checkbox.get() else 100,
            "convert_format": self.image_format.get().lower() if self.convert.get() else None
        }
        
        threading.Thread(target=self._preview_worker, kwargs=settings, daemon=True).start()

    def _preview_worker(self, source_path, quality, width_percent, convert_format):
        """
        Runs in a background thread to process an image and put it in the queue.
        This function does NOT interact with the GUI directly.
        """
        try:
            with Image.open(source_path) as image:
                # --- Apply Resizing ---
                new_width = int(image.width * (width_percent / 100))
                new_height = int(image.height * (new_width / image.width))
                if image.width != new_width or image.height != new_height:
                    image = image.resize((new_width, new_height), Image.LANCZOS)

                # --- Determine Format and Handle Transparency ---
                output_format = 'JPEG' # Default
                img_extension = os.path.splitext(source_path)[1].lower()[1:]
                
                if convert_format:
                    if convert_format == 'webp': output_format = 'WEBP'
                    elif convert_format == 'png': output_format = 'PNG'
                    elif convert_format == 'avif': output_format = 'AVIF'
                    elif convert_format == 'jpegli': output_format = 'JPEG'
                else: # Use original format if not converting
                    if img_extension == 'png': output_format = 'PNG'
                    elif img_extension == 'webp': output_format = 'WEBP'
                    elif img_extension == 'avif': output_format = 'AVIF'

                if image.mode == 'RGBA' and output_format == 'JPEG':
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[3])
                    image = background

                # --- Save to In-Memory Buffer ---
                mem_file = io.BytesIO()
                save_params = {'format': output_format}
                if output_format in ['JPEG', 'WEBP', 'AVIF']:
                    save_params['quality'] = quality
                elif output_format == 'PNG':
                    save_params['compress_level'] = 6
                
                image.save(mem_file, **save_params)
                mem_file.seek(0)
                
                # Put the data and the dimensions in the queue
                self.preview_queue.put((mem_file, new_width, new_height))
        except Exception as e:
            # Put the error and None for dimensions
            self.preview_queue.put((f"Error: {e}", None, None))

    def process_preview_queue(self):
        """Checks the queue for a new preview image and updates the GUI."""
        try:
            result, width, height = self.preview_queue.get(block=False)
            
            if isinstance(result, io.BytesIO):
                image = Image.open(result)
                
                preview_width = self.preview_label.winfo_width()
                preview_height = self.preview_label.winfo_height()
                if preview_width > 1 and preview_height > 1:
                    image.thumbnail((preview_width - 10, preview_height - 10))

                self.preview_photo_image = ImageTk.PhotoImage(image)
                self.preview_label.config(image=self.preview_photo_image, text="")
                self.resolution_label.config(text=f"{width} x {height} pixels") # Update resolution
            elif isinstance(result, str): # It's an error message
                self.preview_label.config(image='', text=result)
                self.resolution_label.config(text="")
        
        except queue.Empty:
            pass # No new preview, do nothing
        
        finally:
            self.after(100, self.process_preview_queue) # Keep checking

    def select_file(self):
        file_selected = filedialog.askopenfilename(
            title="Select an image file",
            filetypes=(("jpeg, png, webp, avif files", "*.jpg *.png *.webp *.jpeg *.avif"), ("all files", "*.*"))
        )
        if file_selected:
            self.folder_path.set(file_selected)
            self.source_preview_path = file_selected
            self.request_preview_update()

    def select_folder(self):
        file_or_folder_selected = filedialog.askdirectory(
            title="Select folder where the images are",
        )
        if file_or_folder_selected:
            self.folder_path.set(file_or_folder_selected)
            self.clear_preview()

    def clear_preview(self):
        """Clears the image preview area."""
        if self.scheduled_preview_update:
            self.after_cancel(self.scheduled_preview_update)
        self.preview_label.config(image='', text="Select a single image to see a preview")
        self.resolution_label.config(text="") # Clear resolution text
        self.preview_photo_image = None
        self.source_preview_path = None
    
    def open_image_viewer(self, event=None):
        """Opens the new image viewer window if a source preview image exists."""
        if self.source_preview_path:
            try:
                ImageViewerWindow(self.master, self.source_preview_path)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open image preview:\n{e}")
        else:
            messagebox.showinfo("Info", "Select a single image file to see a preview.")

    def update_resize_label(self, value):
        try: # Added try/except for when widget is destroyed
            self.resize_label.configure(text="{}%".format(round(float(value))))
        except tk.TclError:
            pass
        
    def toggle_resize_slider(self):
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        is_enabled = self.resize_checkbox.get()
        new_state = tk.NORMAL if is_enabled else tk.DISABLED
        cursor = cursor_point if is_enabled else "arrow"
        
        self.resize_label.config(state=new_state)
        self.resize_slider.config(state=new_state, cursor=cursor)

    def toggle_compress(self):
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        is_enabled = self.compress.get()
        new_state = tk.NORMAL if is_enabled else tk.DISABLED
        cursor = cursor_point if is_enabled else "arrow"
        
        self.quality_label.config(state=new_state)
        self.quality_slider.config(state=new_state, cursor=cursor)
            
    def toggle_convert(self):
        new_state = tk.NORMAL if self.convert.get() else tk.DISABLED
        self.format_dropdown.config(state=new_state)
            
    def validate_quality_percentage(self, *args):
        try:
            value_str = self.quality.get()
            value = round(float(value_str)) if value_str else 0
            if value < 1: self.quality.set(1)
            elif value > 100: self.quality.set(100)
            else: self.quality.set(value)
        except (ValueError, tk.TclError):
            self.quality.set(0)
        self.quality_label.configure(text="{}%".format(self.quality.get()))
        self.request_preview_update()
        
    def validate_resize_percentage(self, *args):
        try:
            value_str = self.new_width_percentage.get()
            value = round(float(value_str)) if value_str else 0
            if value < 1: self.new_width_percentage.set(1)
            elif value > 100: self.new_width_percentage.set(100)
            else: self.new_width_percentage.set(value)
        except (ValueError, tk.TclError):
            self.new_width_percentage.set(0)
        self.update_resize_label(self.new_width_percentage.get())
        self.request_preview_update()
        
    def destination_select_folder(self):
        destination_folder_selected = filedialog.askdirectory(title="Select folder where the images will go")
        self.destination_folder_path.set(destination_folder_selected)

    @staticmethod
    def format_time(seconds):
        if seconds >= 60:
            minutes = round(seconds / 60)
            return f"{minutes} minute(s)"
        else:
            return f"{round(seconds, 2)} seconds"
        
    @staticmethod
    def adjust_ppi(image, desired_ppi):
        dpi = image.info.get('dpi', (72, 72))
        if dpi[0] > desired_ppi:
            image = image.copy()
            image.info['dpi'] = (desired_ppi, desired_ppi)
        return image

    def convert_images(self):
        # This function remains largely the same, using multiprocessing for the final "Run"
        if not self.folder_path.get() or not self.destination_folder_path.get():
            tk.messagebox.showerror("Error", "Please select the source and destination folders.")
            return
        self.start_time = time.time()
        path = self.folder_path.get()
        destination_folder_path = self.destination_folder_path.get()
        
        files = []
        if os.path.isdir(path):
            for root, dirs, filenames in os.walk(path):
                for filename in filenames:
                    if re.search(".(jpg|jpeg|png|bmp|tiff|webp|avif)$", filename, re.IGNORECASE):
                        files.append(os.path.join(root, filename))
        elif os.path.isfile(path):
            files.append(path)
        else:
            tk.messagebox.showerror("Error", "Invalid path.")
            return

        if not files:
            tk.messagebox.showerror("Error", "No image files found in the selected folder.")
            return

        if not destination_folder_path:
            self.destination_folder_path.set(path)
            self.overide_images.set(True)
        else:
            self.overide_images.set(False)
            
        total_files = len(files)
        processed_files = 0

        with Pool(processes=cpu_count()) as pool:
            results = []
            for file in files:
                args = {
                    "file_path": file, 
                    "rename": self.rename.get(), 
                    "quality": self.quality.get() if self.compress.get() else 100, 
                    "overide_image": self.overide_images.get(),
                    "folder_path": self.folder_path.get(), 
                    "destination_folder_path": self.destination_folder_path.get(), 
                    "new_width_percentage": self.new_width_percentage.get() if self.resize_checkbox.get() else 100,
                    "single_file_selected": os.path.isfile(path)
                }
                
                if self.convert.get():
                    if self.image_format.get() == "WebP": args["extension"] = "webp"
                    elif self.image_format.get() == "JPEGLI": args["extension"] = "jpeg"
                    elif self.image_format.get() == "AVIF": args["extension"] = "avif"
                    elif self.image_format.get() == "PNG": args["extension"] = "png"
                else:
                    args["extension"] = os.path.splitext(file)[1][1:].lower()

                results.append(pool.apply_async(ImageConverterGUI.convert_file, kwds=args))

            for result in results:
                result.get()
                processed_files += 1
                self.progress.set(processed_files / total_files * 100)
                self.update()
        
        self.end_time = time.time()
        time_taken = self.end_time - self.start_time
        self.time_label.config(text="Time taken: {}".format(ImageConverterGUI.format_time(time_taken)))

    @staticmethod
    def convert_file(file_path, rename, quality, overide_image, extension, folder_path, destination_folder_path, new_width_percentage, single_file_selected):
        try:
            with Image.open(file_path) as image:
                width_percent = new_width_percentage / 100
                new_width = int(image.width * width_percent)
                new_height = int(image.height * (new_width / image.width))
                
                image = image.resize((new_width, new_height), Image.LANCZOS)
                image = ImageConverterGUI.adjust_ppi(image, 72)

                if image.mode == 'RGBA' and extension in ['jpeg', 'jpg']:
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[3])
                    image = background

                if single_file_selected:
                    new_file_path = os.path.join(destination_folder_path, os.path.basename(file_path))
                else:
                    relative_path = os.path.relpath(file_path, folder_path)
                    new_file_path = os.path.join(destination_folder_path, relative_path)
                
                new_file_name = os.path.splitext(os.path.basename(new_file_path))[0]
                if rename:
                    new_file_name = re.sub(r'[^\w\s-]', '', new_file_name).lower().replace(' ', '-')
                    new_file_name = re.sub(r'[-_]+', '-', new_file_name)
                    new_file_name = re.sub(r'^-|-$', '', new_file_name)
                
                new_file_path = os.path.join(os.path.dirname(new_file_path), new_file_name + '.' + extension)
                os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

                save_params = {}
                if extension == "jpeg":
                    save_params = {"format": "JPEG", "quality": quality}
                elif extension == "png":
                    save_params = {"format": "PNG", "compress_level": 6}
                elif extension == "avif":
                    save_params = {"format": "AVIF", "quality": quality}
                elif extension == "webp":
                    save_params = {"format": "WEBP", "quality": quality}
                
                if save_params:
                    image.save(new_file_path, **save_params)
            
            if overide_image and new_file_path != file_path:
                os.remove(file_path)

            return new_file_path
        except Exception as e:
            print(f"Failed to convert {file_path}: {e}")
            return None
        
        
    processes = []
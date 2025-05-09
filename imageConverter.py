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
from tkinter import ttk
from PIL import Image
import concurrent.futures
# import sv_ttk # No longer setting theme here
import time
import shutil
from sys import platform
import pillow_avif


class ImageConverterGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        
        # self.style = ttk.Style(self) # Remove: Style is managed globally
        # self.style.configure("TFrame", background="#1c1c1c") # Remove: Theme handles frame background

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
        
        
        # sv_ttk.set_theme("dark") # Remove: Theme is managed globally
        

        folder_label = ttk.Label(self, text="Image/Folder:")
        folder_label.grid(column=0, row=0, padx=20, pady=20, sticky=tk.W)

        folder_entry = ttk.Entry(self, width=30, textvariable=self.folder_path)
        folder_entry.grid(column=1, row=0, padx=20, pady=20, sticky=tk.W)
        
        folder_button = ttk.Button(self, text="Select Folder", command=self.select_folder, cursor=cursor_point)
        folder_button.grid(column=2, row=0, padx=20, pady=20, sticky=tk.W)
        
        file_button = ttk.Button(self, text="Select File", command=self.select_file, cursor=cursor_point)
        file_button.grid(column=3, row=0, padx=20, pady=20, sticky=tk.W)
        
        destination_folder_label = ttk.Label(self, text="Destination Folder:")
        destination_folder_label.grid(column=0, row=1, padx=20, pady=20, sticky=tk.W)

        destination_folder_entry = ttk.Entry(self, width=30, textvariable=self.destination_folder_path)
        destination_folder_entry.grid(column=1, row=1, padx=20, pady=20, sticky=tk.W)
        
        destination_folder_button = ttk.Button(self, text="Select Folder", command=self.destination_select_folder, cursor=cursor_point)
        destination_folder_button.grid(column=2, row=1, padx=20, pady=20, sticky=tk.W)
        
        convert_checkbox = ttk.Checkbutton(self, text="Convert", variable=self.convert, cursor=cursor_point, command=self.toggle_convert)
        convert_checkbox.grid(column=0, row=2, padx=20, pady=20, sticky=tk.W)
        
        self.image_format = tk.StringVar()
        image_formats = ["WebP", "PNG", "JPEGLI", "AVIF"]
        self.format_dropdown = ttk.Combobox(self, textvariable=self.image_format, values=image_formats, state=tk.DISABLED)
        self.format_dropdown.set("WebP")
        self.format_dropdown.grid(column=1, row=2, padx=20, pady=20, sticky=tk.W)
        
        rename_checkbox = ttk.Checkbutton(self, text="Rename", variable=self.rename, cursor=cursor_point)
        rename_checkbox.grid(column=1, row=3, padx=20, pady=20, sticky=tk.W)
        
        compress_checkbox = ttk.Checkbutton(self, text="Compress", variable=self.compress, command=self.toggle_compress, cursor=cursor_point)
        compress_checkbox.grid(column=0, row=3, padx=20, pady=20, sticky=tk.W)

        quality_label_text = ttk.Label(self, text="Quality:")
        quality_label_text.grid(column=0, row=4, padx=20, pady=20, sticky=tk.W)
        
        self.quality = tk.IntVar(value=100)

        self.quality_slider = ttk.Scale(self, length=250, orient="horizontal", from_=0, to=100, variable=self.quality, command=self.update_quality_label, state=tk.DISABLED, cursor="arrow")
        self.quality_slider.grid(column=1, row=4, padx=20, pady=20, sticky=tk.W)

        self.quality_label = ttk.Label(self, text="Quality: {}%".format(self.quality.get()), state=tk.DISABLED)
        self.quality_label.grid(column=3, row=4, padx=20, pady=20, sticky=tk.W)
        
        
        self.quality_entry = ttk.Entry(self, textvariable=self.quality, width=5, state=tk.DISABLED, cursor="arrow")
        self.quality_entry.grid(column=2, row=4, padx=20, pady=20, sticky=tk.W)
        
        self.resize_checkbox = tk.BooleanVar()
        resize_checkbox = ttk.Checkbutton(self, text="Enable Resizing", variable=self.resize_checkbox, command=self.toggle_resize_slider, cursor=cursor_point)
        resize_checkbox.grid(column=0, padx=20, pady=20, row=5, sticky=tk.W)
        
        resize_label = ttk.Label(self, text="Resize Width (%):")
        resize_label.grid(column=0, row=6, padx=20, pady=20, sticky=tk.W)

        self.new_width_percentage = tk.IntVar(value=100)  # Default value of 100

        self.resize_slider = ttk.Scale(self, length=250, from_=1, to=100, orient="horizontal", variable=self.new_width_percentage, command=self.update_resize_label, state=tk.DISABLED, cursor="arrow")
        self.resize_slider.grid(column=1, row=6, padx=20, pady=20, sticky=tk.W)
        
        
        self.resize_entry = ttk.Entry(self, textvariable=self.new_width_percentage, width=5, state=tk.DISABLED, cursor="arrow")
        self.resize_entry.grid(column=2, row=6, padx=20, pady=20, sticky=tk.W)

        self.resize_label = ttk.Label(self, text="Resize: {}%".format(self.new_width_percentage.get()), state=tk.DISABLED)
        self.resize_label.grid(column=3, row=6, padx=20, pady=20, sticky=tk.W)

        convert_button = ttk.Button(self, text="Run", command=self.convert_images, cursor=cursor_point)
        convert_button.grid(column=0, row=7, padx=20, pady=20, sticky=tk.W)

        progress_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate", variable=self.progress, style="green.Horizontal.TProgressbar")
        progress_bar.grid(column=0, row=8, columnspan=4, padx=20, pady=20, sticky=tk.W+tk.E)
        
        self.time_label = tk.Label(self, text="", font=("Helvetica", 12))
        self.time_label.grid(column=1, row=7, padx=20, pady=20, sticky=tk.W)
        
        # Get the required width and height of the window based on its content
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        self.new_width_percentage.trace('w', self.validate_resize_percentage)
        self.quality.trace('w', self.validate_quality_percentage)
    
    def resource_path(relative_path):
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
            
        return os.path.join(base_path, relative_path)
    
    def update_resize_label(self, value):
        self.resize_label.configure(text="Resize: {}%".format(round(float(value))))
        
    def toggle_resize_slider(self):
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        if self.resize_checkbox.get():
            self.resize_label.config(state=tk.NORMAL)
            self.resize_slider.config(state=tk.NORMAL)
            self.resize_entry.config(state=tk.NORMAL)
            self.resize_slider.config(cursor=cursor_point)
            self.resize_entry.config(cursor="xterm")
        else:
            self.resize_label.config(state=tk.DISABLED)
            self.resize_slider.config(state=tk.DISABLED)
            self.resize_entry.config(state=tk.DISABLED)
            self.resize_slider.config(cursor="arrow")
            self.resize_entry.config(cursor="arrow")


    def toggle_compress(self):
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        if not self.compress.get():
            self.quality_label.config(state=tk.DISABLED)
            self.quality_slider.config(state=tk.DISABLED)
            self.quality_entry.config(state=tk.DISABLED)
            self.quality_slider.config(cursor="arrow")
            self.quality_entry.config(cursor="arrow")
        else:
            self.quality_label.config(state=tk.NORMAL)
            self.quality_slider.config(state=tk.NORMAL)
            self.quality_entry.config(state=tk.NORMAL)
            self.quality_slider.config(cursor=cursor_point)
            self.quality_entry.config(cursor="xterm")
            
    def toggle_convert(self):
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        if not self.convert.get():
            self.format_dropdown.config(state=tk.DISABLED)
        else:
            self.format_dropdown.config(state=tk.NORMAL)
            
    def validate_quality_percentage(self, *args):
        try:
            value_str = self.quality.get()
            
            # Check if the string is empty first
            if not value_str:
                value = 0
            else:
                value = round(float(value_str))
                
            if value < 1:
                self.quality.set(1)
            elif value > 100:
                self.quality.set(100)
            else:
                self.quality.set(value)
        except ValueError:
            # The string is not a number, set to 0
            self.quality.set(0)
        self.quality_label.configure(text="Quality: {}%".format(self.quality.get()))

        
    def validate_resize_percentage(self, *args):
        try:
            value_str = self.new_width_percentage.get()
            
            # Check if the string is empty first
            if not value_str:
                value = 0
            else:
                value = round(float(value_str))
                
            if value < 1:
                self.new_width_percentage.set(1)
            elif value > 100:
                self.new_width_percentage.set(100)
            else:
                self.new_width_percentage.set(value)
        except ValueError:
            # The string is not a number, set to 0
            self.new_width_percentage.set(0)
        self.resize_label.configure(text="Resize: {}%".format(self.new_width_percentage.get()))
        
    def select_file(self):
        file_selected = filedialog.askopenfilename(
            title="Select an image file",
            filetypes=(("jpeg, png, webp, avif files", "*.jpg *.png *.webp *.jpeg *.avif"), ("all files", "*.*"))
        )
        self.folder_path.set(file_selected)


    def select_folder(self):
        file_or_folder_selected = filedialog.askdirectory(
            title="Select folder where the images are",
        )
        self.folder_path.set(file_or_folder_selected)
    
    def destination_select_folder(self):
        destination_folder_selected = filedialog.askdirectory(
            title="Select folder where the images will go",
        )
        self.destination_folder_path.set(destination_folder_selected)

    def update_quality_label(self, value):
        self.quality_label.configure(text="Quality: {}%".format(round(float(value))))
        
    def format_time(seconds):
        if seconds >= 30:
            minutes = round(seconds / 60)
            return f"{minutes} minutes"
        else:
            seconds = round(seconds, 2)
            return f"{seconds} seconds"
        
    def adjust_ppi(image, desired_ppi):
        """Adjust the PPI (pixels per inch) of the image to the desired value."""
        # Get current dpi
        dpi = image.info.get('dpi', (72, 72))
        if dpi[0] > desired_ppi:
            # Change the DPI without changing pixel data
            image = image.copy()
            image.info['dpi'] = (desired_ppi, desired_ppi)
        return image


    def convert_images(self):
        if not self.folder_path.get() or not self.destination_folder_path.get():
            tk.messagebox.showerror("Error", "Please select the source and destination folders.")
            return
        self.start_time = time.time()
        path = self.folder_path.get()
        destination_folder_path = self.destination_folder_path.get()
        if self.compress.get() == True:
            quality = self.quality.get()
        else:
            quality = 100
        files = []
        single_file_selected = False
        if os.path.isdir(path):
            for root, dirs, filenames in os.walk(path):
                for filename in filenames:
                    if re.search(".(jpg|jpeg|png|bmp|tiff|webp|avif)$", filename, re.IGNORECASE):
                        files.append(os.path.join(root, filename))
        elif os.path.isfile(path):
            files.append(path)
            single_file_selected = True
        else:
            tk.messagebox.showerror("Error", "Invalid path.")
            return

        if not files:
            tk.messagebox.showerror("Error", "No image files found in the selected folder.")
            return
        if destination_folder_path == "":
            self.destination_folder_path.set(path)
            destination_folder_path = self.destination_folder_path.get()
            self.overide_images.set(True)
        else:
            self.overide_images.set(False)
        total_files = len(files)
        processed_files = 0

        with Pool(processes=cpu_count()) as pool:
            results = []
            for file in files:
                relative_path = os.path.relpath(os.path.dirname(file), self.folder_path.get())
                destination_path = os.path.join(self.destination_folder_path.get(), relative_path)
                destination_input_path = os.path.join(destination_path, self.fileOut.get())
                convert = self.convert.get()
                extension = os.path.splitext(file)[1][1:].lower()
                if convert == True:
                    if self.image_format.get() == "WebP":
                        extensionConvert = "webp"
                    elif self.image_format.get() == "JPEGLI":
                        extensionConvert = "jpeg"
                    elif self.image_format.get() == "AVIF":
                        extensionConvert = "avif"
                    elif self.image_format.get() == "PNG":
                        extensionConvert = "png"
                    output_path = os.path.splitext(destination_input_path)[0] + extensionConvert
                    self.extension.set(extensionConvert)
                else:
                    self.extension.set(extension)
                    output_path = os.path.splitext(destination_input_path)[0] + os.path.splitext(file)[1]
                overide_image = self.overide_images.get()
                convert = self.convert.get()
                extension = self.extension.get()
                if self.resize_checkbox.get():
                    results.append(pool.apply_async(ImageConverterGUI.convert_file, args=(file, self.rename.get(), quality, overide_image, extension, self.folder_path.get(), self.destination_folder_path.get(), self.new_width_percentage.get(), single_file_selected, convert)))
                else:
                    results.append(pool.apply_async(ImageConverterGUI.convert_file, args=(file, self.rename.get(), quality, overide_image, extension, self.folder_path.get(), self.destination_folder_path.get(), 100, single_file_selected, convert)))

            for result in results:
                result.get()
                processed_files += 1
                self.progress.set(processed_files / total_files * 100)
                self.update()
        self.end_time = time.time()
        time_taken = self.end_time - self.start_time
        formatted_time = ImageConverterGUI.format_time(time_taken)
        self.time_label.config(text="Time taken: {}".format(formatted_time))
        


    @staticmethod
    def convert_file(file_path, rename, quality, overide_image, extension, folder_path, destination_folder_path, new_width_percentage, single_file_selected, convert):
        with Image.open(file_path) as image:
            # Calculate new dimensions maintaining aspect ratio
            width_percent = new_width_percentage / 100
            new_width = int(image.width * width_percent)
            new_height = int(image.height * (new_width / image.width))
            
            image = image.resize((new_width, new_height), Image.LANCZOS)
            image = ImageConverterGUI.adjust_ppi(image, 72)

            # Check if image mode is RGBA (has an alpha channel)
            if image.mode == 'RGBA' and extension in ['jpeg', 'jpg']:
                # Create a new image with a white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])  # 3 is the index of the alpha channel in an RGBA image
                image = background  # Replace the original image with the new one without alpha

            # Determine the base new_file_path
            if single_file_selected:
                new_file_path = os.path.join(destination_folder_path, os.path.basename(file_path))
            else:
                relative_path = os.path.relpath(file_path, folder_path)
                new_file_path = os.path.join(destination_folder_path, relative_path)
            
            # Modify file name if renaming is enabled
            new_file_name = os.path.splitext(os.path.basename(new_file_path))[0]
            if rename:
                new_file_name = re.sub(r'[^\w\s-]', '', new_file_name)  # Remove special characters
                new_file_name = new_file_name.lower()  # Convert to lowercase
                new_file_name = new_file_name.replace(' ', '-')  # Replace spaces with hyphens
                new_file_name = re.sub(r'[-_]+', '-', new_file_name)  # Remove underscores and multiple hyphens
                new_file_name = re.sub(r'^-|-$', '', new_file_name)  # Remove leading and trailing hyphens
            
            # Determine the final new_file_path based on the desired extension
            new_file_path = os.path.join(os.path.dirname(new_file_path), new_file_name + '.' + extension)
            os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

            # Save image in the appropriate format
            if extension == "jpeg":
                image.save(new_file_path, "JPEG", quality=quality)
            elif extension == "png":
                image.save(new_file_path, "PNG", compress_level=6)  # Adjust compress_level as needed
            elif extension == "avif":
                image.save(new_file_path, "AVIF", quality=quality)
            elif extension == "webp":
                image.save(new_file_path, "WEBP", quality=quality)

            # Additional logic if using external conversion tools for JPEGLI
            if extension == "jpeg" and convert == True:
                cjpegli_path = ImageConverterGUI.resource_path("cjpegli.exe")
                cmd = [cjpegli_path, new_file_path, new_file_path]
            
                # Define a constant for hiding the console window
                CREATE_NO_WINDOW = 0x08000000

                # Start subprocess depending on the platform
                if sys.platform == "win32":
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, creationflags=CREATE_NO_WINDOW)
                else:
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                    
        # Remove the original file if override is enabled
        if overide_image:
            os.remove(file_path)

            
    processes = []
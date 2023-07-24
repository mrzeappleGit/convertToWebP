from multiprocessing import Process, Queue, cpu_count
import multiprocessing
from multiprocessing.dummy import Pool
import time
import os
import tkinter as tk
import customtkinter
from tkinter import filedialog
from tkinter import ttk
from PIL import Image
import concurrent.futures

class ImageConverterGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Image Converter")
        self.geometry("400x150")
        self.resizable(False, False)

        self.folder_path = tk.StringVar()
        self.quality = tk.IntVar(value=80)
        self.progress = tk.DoubleVar(value=0)

        folder_label = ttk.Label(self, text="Folder:")
        folder_label.grid(column=0, row=0, padx=5, pady=5, sticky=tk.W)

        folder_entry = ttk.Entry(self, width=30, textvariable=self.folder_path)
        folder_entry.grid(column=1, row=0, padx=5, pady=5, sticky=tk.W)

        folder_button = ttk.Button(self, text="Select Folder", command=self.select_folder)
        folder_button.grid(column=2, row=0, padx=5, pady=5, sticky=tk.W)

        quality_label = ttk.Label(self, text="Quality:")
        quality_label.grid(column=0, row=1, padx=5, pady=5, sticky=tk.W)

        quality_slider = ttk.Scale(self, orient="horizontal", from_=0, to=100, variable=self.quality, command=self.update_quality_label)
        quality_slider.grid(column=1, row=1, padx=5, pady=5, sticky=tk.W)

        self.quality_label = ttk.Label(self, text="Quality: {}%".format(self.quality.get()))
        self.quality_label.grid(column=2, row=1, padx=5, pady=5, sticky=tk.W)

        convert_button = ttk.Button(self, text="Convert", command=self.convert_images)
        convert_button.grid(column=1, row=2, padx=5, pady=5, sticky=tk.W)

        progress_bar = ttk.Progressbar(self, orient="horizontal", mode="determinate", variable=self.progress)
        progress_bar.grid(column=0, row=3, columnspan=3, padx=5, pady=5, sticky=tk.W+tk.E)

    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        self.folder_path.set(folder_selected)

    def update_quality_label(self, value):
        self.quality_label.configure(text="Quality: {}%".format(round(float(value))))

    def convert_images(self):
        folder_path = self.folder_path.get()
        quality = self.quality.get()        
        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        total_files = len(files)
        processed_files = 0

        with Pool(processes=cpu_count()) as pool:
            results = []
            for file in files:
                input_path = os.path.join(folder_path, file)
                output_path = os.path.splitext(input_path)[0] + ".webp"
                results.append(pool.apply_async(ImageConverterGUI.convert_file, args=(input_path, output_path, quality)))

            for result in results:
                result.get()
                processed_files += 1
                self.progress.set(processed_files / total_files * 100)
                self.update()


    @staticmethod
    def convert_file(file_path, output_path, quality):
        with Image.open(file_path) as image:
            image.save(output_path, "webp", quality=quality, method=6)
        os.remove(file_path)
    processes = []

    def convert_image(self, file):
        input_path = os.path.join(self.folder_path, file)
        output_path = os.path.splitext(input_path)[0] + ".webp"

        with Image.open(input_path) as image:
            image.save(output_path, "webp", quality=self.quality, method=6)
            
if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = ImageConverterGUI()
    app.mainloop()
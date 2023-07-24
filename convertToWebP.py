from multiprocessing import Process, Queue, cpu_count
import multiprocessing
from multiprocessing.dummy import Pool
import re
import sys
import time
import os
import tkinter as tk
from tkinter import  filedialog
from tkinter import ttk
from PIL import Image
import concurrent.futures
import sv_ttk
import time
import shutil
from sys import platform
from imageConverter import ImageConverterGUI
from fileRenamer import FileRenamerGUI

class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.style = ttk.Style(self)
        self.style.configure("TFrame", background="#1c1c1c")
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"

        self.title("Image Converter and File Renamer")

        def resource_path(relative_path):
            try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
                
            return os.path.join(base_path, relative_path)
        
        iconPath = resource_path('convertToWebPIcon.ico')
        self.iconbitmap(iconPath)
        self.resizable(True, True)
        sv_ttk.set_theme("dark")
        
        self.button_frame = tk.Frame(self)
        self.button_frame.pack(side="top", fill="x")

        self.image_converter_button = ttk.Button(self.button_frame, text="Converter", command=self.show_image_converter, cursor="arrow", state="disabled")
        self.image_converter_button.pack(side="left", ipadx=10, ipady=10, padx=5, pady=5)

        self.file_renamer_button = ttk.Button(self.button_frame, text="File Renamer", command=self.show_file_renamer, cursor=cursor_point)
        self.file_renamer_button.pack(side="left", ipadx=10, ipady=10, padx=5, pady=5)

        self.image_converter = ImageConverterGUI(self)
        self.image_converter.pack(side="left", fill="both", expand=True)
        self.file_renamer = FileRenamerGUI(self)
        self.file_renamer.pack(side="right", fill="both", expand=True)

        # Hide the file renamer at startup
        self.file_renamer.pack_forget()

        self.geometry('800x600')

    def show_image_converter(self):
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        # Fade out
        for i in range(10, -1, -1):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)

        self.file_renamer.pack_forget()
        self.image_converter.pack(side="left", fill="both", expand=True)

        self.image_converter_button.config(state='disabled', cursor="arrow")
        self.file_renamer_button.config(state='normal', cursor=cursor_point)

        # Fade in
        for i in range(0, 11):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)

    def show_file_renamer(self):
        cursor=cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        # Fade out
        for i in range(10, -1, -1):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)

        self.image_converter.pack_forget()
        self.file_renamer.pack(side="right", fill="both", expand=True)

        self.file_renamer_button.config(state='disabled', cursor="arrow")
        self.image_converter_button.config(state='normal', cursor=cursor_point)

        # Fade in
        for i in range(0, 11):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = MainApp()
    app.mainloop()
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

class FileRenamerGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        
        self.folder_path = tk.StringVar()
        self.single_file_path = tk.StringVar()  # To store the path of the single selected file
        sv_ttk.set_theme("dark")
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"

        folder_label = ttk.Label(self, text="Location Folder:")
        folder_label.grid(column=0, row=0, padx=20, pady=20, sticky=tk.W)

        folder_entry = ttk.Entry(self, width=30, textvariable=self.folder_path)
        folder_entry.grid(column=1, row=0, padx=20, pady=20, sticky=tk.W)
        
        folder_button = ttk.Button(self, text="Select Folder", command=self.select_folder, cursor=cursor_point)
        folder_button.grid(column=2, row=0, padx=20, pady=20, sticky=tk.W)
        
        file_label = ttk.Label(self, text="Single File:")
        file_label.grid(column=0, row=1, padx=20, pady=20, sticky=tk.W)
        
        file_entry = ttk.Entry(self, width=30, textvariable=self.single_file_path)
        file_entry.grid(column=1, row=1, padx=20, pady=20, sticky=tk.W)

        file_button = ttk.Button(self, text="Select File", command=self.select_file, cursor=cursor_point)
        file_button.grid(column=2, row=1, padx=20, pady=20, sticky=tk.W)

        rename_button = ttk.Button(self, text="Rename Files", command=self.rename_files, cursor=cursor_point)
        rename_button.grid(column=0, row=2, padx=20, pady=20, sticky=tk.W)

    def select_folder(self):
        folder_selected = filedialog.askdirectory(
            title="Select folder where the files are",
        )
        self.folder_path.set(folder_selected)

    def select_file(self):
        file_selected = filedialog.askopenfilename(
            title="Select a file",
        )
        self.single_file_path.set(file_selected)

    def rename_files(self):
        folder_path = self.folder_path.get()
        single_file_path = self.single_file_path.get()

        # Check if either a folder or a single file is selected
        if not folder_path and not single_file_path:
            tk.messagebox.showerror("Error", "Please select a source folder or a file.")
            return

        files = []
        if folder_path:
            for root, dirs, filenames in os.walk(folder_path):
                for filename in filenames:
                    files.append(os.path.join(root, filename))

        if single_file_path:
            files.append(single_file_path)

        if not files:
            tk.messagebox.showerror("Error", "No files found in the selected folder or file.")
            return

        for file in files:
            old_file_path = file
            new_file_name = os.path.splitext(os.path.basename(old_file_path))[0]
            new_file_name = re.sub(r'[^\w\s-]', '', new_file_name)  # Remove special characters
            new_file_name = new_file_name.lower()  # Convert to lowercase
            new_file_name = new_file_name.replace(' ', '-')  # Replace spaces with hyphens
            new_file_name = re.sub(r'[-_]+', '-', new_file_name)  # Remove underscores and multiple hyphens
            new_file_name = re.sub(r'^-|-$', '', new_file_name)  # Remove leading and trailing hyphens
            new_file_path = os.path.join(os.path.dirname(old_file_path), new_file_name + os.path.splitext(old_file_path)[1])
            os.rename(old_file_path, new_file_path)
        tk.messagebox.showinfo("Success", "All files have been renamed.")

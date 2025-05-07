import time
import tkinter as tk
from tkinter import ttk, filedialog
import os
import subprocess
import sys
from sys import platform
import threading



class VideoConverterGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        
        # self.style = ttk.Style(self) # Remove: Style is managed globally
        # self.style.configure("TFrame", background="#1c1c1c") # Remove: Theme handles frame background

        self.folder_path = tk.StringVar()
        self.destination_folder_path = tk.StringVar()
        
        folder_label = ttk.Label(self, text="Video File:")
        folder_label.grid(column=0, row=0, padx=20, pady=20, sticky=tk.W)

        folder_entry = ttk.Entry(self, width=30, textvariable=self.folder_path)
        folder_entry.grid(column=1, row=0, padx=20, pady=20, sticky=tk.W)
        
        file_button = ttk.Button(self, text="Select File", command=self.select_file, cursor=cursor_point)
        file_button.grid(column=2, row=0, padx=20, pady=20, sticky=tk.W)

        destination_folder_label = ttk.Label(self, text="Destination Folder:")
        destination_folder_label.grid(column=0, row=1, padx=20, pady=20, sticky=tk.W)

        destination_folder_entry = ttk.Entry(self, width=30, textvariable=self.destination_folder_path)
        destination_folder_entry.grid(column=1, row=1, padx=20, pady=20, sticky=tk.W)
        
        destination_folder_button = ttk.Button(self, text="Select Folder", command=self.destination_select_folder, cursor=cursor_point)
        destination_folder_button.grid(column=2, row=1, padx=20, pady=20, sticky=tk.W)
        
        video_format_label = ttk.Label(self, text="Output Format:")
        video_format_label.grid(column=0, row=2, padx=20, pady=20, sticky=tk.W)
        
        self.video_format = tk.StringVar()
        video_formats = ["webm", "mp4"]
        self.format_dropdown = ttk.Combobox(self, textvariable=self.video_format, values=video_formats)
        self.format_dropdown.set("webm")
        self.format_dropdown.grid(column=1, row=2, padx=20, pady=20, sticky=tk.W)

        convert_button = ttk.Button(self, text="Convert", command=self.convert_video, cursor=cursor_point)
        convert_button.grid(column=2, row=3, padx=20, pady=20, sticky=tk.W)
        self.video_progress = ttk.Progressbar(self, orient="horizontal", mode="determinate", value=0)
        self.video_progress.grid(column=0, row=4, columnspan=4, padx=20, pady=20, sticky=tk.W+tk.E)
        self.estimated_time_label = ttk.Label(self, text="Estimated Time Remaining: --:--", font=("Helvetica", 10))
        self.estimated_time_label.grid(column=1, row=5, padx=20, pady=5, sticky=tk.W)
    # Helper function to get resources when bundled with PyInstaller
    def resource_path(relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)



    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Select an video file",
            filetypes=(("WebM, MP4, MOV", "*.webm *.mp4 *.mov"), ("all files", "*.*"))
        )
        if file_path:
            self.folder_path.set(file_path)

    def destination_select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.destination_folder_path.set(folder_path)
            
    def convert_video(self):
        # Create a new thread to run the conversion
        threading.Thread(target=self.start_conversion).start()
        
    def update_gui(self, progress, estimated_time_left):
        """Update the GUI with the provided progress and estimated_time_left."""
        self.video_progress["value"] = progress
        mins, secs = divmod(estimated_time_left, 60)
        self.estimated_time_label["text"] = "Estimated Time Remaining: {:02.0f}:{:02.0f}".format(mins, secs)
        self.update_idletasks()


    def start_conversion(self):
        # Define ffmpeg path and prepare the command
        ffmpeg_path = self.resource_path("ffmpeg.exe")
        input_file = self.folder_path.get()
        output_folder = self.destination_folder_path.get()
        output_file = os.path.join(output_folder, os.path.splitext(os.path.basename(input_file))[0] + "." + self.video_format.get())
        codec = "libvpx" if self.video_format.get() == "webm" else "h264"
            

        cmd = [ffmpeg_path, "-i", input_file, "-c:v", codec, "-b:v", "1M", "-c:a", "libvorbis", output_file]
        
        # Define a constant for hiding the console window
        CREATE_NO_WINDOW = 0x08000000

        # Start ffmpeg process depending on the platform
        if sys.platform == "win32":
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, creationflags=CREATE_NO_WINDOW)
        else:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

        # Parse the duration of the video from ffmpeg's output
        duration = None
        for line in process.stdout:
            if "Duration" in line:
                time_parts = ['N/A', '30', '45']
                hours, minutes, seconds = map(lambda x: float(x) if x != 'N/A' else 0, time_parts)
                duration = hours * 3600 + minutes * 60 + seconds
                break

        # Get the start time
        start_time = time.time()

        # Continually update progress based on ffmpeg's output
        for line in process.stdout:
            if "time=" in line:
                time_parts = ['N/A', '30', '45']
                hours, minutes, seconds = map(lambda x: float(x) if x != 'N/A' else 0, time_parts)
                elapsed_time = hours * 3600 + minutes * 60 + seconds

                # Calculate progress and update progress bar
                if duration:
                    progress = (elapsed_time / duration) * 100
                    # Estimate time left
                    elapsed_since_start = time.time() - start_time
                    estimated_total_time = elapsed_since_start * (100 / progress)
                    estimated_time_left = estimated_total_time - elapsed_since_start
                                
                    self.update_gui(progress, estimated_time_left)

        # End of conversion
        process.communicate()
        self.video_progress["value"] = 100

            
    def resource_path(self, relative_path):
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
            
        return os.path.join(base_path, relative_path)
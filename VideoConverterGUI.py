import time
import tkinter as tk
from tkinter import ttk, filedialog
import os
import subprocess
import sys
from sys import platform
import threading
import re # Import the 're' module for regular expressions

class VideoConverterGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        
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
        video_formats = ["webm", "mp4"] # Consider "mkv", "mov" as well
        self.format_dropdown = ttk.Combobox(self, textvariable=self.video_format, values=video_formats)
        self.format_dropdown.set("webm") # Default format
        self.format_dropdown.grid(column=1, row=2, padx=20, pady=20, sticky=tk.W)

        convert_button = ttk.Button(self, text="Convert", command=self.convert_video, cursor=cursor_point)
        convert_button.grid(column=2, row=3, padx=20, pady=20, sticky=tk.W)
        self.video_progress = ttk.Progressbar(self, orient="horizontal", mode="determinate", value=0)
        self.video_progress.grid(column=0, row=4, columnspan=4, padx=20, pady=20, sticky=tk.W+tk.E)
        self.estimated_time_label = ttk.Label(self, text="Estimated Time Remaining: --:--", font=("Helvetica", 10))
        self.estimated_time_label.grid(column=1, row=5, padx=20, pady=5, sticky=tk.W)

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Select a video file",
            filetypes=(("Video Files", "*.webm *.mp4 *.mov *.mkv *.avi"), ("all files", "*.*"))
        )
        if file_path:
            self.folder_path.set(file_path)

    def destination_select_folder(self):
        folder_path = filedialog.askdirectory(title="Select Destination Folder")
        if folder_path:
            self.destination_folder_path.set(folder_path)
            
    def convert_video(self):
        input_file = self.folder_path.get()
        output_folder = self.destination_folder_path.get()

        if not input_file:
            # Optionally: show a warning to the user
            print("Error: No input file selected.")
            self.estimated_time_label["text"] = "Error: Select an input file."
            return
        if not output_folder:
            # Optionally: show a warning to the user
            print("Error: No destination folder selected.")
            self.estimated_time_label["text"] = "Error: Select a destination folder."
            return

        threading.Thread(target=self.start_conversion, daemon=True).start() # Use daemon thread
        
    def update_gui(self, progress, estimated_time_left):
        self.video_progress["value"] = progress
        if estimated_time_left >= 0:
            mins, secs = divmod(int(estimated_time_left), 60)
            self.estimated_time_label["text"] = f"Estimated Time Remaining: {mins:02d}:{secs:02d}"
        else: # Handles case where ETA might be negative (e.g. at completion or if calculation is off)
             self.estimated_time_label["text"] = "Estimated Time Remaining: --:--"
        self.update_idletasks() # Necessary for GUI updates from a non-main thread

    def start_conversion(self):
        ffmpeg_path = self.resource_path("ffmpeg.exe") # Ensure ffmpeg.exe is in the correct path
        input_file = self.folder_path.get()
        output_folder = self.destination_folder_path.get()
        
        if not os.path.exists(input_file):
            self.update_gui(0, -1)
            self.estimated_time_label["text"] = "Error: Input file not found."
            return

        if not os.path.isdir(output_folder):
            self.update_gui(0,-1)
            self.estimated_time_label["text"] = "Error: Output folder does not exist."
            return


        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_format = self.video_format.get()
        output_file = os.path.join(output_folder, f"{base_name}.{output_format}")

        # Codec selection based on format
        if output_format == "webm":
            video_codec = "libvpx-vp9" # VP9 is generally preferred over libvpx (VP8)
            audio_codec = "libopus"    # Opus is generally preferred for WebM
        elif output_format == "mp4":
            video_codec = "libx264"    # Common H.264 encoder
            audio_codec = "aac"        # Common AAC encoder
        else:
            # Fallback or error for unsupported formats if any new ones are added
            self.estimated_time_label["text"] = f"Error: Unsupported format {output_format}"
            return

        cmd = [
            ffmpeg_path, "-i", input_file,
            "-c:v", video_codec, "-b:v", "1M", # Video codec and bitrate
            "-c:a", audio_codec,               # Audio codec
            "-y",                              # Overwrite output file if it exists
            output_file
        ]
        
        CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Merge stdout and stderr
                universal_newlines=True,  # Decode output as text
                creationflags=CREATE_NO_WINDOW,
                bufsize=1 # Line buffered
            )
        except FileNotFoundError:
            self.update_gui(0,0)
            self.estimated_time_label["text"] = "Error: ffmpeg.exe not found."
            print(f"Error: ffmpeg.exe not found at {ffmpeg_path}. Please ensure it's in the application directory or your system PATH.")
            return
        except Exception as e:
            self.update_gui(0,0)
            self.estimated_time_label["text"] = f"Error starting ffmpeg: {e}"
            print(f"Error starting ffmpeg: {e}")
            return


        duration_seconds = None
        conversion_start_time = None
        
        self.update_gui(0, 0) # Initialize GUI
        self.estimated_time_label["text"] = "Starting conversion..."


        # Single loop to read all output lines
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            # print(f"ffmpeg: {line}") # Uncomment for debugging ffmpeg output

            if duration_seconds is None:
                # Regex to find Duration: 00:00:28.00
                duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})", line)
                if duration_match:
                    h, m, s, ms = map(int, duration_match.groups())
                    duration_seconds = h * 3600 + m * 60 + s + ms / 100.0
                    conversion_start_time = time.time()
                    self.estimated_time_label["text"] = "Processing..."


            if duration_seconds is not None and conversion_start_time is not None:
                # Regex to find time=00:00:01.23
                time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})", line)
                if time_match:
                    h, m, s, ms = map(int, time_match.groups())
                    current_progress_time_seconds = h * 3600 + m * 60 + s + ms / 100.0

                    if duration_seconds > 0:
                        progress = (current_progress_time_seconds / duration_seconds) * 100
                        progress = min(progress, 100.0) # Cap progress at 100%

                        time_elapsed_wall_clock = time.time() - conversion_start_time
                        estimated_time_left = 0
                        if progress > 0.1 and progress < 100: # Avoid division by zero and calc when nearly done
                            estimated_total_time = (time_elapsed_wall_clock / progress) * 100
                            estimated_time_left = estimated_total_time - time_elapsed_wall_clock
                        elif progress >= 100:
                             estimated_time_left = 0
                        
                        self.update_gui(progress, estimated_time_left)
        
        # After the loop, ffmpeg's stdout has been closed or fully read.
        # Now, wait for the process to terminate and get the return code.
        process.stdout.close() # Close the stdout stream
        return_code = process.wait()

        if return_code == 0:
            self.update_gui(100, 0)
            self.estimated_time_label["text"] = "Conversion Completed!"
        else:
            self.video_progress["value"] = 0 # Or indicate error state on progress bar
            self.estimated_time_label["text"] = f"Error: FFMPEG failed (code {return_code})"
            print(f"FFMPEG conversion failed with code: {return_code}. Check ffmpeg output above if debugging was enabled.")
            # Consider showing the last few lines of output or a more specific error.

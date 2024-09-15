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
from tkinter import messagebox
import webbrowser
from PIL import Image, ImageTk
import concurrent.futures
# from imageManipulationGUI import ImageManipulationGUI
import sv_ttk
import time
import shutil
from sys import platform
from imageConverter import ImageConverterGUI
from fileRenamer import FileRenamerGUI
from pdfToImage import pdfToImageGUI
from VideoConverterGUI import VideoConverterGUI
from textFormatter import TextFormatterGUI
import requests
import subprocess
from datetime import datetime
import numpy
from cryptography.fernet import Fernet
SERVER_URL = "http://webp.mts-studios.com:5000/current_version"
currentVersion = "1.7.2"

headers = {
    'User-Agent': 'convertToWebP/1.0'
}

class HyperlinkManager:
    def __init__(self, text):
        self.text = text
        self.text.tag_config("hyper", foreground="white", underline=1)
        self.text.tag_bind("hyper", "<Enter>", self._enter)
        self.text.tag_bind("hyper", "<Leave>", self._leave)
        self.text.tag_bind("hyper", "<Button-1>", self._click)
        self.links = {}

    def add(self, url):
        tag = "hyper-%d" % len(self.links)
        self.links[tag] = url
        return "hyper", tag

    def _enter(self, event):
        self.text.config(cursor="hand2")

    def _leave(self, event):
        self.text.config(cursor="")

    def _click(self, event):
        for tag in self.text.tag_names(tk.CURRENT):
            url = self.links.get(tag)
            if url:
                webbrowser.open(url)


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.style = ttk.Style(self)
        self.style.configure("TFrame", background="#1c1c1c")
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"

        self.title("Universal File & WebP Tool Set")

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
        
        self.pdf_to_image_button = ttk.Button(self.button_frame, text="PDF to Image", command=self.show_pdf_to_image, cursor=cursor_point)
        self.pdf_to_image_button.pack(side="left", ipadx=10, ipady=10, padx=5, pady=5)
        
        self.video_converter_button = ttk.Button(self.button_frame, text="Video converter", command=self.show_video_converter, cursor=cursor_point)
        self.video_converter_button.pack(side="left", ipadx=10, ipady=10, padx=5, pady=5)        
        
        self.text_formatter_button = ttk.Button(self.button_frame, text="Text Formatter", command=self.show_text_converter, cursor=cursor_point)
        self.text_formatter_button.pack(side="left", ipadx=10, ipady=10, padx=5, pady=5)        
        
        #self.image_manipulation_button = ttk.Button(self.button_frame, text="Image Manipulation", command=self.show_image_manipulation, cursor=cursor_point)
        #self.image_manipulation_button.pack(side="left", ipadx=10, ipady=10, padx=5, pady=5)   
        
        # Hamburger menu button
        self.menu_button = ttk.Button(self.button_frame, text="≡", command=self.show_menu)
        self.menu_button.pack(side="right", padx=5, pady=5)
        self.menu_button.config(width=1, cursor=cursor_point)
        
        # Dropdown menu for the hamburger menu button
        self.dropdown_menu = tk.Menu(self, tearoff=0)
        self.dropdown_menu.add_command(label="Check for Updates", command=self.check_and_update)


        self.image_converter = ImageConverterGUI(self)
        self.image_converter.pack(side="left", fill="both", expand=True)
        self.file_renamer = FileRenamerGUI(self)
        self.file_renamer.pack(side="right", fill="both", expand=True)
        self.pdf_to_image = pdfToImageGUI(self)
        self.pdf_to_image.pack(side="top", fill="both", expand=True)
        self.video_converter = VideoConverterGUI(self)
        self.video_converter.pack(side="top", fill="both", expand=True)
        self.text_formatter = TextFormatterGUI(self)
        self.text_formatter.pack(side="top", fill="both", expand=True)
        #self.image_manipulation = ImageManipulationGUI(self)
        #self.image_manipulation.pack(side="left", fill="both", expand=True)


        # Hide the file renamer at startup
        self.file_renamer.pack_forget()
        self.pdf_to_image.pack_forget()
        self.video_converter.pack_forget()
        self.text_formatter.pack_forget()
        #self.image_manipulation.pack_forget()

        self.geometry('')
        is_update_available(currentVersion)
        
        # Check for updates on startup
        self.update_available = self.check_for_updates_at_start()
        
        # Modify the hamburger menu button accordingly
        self.update_menu_button_text()
        
        # Dropdown menu for the hamburger menu button
        self.dropdown_menu = tk.Menu(self, tearoff=0)
        self.update_dropdown_menu()
        self.periodic_check_for_updates()

        
        
    def check_for_updates_at_start(self):
        # Check for updates
        isAvailable = is_update_available(currentVersion)
        boolAvailable = isAvailable[0]
        if boolAvailable:
            return True
        else:
            return False
        
    def update_menu_button_text(self):
        # Set button text based on whether an update is available
        btn_text = "≡"
        if self.update_available:
            btn_text = "! " + btn_text
        
        # Update the text of the already initialized menu_button
        self.menu_button.config(text=btn_text)

    def update_dropdown_menu(self):
        # Set menu text based on whether an update is available
        menu_text = "Check for Updates"
        if self.update_available:
            menu_text = "! " + menu_text
        
        self.dropdown_menu.add_command(label=menu_text, command=self.check_and_update)
        self.dropdown_menu.add_command(label="About", command=self.show_about)
        self.dropdown_menu.add_command(label="Licenses", command=self.show_licenses)
        
        
    def show_licenses(self):
        license_window = tk.Toplevel(self)
        license_window.title("Licenses")
        license_window.geometry('')

        text = tk.Text(license_window, wrap='word', font=('TkDefaultFont', 11))
        text.pack(expand=True, fill='both', padx=10, pady=10)
        text.config(state='disabled')  # Make the text read-only initially

        hyperlink = HyperlinkManager(text)  # Create a hyperlink manager

        button_frame = tk.Frame(license_window)
        button_frame.pack(side='top', pady=10)

        def update_license(license_text, add_link=False):
            text.config(state='normal')
            text.delete('1.0', 'end')
            text.tag_configure('body', lmargin1=0, lmargin2=0, rmargin=0)
            text.insert('end', license_text, 'body')
            if add_link:
                text.insert('end', " LGPLv2.1.", hyperlink.add("http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html"))
            text.config(state='disabled')

        ffmpeg_button = ttk.Button(button_frame, text="FFmpeg License",
                                    command=lambda: update_license("""This software uses libraries from the FFmpeg project under the """, add_link=True))
        ffmpeg_button.pack(side='left', padx=5)

        jpegxl_button = ttk.Button(button_frame, text="JPEG XL License",
                                    command=lambda: update_license("""This software includes the JPEG XL codec under the BSD-3-Clause License.
                                    
Copyright (c) the JPEG XL Project Authors.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
contributors may be used to endorse or promote products derived from
this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."""))
        jpegxl_button.pack(side='left', padx=5)


        

    def show_image_converter(self):
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        self.geometry('')
        # Fade out
        for i in range(10, -1, -1):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)

        self.file_renamer.pack_forget()
        self.pdf_to_image.pack_forget()
        self.image_converter.pack(side="left", fill="both", expand=True)
        self.video_converter.pack_forget()
        self.text_formatter.pack_forget()

        self.image_converter_button.config(state='disabled', cursor="arrow")
        self.file_renamer_button.config(state='normal', cursor=cursor_point)
        self.pdf_to_image_button.config(state='normal', cursor=cursor_point)
        self.video_converter_button.config(state='normal', cursor=cursor_point)
        self.text_formatter_button.config(state='normal', cursor=cursor_point)

        # Fade in
        for i in range(0, 11):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)
            
    def show_menu(self):
        # Display the dropdown menu below the menu button
        self.dropdown_menu.post(self.menu_button.winfo_rootx(), self.menu_button.winfo_rooty() + self.menu_button.winfo_height())

    def show_file_renamer(self):
        cursor=cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        self.geometry('')
        # Fade out
        for i in range(10, -1, -1):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)

        self.image_converter.pack_forget()
        self.pdf_to_image.pack_forget()
        self.file_renamer.pack(side="right", fill="both", expand=True)
        self.video_converter.pack_forget()
        self.text_formatter.pack_forget()

        self.file_renamer_button.config(state='disabled', cursor="arrow")
        self.image_converter_button.config(state='normal', cursor=cursor_point)
        self.pdf_to_image_button.config(state='normal', cursor=cursor_point)
        self.video_converter_button.config(state='normal', cursor=cursor_point)
        self.text_formatter_button.config(state='normal', cursor=cursor_point)

        # Fade in
        for i in range(0, 11):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)
            
    def show_pdf_to_image(self):
        cursor=cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        self.geometry('')
        # Fade out
        for i in range(10, -1, -1):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)

        self.image_converter.pack_forget()
        self.file_renamer.pack_forget()
        self.pdf_to_image.pack(side="right", fill="both", expand=True)
        self.video_converter.pack_forget()
        self.text_formatter.pack_forget()

        self.file_renamer_button.config(state='normal', cursor=cursor_point)
        self.image_converter_button.config(state='normal', cursor=cursor_point)
        self.pdf_to_image_button.config(state='disabled', cursor="arrow")
        self.video_converter_button.config(state='normal', cursor=cursor_point)
        self.text_formatter_button.config(state='normal', cursor=cursor_point)

        # Fade in
        for i in range(0, 11):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)
            
    def show_video_converter(self):
        cursor=cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        self.geometry('')
        # Fade out
        for i in range(10, -1, -1):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)

        self.image_converter.pack_forget()
        self.file_renamer.pack_forget()
        self.pdf_to_image.pack_forget()
        self.video_converter.pack(side="right", fill="both", expand=True)
        self.text_formatter.pack_forget()

        self.file_renamer_button.config(state='normal', cursor=cursor_point)
        self.image_converter_button.config(state='normal', cursor=cursor_point)
        self.pdf_to_image_button.config(state='normal', cursor=cursor_point)
        self.video_converter_button.config(state='disabled', cursor="arrow")
        self.text_formatter_button.config(state='normal', cursor=cursor_point)

        # Fade in
        for i in range(0, 11):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)
            
    def show_text_converter(self):
        cursor=cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        self.geometry('')
        # Fade out
        for i in range(10, -1, -1):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)

        self.image_converter.pack_forget()
        self.file_renamer.pack_forget()
        self.pdf_to_image.pack_forget()
        self.video_converter.pack_forget()
        self.text_formatter.pack(side="right", fill="both", expand=True)

        self.file_renamer_button.config(state='normal', cursor=cursor_point)
        self.image_converter_button.config(state='normal', cursor=cursor_point)
        self.pdf_to_image_button.config(state='normal', cursor=cursor_point)
        self.video_converter_button.config(state='normal', cursor="arrow")
        self.text_formatter_button.config(state='disabled', cursor=cursor_point)

        # Fade in
        for i in range(0, 11):
            self.attributes('-alpha', i/10)
            self.update()
            time.sleep(0.05)
            
    def check_and_update(self):
        update_available, download_url = is_update_available(currentVersion)
        if update_available:
            answer = messagebox.askyesno("Update Available", "An update is available. Do you want to download and install it?")
            if answer:
                download_success = download_update(download_url)  # Pass the download URL
                if download_success:
                    apply_update()
                    messagebox.showinfo("Update Successful", "The application was updated successfully. Please restart the application to use the new version.")
                    self.quit()
        else:
            messagebox.showinfo("No Update", "You are using the latest version.")
            
    def show_about(self):
        about_win = tk.Toplevel(self)
        about_win.title("About")
        def resource_path(relative_path):
            try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
                
            return os.path.join(base_path, relative_path)

        # Set the icon for the About window
        iconPath = resource_path('convertToWebPIcon.ico')
        about_win.iconbitmap(iconPath)

        # Load and display the image
        image_path = resource_path('convertToWebPLogo.png')
        logo_image = Image.open(image_path)
        # Resize the image
        desired_size = (256, 256)  # Set width and height as needed
        logo_image = logo_image.resize(desired_size, Image.Resampling.LANCZOS)
        logo_photo = ImageTk.PhotoImage(logo_image)
        logo_label = ttk.Label(about_win, image=logo_photo)
        logo_label.image = logo_photo  # Keep a reference to avoid garbage collection
        logo_label.pack(pady=10)

        # Create and pack widgets for the version, copyright, and link to GitHub
        ttk.Label(about_win, text="Version: " + currentVersion).pack(pady=5)
        copyright = ttk.Label(about_win, text="©2024 Matthew Thomas Stevens Studios LLC", cursor="hand2", foreground="white", font="TkDefaultFont 10 underline")
        copyright.pack(pady=5)
        copyright.bind("<Button-1>", lambda e: webbrowser.open("https://www.matthewstevens.me"))
        
        link_label = ttk.Label(about_win, text="Visit GitHub Repo", cursor="hand2", foreground="white", font="TkDefaultFont 10 underline")
        link_label.pack(pady=5)
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/mrzeappleGit/convertToWebP"))
        
        about_win.geometry('300x400')  # Adjusted the size for the image
        about_win.mainloop()
        
    def periodic_check_for_updates(self):
        # Check for updates
        self.update_available = self.check_for_updates_at_start()
        
        # Modify the hamburger menu button accordingly
        self.update_menu_button_text()
        
        # Schedule the next check for 24 hours from now
        self.after(15*60*60*1000, self.periodic_check_for_updates)
    
    def show_image_manipulation(self):
        cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        self.geometry('')  # Adjust size as needed

        # Fade out current components
        for i in range(10, -1, -1):
            self.attributes('-alpha', i / 10)
            self.update()
            time.sleep(0.05)

        # Hide other components
        self.image_converter.pack_forget()
        self.file_renamer.pack_forget()
        self.pdf_to_image.pack_forget()
        self.video_converter.pack_forget()

        # Show the Image Manipulation GUI
        self.image_manipulation.pack(side="left", fill="both", expand=True)

        # Update button states
        self.image_converter_button.config(state='normal', cursor=cursor_point)
        self.file_renamer_button.config(state='normal', cursor=cursor_point)
        self.pdf_to_image_button.config(state='normal', cursor=cursor_point)
        self.video_converter_button.config(state='normal', cursor=cursor_point)
        #self.image_manipulation_button.config(state='disabled', cursor="arrow")

        # Fade in the new component
        for i in range(0, 11):
            self.attributes('-alpha', i / 10)
            self.update()
            time.sleep(0.05)

        

            
def download_update(download_url):
    try:
        # Download the .exe file
        response = requests.get(download_url, stream=True)
        with open('latest_app.exe', 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading update: {e}")
        return False

    
def apply_update():
    try:
        # Rename the downloaded exe to a temporary name
        os.rename('latest_app.exe', 'update_temp.exe')
        
        # Create the helper script
        with open('update_helper.bat', 'w') as bat_file:
            exeName = os.path.basename(sys.executable)
            bat_file.write("@echo off\n")
            bat_file.write("timeout /t 5 /nobreak\n")
            bat_file.write("taskkill /IM " + exeName + " /F\n")
            bat_file.write("move /y update_temp.exe " + exeName + "\n")
            bat_file.write("start " + exeName + "\n")
            bat_file.write("del update_helper.bat")
        
        # Start the helper script to handle the replacement without showing the command prompt
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.Popen(['update_helper.bat'], startupinfo=startupinfo)
        
        # Close the current application
        sys.exit(0)
        
    except Exception as e:
        print(f"Error applying update: {e}")
        return False

            
def is_update_available(current_version):
    try:
        # Generate headers with the token
        headers = {
            'User-Agent': 'convertToWebP/1.0'
        }
        
        response = requests.get(SERVER_URL, headers=headers)
        data = response.json()
        
        latest_version = data.get('version', "")
        download_url = data.get('download_url', "")
        
        return latest_version > current_version, download_url
    except Exception as e:
        print(f"Error checking for update: {e}")
        return False, ""

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = MainApp()
    app.mainloop()
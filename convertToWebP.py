# Required imports for title bar theming on Windows
import sys
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

# --- Existing imports ---
from multiprocessing import Process, Queue, cpu_count
import multiprocessing
from multiprocessing.dummy import Pool
import re
# import sys # Already imported above
import time
import os
import tkinter as tk
from tkinter import filedialog, BOTH, YES, X # Added X
import ttkbootstrap as ttk # Changed to use ttkbootstrap's ttk
from ttkbootstrap.constants import SUCCESS # Import constants like SUCCESS
from tkinter import messagebox
import webbrowser
from PIL import Image, ImageTk
# import concurrent.futures # Not directly used in this diff, consider if needed elsewhere
# from imageManipulationGUI import ImageManipulationGUI # Assuming this might be added later
import sv_ttk
# import time # Already imported
import shutil
from sys import platform # Keep this for cross-platform checks like cursor
import requests
import json # Added for saving/loading settings
import subprocess
from datetime import datetime
# Removed unused imports: numpy, cryptography.fernet

# --- Import your existing GUI components ---
from imageConverter import ImageConverterGUI
from fileRenamer import FileRenamerGUI
from pdfToImage import pdfToImageGUI
from VideoConverterGUI import VideoConverterGUI
from textFormatter import TextFormatterGUI
# --- Import the NEW SVG Circle Generator GUI ---
from svgCircleGenerator import SVGCircleGeneratorGUI # Added Import

SERVER_URL = "http://webp.mts-studios.com:5000/current_version"
currentVersion = "1.9.0" # Consider updating this if needed

headers = {
    'User-Agent': f'convertToWebP/{currentVersion}' # Use f-string
}

# --- NEW: Function to apply theme to title bar (Windows only) ---
def apply_theme_to_titlebar(tk_window):
    """
    Applies the current sv_ttk theme (dark/light) to the window title bar
    on Windows 10 build 19041+ / Windows 11.
    """
    if sys.platform != "win32":
        # print("Title bar theming only supported on Windows.")
        return # Only works on Windows

    try:
        # Get the ttkbootstrap style instance
        # Ensure ttk is imported from ttkbootstrap for this to work as expected
        # For example: import ttkbootstrap as ttk
        # If ttk is from tkinter, this won't have .theme.type
        style = ttk.Style.get_instance() 

        value = 0 # Default to light
        if hasattr(style, 'theme') and hasattr(style.theme, 'type'):
            theme_type = style.theme.type  # 'dark' or 'light' for ttkbootstrap themes
            value = 1 if theme_type == "dark" else 0
            # print(f"Applying '{theme_type}' (from ttkbootstrap) theme to title bar.")
        else:
            # Fallback if ttkbootstrap theme isn't fully set or Style is not from ttkbootstrap
            print("Warning: ttkbootstrap theme type not found. Falling back for title bar.")
            try: # Try sv_ttk as a last resort if it was used before
                sv_theme_type = sv_ttk.get_theme()
                value = 1 if sv_theme_type == "dark" else 0
            except Exception:
                print("Fallback to sv_ttk for title bar also failed. Defaulting to light.")

        # Get the window handle (HWND)
        # Using GetParent because winfo_id() often gives the client area handle
        hwnd = ctypes.windll.user32.GetParent(tk_window.winfo_id())
        if not hwnd:
            print("Error: Could not get window handle (HWND).")
            return

        # Define DWMWINDOWATTRIBUTE constants (use 20 for newer builds)
        # DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20

        # Call DwmSetWindowAttribute
        # HRESULT DwmSetWindowAttribute(
        #   HWND    hwnd,
        #   DWORD   dwAttribute,
        #   LPCVOID pvAttribute,
        #   DWORD   cbAttribute
        # );
        attribute = DWMWA_USE_IMMERSIVE_DARK_MODE
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            attribute,
            ctypes.byref(ctypes.wintypes.BOOL(value)), # Pointer to the value
            ctypes.sizeof(ctypes.wintypes.BOOL)        # Size of the value type
        )

        if result != 0: # S_OK is 0, other values indicate an error
            print(f"Warning: DwmSetWindowAttribute failed with result code {result}. May require Windows 10 20H1+ or Win 11.")

    except AttributeError as e:
        print(f"Error applying title bar theme: Missing attribute. Ensure 'ctypes' is available and sv_ttk is installed. Details: {e}")
    except OSError as e:
        print(f"Error applying title bar theme: OS error. dwmapi.dll might be missing or inaccessible. Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while applying title bar theme: {e}")

# --- Settings Management Functions ---
APP_NAME = "WebWeaverKit"
SETTINGS_FILENAME = "settings.json"

def get_settings_dir():
    """Gets the application-specific settings directory path."""
    if sys.platform == "win32":
        app_data_dir = os.getenv('APPDATA')
        if app_data_dir:
            return os.path.join(app_data_dir, APP_NAME)
    # For macOS and Linux, use a .config directory in the user's home
    home_dir = os.path.expanduser("~")
    return os.path.join(home_dir, ".config", APP_NAME)

def get_settings_path():
    """Gets the full path to the settings file."""
    return os.path.join(get_settings_dir(), SETTINGS_FILENAME)

def load_settings():
    """Loads settings from the JSON file."""
    settings_path = get_settings_path()
    default_settings = {"theme": "superhero"} # Default theme
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading settings file ({settings_path}): {e}. Using defaults.")
            return default_settings
    return default_settings

def save_settings(settings_data):
    """Saves settings to the JSON file."""
    settings_dir = get_settings_dir()
    os.makedirs(settings_dir, exist_ok=True) # Ensure directory exists
    settings_path = get_settings_path()
    try:
        with open(settings_path, 'w') as f:
            json.dump(settings_data, f, indent=4)
        print(f"Settings saved to {settings_path}")
    except IOError as e:
        print(f"Error saving settings to {settings_path}: {e}")

class HyperlinkManager:
    # No changes needed in HyperlinkManager
    def __init__(self, text):
        self.text = text
        # Consider using ttk.Style().lookup('TLabel', 'foreground') for default text color
        # and a specific style color for links if sv_ttk doesn't handle Text widget tags well.
        self.text.tag_config("hyper", foreground="cyan", underline=1) # Using cyan as before
        self.text.tag_bind("hyper", "<Enter>", self._enter)
        self.text.tag_bind("hyper", "<Leave>", self._leave)
        self.text.tag_bind("hyper", "<Button-1>", self._click)
        self.links = {}

    def add(self, url):
        tag = "hyper-%d" % len(self.links)
        self.links[tag] = url
        return "hyper", tag

    def _enter(self, event):
        self.text.config(cursor="hand2") # Use standard cursor names

    def _leave(self, event):
        self.text.config(cursor="")

    def _click(self, event):
        # Find the tag associated with the click position
        index = self.text.index(f"@{event.x},{event.y}")
        tag_names = self.text.tag_names(index)

        for tag in tag_names:
             if tag.startswith("hyper-"): # Check if it's one of our hyperlink tags
                 url = self.links.get(tag)
                 if url:
                     try:
                         print(f"Opening URL: {url}") # Debug print
                         webbrowser.open(url)
                         return # Stop after opening one link
                     except Exception as e:
                         print(f"Error opening URL {url}: {e}") # Add basic error handling


class MainApp(tk.Tk):
    @staticmethod
    def get_resource_path(relative_path):
        """Gets the absolute path to a resource, works for dev and PyInstaller"""
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        else:
            # Not bundled, use the script's directory
            if getattr(sys, 'frozen', False): # Running as a frozen executable (not PyInstaller bundle)
                base_path = os.path.dirname(sys.executable)
            else: # Running as a script
                base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)

    def __init__(self):
        super().__init__()
        
        # --- Load settings early ---
        self.app_settings = load_settings()
        self.current_selected_theme = self.app_settings.get("theme", "superhero")
        # Removed redundant style creation, sv_ttk handles it
        # self.style = ttk.Style(self)
        # self.style.configure("TFrame", background="#1c1c1c") # sv_ttk handles frame background

        cursor_point = "hand2" if platform != "darwin" else "pointinghand" # Use standard cursor name

        self.title("Web Weaver Kit")

        # --- Set Icon ---
        try:
            iconPath = MainApp.get_resource_path('convertToWebPIcon.ico')
            if os.path.exists(iconPath):
                 self.iconbitmap(iconPath)
            else:
                 print(f"Warning: Icon file not found at {iconPath}")
        except tk.TclError as e:
             # This error often happens on non-Windows systems or if .ico is invalid
             print(f"Warning: Could not set icon ({iconPath}): {e}. Trying .png/.xbm as fallback.")
             # Try PNG fallback (requires Pillow)
             try: # Nested try for PNG
                 pngIconPath = MainApp.get_resource_path('convertToWebPLogo.png')
                 if os.path.exists(pngIconPath):
                     img = tk.PhotoImage(file=pngIconPath)
                     self.iconphoto(True, img) # Set icon for window and taskbar
                 else:
                     print(f"Warning: PNG icon fallback not found at {pngIconPath}")
             except Exception as png_e:
                 print(f"Warning: Could not set PNG icon: {png_e}")
        except Exception as e:
             print(f"Warning: Error accessing icon file ({iconPath}): {e}")


        self.resizable(True, True)

        # --- Set Theme AND Apply to Title Bar ---
        # Initialize with a default ttkbootstrap theme
        # sv_ttk.set_theme("dark") # REMOVE THIS - ttkbootstrap handles it
        # super().__init__() is called implicitly by tk.Tk, if we want themed window from start:
        # Apply loaded or default theme
        self.style = ttk.Style(theme=self.current_selected_theme)
        self.update_idletasks() # Ensure window exists before getting HWND for title bar
        apply_theme_to_titlebar(self) # <<--- ADDED CALL HERE

        self.button_frame = ttk.Frame(self) # Use ttk.Frame for consistency
        self.button_frame.pack(side="top", fill="x", padx=5, pady=5) # Add some padding

        # --- Button Definitions ---
        # Use a dictionary to store buttons for easier state management
        self.buttons = {}
        button_defs = [
            ("Converter", self.show_image_converter, "image_converter"),
            ("File Renamer", self.show_file_renamer, "file_renamer"),
            ("PDF to Image", self.show_pdf_to_image, "pdf_to_image"),
            ("Video Converter", self.show_video_converter, "video_converter"),
            ("Text Formatter", self.show_text_converter, "text_formatter"),
            ("Image Mapping Tool", self.show_svg_generator, "svg_generator") # Added SVG Generator Button
        ]

        for text, command, name in button_defs:
            button = ttk.Button(self.button_frame, text=text, command=command, cursor=cursor_point)
            button.pack(side="left", padx=5, pady=5) # Removed ipady/ipadx, rely on theme
            self.buttons[name] = button

        # Hamburger menu button
        self.menu_button = ttk.Button(self.button_frame, text="≡", command=self.show_menu, width=3) # Slightly wider
        self.menu_button.pack(side="right", padx=5, pady=5)
        self.menu_button.config(cursor=cursor_point)

        # --- Frame Definitions ---
        # Use a dictionary to store frames for easier management
        self.frames = {}
        self.frames["image_converter"] = ImageConverterGUI(self)
        self.frames["file_renamer"] = FileRenamerGUI(self)
        self.frames["pdf_to_image"] = pdfToImageGUI(self)
        self.frames["video_converter"] = VideoConverterGUI(self)
        self.frames["text_formatter"] = TextFormatterGUI(self)
        self.frames["svg_generator"] = SVGCircleGeneratorGUI(self) # Added SVG Generator Frame instance

        # Pack the initial frame (image_converter)
        self.current_frame_name = "image_converter"
        self.frames[self.current_frame_name].pack(fill="both", expand=True, padx=10, pady=10) # Add padding to frame content
        self.buttons[self.current_frame_name].config(state='disabled', cursor="arrow")

        # Hide other frames initially
        for name, frame in self.frames.items():
            if name != self.current_frame_name:
                frame.pack_forget()

        # --- Update checks and Menu ---
        self.update_available = False # Initialize
        self.download_url = ""
        self.check_for_updates_at_start() # Run initial check

        # Dropdown menu (create after update check)
        self.dropdown_menu = tk.Menu(self, tearoff=0)
        self.update_dropdown_menu() # Populate menu

        self.update_menu_button_text() # Update button based on check

        # Schedule periodic checks (e.g., every 12 hours)
        self.after(12 * 60 * 60 * 1000, self.periodic_check_for_updates)

        # Set initial size (optional, can let it auto-size)
        # self.geometry('800x600') # Example initial size


    def _switch_frame(self, target_frame_name):
        """Helper function to switch frames with fade effect."""
        if target_frame_name == self.current_frame_name:
            return # Already showing this frame

        cursor_point = "hand2" if platform != "darwin" else "pointinghand"
        do_fade = True # Control fade effect

        # --- Fade Out ---
        if do_fade:
            try:
                # Check if alpha is supported before trying to use it
                if self.attributes('-alpha') is not None:
                    for i in range(10, -1, -1):
                        self.attributes('-alpha', i/10)
                        self.update()
                        time.sleep(0.015) # Faster fade
                else:
                    do_fade = False # Disable fade if not supported from the start
            except tk.TclError: # Handle cases where alpha might not be supported mid-fade
                print("Alpha transparency not supported on this system/window manager.")
                do_fade = False # Disable fade if not supported
                self.attributes('-alpha', 1.0) # Ensure fully opaque if fade fails


        # --- Hide Current Frame ---
        if self.current_frame_name and self.current_frame_name in self.frames:
            self.frames[self.current_frame_name].pack_forget()

        # --- Show Target Frame ---
        self.current_frame_name = target_frame_name
        if self.current_frame_name in self.frames:
             # Add padding when packing the frame content
             self.frames[self.current_frame_name].pack(fill="both", expand=True, padx=10, pady=10)
        else:
             print(f"Error: Frame '{self.current_frame_name}' not found.")
             # Optionally show a default frame or error message
             self.current_frame_name = "image_converter" # Fallback
             self.frames[self.current_frame_name].pack(fill="both", expand=True, padx=10, pady=10)


        # --- Update Button States ---
        for name, button in self.buttons.items():
            if name == self.current_frame_name:
                button.config(state='disabled', cursor="arrow")
            else:
                button.config(state='normal', cursor=cursor_point)

        # --- Fade In ---
        if do_fade:
            try:
                # Check again if alpha is supported
                if self.attributes('-alpha') is not None:
                    for i in range(0, 11):
                        self.attributes('-alpha', i/10)
                        self.update()
                        time.sleep(0.015) # Faster fade
                    self.attributes('-alpha', 1.0) # Ensure fully opaque
                else:
                    self.attributes('-alpha', 1.0) # Ensure visible if fade disabled at start
            except tk.TclError:
                # Handle error during fade-in (less likely but possible)
                print("Alpha transparency not supported on this system/window manager.")
                self.attributes('-alpha', 1.0) # Ensure fully opaque
        else:
             # Ensure window is fully opaque if fade was disabled or failed
             try:
                 self.attributes('-alpha', 1.0)
             except tk.TclError:
                 pass # Ignore if alpha wasn't supported anyway


    # --- Show Frame Methods ---
    def show_image_converter(self):
        self._switch_frame("image_converter")

    def show_file_renamer(self):
        self._switch_frame("file_renamer")

    def show_pdf_to_image(self):
        self._switch_frame("pdf_to_image")

    def show_video_converter(self):
        self._switch_frame("video_converter")

    def show_text_converter(self):
         self._switch_frame("text_formatter") # Corrected frame name

    def show_svg_generator(self): # Added method for SVG Generator
        self._switch_frame("svg_generator")

    # --- Menu and Update Methods ---
    def show_menu(self):
        # Ensure menu is up-to-date before showing
        self.update_dropdown_menu()
        try:
            # Position menu just below the button
            x = self.menu_button.winfo_rootx()
            y = self.menu_button.winfo_rooty() + self.menu_button.winfo_height()
            self.dropdown_menu.tk_popup(x, y)
        finally:
            # Make sure the menu is grabbed (important on some platforms)
            self.dropdown_menu.grab_release()


    def check_for_updates_at_start(self):
        # Check for updates and store result
        self.update_available, self.download_url = is_update_available(currentVersion)
        print(f"Update check: Available={self.update_available}, URL='{self.download_url}'") # Debug print

    def update_menu_button_text(self):
        # Set button text based on whether an update is available
        btn_text = "≡"
        if self.update_available:
            btn_text = "! " + btn_text # Add indicator
        self.menu_button.config(text=btn_text)

    def update_dropdown_menu(self):
        # Clear existing menu items
        self.dropdown_menu.delete(0, tk.END)

        # Set menu text based on whether an update is available
        update_label = "Check for Updates"
        if self.update_available:
            update_label = "! Check for Updates" # Add indicator

        self.dropdown_menu.add_command(label=update_label, command=self.check_and_update)
        self.dropdown_menu.add_command(label="Change Theme...", command=self.open_theme_dialog) # New theme option
        self.dropdown_menu.add_command(label="About", command=self.show_about)
        self.dropdown_menu.add_command(label="Licenses", command=self.show_licenses)

    def open_theme_dialog(self):
        """Opens a Toplevel window to select a ttkbootstrap theme."""
        dialog = ttk.Toplevel(self)
        dialog.title("Select Theme")
        dialog.geometry("700x480") # Increased size for preview
        dialog.transient(self)
        dialog.grab_set()

        # Apply title bar theme to the dialog itself
        dialog.update_idletasks()
        apply_theme_to_titlebar(dialog)

        # Main container frame in the dialog
        main_dialog_frame = ttk.Frame(dialog, padding=10)
        main_dialog_frame.pack(fill=BOTH, expand=YES)

        # Left frame for controls
        controls_frame = ttk.Frame(main_dialog_frame)
        controls_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # Right frame for preview
        preview_frame = ttk.Frame(main_dialog_frame, padding=5)
        preview_frame.pack(side=tk.RIGHT, fill=BOTH, expand=YES)
        # Add a border to the preview frame for better visual separation
        preview_frame.config(relief="sunken", borderwidth=1)


        ttk.Label(controls_frame, text="Choose a theme:").pack(pady=(0, 10), anchor=tk.W)

        style_instance = ttk.Style.get_instance()
        # print(f"DEBUG: Style instance in dialog: {style_instance}")
        # print(f"DEBUG: Style instance type: {type(style_instance)}")

        available_themes = []
        try:
            available_themes = sorted(style_instance.theme_names())
            # print(f"DEBUG: Available themes via get_instance(): {available_themes}")
        except Exception as e:
            print(f"DEBUG: Error getting theme_names via get_instance(): {e}")

        if not available_themes:
            # print("DEBUG: No themes found by ttk.Style.get_instance().theme_names(). Attempting fallback.")
            try:
                # Fallback: Create a new temporary style object just to get theme names
                # This can help if get_instance() is returning an uninitialized/different style object
                temp_style = ttk.Style()
                available_themes = sorted(temp_style.theme_names())
                # print(f"DEBUG: Available themes (fallback attempt with new Style()): {available_themes}")
                if not available_themes:
                    messagebox.showerror("Theme Error", "No ttkbootstrap themes could be loaded. Please check your ttkbootstrap installation.", parent=dialog)
                    dialog.destroy()
                    return
            except Exception as e_fallback:
                print(f"DEBUG: Fallback theme loading also failed: {e_fallback}")
                messagebox.showerror("Theme Error", f"Failed to load themes: {e_fallback}. Check ttkbootstrap installation.", parent=dialog)
                dialog.destroy()
                return

        # --- Theme Preview Label ---
        self.theme_preview_label = ttk.Label(preview_frame, text="Preview N/A", anchor=tk.CENTER)
        self.theme_preview_label.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        self.theme_preview_photo = None # To keep a reference to PhotoImage
        dialog_active = True # Flag to control operations within the dialog

        # --- Function to load and display theme preview ---
        def load_and_display_theme_preview(theme_name):
            # Check if the dialog and preview frame still exist
            # Also check our custom flag
            if not dialog_active or not dialog.winfo_exists() or not preview_frame.winfo_exists():
                return # Dialog or frame was destroyed, do nothing

            preview_image_filename = f"{theme_name}.png"
            preview_image_path = MainApp.get_resource_path(os.path.join("theme_previews", preview_image_filename))

            # Define max preview dimensions
            max_width = preview_frame.winfo_width() - 20 # Account for padding/border
            max_height = preview_frame.winfo_height() - 20
            if max_width <= 0 or max_height <= 0: # If frame not yet sized
                max_width = 380 # Adjusted default if frame not sized, to fit better
                max_height = 300

            if os.path.exists(preview_image_path):
                try:
                    image = Image.open(preview_image_path)
                    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                    self.theme_preview_photo = ImageTk.PhotoImage(image)
                    if self.theme_preview_label.winfo_exists(): # Check label too
                        self.theme_preview_label.config(image=self.theme_preview_photo, text="")
                        self.theme_preview_label.image = self.theme_preview_photo # Keep reference
                except Exception as e:
                    print(f"Error loading preview for {theme_name}: {e}")
                    if self.theme_preview_label.winfo_exists():
                        self.theme_preview_label.config(image="", text=f"Error loading\n{theme_name}.png")
                        self.theme_preview_label.image = None
            else:
                if self.theme_preview_label.winfo_exists():
                    self.theme_preview_label.config(image="", text=f"Preview for\n'{theme_name}'\nnot found.")
                    self.theme_preview_label.image = None
            
            # Ensure the dialog is still active and our flag is set before trying to update it further
            if dialog_active and dialog.winfo_exists():
                dialog.update_idletasks()

        # current_theme_in_use = style_instance.theme_use()
        # print(f"DEBUG: Current theme in use by style_instance: {current_theme_in_use}")
        # Use a tk.StringVar for the Combobox
        # Use the theme that was actually applied to the app at startup
        initial_theme = self.current_selected_theme
        self.selected_theme_var = tk.StringVar(value=initial_theme)

        theme_combo = ttk.Combobox(
            controls_frame, # Corrected: Pack into controls_frame
            textvariable=self.selected_theme_var,
            values=available_themes,
            state="readonly",
            width=20 # Adjusted width
        )
        theme_combo.pack(pady=5, anchor=tk.W)

        def on_theme_selected_in_combo(event=None): # Can be called by event or directly
            # Check if the dialog and combobox still exist
            if not dialog_active or not dialog.winfo_exists() or not theme_combo.winfo_exists():
                return
            selected_theme = self.selected_theme_var.get() # Get theme only if combo exists
            load_and_display_theme_preview(selected_theme) # Call preview update

        theme_combo.bind("<<ComboboxSelected>>", on_theme_selected_in_combo)
        
        def safe_dialog_destroy():
            nonlocal dialog_active
            dialog_active = False # Signal that dialog operations should cease
            if dialog and dialog.winfo_exists():
                dialog.destroy()

        def apply_theme_action():
            nonlocal dialog_active
            # Get the chosen theme *before* disabling anything
            chosen_theme = self.selected_theme_var.get()

            # Immediately disable the combobox to prevent further events or access
            if theme_combo.winfo_exists():
                theme_combo.config(state=tk.DISABLED)

            # Save the chosen theme to settings *before* attempting to apply it visually
            self.app_settings["theme"] = chosen_theme
            save_settings(self.app_settings)
            print(f"Theme '{chosen_theme}' saved to settings.")
            try:
                style_instance.theme_use(chosen_theme)
                print(f"Theme changed to: {chosen_theme}")
                # Update title bar for main window and any other open Toplevels
                apply_theme_to_titlebar(self)
                for child_widget in self.winfo_children():
                    if isinstance(child_widget, tk.Toplevel):
                        if child_widget.winfo_exists(): # Check if child toplevel still exists
                            apply_theme_to_titlebar(child_widget)
                # Visual application successful
            except tk.TclError as e:
                # Instead of showing a messagebox, print the error to the console
                print(f"Theme Error: Could not apply theme '{chosen_theme}'.\n{e}")
            
            # Schedule the dialog destruction to happen after current event processing
            self.after_idle(safe_dialog_destroy)

        apply_button = ttk.Button(controls_frame, text="Apply", command=apply_theme_action, bootstyle=SUCCESS)
        apply_button.pack(pady=(20,0), anchor=tk.W)

        # Load initial preview after dialog elements are packed and sized
        if dialog.winfo_exists(): # Check before calling update_idletasks and loading preview
            dialog.update_idletasks() # Ensure preview_frame has dimensions
            on_theme_selected_in_combo() # Load preview for the initially selected theme
        
        # Override the dialog's close button (X) to also use safe_dialog_destroy
        if dialog.winfo_exists():
            dialog.protocol("WM_DELETE_WINDOW", safe_dialog_destroy)

    def periodic_check_for_updates(self):
        print("Performing periodic update check...")
        self.check_for_updates_at_start()
        self.update_menu_button_text()
        # Reschedule the next check
        self.after(12 * 60 * 60 * 1000, self.periodic_check_for_updates)

    def check_and_update(self):
        # Re-check just in case status changed since last periodic check
        update_avail, download_url_latest = is_update_available(currentVersion)

        # Update internal state and button based on the fresh check
        self.update_available = update_avail
        self.download_url = download_url_latest
        self.update_menu_button_text()

        if update_avail:
            # Extract filename from URL for display
            try:
                filename = os.path.basename(download_url_latest) if download_url_latest else "update"
            except Exception:
                filename = "update"

            answer = messagebox.askyesno("Update Available", f"An update ({filename}) is available. Do you want to download and install it?")
            if answer:
                # Make sure we have a valid URL
                if not download_url_latest or not download_url_latest.startswith(('http://', 'https://')):
                     messagebox.showerror("Update Error", "Invalid download URL received from server.")
                     return

                # Use the latest URL found
                download_success = download_update(download_url_latest)
                if download_success:
                    if apply_update(): # apply_update handles exit
                         # No need for messagebox here as apply_update should exit/restart
                         print("Update process initiated...")
                         # apply_update should exit, but call self.quit() as fallback
                         self.quit()
                    else:
                         messagebox.showerror("Update Error", "Failed to apply the update. Please try again or update manually.")
                else:
                     messagebox.showerror("Download Error", "Failed to download the update.")
        else:
            messagebox.showinfo("No Update", "You are using the latest version.")
            # No need to explicitly reset indicator here, it was done by update_menu_button_text()


    def show_about(self):
        # --- About Window ---
        about_win = tk.Toplevel(self)
        about_win.title("About")
        about_win.transient(self) # Make it transient to the main window
        about_win.grab_set()      # Grab focus
        about_win.resizable(False, False)

        # --- Apply Title Bar Theme to Toplevel ---
        # Need to ensure sv_ttk theme is applied to Toplevels if needed
        # sv_ttk might handle this, but explicit call ensures title bar matches.
        about_win.update_idletasks() # Ensure window exists for HWND
        apply_theme_to_titlebar(about_win) # <<--- APPLY THEME TO TOPLEVEL

        # Use the same resource_path function as in __init__
        # --- Set Icon for About Window ---
        try:
            iconPath = MainApp.get_resource_path('convertToWebPIcon.ico')
            if os.path.exists(iconPath):
                 about_win.iconbitmap(iconPath)
            else: # Try PNG fallback
                 pngIconPath = MainApp.get_resource_path('convertToWebPLogo.png')
                 if os.path.exists(pngIconPath):
                     img = tk.PhotoImage(file=pngIconPath)
                     about_win.iconphoto(True, img)
        except Exception as e:
             print(f"Warning: Could not set About window icon: {e}")

        # --- Load and display the image ---
        try:
            image_path = MainApp.get_resource_path('convertToWebPLogo.png')
            if os.path.exists(image_path):
                logo_image_pil = Image.open(image_path)
                desired_size = (128, 128) # Smaller logo
                logo_image_pil = logo_image_pil.resize(desired_size, Image.Resampling.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_image_pil)
                logo_label = ttk.Label(about_win, image=logo_photo)
                logo_label.image = logo_photo # Keep reference
                logo_label.pack(pady=10)
            else:
                 print(f"Warning: Logo file not found at {image_path}")
        except Exception as e:
            print(f"Error loading logo: {e}")


        ttk.Label(about_win, text=f"Version: {currentVersion}").pack(pady=5)

        # --- Style for hyperlink labels ---
        # Ensure the style is configured before creating labels that use it
        style = ttk.Style()
        # Use a distinct style name like "Hyperlink.TLabel"
        # Using 'cyan' as before, but ideally use a theme color like 'link.fg' if defined
        style.configure("Hyperlink.TLabel", foreground="cyan", underline=True)

        copyright_label = ttk.Label(about_win, text="©2024 Matthew Thomas Stevens Studios LLC", cursor="hand2", style="Hyperlink.TLabel")
        copyright_label.pack(pady=5)
        copyright_label.bind("<Button-1>", lambda e: webbrowser.open("https://www.matthewstevens.me"))

        link_label = ttk.Label(about_win, text="Visit GitHub Repo", cursor="hand2", style="Hyperlink.TLabel")
        link_label.pack(pady=5)
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/mrzeappleGit/convertToWebP"))


        # Center the window relative to the main window
        about_win.update_idletasks() # Ensure dimensions are calculated
        main_x = self.winfo_rootx()
        main_y = self.winfo_rooty()
        main_w = self.winfo_width()
        main_h = self.winfo_height()
        popup_w = about_win.winfo_width()
        popup_h = about_win.winfo_height()
        x = main_x + (main_w // 2) - (popup_w // 2)
        y = main_y + (main_h // 2) - (popup_h // 2)
        about_win.geometry(f"+{x}+{y}")

        # Ensure focus returns to main window on close
        about_win.protocol("WM_DELETE_WINDOW", lambda: (about_win.grab_release(), about_win.destroy()))


    def show_licenses(self):
        # --- License Window ---
        license_window = tk.Toplevel(self)
        license_window.title("Licenses")
        license_window.geometry('700x500') # Adjusted size
        license_window.transient(self)
        license_window.grab_set()

        # --- Apply Title Bar Theme to Toplevel ---
        license_window.update_idletasks() # Ensure window exists for HWND
        apply_theme_to_titlebar(license_window) # <<--- APPLY THEME TO TOPLEVEL

        # --- Main frame for content ---
        main_license_frame = ttk.Frame(license_window)
        main_license_frame.pack(expand=True, fill='both', padx=10, pady=10)

        # --- Frame for buttons at the top ---
        button_frame = ttk.Frame(main_license_frame)
        button_frame.pack(side='top', pady=(0,10), fill='x') # Pad bottom only

        # --- Frame for text area and scrollbar ---
        text_frame = ttk.Frame(main_license_frame)
        text_frame.pack(expand=True, fill='both')

        # --- Text Area ---
        # Let sv_ttk handle the text widget styling if possible
        text = tk.Text(text_frame, wrap='word', font=('TkDefaultFont', 10), height=15,
                       # insertbackground="white", # Let theme handle this
                       relief="flat",
                       borderwidth=0, highlightthickness=0) # Basic styling, remove border
        # --- Scrollbar ---
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)

        # --- Packing Text and Scrollbar ---
        scrollbar.pack(side="right", fill="y")
        text.pack(side="left", expand=True, fill="both")

        text.config(state='disabled') # Read-only initially
        hyperlink = HyperlinkManager(text) # Use the manager

        # --- License Data (Store in a dictionary for easier management) ---
        licenses = {
            "FFmpeg": {
                "text": "This software uses libraries from the FFmpeg project under the",
                "link": {'text': " LGPLv2.1.", 'url': "http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html"}
            },
            "JPEG XL": {
                "text": """This software includes the JPEG XL codec (libjxl) under the BSD 3-Clause License.

Copyright (c) the JPEG XL Project Authors. All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."""
            },
             "Pillow": {
                "text": """The Python Imaging Library (Pillow) is licensed under the HPND License (similar to the MIT License).

Copyright © 1997-2011 by Secret Labs AB
Copyright © 1995-2011 by Fredrik Lundh
Copyright © 2010-2024 by Alex Clark and contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."""
            },
            "sv-ttk": {
                "text": """Sun Valley ttk Theme (sv-ttk) is licensed under the MIT License.

Copyright (c) 2021 rdbende

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
            },
            # Add other licenses here: Python, Tcl/Tk, etc.
        }

        # --- Function to update the text area ---
        def update_license_display(license_key):
            data = licenses.get(license_key)
            if not data: return

            text.config(state='normal')
            text.delete('1.0', 'end')
            text.insert('1.0', data['text']) # Insert at the beginning

            link_info = data.get('link')
            if link_info:
                # Insert the link text and apply the tag
                text.insert('end', link_info['text'], hyperlink.add(link_info['url']))

            text.config(state='disabled')
            text.yview_moveto(0) # Scroll to top

        # --- Create Buttons for each license ---
        for key in licenses.keys():
             button = ttk.Button(button_frame, text=key, width=12,
                                 command=lambda k=key: update_license_display(k))
             button.pack(side='left', padx=3)


        # --- Show FFmpeg license by default ---
        update_license_display("FFmpeg")

        # --- Center the window ---
        license_window.update_idletasks()
        main_x = self.winfo_rootx(); main_y = self.winfo_rooty()
        main_w = self.winfo_width(); main_h = self.winfo_height()
        popup_w = license_window.winfo_width(); popup_h = license_window.winfo_height()
        x = main_x + (main_w // 2) - (popup_w // 2)
        y = main_y + (main_h // 2) - (popup_h // 2)
        license_window.geometry(f"+{x}+{y}")

        # --- Ensure focus returns on close ---
        license_window.protocol("WM_DELETE_WINDOW", lambda: (license_window.grab_release(), license_window.destroy()))


# === Helper Functions (Outside Class - No changes here related to title bar) ===

def download_update(download_url):
    """Downloads the update file from the given URL."""
    download_path = 'latest_app_update.exe' # Use a distinct name
    print(f"Downloading update from: {download_url}")
    try:
        response = requests.get(download_url, stream=True, headers=headers, timeout=300) # Added timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192 # Increased block size
        start_time = time.time()
        downloaded_size = 0

        # --- Simple Progress Bar in Console ---
        progress_bar_length = 40
        print("Downloading:")
        sys.stdout.write("[%s]" % (" " * progress_bar_length))
        sys.stdout.flush()
        sys.stdout.write("\b" * (progress_bar_length+1)) # return to start of line

        with open(download_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=block_size):
                file.write(chunk)
                downloaded_size += len(chunk)
                if total_size > 0:
                    # Avoid division by zero if total_size is somehow 0
                    percent_float = (downloaded_size / total_size) if total_size > 0 else 0
                    percent_int = int(progress_bar_length * percent_float)
                    # Ensure percent_int doesn't exceed length due to float inaccuracies
                    percent_int = min(percent_int, progress_bar_length)

                    sys.stdout.write("-" * percent_int)
                    sys.stdout.write(" " * (progress_bar_length - percent_int))
                    sys.stdout.write("] %d%%" % int(100 * percent_float))
                    sys.stdout.flush()
                    # Adjust backspace count: bar length + start/end brackets + space + percentage (e.g., " 99%") = 4
                    backspace_count = progress_bar_length + 2 + 4
                    sys.stdout.write("\b" * backspace_count) # Adjust backspace count


        sys.stdout.write("-" * progress_bar_length) # Fill bar at end
        sys.stdout.write("] 100%\n")
        sys.stdout.flush()
        print(f"Download complete: {download_path}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"\nError downloading update (RequestException): {e}")
        messagebox.showerror("Download Error", f"Network error during download: {e}")
    except Exception as e:
        print(f"\nError downloading update (General): {e}")
        messagebox.showerror("Download Error", f"An error occurred during download: {e}")

    # Cleanup failed download
    if os.path.exists(download_path):
        try:
            os.remove(download_path)
        except OSError as oe:
            print(f"Error removing incomplete download {download_path}: {oe}")
    return False


def apply_update():
    """Applies the downloaded update using a helper batch script."""
    update_exe = 'latest_app_update.exe'
    helper_bat = 'update_helper.bat'

    if not os.path.exists(update_exe):
        print("Update file not found.")
        messagebox.showerror("Update Error", "Update file not found. Please download again.")
        return False

    try:
        current_exe = os.path.basename(sys.executable)
        # Ensure we get the correct directory, especially when frozen
        if getattr(sys, 'frozen', False):
            current_dir = os.path.dirname(sys.executable)
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))

        target_exe_path = os.path.join(current_dir, current_exe)
        update_exe_path = os.path.join(current_dir, update_exe) # Ensure full path

        print(f"Current executable: {target_exe_path}")
        print(f"Update file: {update_exe_path}")

        # Create the helper script in the same directory
        helper_bat_path = os.path.join(current_dir, helper_bat)

        with open(helper_bat_path, 'w') as bat_file:
            bat_file.write("@echo off\n")
            bat_file.write("echo Waiting for application to close...\n")
            bat_file.write("timeout /t 3 /nobreak > NUL\n") # Short delay
            bat_file.write(f"echo Attempting to terminate {current_exe}...\n")
            # Use taskkill with quotes around the image name in case of spaces
            bat_file.write(f"taskkill /IM \"{current_exe}\" /F > NUL 2>&1\n")
            bat_file.write("timeout /t 2 /nobreak > NUL\n") # Wait after kill
            bat_file.write(f"echo Replacing application file...\n")
            # Use move command, /Y overwrites without prompting. Quote paths.
            bat_file.write(f"move /Y \"{update_exe_path}\" \"{target_exe_path}\"\n")
            # Check if move was successful (errorlevel 0)
            bat_file.write("if errorlevel 1 (\n")
            bat_file.write("  echo ERROR: Failed to replace the application file.\n")
            bat_file.write("  echo Please ensure the application is closed and try updating manually.\n")
            bat_file.write("  pause\n") # Pause so user can see error
            # Attempt to delete downloaded file on failure, quote path
            bat_file.write(f"  if exist \"{update_exe_path}\" del \"{update_exe_path}\" > NUL 2>&1\n")
            bat_file.write("  goto cleanup\n") # Go to cleanup section
            bat_file.write(")\n")
            bat_file.write(f"echo Relaunching application...\n")
            # Use start command to launch detached. Quote path.
            bat_file.write(f"start \"\" \"{target_exe_path}\"\n")
            # Label for cleanup
            bat_file.write(":cleanup\n")
            bat_file.write("echo Cleaning up...\n")
            # Self-delete the batch file
            bat_file.write("(goto) 2>nul & del \"%~f0\"\n") # Self-deletion technique

        print(f"Created {helper_bat_path}")

        # Start the helper script without showing the command prompt window
        # Use DETACHED_PROCESS flag for independent execution
        # Ensure the path to the batch file is used
        # Add CREATE_NO_WINDOW to hide the console window completely
        creation_flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        subprocess.Popen([helper_bat_path], creationflags=creation_flags, close_fds=True)
        print(f"Launched {helper_bat_path}")

        # The application should exit here to allow replacement
        print("Application exiting to allow update...")
        return True # Signal that update process started

    except Exception as e:
        print(f"Error preparing update application: {e}")
        messagebox.showerror("Update Error", f"Could not prepare the update process: {e}")
        # Cleanup helper script if created
        helper_bat_path_cleanup = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__)), helper_bat)
        if os.path.exists(helper_bat_path_cleanup):
             try: os.remove(helper_bat_path_cleanup)
             except OSError: pass
        return False


def is_update_available(current_v):
    """Checks the server for a newer version."""
    print(f"Checking for updates... Current version: {current_v}")
    try:
        response = requests.get(SERVER_URL, headers=headers, timeout=10) # Added timeout
        response.raise_for_status() # Check for HTTP errors
        data = response.json()

        latest_version = data.get('version')
        download_url = data.get('download_url')

        if not latest_version or not download_url:
             print("Error: Invalid data received from update server.")
             return False, ""

        print(f"Server version: {latest_version}, URL: {download_url}")

        # --- Version Comparison (Handle potential errors) ---
        try:
            # Use a simple tuple comparison for versions like '1.8.1', '1.10.0'
            current_parts = tuple(map(int, current_v.split('.')))
            latest_parts = tuple(map(int, latest_version.split('.')))
            update_needed = latest_parts > current_parts
        except ValueError:
            print("Warning: Could not parse version numbers for comparison. Assuming no update.")
            update_needed = False # Fallback if version format is unexpected

        return update_needed, download_url

    except requests.exceptions.Timeout:
        print("Error checking for update: Request timed out.")
        return False, ""
    except requests.exceptions.RequestException as e:
        print(f"Error checking for update (RequestException): {e}")
        return False, ""
    except Exception as e:
        print(f"Error checking for update (General): {e}")
        return False, ""

# === Main Execution Guard ===
if __name__ == "__main__":
    # Required for multiprocessing support when bundled with PyInstaller
    multiprocessing.freeze_support()
    
    # To initialize with a ttkbootstrap theme from the start for the MainApp (tk.Tk)
    # we need to make MainApp a ttk.Window or apply style before widgets are created.
    # For simplicity, let's assume MainApp itself is a tk.Tk window and widgets inside will pick up the theme.
    # If MainApp were a ttk.Window, it would be: app = MainApp(themename="superhero")
    app = MainApp() 
    # The theme is now loaded and applied within MainApp.__init__
    # So, this line is no longer strictly needed here, but ensure self.style is set in __init__
    # app.style = ttk.Style(theme=app.current_selected_theme) # This is now done inside __init__
    app.mainloop()
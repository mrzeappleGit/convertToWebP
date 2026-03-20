import sys
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

import multiprocessing
import os
import tkinter as tk
from tkinter import filedialog, BOTH, YES, X
from tkinter import ttk
from tkinter import messagebox
import webbrowser
from PIL import Image, ImageTk
Image.MAX_IMAGE_PIXELS = None  # disable decompression bomb check for local desktop use
from sys import platform
import requests
import json
import subprocess
import threading

# ── Load saved color scheme BEFORE any module imports theme colors ──
from theme import set_color_scheme, COLOR_SCHEMES, get_active_scheme_name

def _load_saved_scheme():
    """Read settings.json early to apply color scheme before modules load."""
    _settings_dir = os.path.join(os.getenv('APPDATA', ''), "WebWeaverKit") if sys.platform == "win32" \
        else os.path.join(os.path.expanduser("~"), ".config", "WebWeaverKit")
    _settings_path = os.path.join(_settings_dir, "settings.json")
    try:
        with open(_settings_path, 'r') as f:
            _data = json.load(f)
            _scheme = _data.get("color_scheme", "Synthetic Atelier")
            if _scheme in COLOR_SCHEMES:
                set_color_scheme(_scheme)
    except Exception:
        pass

_load_saved_scheme()

from theme import (
    SURFACE, SURFACE_CONTAINER, SURFACE_CONTAINER_LOW, SURFACE_CONTAINER_HIGH,
    SURFACE_CONTAINER_HIGHEST, SURFACE_CONTAINER_LOWEST,
    PRIMARY, PRIMARY_CONTAINER, SECONDARY, SECONDARY_CONTAINER,
    ON_PRIMARY, ON_SURFACE, ON_SURFACE_VARIANT, OUTLINE_VARIANT,
    TERTIARY, ERROR,
    FONT_FAMILY, DISPLAY_SM, TITLE_LG, TITLE_MD, TITLE_SM, BODY, BODY_SM, LABEL_SM,
    SP_1, SP_2, SP_4, SP_6, SP_8, SP_10,
    apply_atelier_theme, Tooltip,
)
from imageConverter import ImageConverterGUI
from fileRenamer import FileRenamerGUI
from pdfToImage import pdfToImageGUI
from VideoConverterGUI import VideoConverterGUI
from textFormatter import TextFormatterGUI
from svgCircleGenerator import SVGCircleGeneratorGUI

GITHUB_REPO = "mrzeappleGit/convertToWebP"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
currentVersion = "1.10.0"

headers = {
    'User-Agent': f'WebWeaverKit/{currentVersion}',
    'Accept': 'application/vnd.github.v3+json',
}


def apply_theme_to_titlebar(tk_window):
    if sys.platform != "win32":
        return
    try:
        hwnd = ctypes.windll.user32.GetParent(tk_window.winfo_id())
        if not hwnd:
            return
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.wintypes.BOOL(1)),
            ctypes.sizeof(ctypes.wintypes.BOOL),
        )
    except Exception:
        pass


APP_NAME = "WebWeaverKit"
SETTINGS_FILENAME = "settings.json"


def get_settings_dir():
    if sys.platform == "win32":
        app_data_dir = os.getenv('APPDATA')
        if app_data_dir:
            return os.path.join(app_data_dir, APP_NAME)
    return os.path.join(os.path.expanduser("~"), ".config", APP_NAME)


def get_settings_path():
    return os.path.join(get_settings_dir(), SETTINGS_FILENAME)


def load_settings():
    settings_path = get_settings_path()
    default_settings = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default_settings
    return default_settings


def save_settings(settings_data):
    settings_dir = get_settings_dir()
    os.makedirs(settings_dir, exist_ok=True)
    settings_path = get_settings_path()
    try:
        with open(settings_path, 'w') as f:
            json.dump(settings_data, f, indent=4)
    except IOError as e:
        print(f"Error saving settings to {settings_path}: {e}")


class HyperlinkManager:
    def __init__(self, text):
        self.text = text
        self.text.tag_config("hyper", foreground=SECONDARY, underline=1)
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
        index = self.text.index(f"@{event.x},{event.y}")
        for tag in self.text.tag_names(index):
            if tag.startswith("hyper-"):
                url = self.links.get(tag)
                if url:
                    try:
                        webbrowser.open(url)
                    except Exception:
                        pass
                    return


# ---------------------------------------------------------------------------
# Tab button with tonal hover / SECONDARY active underline
# ---------------------------------------------------------------------------
class TabButton(tk.Frame):
    """Horizontal tab: icon + label, SECONDARY underline when active, tonal hover."""

    def __init__(self, parent, text, icon, command, **kw):
        super().__init__(parent, bg=SURFACE_CONTAINER_LOW, **kw)
        self._command = command
        self._active = False

        self._label = tk.Label(
            self,
            text=f" {icon}  {text}",
            font=BODY,
            fg=ON_SURFACE_VARIANT,
            bg=SURFACE_CONTAINER_LOW,
            cursor="hand2",
            padx=SP_4,
            pady=SP_2,
        )
        self._label.pack(side="top", fill="x")
        self._label.bind("<Button-1>", self._on_click)
        self._label.bind("<Enter>", self._on_enter)
        self._label.bind("<Leave>", self._on_leave)

        self._indicator = tk.Frame(self, height=2, bg=SURFACE_CONTAINER_LOW)
        self._indicator.pack(side="bottom", fill="x")

    def _on_click(self, _event=None):
        if not self._active and self._command:
            self._command()

    def _on_enter(self, _event=None):
        if not self._active:
            self._label.configure(bg=SURFACE_CONTAINER_HIGH, fg=ON_SURFACE)

    def _on_leave(self, _event=None):
        if not self._active:
            self._label.configure(bg=SURFACE_CONTAINER_LOW, fg=ON_SURFACE_VARIANT)

    def set_active(self, active: bool):
        self._active = active
        if active:
            self._indicator.configure(bg=SECONDARY)
            self._label.configure(
                font=TITLE_SM, fg=ON_SURFACE, bg=SURFACE_CONTAINER_LOW, cursor="arrow",
            )
        else:
            self._indicator.configure(bg=SURFACE_CONTAINER_LOW)
            self._label.configure(
                font=BODY, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_LOW, cursor="hand2",
            )


class MainApp(tk.Tk):
    @staticmethod
    def get_resource_path(relative_path):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)

    def __init__(self):
        super().__init__()
        self.update_idletasks()

        self.app_settings = load_settings()
        self.title("Web Weaver Kit")

        # Apply the Atelier theme (scheme already set at module load time)
        self.style = apply_atelier_theme(self)

        try:
            iconPath = MainApp.get_resource_path('convertToWebPIcon.ico')
            if os.path.exists(iconPath):
                self.iconbitmap(iconPath)
        except tk.TclError:
            try:
                pngIconPath = MainApp.get_resource_path('convertToWebPLogo.png')
                if os.path.exists(pngIconPath):
                    img = tk.PhotoImage(file=pngIconPath)
                    self.iconphoto(True, img)
            except Exception:
                pass
        except Exception:
            pass

        self.resizable(True, True)
        self.minsize(960, 640)
        self.configure(bg=SURFACE)

        self.update_idletasks()
        apply_theme_to_titlebar(self)

        # ── Tab bar (SURFACE_CONTAINER_LOW structural section) ────
        self.tab_bar_frame = tk.Frame(self, bg=SURFACE_CONTAINER_LOW)
        self.tab_bar_frame.pack(side="top", fill="x")

        tab_inner = tk.Frame(self.tab_bar_frame, bg=SURFACE_CONTAINER_LOW)
        tab_inner.pack(side="left", fill="x", expand=True, padx=SP_2, pady=(SP_2, 0))

        button_defs = [
            ("Converter",          "\u2B9F",  self.show_image_converter, "image_converter"),
            ("File Renamer",       "\u270F",  self.show_file_renamer,    "file_renamer"),
            ("PDF to Image",       "\u2B07",  self.show_pdf_to_image,    "pdf_to_image"),
            ("Video Converter",    "\u25B6",  self.show_video_converter, "video_converter"),
            ("Text Formatter",     "Aa",      self.show_text_converter,  "text_formatter"),
            ("Image Mapping",      "\u25CE",  self.show_svg_generator,   "svg_generator"),
        ]

        self.tab_buttons = {}
        for text, icon, command, name in button_defs:
            tab = TabButton(tab_inner, text=text, icon=icon, command=command)
            tab.pack(side="left", padx=1)
            self.tab_buttons[name] = tab

        self.menu_button = ttk.Button(
            self.tab_bar_frame, text="\u2261", command=self.show_menu,
            width=4, style="Menu.TButton",
        )
        self.menu_button.pack(side="right", padx=SP_4, pady=SP_2)

        # ── Content area (SURFACE_CONTAINER) ──────────────────────
        self.content_frame = tk.Frame(self, bg=SURFACE_CONTAINER)
        self.content_frame.pack(side="top", fill="both", expand=True)

        self.frames = {}
        self.frame_classes = {
            "image_converter": ImageConverterGUI,
            "file_renamer":    FileRenamerGUI,
            "pdf_to_image":    pdfToImageGUI,
            "video_converter": VideoConverterGUI,
            "text_formatter":  TextFormatterGUI,
            "svg_generator":   SVGCircleGeneratorGUI,
        }

        self.current_frame_name = "image_converter"
        self._get_or_create_frame(self.current_frame_name).pack(
            in_=self.content_frame, fill="both", expand=True, padx=SP_8, pady=SP_8,
        )
        self.tab_buttons[self.current_frame_name].set_active(True)

        # ── Updates & menu ────────────────────────────────────────
        self.update_available = False
        self.download_url = ""
        self.check_for_updates_at_start()

        import theme as _t
        self.dropdown_menu = tk.Menu(
            self, tearoff=0,
            bg=_t.SURFACE_CONTAINER_HIGHEST, fg=_t.ON_SURFACE,
            activebackground=_t.SURFACE_CONTAINER_HIGH, activeforeground=_t.ON_SURFACE,
            borderwidth=0, relief="flat", font=BODY,
        )
        self.update_dropdown_menu()
        self.update_menu_button_text()

        self.after(12 * 60 * 60 * 1000, self.periodic_check_for_updates)

    # ── Frame management ──────────────────────────────────────────

    def _get_or_create_frame(self, name):
        if name not in self.frames:
            self.frames[name] = self.frame_classes[name](self)
        return self.frames[name]

    def _switch_frame(self, target_frame_name):
        if target_frame_name == self.current_frame_name:
            return

        if self.current_frame_name and self.current_frame_name in self.frames:
            self.frames[self.current_frame_name].pack_forget()

        self.current_frame_name = target_frame_name
        self._get_or_create_frame(self.current_frame_name).pack(
            in_=self.content_frame, fill="both", expand=True, padx=SP_8, pady=SP_8,
        )

        for name, tab in self.tab_buttons.items():
            tab.set_active(name == self.current_frame_name)

    def show_image_converter(self):  self._switch_frame("image_converter")
    def show_file_renamer(self):     self._switch_frame("file_renamer")
    def show_pdf_to_image(self):     self._switch_frame("pdf_to_image")
    def show_video_converter(self):  self._switch_frame("video_converter")
    def show_text_converter(self):   self._switch_frame("text_formatter")
    def show_svg_generator(self):    self._switch_frame("svg_generator")

    # ── Menu ──────────────────────────────────────────────────────

    def show_menu(self):
        self.update_dropdown_menu()
        try:
            x = self.menu_button.winfo_rootx()
            y = self.menu_button.winfo_rooty() + self.menu_button.winfo_height()
            self.dropdown_menu.tk_popup(x, y)
        finally:
            self.dropdown_menu.grab_release()

    def check_for_updates_at_start(self):
        threading.Thread(target=self._bg_check_update, daemon=True).start()

    def _bg_check_update(self):
        available, url = is_update_available(currentVersion)
        self.after(0, lambda: self._on_update_check_complete(available, url))

    def _on_update_check_complete(self, available, url):
        self.update_available = available
        self.download_url = url
        self.update_menu_button_text()
        self.update_dropdown_menu()

    def update_menu_button_text(self):
        btn_text = "\u2261"
        if self.update_available:
            btn_text = "\u2022 " + btn_text
        self.menu_button.config(text=btn_text)

    def update_dropdown_menu(self):
        self.dropdown_menu.delete(0, tk.END)

        # Theme submenu
        import theme as _t
        theme_menu = tk.Menu(
            self.dropdown_menu, tearoff=0,
            bg=_t.SURFACE_CONTAINER_HIGHEST, fg=_t.ON_SURFACE,
            activebackground=_t.SURFACE_CONTAINER_HIGH, activeforeground=_t.ON_SURFACE,
            borderwidth=0, relief="flat", font=BODY,
        )
        current_scheme = get_active_scheme_name()
        for scheme_name in COLOR_SCHEMES:
            prefix = "\u2713  " if scheme_name == current_scheme else "    "
            theme_menu.add_command(
                label=prefix + scheme_name,
                command=lambda s=scheme_name: self._change_color_scheme(s),
            )
        self.dropdown_menu.add_cascade(label="Theme", menu=theme_menu)
        self.dropdown_menu.add_separator()

        lbl = "\u2022  Update Available" if self.update_available else "Check for Updates"
        self.dropdown_menu.add_command(label=lbl, command=self.check_and_update)
        self.dropdown_menu.add_command(label="About", command=self.show_about)
        self.dropdown_menu.add_command(label="Licenses", command=self.show_licenses)

    def _change_color_scheme(self, scheme_name):
        """Save the chosen color scheme and restart the app via subprocess."""
        self.app_settings["color_scheme"] = scheme_name
        save_settings(self.app_settings)
        # Launch a fresh process and exit this one cleanly
        import sys
        subprocess.Popen([sys.executable] + sys.argv)
        self.quit()

    # ── About dialog ──────────────────────────────────────────────

    def show_about(self):
        about_win = tk.Toplevel(self, bg=SURFACE_CONTAINER_HIGH)
        about_win.title("About")
        about_win.transient(self)
        about_win.grab_set()
        about_win.resizable(False, False)
        about_win.geometry("420x380")
        about_win.update_idletasks()
        apply_theme_to_titlebar(about_win)

        try:
            iconPath = MainApp.get_resource_path('convertToWebPIcon.ico')
            if os.path.exists(iconPath):
                about_win.iconbitmap(iconPath)
        except Exception:
            pass

        card = tk.Frame(about_win, bg=SURFACE_CONTAINER_HIGH, padx=SP_10, pady=SP_10)
        card.pack(fill=BOTH, expand=YES)

        # Logo area with decorative glow backdrop
        logo_area = tk.Frame(card, bg=SURFACE_CONTAINER_HIGH)
        logo_area.pack(pady=(0, SP_4))

        # Glow frame: tonal layer behind the logo for depth
        glow_frame = tk.Frame(logo_area, bg=PRIMARY, padx=2, pady=2)
        glow_frame.pack()
        glow_inner = tk.Frame(glow_frame, bg=SURFACE_CONTAINER_HIGH, padx=SP_2, pady=SP_2)
        glow_inner.pack()

        # Decorative canvas circle behind the logo
        canvas_size = 96
        logo_canvas = tk.Canvas(
            glow_inner, width=canvas_size, height=canvas_size,
            bg=SURFACE_CONTAINER_HIGH, highlightthickness=0,
        )
        logo_canvas.pack()
        # Draw a subtle primary-colored circle as backdrop
        logo_canvas.create_oval(
            8, 8, canvas_size - 8, canvas_size - 8,
            fill=SURFACE_CONTAINER, outline=PRIMARY, width=2,
        )

        try:
            image_path = MainApp.get_resource_path('convertToWebPLogo.png')
            if os.path.exists(image_path):
                logo_pil = Image.open(image_path).resize((80, 80), Image.Resampling.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_pil)
                logo_canvas.create_image(
                    canvas_size // 2, canvas_size // 2,
                    image=logo_photo, anchor="center",
                )
                logo_canvas.image = logo_photo
        except Exception:
            pass

        # Title with DISPLAY_SM typography
        tk.Label(
            card, text="Web Weaver Kit", font=DISPLAY_SM,
            fg=ON_SURFACE, bg=SURFACE_CONTAINER_HIGH,
        ).pack(pady=(0, SP_1))

        tk.Label(
            card, text=f"Version {currentVersion}", font=BODY_SM,
            fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_HIGH,
        ).pack(pady=(0, SP_8))

        # Copyright
        cr = tk.Label(
            card, text="\u00A92025 Matthew Thomas Stevens Studios LLC",
            font=LABEL_SM, fg=ON_SURFACE_VARIANT, bg=SURFACE_CONTAINER_HIGH, cursor="hand2",
        )
        cr.pack(pady=SP_1)
        cr.bind("<Button-1>", lambda e: webbrowser.open("https://www.matthewstevens.me"))

        # GitHub link
        link = tk.Label(
            card, text="GitHub Repository \u2197",
            font=(FONT_FAMILY, 9, "underline"), fg=SECONDARY,
            bg=SURFACE_CONTAINER_HIGH, cursor="hand2",
        )
        link.pack(pady=SP_1)
        link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/mrzeappleGit/convertToWebP"))

        # Check for Updates link
        update_link = tk.Label(
            card, text="Check for Updates",
            font=(FONT_FAMILY, 9, "underline"), fg=SECONDARY,
            bg=SURFACE_CONTAINER_HIGH, cursor="hand2",
        )
        update_link.pack(pady=(SP_2, 0))
        update_link.bind("<Button-1>", lambda e: self.check_and_update())

        about_win.update_idletasks()
        mx, my = self.winfo_rootx(), self.winfo_rooty()
        mw, mh = self.winfo_width(), self.winfo_height()
        pw, ph = about_win.winfo_width(), about_win.winfo_height()
        about_win.geometry(f"+{mx + (mw - pw) // 2}+{my + (mh - ph) // 2}")
        about_win.protocol("WM_DELETE_WINDOW", lambda: (about_win.grab_release(), about_win.destroy()))

    # ── Licenses dialog ───────────────────────────────────────────

    def show_licenses(self):
        lw = tk.Toplevel(self, bg=SURFACE_CONTAINER)
        lw.title("Licenses")
        lw.geometry("720x520")
        lw.transient(self)
        lw.grab_set()
        lw.update_idletasks()
        apply_theme_to_titlebar(lw)

        notebook = ttk.Notebook(lw)
        notebook.pack(expand=True, fill="both", padx=SP_4, pady=SP_4)

        licenses = {
            "FFmpeg": {
                "text": "This software uses libraries from the FFmpeg project under the LGPLv2.1.",
                "link": {'text': "\n\nView license: http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html",
                         'url': "http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html"}
            },
            "JPEG XL": {
                "text": "This software includes the JPEG XL codec (libjxl) under the BSD 3-Clause License.\n\nCopyright (c) the JPEG XL Project Authors. All rights reserved.\n\nRedistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:\n\n1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.\n\n2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.\n\n3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.\n\nTHIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS \"AS IS\" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
            },
            "Pillow": {
                "text": "The Python Imaging Library (Pillow) is licensed under the HPND License.\n\nCopyright \u00A9 1997-2011 by Secret Labs AB\nCopyright \u00A9 1995-2011 by Fredrik Lundh\nCopyright \u00A9 2010-2024 by Alex Clark and contributors\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the \"Software\"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT."
            },
            "sv-ttk": {
                "text": "Sun Valley ttk Theme (sv-ttk) is licensed under the MIT License.\n\nCopyright (c) 2021 rdbende\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the \"Software\"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:\n\nThe above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT."
            },
        }

        for key, data in licenses.items():
            tab_frame = ttk.Frame(notebook)
            notebook.add(tab_frame, text=f"  {key}  ")

            tw = tk.Text(
                tab_frame, wrap="word", font=BODY, height=15, relief="flat",
                bg=SURFACE_CONTAINER_LOWEST, fg=ON_SURFACE,
                borderwidth=0, highlightthickness=0,
                insertbackground=ON_SURFACE, selectbackground=SECONDARY_CONTAINER,
            )
            sb = ttk.Scrollbar(tab_frame, orient="vertical", command=tw.yview)
            tw.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            tw.pack(side="left", expand=True, fill="both", padx=SP_2, pady=SP_2)

            hyperlink = HyperlinkManager(tw)
            tw.insert("1.0", data["text"])
            link_info = data.get("link")
            if link_info:
                tw.insert("end", link_info["text"], hyperlink.add(link_info["url"]))
            tw.config(state="disabled")

        lw.update_idletasks()
        mx, my = self.winfo_rootx(), self.winfo_rooty()
        mw, mh = self.winfo_width(), self.winfo_height()
        pw, ph = lw.winfo_width(), lw.winfo_height()
        lw.geometry(f"+{mx + (mw - pw) // 2}+{my + (mh - ph) // 2}")
        lw.protocol("WM_DELETE_WINDOW", lambda: (lw.grab_release(), lw.destroy()))

    # ── Periodic updates ──────────────────────────────────────────

    def periodic_check_for_updates(self):
        self.check_for_updates_at_start()
        self.after(12 * 60 * 60 * 1000, self.periodic_check_for_updates)

    def check_and_update(self):
        """Non-blocking update check with themed progress dialog."""
        import theme as _t

        # Show a small "Checking..." dialog
        dlg = tk.Toplevel(self, bg=_t.SURFACE_CONTAINER_HIGH)
        dlg.title("Update")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)
        dlg.geometry("360x160")
        dlg.update_idletasks()
        apply_theme_to_titlebar(dlg)
        # Center on parent
        mx, my = self.winfo_rootx(), self.winfo_rooty()
        mw, mh = self.winfo_width(), self.winfo_height()
        dlg.geometry(f"+{mx + (mw - 360) // 2}+{my + (mh - 160) // 2}")

        card = tk.Frame(dlg, bg=_t.SURFACE_CONTAINER_HIGH, padx=SP_10, pady=SP_8)
        card.pack(fill=BOTH, expand=YES)

        status_label = tk.Label(card, text="Checking for updates\u2026", font=BODY,
                                fg=_t.ON_SURFACE, bg=_t.SURFACE_CONTAINER_HIGH)
        status_label.pack(pady=(0, SP_4))

        progress_var = tk.DoubleVar(value=0)
        progress_bar = ttk.Progressbar(card, orient="horizontal", mode="indeterminate",
                                       variable=progress_var, length=280)
        progress_bar.pack(pady=(0, SP_4))
        progress_bar.start(15)

        pct_label = tk.Label(card, text="", font=LABEL_SM,
                             fg=_t.ON_SURFACE_VARIANT, bg=_t.SURFACE_CONTAINER_HIGH)
        pct_label.pack()

        cancel_flag = {"cancelled": False}

        def _cancel():
            cancel_flag["cancelled"] = True
            dlg.destroy()

        dlg.protocol("WM_DELETE_WINDOW", _cancel)

        def _do_check():
            available, url = is_update_available(currentVersion)
            if cancel_flag["cancelled"]:
                return
            self.after(0, lambda: _on_check_done(available, url))

        def _on_check_done(available, url):
            self.update_available = available
            self.download_url = url
            self.update_menu_button_text()
            self.update_dropdown_menu()

            if not available:
                status_label.config(text="You are using the latest version.")
                progress_bar.stop()
                progress_bar.config(mode="determinate")
                progress_var.set(100)
                pct_label.config(text="")
                dlg.after(1500, dlg.destroy)
                return

            if not url or not url.startswith(('http://', 'https://')):
                status_label.config(text="Update available but invalid URL.")
                progress_bar.stop()
                dlg.after(2000, dlg.destroy)
                return

            # Ask user
            progress_bar.stop()
            try:
                filename = os.path.basename(url)
            except Exception:
                filename = "update"
            status_label.config(text=f"Update available: {filename}")
            progress_bar.config(mode="determinate")
            progress_var.set(0)
            pct_label.config(text="Ready to download")

            btn_frame = tk.Frame(card, bg=_t.SURFACE_CONTAINER_HIGH)
            btn_frame.pack(pady=(SP_4, 0))
            ttk.Button(btn_frame, text="Download & Install",
                       command=lambda: _start_download(url),
                       style="Primary.TButton").pack(side="left", padx=(0, SP_2))
            ttk.Button(btn_frame, text="Later",
                       command=dlg.destroy).pack(side="left")

        def _start_download(url):
            status_label.config(text="Downloading\u2026")
            pct_label.config(text="0%")
            # Remove buttons
            for w in card.winfo_children():
                if isinstance(w, tk.Frame) and w is not card:
                    w.destroy()
            threading.Thread(target=_download_worker, args=(url,), daemon=True).start()

        def _download_worker(url):
            download_path = os.path.join(_get_current_dir(), 'latest_app_update.exe')
            try:
                resp = requests.get(url, stream=True, headers=headers, timeout=300)
                resp.raise_for_status()
                total = int(resp.headers.get('content-length', 0))
                downloaded = 0
                with open(download_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if cancel_flag["cancelled"]:
                            f.close()
                            _cleanup_file(download_path)
                            return
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = downloaded / total * 100
                            self.after(0, lambda p=pct, d=downloaded, t=total:
                                       _update_download_progress(p, d, t))
                self.after(0, lambda: _on_download_complete(download_path))
            except Exception as e:
                if not cancel_flag["cancelled"]:
                    self.after(0, lambda: _on_download_error(str(e)))
                _cleanup_file(download_path)

        def _update_download_progress(pct, downloaded, total):
            if cancel_flag["cancelled"]:
                return
            progress_var.set(pct)
            dl_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            pct_label.config(text=f"{pct:.0f}%  ({dl_mb:.1f} / {total_mb:.1f} MB)")
            status_label.config(text="Downloading\u2026")

        def _on_download_complete(download_path):
            status_label.config(text="Installing update\u2026")
            pct_label.config(text="Restarting app")
            progress_var.set(100)
            if _apply_update(download_path):
                dlg.after(500, self.quit)
            else:
                status_label.config(text="Failed to apply update.")
                pct_label.config(text="")

        def _on_download_error(error_msg):
            status_label.config(text="Download failed")
            pct_label.config(text=error_msg[:60])
            progress_var.set(0)

        threading.Thread(target=_do_check, daemon=True).start()


# ══════════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════════

def _get_current_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _cleanup_file(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _apply_update(update_exe_path):
    """Replace the running exe via a helper batch script and restart."""
    current_dir = _get_current_dir()
    helper_bat = os.path.join(current_dir, 'update_helper.bat')
    exe_name = os.path.basename(sys.executable)
    target = os.path.join(current_dir, exe_name)
    log_path = os.path.join(current_dir, 'update_log.txt')

    if not os.path.exists(update_exe_path):
        return False

    try:
        with open(helper_bat, 'w') as f:
            f.write("@echo off\n")
            f.write(f'echo [%DATE% %TIME%] Starting update > "{log_path}"\n')
            f.write("timeout /t 2 /nobreak > NUL\n")
            f.write(f'taskkill /IM "{exe_name}" /F > NUL 2>&1\n')
            f.write("timeout /t 1 /nobreak > NUL\n")
            f.write(f'move /Y "{update_exe_path}" "{target}"\n')
            f.write(f'if %errorlevel% NEQ 0 (\n')
            f.write(f'  echo [%DATE% %TIME%] Move failed >> "{log_path}"\n')
            f.write(f'  del "{update_exe_path}" > NUL 2>&1\n')
            f.write("  goto end\n)\n")
            f.write(f'echo [%DATE% %TIME%] Update applied >> "{log_path}"\n')
            f.write(f'start "" "{target}"\n')
            f.write(":end\n")
            f.write('(goto) 2>nul & del "%~f0"\n')

        flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(['cmd.exe', '/c', helper_bat], creationflags=flags,
                         close_fds=True, cwd=current_dir)
        return True
    except Exception:
        _cleanup_file(helper_bat)
        return False


def _parse_version(v):
    """Strip leading 'v' and split into int tuple: 'v1.10.0' -> (1, 10, 0)."""
    return tuple(map(int, v.lstrip('vV').split('.')))


def is_update_available(current_v):
    """Check GitHub Releases for a newer version. Returns (bool, download_url)."""
    try:
        resp = requests.get(GITHUB_API_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        release = resp.json()

        tag = release.get('tag_name', '')
        if not tag:
            return False, ""

        if _parse_version(tag) <= _parse_version(current_v):
            return False, ""

        # Find the .exe asset in the release
        for asset in release.get('assets', []):
            name = asset.get('name', '').lower()
            if name.endswith('.exe'):
                return True, asset.get('browser_download_url', '')

        # No exe found — fall back to the release page itself
        html_url = release.get('html_url', '')
        if html_url:
            return True, html_url

        return False, ""
    except Exception:
        return False, ""


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = MainApp()
    app.mainloop()

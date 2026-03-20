import time
import tkinter as tk
from tkinter import ttk, filedialog
import os
import subprocess
import sys
import threading
import re

from theme import (
    SURFACE, SURFACE_CONTAINER, SURFACE_CONTAINER_LOW, SURFACE_CONTAINER_HIGH,
    SURFACE_CONTAINER_HIGHEST, SURFACE_CONTAINER_LOWEST,
    PRIMARY, PRIMARY_CONTAINER, SECONDARY, SECONDARY_CONTAINER,
    ON_PRIMARY, ON_SURFACE, ON_SURFACE_VARIANT, OUTLINE_VARIANT,
    TERTIARY, ERROR,
    FONT_FAMILY, DISPLAY_SM, TITLE_LG, TITLE_MD, TITLE_SM, BODY, BODY_SM, LABEL_SM, LABEL_SM_MONO,
    SP_1, SP_2, SP_4, SP_6, SP_8, SP_10,
    apply_atelier_theme, Tooltip, create_section, PillSelector, StatusDot,
)


# Default CRF values per video codec
_DEFAULT_CRF = {
    "libx264": 23,
    "libx265": 28,
    "libvpx-vp9": 31,
}

# Codec maps keyed by format
_VIDEO_CODECS = {
    "mp4": [("libx264", "H.264"), ("libx265", "H.265 (HEVC)")],
    "webm": [("libvpx-vp9", "VP9")],
}

_AUDIO_CODECS = [("aac", "AAC"), ("libopus", "Opus")]

_FORMAT_DEFAULTS = {
    "mp4":  ("libx264", "aac"),
    "webm": ("libvpx-vp9", "libopus"),
}


class VideoConverterGUI(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self.folder_path = tk.StringVar()
        self.destination_folder_path = tk.StringVar()
        self.video_codec_var = tk.StringVar()
        self.audio_codec_var = tk.StringVar()
        self.crf_var = tk.IntVar(value=23)
        self._converting = False

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)

        # ════════════════════════════════════════════════════════════
        # LEFT PANEL -- controls
        # ════════════════════════════════════════════════════════════
        left = tk.Frame(self, bg=SURFACE_CONTAINER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, SP_4))

        # ── Source ─────────────────────────────────────────────────
        src_wrap, src = create_section(left, "SOURCE")
        src_wrap.pack(fill="x", pady=(0, SP_8))
        src.grid_columnconfigure(1, weight=1)

        tk.Label(
            src, text="Video File", font=BODY, fg=ON_SURFACE,
            bg=SURFACE_CONTAINER_LOW,
        ).grid(row=0, column=0, sticky="w", padx=(0, SP_2), pady=SP_1)
        ttk.Entry(src, textvariable=self.folder_path).grid(
            row=0, column=1, sticky="ew", pady=SP_1,
        )
        ttk.Button(
            src, text="Browse\u2026", command=self.select_file,
            style="Tertiary.TButton",
        ).grid(row=0, column=2, padx=(SP_2, 0), pady=SP_1)

        # ── Destination ────────────────────────────────────────────
        dst_wrap, dst = create_section(left, "DESTINATION")
        dst_wrap.pack(fill="x", pady=(0, SP_8))
        dst.grid_columnconfigure(1, weight=1)

        tk.Label(
            dst, text="Output Folder", font=BODY, fg=ON_SURFACE,
            bg=SURFACE_CONTAINER_LOW,
        ).grid(row=0, column=0, sticky="w", padx=(0, SP_2), pady=SP_1)
        ttk.Entry(dst, textvariable=self.destination_folder_path).grid(
            row=0, column=1, sticky="ew", pady=SP_1,
        )
        ttk.Button(
            dst, text="Browse\u2026", command=self.destination_select_folder,
            style="Tertiary.TButton",
        ).grid(row=0, column=2, padx=(SP_2, 0), pady=SP_1)

        # ── Output Format ──────────────────────────────────────────
        fmt_wrap, fmt_body = create_section(left, "OUTPUT FORMAT")
        fmt_wrap.pack(fill="x", pady=(0, SP_8))

        self.format_pills = PillSelector(
            fmt_body,
            options=[("mp4", "MP4"), ("webm", "WebM")],
            default="mp4",
            command=self._on_format_change,
        )
        self.format_pills.pack(anchor="w")

        # ── Encoding ───────────────────────────────────────────────
        enc_wrap, enc = create_section(left, "ENCODING")
        enc_wrap.pack(fill="x", pady=(0, SP_8))

        # Video codec
        tk.Label(
            enc, text="Video Codec", font=BODY, fg=ON_SURFACE,
            bg=SURFACE_CONTAINER_LOW,
        ).grid(row=0, column=0, sticky="w", padx=(0, SP_2), pady=SP_1)
        self.video_codec_combo = ttk.Combobox(
            enc, textvariable=self.video_codec_var, state="readonly", width=18,
        )
        self.video_codec_combo.grid(row=0, column=1, sticky="w", pady=SP_1)
        self.video_codec_combo.bind("<<ComboboxSelected>>", self._on_video_codec_change)

        # Audio codec
        tk.Label(
            enc, text="Audio Codec", font=BODY, fg=ON_SURFACE,
            bg=SURFACE_CONTAINER_LOW,
        ).grid(row=1, column=0, sticky="w", padx=(0, SP_2), pady=SP_1)
        self.audio_codec_combo = ttk.Combobox(
            enc, textvariable=self.audio_codec_var, state="readonly", width=18,
        )
        self.audio_codec_combo.grid(row=1, column=1, sticky="w", pady=SP_1)
        self.audio_codec_combo["values"] = [label for _, label in _AUDIO_CODECS]

        # CRF quality
        crf_label = tk.Label(
            enc, text="Quality (CRF)", font=BODY, fg=ON_SURFACE,
            bg=SURFACE_CONTAINER_LOW,
        )
        crf_label.grid(row=2, column=0, sticky="w", padx=(0, SP_2), pady=SP_1)

        crf_frame = tk.Frame(enc, bg=SURFACE_CONTAINER_LOW)
        crf_frame.grid(row=2, column=1, sticky="ew", pady=SP_1)
        crf_frame.grid_columnconfigure(0, weight=1)

        self.crf_slider = ttk.Scale(
            crf_frame, from_=0, to=51, orient="horizontal",
            variable=self.crf_var, command=self._on_crf_slide,
        )
        self.crf_slider.grid(row=0, column=0, sticky="ew")

        self.crf_value_label = tk.Label(
            crf_frame, text="23", font=LABEL_SM_MONO, fg=ON_SURFACE,
            bg=SURFACE_CONTAINER_LOW, width=4, anchor="e",
        )
        self.crf_value_label.grid(row=0, column=1, padx=(SP_2, 0))

        # Resolution
        tk.Label(
            enc, text="Resolution", font=BODY, fg=ON_SURFACE,
            bg=SURFACE_CONTAINER_LOW,
        ).grid(row=3, column=0, sticky="w", padx=(0, SP_2), pady=(SP_4, SP_1))
        res_frame = tk.Frame(enc, bg=SURFACE_CONTAINER_LOW)
        res_frame.grid(row=3, column=1, sticky="w", pady=(SP_4, SP_1))

        self.resolution_pills = PillSelector(
            res_frame,
            options=[
                ("original", "Original"),
                ("1080", "1080p"),
                ("720", "720p"),
                ("480", "480p"),
            ],
            default="original",
        )
        self.resolution_pills.pack(anchor="w")

        # ── Convert button + progress ──────────────────────────────
        action = tk.Frame(left, bg=SURFACE_CONTAINER)
        action.pack(fill="x", pady=(0, SP_2))

        ttk.Button(
            action, text="\u25B6  Convert", command=self.convert_video,
            style="Primary.TButton",
        ).pack(side="left")

        self.estimated_time_label = tk.Label(
            action, text="", font=LABEL_SM, fg=ON_SURFACE_VARIANT,
            bg=SURFACE_CONTAINER,
        )
        self.estimated_time_label.pack(side="right")

        self.video_progress = ttk.Progressbar(
            left, orient="horizontal", mode="determinate", value=0,
        )
        self.video_progress.pack(fill="x")

        # ════════════════════════════════════════════════════════════
        # RIGHT PANEL -- ffmpeg log
        # ════════════════════════════════════════════════════════════
        right = tk.Frame(self, bg=SURFACE_CONTAINER)
        right.grid(row=0, column=1, sticky="nsew")

        log_wrap, log_body = create_section(right, "FFMPEG LOG")
        log_wrap.pack(fill="both", expand=True)
        log_body.pack_configure(fill="both", expand=True)

        self.log_text = tk.Text(
            log_body,
            bg=SURFACE_CONTAINER_LOWEST,
            fg=ON_SURFACE_VARIANT,
            font=LABEL_SM_MONO,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            wrap="word",
            state="disabled",
            padx=SP_4,
            pady=SP_2,
        )
        log_scrollbar = ttk.Scrollbar(log_body, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        log_scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        # ── Apply initial format defaults ──────────────────────────
        self._on_format_change("mp4")

    # ================================================================
    # Helpers
    # ================================================================

    def resource_path(self, relative_path):
        try:
            base = sys._MEIPASS
        except Exception:
            base = os.path.abspath(".")
        return os.path.join(base, relative_path)

    def _log_append(self, text):
        """Thread-safe append to the log viewer."""
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _log_clear(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ================================================================
    # Codec / format linkage
    # ================================================================

    def _on_format_change(self, fmt):
        """Update codec dropdowns when the output format changes."""
        # Video codecs
        entries = _VIDEO_CODECS.get(fmt, _VIDEO_CODECS["mp4"])
        self.video_codec_combo["values"] = [label for _, label in entries]

        # Set defaults
        default_vc, default_ac = _FORMAT_DEFAULTS.get(fmt, _FORMAT_DEFAULTS["mp4"])
        # Select matching display label
        for codec_id, label in entries:
            if codec_id == default_vc:
                self.video_codec_var.set(label)
                break

        for codec_id, label in _AUDIO_CODECS:
            if codec_id == default_ac:
                self.audio_codec_var.set(label)
                break

        # Update CRF default for the new video codec
        self.crf_var.set(_DEFAULT_CRF.get(default_vc, 23))
        self.crf_value_label.configure(text=str(self.crf_var.get()))

    def _on_video_codec_change(self, event=None):
        """Adjust CRF default when the user manually switches video codec."""
        codec_id = self._get_video_codec_id()
        if codec_id in _DEFAULT_CRF:
            self.crf_var.set(_DEFAULT_CRF[codec_id])
            self.crf_value_label.configure(text=str(self.crf_var.get()))

    def _on_crf_slide(self, value):
        self.crf_value_label.configure(text=str(int(float(value))))

    def _get_video_codec_id(self):
        """Resolve display label back to ffmpeg codec identifier."""
        label = self.video_codec_var.get()
        fmt = self.format_pills.get()
        for codec_id, display in _VIDEO_CODECS.get(fmt, []):
            if display == label:
                return codec_id
        return "libx264"

    def _get_audio_codec_id(self):
        label = self.audio_codec_var.get()
        for codec_id, display in _AUDIO_CODECS:
            if display == label:
                return codec_id
        return "aac"

    # ================================================================
    # File / folder selection
    # ================================================================

    def select_file(self):
        f = filedialog.askopenfilename(
            title="Select a video file",
            filetypes=(
                ("Video Files", "*.webm *.mp4 *.mov *.mkv *.avi"),
                ("All files", "*.*"),
            ),
        )
        if f:
            self.folder_path.set(f)

    def destination_select_folder(self):
        d = filedialog.askdirectory(title="Select Destination Folder")
        if d:
            self.destination_folder_path.set(d)

    # ================================================================
    # Conversion
    # ================================================================

    def convert_video(self):
        if self._converting:
            return
        if not self.folder_path.get():
            self.estimated_time_label["text"] = "Select an input file."
            return
        if not self.destination_folder_path.get():
            self.estimated_time_label["text"] = "Select a destination folder."
            return
        threading.Thread(target=self.start_conversion, daemon=True).start()

    def update_gui(self, progress, eta):
        self.video_progress["value"] = progress
        if eta >= 0:
            m, s = divmod(int(eta), 60)
            self.estimated_time_label["text"] = f"ETA: {m:02d}:{s:02d}"
        else:
            self.estimated_time_label["text"] = ""
        self.update_idletasks()

    def _build_ffmpeg_cmd(self, ffmpeg, inp, out_file):
        """Construct the ffmpeg command list from current UI state."""
        vc = self._get_video_codec_id()
        ac = self._get_audio_codec_id()
        crf = self.crf_var.get()
        resolution = self.resolution_pills.get()

        cmd = [ffmpeg, "-i", inp, "-c:v", vc]

        # CRF
        cmd += ["-crf", str(crf)]

        # VP9 needs -b:v 0 alongside CRF to enable constant-quality mode
        if vc == "libvpx-vp9":
            cmd += ["-b:v", "0"]

        # Audio
        cmd += ["-c:a", ac]

        # Scale filter
        if resolution != "original":
            height = int(resolution)
            cmd += ["-vf", f"scale=-2:{height}"]

        # Overwrite + output
        cmd += ["-y", out_file]
        return cmd

    def start_conversion(self):
        self._converting = True
        self._log_clear()

        ffmpeg = self.resource_path("ffmpeg.exe")
        inp = self.folder_path.get()
        out_dir = self.destination_folder_path.get()

        if not os.path.exists(inp):
            self.estimated_time_label["text"] = "Error: Input file not found."
            self._converting = False
            return
        if not os.path.isdir(out_dir):
            self.estimated_time_label["text"] = "Error: Output folder missing."
            self._converting = False
            return

        fmt = self.format_pills.get()
        out_file = os.path.join(
            out_dir,
            os.path.splitext(os.path.basename(inp))[0] + f".{fmt}",
        )

        cmd = self._build_ffmpeg_cmd(ffmpeg, inp, out_file)

        # Log the command
        self.after(0, self._log_append, " ".join(cmd))
        self.after(0, self._log_append, "")

        flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=flags,
                bufsize=1,
            )
        except FileNotFoundError:
            self.estimated_time_label["text"] = "Error: ffmpeg not found."
            self._converting = False
            return
        except Exception as e:
            self.estimated_time_label["text"] = f"Error: {e}"
            self._converting = False
            return

        dur = None
        t0 = None
        self.estimated_time_label["text"] = "Starting\u2026"

        for line in iter(proc.stdout.readline, ""):
            line = line.strip()
            if not line:
                continue

            # Append to log viewer (thread-safe via after)
            self.after(0, self._log_append, line)

            if dur is None:
                m = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})", line)
                if m:
                    h, mi, s, ms = map(int, m.groups())
                    dur = h * 3600 + mi * 60 + s + ms / 100.0
                    t0 = time.time()
                    self.estimated_time_label["text"] = "Processing\u2026"

            if dur and t0:
                m = re.search(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})", line)
                if m:
                    h, mi, s, ms = map(int, m.groups())
                    cur = h * 3600 + mi * 60 + s + ms / 100.0
                    pct = min(cur / dur * 100, 100.0) if dur > 0 else 0
                    elapsed = time.time() - t0
                    eta = ((elapsed / pct) * 100 - elapsed) if 0.1 < pct < 100 else 0
                    self.update_gui(pct, eta)

        proc.stdout.close()
        rc = proc.wait()

        if rc == 0:
            self.update_gui(100, 0)
            self.estimated_time_label["text"] = "Conversion complete!"
            self.after(0, self._log_append, "\nConversion complete.")
        else:
            self.video_progress["value"] = 0
            self.estimated_time_label["text"] = f"Error: FFmpeg code {rc}"
            self.after(0, self._log_append, f"\nFFmpeg exited with code {rc}")

        self._converting = False

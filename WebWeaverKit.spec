# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# --- Project Settings ---
# Assuming this .spec file is in the project's root directory
# SPECPATH is a variable provided by PyInstaller that contains the path to the directory
# where the .spec file is located. This is more reliable than __file__.
project_root = SPECPATH

main_script_name = 'convertToWebP.py'
app_name = 'Web Weaver Kit' # This will be the name of your .exe
icon_file_name = 'convertToWebPIcon.ico'

# --- Data files to bundle ---
# Source paths are relative to project_root (where this spec file is)
# Destination paths are relative to the bundle's root (_MEIPASS for onefile)
bundled_datas = [
    (icon_file_name, '.'),                                      # For self.iconbitmap, corresponds to --add-data 'convertToWebPIcon.ico;.'
    ('convertToWebPLogo.png', '.'),                             # Corresponds to --add-data 'convertToWebPLogo.png;.'
    (os.path.join('resources', 'ffmpeg.exe'), '.'),             # Corresponds to --add-data "./resources/ffmpeg.exe;."
    (os.path.join('resources', 'cjpegli.exe'), '.'),            # Corresponds to --add-data "./resources/cjpegli.exe;."
    ('theme_previews', 'theme_previews')                        # For your theme preview images
]

# --- Collect data for sv_ttk ---
# This replicates the --collect-data sv_ttk flag
try:
    sv_ttk_datas = collect_data_files('sv_ttk')
    bundled_datas.extend(sv_ttk_datas)
    print(f"Successfully collected {len(sv_ttk_datas)} data items for sv_ttk.")
except Exception as e:
    print(f"Warning: Could not collect data files for sv_ttk: {e}")
    print("Ensure sv_ttk is installed and accessible. The application might not theme correctly.")

# --- Collect data for ttkbootstrap (themes) ---
# PyInstaller's hooks for ttkbootstrap usually handle this automatically.
# If themes are missing, you might need to uncomment and adjust:
# try:
#     # include_themes_for='all' or specify like ['superhero', 'litera']
#     ttkbootstrap_datas = collect_data_files('ttkbootstrap', include_themes_for='all')
#     bundled_datas.extend(ttkbootstrap_datas)
#     print(f"Successfully collected {len(ttkbootstrap_datas)} data items for ttkbootstrap.")
# except Exception as e:
#     print(f"Warning: Could not collect data files for ttkbootstrap: {e}")

# --- Analysis: Gathers all script and module information ---
a = Analysis(
    [os.path.join(project_root, main_script_name)], # Main script
    pathex=[project_root],                          # Search path for modules
    binaries=[],                                    # Any non-python .dll or .so files not automatically found
    datas=bundled_datas,                            # List of data files
    hiddenimports=[                                 # Modules not automatically detected by PyInstaller
        'sv_ttk',
        'ttkbootstrap',
        'PIL.ImageTk',
        'PIL.Image',
        'multiprocessing.dummy',
        'pillow_avif',      # For AVIF support in ImageConverter
        'fitz',             # PyMuPDF for PDF to Image
        'requests',         # For update checks
        # Standard library modules usually found, but can be listed if issues:
        # 'webbrowser', 'json', 'shutil', 'datetime', 'ctypes', 'ctypes.wintypes'
    ],
    hookspath=[],                                   # Custom hook files directory
    hooksconfig={},
    runtime_hooks=[],                               # Scripts to run at runtime before main script
    excludes=[],                                    # Modules to exclude
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,                                # True to not archive (useful for debugging)
)

# --- PYZ: Python library archive (contains all .pyc files) ---
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- EXE: The actual executable ---
# This defines the one-file bundle because it's used directly.
exe = EXE(
    pyz,
    a.scripts,
    [], # a.binaries are typically handled here if not in Analysis
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,                                    # True to strip symbols (smaller file, harder to debug)
    upx=False,                                      # UPX compression not requested
    upx_exclude=[],
    runtime_tmpdir=None,                            # Default for onefile, extracts to a temp dir
    console=False,                                  # False for --noconsole / --windowed
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,                               # Auto-detect architecture
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_root, icon_file_name) # Path to the icon file for the .exe
)

# For a one-file build (-F or --onefile), the `exe` object is the primary output.
# The `COLLECT` step is more relevant for one-dir builds.
# If you were making a one-dir build, you would uncomment and use the `coll` object:
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas, # Note: a.datas here refers to the Analysis object's datas
#     strip=False,
#     upx=False,
#     name=app_name,
# )
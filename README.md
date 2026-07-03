# CipherLoom

![CipherLoom](branding/CipherLoomBanner.png)

A desktop toolkit for designers and developers — convert and compress images, shrink videos to an exact file size, batch-rename files, slice PDFs, transcode video, format text, crop images, and trace SVG image maps. Built with Tauri, React, and Rust.

![License](https://img.shields.io/badge/license-MIT-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![Binary Size](https://img.shields.io/badge/binary-22MB-green)

## Download

Grab the latest release from [Releases](https://github.com/mrzeappleGit/convertToWebP/releases):

| Platform | Format |
|---|---|
| **Windows** | `.exe` (portable) |
| **macOS** | `.dmg` |
| **Linux** | `.AppImage`, `.deb`, or `.rpm` |

macOS builds bundle FFmpeg. The portable Windows exe looks for `ffmpeg.exe` next to the executable or on your `PATH`. Linux packages declare `ffmpeg` as a system dependency.

## Tools

### Image Converter
Batch convert images between formats with compression and resizing.
- **Formats**: WebP, PNG, JPEG, JPEGLI, AVIF, TIFF, BMP, GIF, ICO
- **Quality mode**: Quality compression (0–100%)
- **Target size mode**: Set a max size per image (KB/MB) — quality and resolution are searched automatically until each image fits
- **Options**: Resize by percentage, rename to slug
- **Batch**: Select a folder and convert everything at once

### Video Compressor
Shrink a video to an exact file size with two-pass encoding.
- **Target size**: Pick MB or GB — bitrate is computed from the video's duration
- **Auto everything**: Audio bitrate, video bitrate, and resolution are chosen automatically to fit the target
- **Formats**: MP4 (H.264 + AAC) or WebM (VP9 + Opus)
- **Two-pass**: First pass analyzes, second pass hits the size accurately
- **Live log**: FFmpeg output streams to the UI in real time

### Video Converter
Transcode video files with FFmpeg (bundled).
- **Formats**: MP4 (H.264, H.265) and WebM (VP9)
- **Audio**: AAC or Opus codecs
- **Quality**: CRF slider (0–51)
- **Resolution**: Original, 1080p, 720p, 480p
- **Live log**: FFmpeg output streams to the UI in real time

### File Renamer
Batch rename files with live preview before committing.
- **Slug formatting**: Strips special characters, replaces spaces with hyphens
- **Case conversion**: lowercase, UPPERCASE, Title Case
- **Prefix/suffix**: Add text before or after each filename
- **Preview table**: See original → new names side by side before renaming

### PDF to Image
Convert PDF pages to raster images with quality control.
- **Rendering**: Uses pdf.js (Mozilla's PDF engine) for accurate rendering
- **Formats**: WebP, PNG, JPEG with quality slider
- **Preview**: Live page preview with page navigation
- **Options**: Include/exclude margins

### Text Formatter
Convert text between common programming formats with live preview.
- **Formats**: slug, lowercase, UPPERCASE, Title Case, camelCase, kebab-case, snake_case
- **Live conversion**: Output updates as you type
- **Copy**: One-click copy to clipboard

### Image Crop
Crop images with precision controls and aspect ratio enforcement.
- **Aspect ratios**: Free, 1:1, 4:3, 16:9, 3:2, 9:16
- **Drag handles**: Resize by dragging corners or edges
- **Rule of thirds**: Grid overlay for composition
- **Manual input**: Type exact X, Y, width, height values
- **Output**: PNG, WebP, or JPEG with quality control

### Image Mapping (SVG Generator)
Draw shapes on images and generate SVG path data.
- **Shapes**: Circle, polygon, rectangle
- **Properties**: Stroke width, color picker
- **Coordinates**: Original image coordinates for accurate SVG output
- **Export**: Save as `.svg` file or copy to clipboard
- **Zoom**: Zoom in/out with controls

## Themes

9 built-in themes with live switching:

| Theme | Style |
|---|---|
| **Synthetic Atelier** | Green + cyan on dark gray (default) |
| **Graphite** | Monochrome silver on charcoal |
| **Solar Flare** | Gold + orange on warm dark brown |
| **Ultraviolet** | Purple + blue on deep violet |
| **Forest Floor** | Green + gold on dark forest |
| **Cobalt** | Blue + cyan on deep navy |
| **Textbook** | Red + blue on dark navy |
| **Neon City** | Yellow + pink on deep violet (cyberpunk) |
| **Bone** | Green + teal on warm light beige (light mode) |

Theme selection persists across sessions.

## Settings

Preferences are saved to `%APPDATA%/mts-studios/CipherLoom/settings.json` and persist across sessions (settings from Web Weaver Kit installs are migrated automatically):
- Selected theme
- Converter defaults (format, quality, compression, resize)
- Renamer defaults (slug, case, prefix/suffix)
- PDF/video/text/crop preferences

## Auto-Updater

The app checks GitHub releases on launch. When an update is available:
- A green dot appears on the menu button
- The About dialog shows the new version and release notes
- Click "Install Update" to download and install automatically — the app restarts with the new version

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite 5 |
| Backend | Rust, Tauri 2.11 |
| Image processing | `image` crate (Rust) |
| PDF rendering | pdf.js (Mozilla) |
| Video transcoding | FFmpeg (bundled) |
| HTTP | reqwest (Rust) |
| Tests | Vitest, Testing Library |
| CI | GitHub Actions |
| Design | Claude Design system |

## Development

### Prerequisites
- [Node.js](https://nodejs.org/) 22+
- [Rust](https://rustup.rs/) 1.77+
- npm

### Setup
```bash
git clone https://github.com/mrzeappleGit/convertToWebP.git
cd convertToWebP
npm install
```

### Dev mode
```bash
npm run tauri dev
```

### Run tests
```bash
npm test
```

### Build release
```bash
npm run tauri build
```

The executable lands in `src-tauri/target/release/`; platform installers (when bundling) in `src-tauri/target/release/bundle/`.

## Project Structure

```
├── src/                     # React frontend
│   ├── components/          # Tool components
│   ├── __tests__/           # Test files
│   ├── styles/              # CSS design system + themes
│   ├── App.tsx              # App shell, tabs, menu, dialogs
│   ├── themes.ts            # 9 theme definitions
│   ├── useSettings.ts       # Settings persistence hook
│   └── invoke.ts            # Type-safe Tauri command wrapper
├── src-tauri/               # Rust backend
│   ├── src/lib.rs           # All Tauri commands
│   ├── tauri.conf.json      # Window, bundle, and plugin config
│   └── capabilities/        # Permission definitions
├── branding/                # CipherLoom logos, icons, banners
├── resources/               # Bundled binaries (ffmpeg, cjpegli)
├── public/                  # Static assets
├── .github/workflows/       # CI pipeline (test + build)
├── package.json             # Scripts and dependencies
└── vite.config.ts           # Vite + Vitest config
```

## License

MIT

## Credits

- **FFmpeg** — video transcoding (LGPLv2.1)
- **pdf.js** — PDF rendering (Apache 2.0)
- **image crate** — image processing (MIT/Apache 2.0)
- **Tauri** — desktop framework (MIT/Apache 2.0)

© 2025 Matthew Thomas Stevens Studios LLC

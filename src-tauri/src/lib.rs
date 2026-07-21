use std::path::{Path, PathBuf};
use std::fs;
use std::process::{Command, Stdio};
use std::io::{BufRead, BufReader};
use serde::{Deserialize, Serialize};
use regex::Regex;
use base64::Engine;
use tauri::{Manager, Emitter};
#[cfg(windows)]
use std::os::windows::process::CommandExt;

// ── File picker commands ─────────────────────────────────────────

#[derive(Deserialize)]
struct FileFilter {
    name: String,
    extensions: Vec<String>,
}

#[tauri::command]
async fn pick_file(
    app: tauri::AppHandle,
    title: String,
    filters: Vec<FileFilter>,
) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;
    let mut builder = app.dialog().file().set_title(&title);
    for f in &filters {
        let exts: Vec<&str> = f.extensions.iter().map(|s| s.as_str()).collect();
        builder = builder.add_filter(&f.name, &exts);
    }
    let path = builder.blocking_pick_file();
    Ok(path.map(|p| p.to_string()))
}

#[tauri::command]
async fn pick_folder(
    app: tauri::AppHandle,
    title: String,
) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;
    let path = app.dialog().file().set_title(&title).blocking_pick_folder();
    Ok(path.map(|p| p.to_string()))
}

#[tauri::command]
async fn save_file_dialog(
    app: tauri::AppHandle,
    title: String,
    default_name: String,
    filters: Vec<FileFilter>,
) -> Result<Option<String>, String> {
    use tauri_plugin_dialog::DialogExt;
    let mut builder = app.dialog().file().set_title(&title).set_file_name(&default_name);
    for f in &filters {
        let exts: Vec<&str> = f.extensions.iter().map(|s| s.as_str()).collect();
        builder = builder.add_filter(&f.name, &exts);
    }
    let path = builder.blocking_save_file();
    Ok(path.map(|p| p.to_string()))
}

// ── File I/O helpers ─────────────────────────────────────────────

#[tauri::command]
fn read_file_base64(path: String) -> Result<String, String> {
    let data = fs::read(&path).map_err(|e| format!("Failed to read {}: {}", path, e))?;
    Ok(base64::engine::general_purpose::STANDARD.encode(&data))
}

#[tauri::command]
fn save_base64_image(data: String, path: String, format: String, quality: u8) -> Result<String, String> {
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(&data)
        .map_err(|e| format!("Invalid base64: {}", e))?;
    let img = image::load_from_memory(&bytes).map_err(|e| format!("Invalid image data: {}", e))?;
    save_image(&img, Path::new(&path), &format, quality)?;
    Ok(path)
}

#[tauri::command]
fn write_string_to_file(content: String, path: String) -> Result<(), String> {
    fs::write(&path, &content).map_err(|e| format!("Failed to write {}: {}", path, e))
}

#[tauri::command]
fn list_files_in_dir(dir_path: String, extensions: Vec<String>) -> Result<Vec<FileInfo>, String> {
    let dir = Path::new(&dir_path);
    if !dir.is_dir() {
        return Ok(vec![]);
    }
    let mut files = Vec::new();
    for entry in fs::read_dir(dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let p = entry.path();
        if !p.is_file() { continue; }
        let ext = p.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();
        if !extensions.is_empty() && !extensions.iter().any(|e| e.to_lowercase() == ext) {
            continue;
        }
        let size = fs::metadata(&p).map(|m| m.len()).unwrap_or(0);
        files.push(FileInfo {
            path: p.to_string_lossy().to_string(),
            name: p.file_name().unwrap_or_default().to_string_lossy().to_string(),
            size,
        });
    }
    Ok(files)
}

#[derive(Serialize)]
struct FileInfo {
    path: String,
    name: String,
    size: u64,
}

// ── Image conversion ─────────────────────────────────────────────

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct ConvertImageArgs {
    source_path: String,
    dest_path: String,
    format: String,
    quality: u8,
    #[allow(dead_code)]
    convert: bool,
    compress: bool,
    rename: bool,
    resize: bool,
    resize_percent: u32,
    #[serde(default)]
    target_size_bytes: Option<u64>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct ConvertResult {
    files_processed: u32,
    total_files: u32,
    input_size_bytes: u64,
    output_size_bytes: u64,
}

#[tauri::command]
async fn convert_images(app: tauri::AppHandle, args: ConvertImageArgs) -> Result<ConvertResult, String> {
    let source = Path::new(&args.source_path);
    let dest = PathBuf::from(&args.dest_path);
    fs::create_dir_all(&dest).map_err(|e| e.to_string())?;

    let files = gather_image_files(source)?;
    let total = files.len();
    let mut completed = 0u32;
    let mut total_input_size = 0u64;
    let mut total_output_size = 0u64;

    let q = if args.compress { args.quality } else { 100 };

    for (i, file_path) in files.iter().enumerate() {
        let fname = file_path.file_name().unwrap_or_default().to_string_lossy().to_string();
        app.emit("convert-progress", serde_json::json!({
            "current": i + 1,
            "total": total,
            "file": fname,
        })).ok();
        let input_size = fs::metadata(file_path).map(|m| m.len()).unwrap_or(0);
        total_input_size += input_size;

        let mut img = image::open(file_path)
            .map_err(|e| format!("Failed to open {}: {}", file_path.display(), e))?;

        if args.resize && args.resize_percent < 100 && args.resize_percent > 0 {
            let nw = (img.width() as f64 * args.resize_percent as f64 / 100.0).max(1.0) as u32;
            let nh = (img.height() as f64 * args.resize_percent as f64 / 100.0).max(1.0) as u32;
            img = img.resize_exact(nw, nh, image::imageops::FilterType::Lanczos3);
        }

        let stem = file_path.file_stem().unwrap_or_default().to_string_lossy();
        let out_name = if args.rename { slugify(&stem) } else { stem.to_string() };
        let ext = map_format_ext(&args.format);
        let out_path = dest.join(format!("{}.{}", out_name, ext));

        if let Some(target) = args.target_size_bytes.filter(|t| *t > 0) {
            let data = fit_image_to_target(&img, &args.format, target)
                .map_err(|e| format!("{}: {}", fname, e))?;
            fs::write(&out_path, &data).map_err(|e| e.to_string())?;
        } else {
            save_image(&img, &out_path, &args.format, q)?;
        }

        let output_size = fs::metadata(&out_path).map(|m| m.len()).unwrap_or(0);
        total_output_size += output_size;
        completed += 1;
    }

    Ok(ConvertResult {
        files_processed: completed,
        total_files: total as u32,
        input_size_bytes: total_input_size,
        output_size_bytes: total_output_size,
    })
}

#[tauri::command]
fn list_source_files(source_path: String) -> Result<Vec<FileInfo>, String> {
    let files = gather_image_files(Path::new(&source_path))?;
    Ok(files.iter().map(|p| {
        let size = fs::metadata(p).map(|m| m.len()).unwrap_or(0);
        FileInfo {
            path: p.to_string_lossy().to_string(),
            name: p.file_name().unwrap_or_default().to_string_lossy().to_string(),
            size,
        }
    }).collect())
}

fn gather_image_files(path: &Path) -> Result<Vec<PathBuf>, String> {
    let exts = ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "ico", "avif"];
    let mut files = Vec::new();
    if path.is_file() {
        files.push(path.to_path_buf());
    } else if path.is_dir() {
        for entry in fs::read_dir(path).map_err(|e| e.to_string())? {
            let entry = entry.map_err(|e| e.to_string())?;
            let p = entry.path();
            if p.is_file() {
                if let Some(ext) = p.extension().and_then(|e| e.to_str()) {
                    if exts.contains(&ext.to_lowercase().as_str()) {
                        files.push(p);
                    }
                }
            }
        }
    }
    Ok(files)
}

fn map_format_ext(format: &str) -> &str {
    match format {
        "jpeg" | "jpegli" => "jpg",
        "tiff" => "tif",
        other => other,
    }
}

fn save_image(img: &image::DynamicImage, path: &Path, format: &str, quality: u8) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let data = encode_image_to_memory(img, format, quality)?;
    fs::write(path, &data).map_err(|e| e.to_string())
}

fn encode_image_to_memory(img: &image::DynamicImage, format: &str, quality: u8) -> Result<Vec<u8>, String> {
    use image::ImageFormat;
    use std::io::Cursor;
    match format {
        "webp" => {
            // The webp encoder only accepts 8-bit RGB/RGBA buffers
            let rgba = image::DynamicImage::ImageRgba8(img.to_rgba8());
            let encoder = webp::Encoder::from_image(&rgba)
                .map_err(|e| format!("WebP encode error: {}", e))?;
            let data = if quality >= 100 {
                encoder.encode_lossless()
            } else {
                encoder.encode(quality as f32)
            };
            Ok(data.to_vec())
        }
        "avif" => {
            let mut buf = Vec::new();
            let encoder = image::codecs::avif::AvifEncoder::new_with_speed_quality(&mut buf, 6, quality.min(100));
            img.write_with_encoder(encoder).map_err(|e| e.to_string())?;
            Ok(buf)
        }
        "png" if quality < 100 => encode_quantized_png(img, quality),
        "png" | "gif" | "bmp" | "tiff" | "ico" => {
            let fmt = match format {
                "png" => ImageFormat::Png,
                "gif" => ImageFormat::Gif,
                "bmp" => ImageFormat::Bmp,
                "tiff" => ImageFormat::Tiff,
                _ => ImageFormat::Ico,
            };
            let mut buf = Cursor::new(Vec::new());
            img.write_to(&mut buf, fmt).map_err(|e| e.to_string())?;
            Ok(buf.into_inner())
        }
        _ => {
            // JPEG / JPEGLI — JPEG has no alpha channel, so flatten first
            let rgb = image::DynamicImage::ImageRgb8(img.to_rgb8());
            let mut buf = Vec::new();
            let encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(&mut buf, quality);
            rgb.write_with_encoder(encoder).map_err(|e| e.to_string())?;
            Ok(buf)
        }
    }
}

/// TinyPNG-style lossy PNG: quantize to a 256-color RGBA palette and write an
/// indexed PNG (1 byte/px + PLTE/tRNS instead of truecolor) — typically far
/// smaller with little visible loss. Lower quality samples fewer pixels when
/// building the palette (faster, rougher).
fn encode_quantized_png(img: &image::DynamicImage, quality: u8) -> Result<Vec<u8>, String> {
    let rgba = img.to_rgba8();
    let (w, h) = rgba.dimensions();
    let samplefac = ((100 - quality as i32) / 10 + 1).clamp(1, 10);
    let nq = color_quant::NeuQuant::new(samplefac, 256, rgba.as_raw());
    let indices: Vec<u8> = rgba.pixels().map(|p| nq.index_of(&p.0) as u8).collect();

    let mut plte = Vec::with_capacity(256 * 3);
    let mut trns = Vec::with_capacity(256);
    for c in nq.color_map_rgba().chunks(4) {
        plte.extend_from_slice(&c[..3]);
        trns.push(c[3]);
    }

    let mut buf = Vec::new();
    let mut enc = png::Encoder::new(&mut buf, w, h);
    enc.set_color(png::ColorType::Indexed);
    enc.set_depth(png::BitDepth::Eight);
    enc.set_palette(plte);
    enc.set_trns(trns);
    enc.set_compression(png::Compression::Best);
    let mut writer = enc.write_header().map_err(|e| e.to_string())?;
    writer.write_image_data(&indices).map_err(|e| e.to_string())?;
    writer.finish().map_err(|e| e.to_string())?;
    Ok(buf)
}

/// Formats where a quality knob meaningfully changes output size.
fn is_lossy_format(format: &str) -> bool {
    matches!(format, "webp" | "jpeg" | "jpegli" | "avif")
}

/// Find the encoding of `img` that fits within `target_bytes`, trading both
/// quality and resolution. Lossy formats: binary-search quality; if fitting
/// requires quality below GOOD_Q, downscale and re-search so the result is a
/// smaller-but-clean image rather than a full-size artifact-ridden one (the
/// low-quality fit is kept as a fallback). Lossless formats: downscale only,
/// except PNG which tries palette quantization first.
fn fit_image_to_target(img: &image::DynamicImage, format: &str, target_bytes: u64) -> Result<Vec<u8>, String> {
    const MIN_Q: u8 = 5;
    const MAX_Q: u8 = 95;
    // ponytail: fixed quality floor; make user-tunable if 70 proves wrong
    const GOOD_Q: u8 = 70;
    let lossy = is_lossy_format(format);
    let mut current = img.clone();
    let mut fallback: Option<Vec<u8>> = None;

    for _ in 0..12 {
        // Smallest encoding achievable at the current dimensions, or None if
        // we already fit here (just not at a quality worth keeping)
        let floor_data = if lossy {
            let mut lo = MIN_Q;
            let mut hi = MAX_Q;
            let mut best: Option<(u8, Vec<u8>)> = None;
            while lo <= hi {
                let mid = ((lo as u16 + hi as u16) / 2) as u8;
                let data = encode_image_to_memory(&current, format, mid)?;
                if data.len() as u64 <= target_bytes {
                    best = Some((mid, data));
                    lo = mid + 1;
                } else if mid <= MIN_Q {
                    break;
                } else {
                    hi = mid - 1;
                }
            }
            match best {
                Some((q, data)) if q >= GOOD_Q => return Ok(data),
                Some((_, data)) => {
                    fallback = Some(data);
                    None
                }
                None => Some(encode_image_to_memory(&current, format, MIN_Q)?),
            }
        } else {
            let data = encode_image_to_memory(&current, format, 100)?;
            if data.len() as u64 <= target_bytes {
                return Ok(data);
            }
            if format == "png" {
                // Quantized palette PNG before giving up resolution
                let q = encode_quantized_png(&current, 80)?;
                if q.len() as u64 <= target_bytes {
                    return Ok(q);
                }
                Some(q)
            } else {
                Some(data)
            }
        };

        // Shrink: proportionally to the overshoot when nothing fits, a gentle
        // step when we fit but want the quality back
        let factor = match &floor_data {
            Some(data) => {
                let ratio = target_bytes as f64 / data.len() as f64;
                (ratio.sqrt() * 0.95).clamp(0.3, 0.9)
            }
            None => 0.85,
        };
        let nw = ((current.width() as f64) * factor).round() as u32;
        let nh = ((current.height() as f64) * factor).round() as u32;
        if nw < 16 || nh < 16 {
            break;
        }
        current = current.resize_exact(nw, nh, image::imageops::FilterType::Lanczos3);
    }
    fallback.ok_or_else(|| format!("Could not reach target size of {}", format_bytes(target_bytes)))
}

fn format_bytes(bytes: u64) -> String {
    if bytes >= 1_048_576 {
        format!("{:.1} MB", bytes as f64 / 1_048_576.0)
    } else {
        format!("{:.0} KB", bytes as f64 / 1024.0)
    }
}

// ── File renaming ────────────────────────────────────────────────

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct RenameArgs {
    folder_path: String,
    single_file_path: String,
    prefix: String,
    suffix: String,
    slug: bool,
    case_mode: String,
}

#[derive(Serialize)]
struct RenamePreviewItem {
    original: String,
    renamed: String,
    changed: bool,
}

#[derive(Serialize)]
struct RenameResult {
    modified: u32,
    errors: u32,
    total: u32,
}

#[tauri::command]
fn preview_rename(args: RenameArgs) -> Result<Vec<RenamePreviewItem>, String> {
    let files = gather_rename_files(&args.folder_path, &args.single_file_path)?;
    Ok(files.iter().map(|p| {
        let original = p.file_name().unwrap_or_default().to_string_lossy().to_string();
        let renamed = compute_new_name(&original, &args);
        let changed = original != renamed;
        RenamePreviewItem { original, renamed, changed }
    }).collect())
}

#[tauri::command]
fn execute_rename(args: RenameArgs) -> Result<RenameResult, String> {
    let files = gather_rename_files(&args.folder_path, &args.single_file_path)?;
    let mut modified = 0u32;
    let mut errors = 0u32;
    for p in &files {
        let original = p.file_name().unwrap_or_default().to_string_lossy().to_string();
        let renamed = compute_new_name(&original, &args);
        if original != renamed {
            match fs::rename(p, p.with_file_name(&renamed)) {
                Ok(_) => modified += 1,
                Err(_) => errors += 1,
            }
        }
    }
    Ok(RenameResult { modified, errors, total: files.len() as u32 })
}

fn gather_rename_files(folder: &str, single: &str) -> Result<Vec<PathBuf>, String> {
    let mut files = Vec::new();
    if !folder.is_empty() {
        let dir = Path::new(folder);
        if dir.is_dir() {
            for entry in fs::read_dir(dir).map_err(|e| e.to_string())? {
                let entry = entry.map_err(|e| e.to_string())?;
                if entry.path().is_file() { files.push(entry.path()); }
            }
        }
    }
    if !single.is_empty() {
        let p = PathBuf::from(single);
        if p.is_file() { files.push(p); }
    }
    Ok(files)
}

fn compute_new_name(filename: &str, args: &RenameArgs) -> String {
    let (stem, ext) = match filename.rfind('.') {
        Some(i) => (&filename[..i], &filename[i..]),
        None => (filename, ""),
    };
    let mut name = stem.to_string();
    if args.slug {
        let re1 = Regex::new(r"[^\w\s-]").unwrap();
        let re2 = Regex::new(r"[-_]+").unwrap();
        let re3 = Regex::new(r"^-|-$").unwrap();
        name = re1.replace_all(&name, "").to_string();
        name = name.replace(' ', "-");
        name = re2.replace_all(&name, "-").to_string();
        name = re3.replace_all(&name, "").to_string();
    }
    name = match args.case_mode.as_str() {
        "lower" => name.to_lowercase(),
        "upper" => name.to_uppercase(),
        "title" => name.replace('-', " ").split_whitespace().map(|w| {
            let mut c = w.chars();
            match c.next() {
                None => String::new(),
                Some(f) => f.to_uppercase().to_string() + &c.as_str().to_lowercase(),
            }
        }).collect::<Vec<_>>().join("-"),
        _ => if args.slug { name.to_lowercase() } else { name },
    };
    if !args.prefix.is_empty() { name = format!("{}{}", args.prefix, name); }
    if !args.suffix.is_empty() { name = format!("{}{}", name, args.suffix); }
    format!("{}{}", name, ext)
}

fn slugify(text: &str) -> String {
    let re1 = Regex::new(r"[^\w\s-]").unwrap();
    let re2 = Regex::new(r"[-_]+").unwrap();
    let re3 = Regex::new(r"^-|-$").unwrap();
    let mut s = re1.replace_all(text, "").to_string();
    s = s.replace(' ', "-");
    s = re2.replace_all(&s, "-").to_string();
    s = re3.replace_all(&s, "").to_string();
    s.to_lowercase()
}

// ── Video conversion (FFmpeg) ────────────────────────────────────

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct VideoConvertArgs {
    source_path: String,
    dest_path: String,
    format: String,
    video_codec: String,
    audio_codec: String,
    crf: u32,
    resolution: String,
}

#[tauri::command]
async fn convert_video(app: tauri::AppHandle, args: VideoConvertArgs) -> Result<String, String> {
    let ffmpeg = find_ffmpeg(&app)?;
    let source = PathBuf::from(&args.source_path);
    let stem = source.file_stem().unwrap_or_default().to_string_lossy();
    let dest_dir = if args.dest_path.is_empty() {
        source.parent().unwrap_or(Path::new(".")).to_path_buf()
    } else {
        PathBuf::from(&args.dest_path)
    };
    fs::create_dir_all(&dest_dir).map_err(|e| e.to_string())?;
    let output = dest_dir.join(format!("{}_converted.{}", stem, args.format));

    let mut cmd_args: Vec<String> = vec![
        "-i".into(), args.source_path.clone(),
        "-c:v".into(), args.video_codec.clone(),
        "-c:a".into(), args.audio_codec.clone(),
        "-crf".into(), args.crf.to_string(),
    ];

    match args.resolution.as_str() {
        "1080" => { cmd_args.extend(["-vf".into(), "scale=-2:1080".into()]); }
        "720"  => { cmd_args.extend(["-vf".into(), "scale=-2:720".into()]); }
        "480"  => { cmd_args.extend(["-vf".into(), "scale=-2:480".into()]); }
        _ => {}
    }

    cmd_args.extend(["-y".into(), output.to_string_lossy().to_string()]);

    run_ffmpeg_streaming(&app, &ffmpeg, &cmd_args, "ffmpeg-log")?;
    Ok(output.to_string_lossy().to_string())
}

/// Run FFmpeg, streaming its stderr to the given frontend event channel.
fn run_ffmpeg_streaming(app: &tauri::AppHandle, ffmpeg: &Path, args: &[String], event: &str) -> Result<(), String> {
    let mut cmd = Command::new(ffmpeg);
    cmd.args(args).stdout(Stdio::piped()).stderr(Stdio::piped());
    #[cfg(windows)]
    { cmd.creation_flags(0x08000000); } // CREATE_NO_WINDOW
    let mut child = cmd.spawn()
        .map_err(|e| format!("Failed to start FFmpeg: {}", e))?;

    if let Some(stderr) = child.stderr.take() {
        let app_handle = app.clone();
        let event = event.to_string();
        std::thread::spawn(move || {
            let reader = BufReader::new(stderr);
            for line in reader.lines() {
                if let Ok(line) = line {
                    let _ = app_handle.emit(&event, &line);
                }
            }
        });
    }

    let status = child.wait().map_err(|e| format!("FFmpeg error: {}", e))?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("FFmpeg exited with code {}", status.code().unwrap_or(-1)))
    }
}

// ── Video compression to a target size ───────────────────────────

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct CompressVideoArgs {
    source_path: String,
    dest_path: String,
    format: String, // "mp4" | "webm"
    target_size_bytes: u64,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct CompressVideoResult {
    output_path: String,
    input_size_bytes: u64,
    output_size_bytes: u64,
    target_size_bytes: u64,
    video_kbps: u32,
    audio_kbps: u32,
    resolution: String,
    duration_secs: f64,
}

struct VideoProbe {
    duration_secs: f64,
    width: u32,
    height: u32,
    has_audio: bool,
}

/// Read duration, dimensions and audio presence by parsing `ffmpeg -i` output.
/// (ffprobe is not bundled, but ffmpeg prints the same stream info to stderr.)
fn probe_video(ffmpeg: &Path, source: &str) -> Result<VideoProbe, String> {
    let mut cmd = Command::new(ffmpeg);
    cmd.args(["-hide_banner", "-i", source])
        .stdout(Stdio::null())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    { cmd.creation_flags(0x08000000); } // CREATE_NO_WINDOW
    // ffmpeg exits non-zero here (no output file given) — only the stderr matters
    let out = cmd.output().map_err(|e| format!("Failed to run FFmpeg: {}", e))?;
    let stderr = String::from_utf8_lossy(&out.stderr);
    parse_probe_output(&stderr)
}

fn parse_probe_output(stderr: &str) -> Result<VideoProbe, String> {
    let dur_re = Regex::new(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)").unwrap();
    let caps = dur_re.captures(stderr).ok_or_else(|| {
        format!("Could not read video info. FFmpeg said:\n{}",
            stderr.lines().rev().take(4).collect::<Vec<_>>().into_iter().rev().collect::<Vec<_>>().join("\n"))
    })?;
    let h: f64 = caps[1].parse().unwrap_or(0.0);
    let m: f64 = caps[2].parse().unwrap_or(0.0);
    let s: f64 = caps[3].parse().unwrap_or(0.0);
    let duration_secs = h * 3600.0 + m * 60.0 + s;

    let mut width = 0u32;
    let mut height = 0u32;
    let dim_re = Regex::new(r"(\d{2,5})x(\d{2,5})").unwrap();
    for line in stderr.lines() {
        // Embedded cover art (mp3/m4a "attached pic") is not a real video stream
        if line.contains("Video:") && !line.contains("attached pic") {
            for c in dim_re.captures_iter(line) {
                let w: u32 = c[1].parse().unwrap_or(0);
                let hh: u32 = c[2].parse().unwrap_or(0);
                if w >= 16 && hh >= 16 {
                    width = w;
                    height = hh;
                    break;
                }
            }
            break;
        }
    }
    if height == 0 {
        return Err("No video stream found in this file".into());
    }
    let has_audio = stderr.lines().any(|l| l.contains("Audio:"));
    Ok(VideoProbe { duration_secs, width, height, has_audio })
}

/// Highest resolution that still looks reasonable at the given video bitrate.
fn auto_cap_height(video_kbps: f64) -> u32 {
    if video_kbps >= 7000.0 { u32::MAX }
    else if video_kbps >= 3500.0 { 2160 }
    else if video_kbps >= 1800.0 { 1440 }
    else if video_kbps >= 900.0 { 1080 }
    else if video_kbps >= 450.0 { 720 }
    else if video_kbps >= 220.0 { 480 }
    else { 360 }
}

#[tauri::command]
async fn compress_video(app: tauri::AppHandle, args: CompressVideoArgs) -> Result<CompressVideoResult, String> {
    let ffmpeg = find_ffmpeg(&app)?;
    let source = PathBuf::from(&args.source_path);
    if !source.is_file() {
        return Err(format!("Source file not found: {}", args.source_path));
    }
    let input_size = fs::metadata(&source).map(|m| m.len()).unwrap_or(0);

    app.emit("compress-log", "Analyzing source video…").ok();
    let probe = probe_video(&ffmpeg, &args.source_path)?;
    if probe.duration_secs <= 0.0 {
        return Err("Could not determine video duration".into());
    }

    // Container overhead grows with duration (per-sample mp4/webm index tables),
    // not with bitrate — reserve a fixed floor plus ~1 KB per second, then keep
    // a 1% cushion for two-pass ABR tolerance.
    let container_overhead = 20_000.0 + 1000.0 * probe.duration_secs;
    let min_target_err = || format!(
        "Target of {} is too small for a {:.1}-second video — try at least {}",
        format_bytes(args.target_size_bytes),
        probe.duration_secs,
        format_bytes((((25.0 + 48.0) * 125.0 * probe.duration_secs / 0.99 + container_overhead) as u64).max(50 * 1024)),
    );
    let budget_bytes = args.target_size_bytes as f64 - container_overhead;
    if budget_bytes <= 0.0 {
        return Err(min_target_err());
    }
    let usable_bits = budget_bytes * 8.0 * 0.99;
    let total_kbps = usable_bits / probe.duration_secs / 1000.0;
    let audio_kbps: u32 = if !probe.has_audio { 0 }
        else if total_kbps >= 1000.0 { 128 }
        else if total_kbps >= 500.0 { 96 }
        else if total_kbps >= 250.0 { 64 }
        else { 48 };
    let video_kbps = total_kbps - audio_kbps as f64;
    if video_kbps < 25.0 {
        return Err(min_target_err());
    }

    // Cap by the SHORT side so portrait/landscape are treated alike ("720p-class"),
    // and always normalize to even dimensions + yuv420p for encoder/player compatibility.
    let cap = auto_cap_height(video_kbps);
    let short_side = probe.width.min(probe.height);
    let (scale_filter, res_label): (String, String) = if short_side > cap {
        (
            format!("scale='if(gt(iw,ih),-2,{cap})':'if(gt(iw,ih),{cap},-2)'"),
            format!("{}p", cap),
        )
    } else {
        ("scale=trunc(iw/2)*2:trunc(ih/2)*2".into(), "original".into())
    };
    let scale_args: Vec<String> = vec!["-vf".into(), scale_filter, "-pix_fmt".into(), "yuv420p".into()];

    let (vcodec, acodec) = if args.format == "webm" {
        ("libvpx-vp9", "libopus")
    } else {
        ("libx264", "aac")
    };

    let stem = source.file_stem().unwrap_or_default().to_string_lossy();
    let dest_dir = if args.dest_path.is_empty() {
        source.parent().unwrap_or(Path::new(".")).to_path_buf()
    } else {
        PathBuf::from(&args.dest_path)
    };
    fs::create_dir_all(&dest_dir).map_err(|e| e.to_string())?;
    let mut output = dest_dir.join(format!("{}_compressed.{}", stem, args.format));
    let mut n = 2u32;
    while output.exists() {
        output = dest_dir.join(format!("{}_compressed_{}.{}", stem, n, args.format));
        n += 1;
    }

    // Unique per invocation, not just per process — concurrent jobs must not share stats
    use std::sync::atomic::{AtomicU64, Ordering};
    static COMPRESS_SEQ: AtomicU64 = AtomicU64::new(0);
    let seq = COMPRESS_SEQ.fetch_add(1, Ordering::Relaxed);
    let passlog = std::env::temp_dir().join(format!("cipherloom_2pass_{}_{}", std::process::id(), seq));
    let plog = passlog.to_string_lossy().to_string();
    let vb = format!("{}k", video_kbps.round() as u64);

    app.emit("compress-log", format!(
        "Plan: video {} kbps · audio {} kbps · resolution {} · two-pass {}",
        video_kbps.round(), audio_kbps, res_label, vcodec
    )).ok();

    // Pass 1 — analysis only, no output file
    app.emit("compress-log", "── Pass 1/2 ──").ok();
    let mut p1: Vec<String> = vec![
        "-y".into(), "-i".into(), args.source_path.clone(),
        "-map".into(), "0:V:0".into(),
        "-c:v".into(), vcodec.into(), "-b:v".into(), vb.clone(),
        "-pass".into(), "1".into(), "-passlogfile".into(), plog.clone(),
    ];
    p1.extend(scale_args.iter().cloned());
    if vcodec == "libvpx-vp9" {
        p1.extend(["-row-mt".into(), "1".into(), "-cpu-used".into(), "4".into()]);
    }
    p1.extend(["-an".into(), "-f".into(), "null".into(), "-".into()]);
    let r1 = run_ffmpeg_streaming(&app, &ffmpeg, &p1, "compress-log");
    if r1.is_err() {
        cleanup_passlogs(&plog);
        r1?;
    }

    // Pass 2 — actual encode
    app.emit("compress-log", "── Pass 2/2 ──").ok();
    let mut p2: Vec<String> = vec![
        "-y".into(), "-i".into(), args.source_path.clone(),
        "-map".into(), "0:V:0".into(),
    ];
    if probe.has_audio {
        p2.extend(["-map".into(), "0:a:0".into()]);
    }
    p2.extend([
        "-c:v".into(), vcodec.into(), "-b:v".into(), vb.clone(),
        "-pass".into(), "2".into(), "-passlogfile".into(), plog.clone(),
    ]);
    p2.extend(scale_args.iter().cloned());
    if vcodec == "libvpx-vp9" {
        p2.extend(["-row-mt".into(), "1".into(), "-cpu-used".into(), "2".into()]);
    } else {
        p2.extend([
            "-maxrate".into(), format!("{}k", (video_kbps * 1.5).round() as u64),
            "-bufsize".into(), format!("{}k", (video_kbps * 2.0).round() as u64),
            "-movflags".into(), "+faststart".into(),
        ]);
    }
    if probe.has_audio {
        p2.extend(["-c:a".into(), acodec.into(), "-b:a".into(), format!("{}k", audio_kbps)]);
        if acodec == "libopus" {
            // libopus rejects layouts like 5.1(side) — remap to a supported one
            p2.extend(["-af".into(), "aformat=channel_layouts=7.1|5.1|stereo|mono".into()]);
        }
    } else {
        p2.push("-an".into());
    }
    p2.push(output.to_string_lossy().to_string());
    let r2 = run_ffmpeg_streaming(&app, &ffmpeg, &p2, "compress-log");
    cleanup_passlogs(&plog);
    r2?;

    let output_size = fs::metadata(&output).map(|m| m.len()).unwrap_or(0);
    Ok(CompressVideoResult {
        output_path: output.to_string_lossy().to_string(),
        input_size_bytes: input_size,
        output_size_bytes: output_size,
        target_size_bytes: args.target_size_bytes,
        video_kbps: video_kbps.round() as u32,
        audio_kbps,
        resolution: res_label,
        duration_secs: probe.duration_secs,
    })
}

fn cleanup_passlogs(plog_prefix: &str) {
    // x264 writes "<prefix>-0.log" (+ ".mbtree"); libvpx writes "<prefix>-0.log"
    for suffix in ["-0.log", "-0.log.mbtree", "-0.log.temp", "-0.log.mbtree.temp"] {
        let _ = fs::remove_file(format!("{}{}", plog_prefix, suffix));
    }
}

fn find_ffmpeg(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let ffmpeg_name = if cfg!(windows) { "ffmpeg.exe" } else { "ffmpeg" };

    // Check bundled resource first
    if let Ok(resource_dir) = app.path().resource_dir() {
        let bundled = resource_dir.join("resources").join(ffmpeg_name);
        if bundled.exists() { return Ok(bundled); }
        let bundled2 = resource_dir.join(ffmpeg_name);
        if bundled2.exists() { return Ok(bundled2); }
    }
    // Check alongside exe
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(dir) = exe_path.parent() {
            let local = dir.join(ffmpeg_name);
            if local.exists() { return Ok(local); }
        }
    }
    // Fall back to PATH (ffmpeg is commonly installed on Linux/macOS)
    if Command::new("ffmpeg").arg("-version").stdout(Stdio::null()).stderr(Stdio::null()).status().is_ok() {
        return Ok(PathBuf::from("ffmpeg"));
    }
    Err("FFmpeg not found. Install ffmpeg to your PATH or place it next to the application.".into())
}

// ── PDF helpers ──────────────────────────────────────────────────

#[tauri::command]
fn save_pdf_page_image(
    png_base64: String,
    pdf_path: String,
    format: String,
    quality: u8,
) -> Result<String, String> {
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(&png_base64)
        .map_err(|e| format!("Invalid base64: {}", e))?;
    let img = image::load_from_memory(&bytes)
        .map_err(|e| format!("Invalid image data: {}", e))?;

    let stem = Path::new(&pdf_path).file_stem().unwrap_or_default().to_string_lossy();
    let parent = Path::new(&pdf_path).parent().unwrap_or(Path::new("."));
    let ext = map_format_ext(&format);
    let out_path = parent.join(format!("{}-thumbnail.{}", stem, ext));

    save_image(&img, &out_path, &format, quality)?;
    Ok(out_path.to_string_lossy().to_string())
}

// ── Settings persistence (%APPDATA%/mts-studios/CipherLoom/) ─────

const SETTINGS_DIR: &str = "mts-studios";
const SETTINGS_APP: &str = "CipherLoom";
const LEGACY_SETTINGS_APP: &str = "WebWeaverKit";
const SETTINGS_FILE: &str = "settings.json";

fn config_base() -> PathBuf {
    if cfg!(windows) {
        std::env::var("APPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(|_| dirs::config_dir().unwrap_or_else(|| PathBuf::from(".")))
    } else {
        dirs::config_dir().unwrap_or_else(|| PathBuf::from("."))
    }
}

fn settings_path() -> PathBuf {
    config_base().join(SETTINGS_DIR).join(SETTINGS_APP)
}

#[tauri::command]
fn load_settings() -> Result<serde_json::Value, String> {
    let path = settings_path().join(SETTINGS_FILE);
    if !path.exists() {
        // Migrate settings saved under the old Web Weaver Kit name
        let legacy = config_base().join(SETTINGS_DIR).join(LEGACY_SETTINGS_APP).join(SETTINGS_FILE);
        if legacy.exists() && fs::create_dir_all(settings_path()).is_ok() {
            let _ = fs::copy(&legacy, &path);
        }
    }
    if !path.exists() {
        return Ok(serde_json::json!({}));
    }
    let data = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    serde_json::from_str(&data).map_err(|e| e.to_string())
}

#[tauri::command]
fn save_settings(settings: serde_json::Value) -> Result<(), String> {
    let dir = settings_path();
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    let path = dir.join(SETTINGS_FILE);
    let data = serde_json::to_string_pretty(&settings).map_err(|e| e.to_string())?;
    fs::write(&path, data).map_err(|e| e.to_string())
}

// ── Auto-updater (GitHub releases) ───────────────────────────────

const GITHUB_REPO: &str = "mrzeappleGit/convertToWebP";
const CURRENT_VERSION: &str = "2.2.1";

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct UpdateInfo {
    available: bool,
    current_version: String,
    latest_version: String,
    download_url: String,
    release_notes: String,
}

fn parse_version(v: &str) -> Vec<u32> {
    v.trim_start_matches('v').trim_start_matches('V')
        .split('.').filter_map(|s| s.parse().ok()).collect()
}

fn version_gt(a: &str, b: &str) -> bool {
    let va = parse_version(a);
    let vb = parse_version(b);
    for i in 0..va.len().max(vb.len()) {
        let x = va.get(i).copied().unwrap_or(0);
        let y = vb.get(i).copied().unwrap_or(0);
        if x > y { return true; }
        if x < y { return false; }
    }
    false
}

#[tauri::command]
async fn check_for_updates() -> Result<UpdateInfo, String> {
    let url = format!("https://api.github.com/repos/{}/releases/latest", GITHUB_REPO);
    let client = reqwest::Client::new();
    let resp = client.get(&url)
        .header("User-Agent", format!("CipherLoom/{}", CURRENT_VERSION))
        .header("Accept", "application/vnd.github.v3+json")
        .send().await
        .map_err(|e| format!("Network error: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("GitHub API returned {}", resp.status()));
    }

    let release: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
    let tag = release["tag_name"].as_str().unwrap_or("");
    let notes = release["body"].as_str().unwrap_or("").to_string();

    if tag.is_empty() || !version_gt(tag, CURRENT_VERSION) {
        return Ok(UpdateInfo {
            available: false,
            current_version: CURRENT_VERSION.to_string(),
            latest_version: tag.to_string(),
            download_url: String::new(),
            release_notes: String::new(),
        });
    }

    // Find .exe asset
    let mut dl_url = String::new();
    if let Some(assets) = release["assets"].as_array() {
        for asset in assets {
            if let Some(name) = asset["name"].as_str() {
                if name.to_lowercase().ends_with(".exe") {
                    dl_url = asset["browser_download_url"].as_str().unwrap_or("").to_string();
                    break;
                }
            }
        }
    }
    if dl_url.is_empty() {
        dl_url = release["html_url"].as_str().unwrap_or("").to_string();
    }

    Ok(UpdateInfo {
        available: true,
        current_version: CURRENT_VERSION.to_string(),
        latest_version: tag.to_string(),
        download_url: dl_url,
        release_notes: notes,
    })
}

// ── Self-updater (download + replace + restart) ──────────────────

#[tauri::command]
async fn download_and_install_update(app: tauri::AppHandle, url: String) -> Result<(), String> {
    // Determine current exe path
    let current_exe = std::env::current_exe().map_err(|e| format!("Cannot find exe: {}", e))?;
    let exe_dir = current_exe.parent().ok_or("Cannot find exe directory")?;
    let exe_name = current_exe.file_name().ok_or("Cannot get exe name")?.to_string_lossy().to_string();
    let download_path = exe_dir.join("latest_update.exe");

    // Download the new exe
    app.emit("update-progress", "Downloading update...").ok();
    let client = reqwest::Client::new();
    let resp = client.get(&url)
        .header("User-Agent", format!("CipherLoom/{}", CURRENT_VERSION))
        .send().await
        .map_err(|e| format!("Download failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("Download failed: HTTP {}", resp.status()));
    }

    let total = resp.content_length().unwrap_or(0);
    let mut downloaded: u64 = 0;
    let mut file = fs::File::create(&download_path).map_err(|e| format!("Cannot create file: {}", e))?;

    use std::io::Write;
    let mut stream = resp.bytes_stream();
    use futures_util::StreamExt;
    while let Some(chunk) = stream.next().await {
        let chunk = chunk.map_err(|e| format!("Download error: {}", e))?;
        file.write_all(&chunk).map_err(|e| format!("Write error: {}", e))?;
        downloaded += chunk.len() as u64;
        if total > 0 {
            let pct = (downloaded as f64 / total as f64 * 100.0) as u32;
            app.emit("update-progress", format!("Downloading... {}%", pct)).ok();
        }
    }
    drop(file);

    app.emit("update-progress", "Installing update...").ok();

    // Platform-specific: write a helper script to replace the binary and restart
    #[cfg(windows)]
    {
        let helper_path = exe_dir.join("update_helper.bat");
        let script = format!(
            "@echo off\r\ntimeout /t 2 /nobreak > NUL\r\n\
            taskkill /IM \"{}\" /F > NUL 2>&1\r\n\
            set retries=0\r\n:retry\r\n\
            move /Y \"{}\" \"{}\" > NUL 2>&1\r\n\
            if %errorlevel% EQU 0 goto success\r\n\
            set /a retries+=1\r\nif %retries% GEQ 10 goto fail\r\n\
            timeout /t 1 /nobreak > NUL\r\ngoto retry\r\n\
            :success\r\ntimeout /t 1 /nobreak > NUL\r\nstart \"\" \"{}\"\r\ngoto cleanup\r\n\
            :fail\r\ndel \"{}\" > NUL 2>&1\r\n\
            :cleanup\r\n(goto) 2>nul & del \"%~f0\"\r\n",
            exe_name, download_path.to_string_lossy(), current_exe.to_string_lossy(),
            current_exe.to_string_lossy(), download_path.to_string_lossy(),
        );
        fs::write(&helper_path, &script).map_err(|e| format!("Cannot write helper: {}", e))?;
        let flags = 0x08000000 | 0x00000008 | 0x00000200;
        Command::new("cmd.exe")
            .args(["/c", &helper_path.to_string_lossy()])
            .creation_flags(flags)
            .spawn()
            .map_err(|e| format!("Cannot launch helper: {}", e))?;
    }

    #[cfg(not(windows))]
    {
        let helper_path = exe_dir.join("update_helper.sh");
        let script = format!(
            "#!/bin/sh\nsleep 2\ncp -f '{}' '{}'\nchmod +x '{}'\n'{}' &\nrm -f '$0'\n",
            download_path.to_string_lossy(), current_exe.to_string_lossy(),
            current_exe.to_string_lossy(), current_exe.to_string_lossy(),
        );
        fs::write(&helper_path, &script).map_err(|e| format!("Cannot write helper: {}", e))?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(&helper_path, fs::Permissions::from_mode(0o755)).ok();
        }
        Command::new("sh")
            .arg(&helper_path)
            .spawn()
            .map_err(|e| format!("Cannot launch helper: {}", e))?;
    }

    app.exit(0);
    Ok(())
}

// ── App entry ────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            pick_file,
            pick_folder,
            save_file_dialog,
            read_file_base64,
            save_base64_image,
            write_string_to_file,
            list_files_in_dir,
            convert_images,
            list_source_files,
            preview_rename,
            execute_rename,
            convert_video,
            compress_video,
            save_pdf_page_image,
            load_settings,
            save_settings,
            check_for_updates,
            download_and_install_update,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Deterministic pseudo-noise so lossy encoders can't compress it to nothing.
    fn noise_image(w: u32, h: u32) -> image::DynamicImage {
        let img = image::RgbImage::from_fn(w, h, |x, y| {
            let v = x.wrapping_mul(31).wrapping_add(y.wrapping_mul(17)) ^ x.wrapping_mul(y);
            image::Rgb([(v % 255) as u8, ((v / 3) % 255) as u8, ((v / 7) % 255) as u8])
        });
        image::DynamicImage::ImageRgb8(img)
    }

    #[test]
    fn fit_webp_hits_target() {
        let img = noise_image(512, 512);
        let target = 20 * 1024;
        let data = fit_image_to_target(&img, "webp", target).unwrap();
        assert!(!data.is_empty());
        assert!(data.len() as u64 <= target, "got {} bytes", data.len());
    }

    #[test]
    fn fit_jpeg_hits_target() {
        let img = noise_image(512, 512);
        let target = 30 * 1024;
        let data = fit_image_to_target(&img, "jpeg", target).unwrap();
        assert!(!data.is_empty());
        assert!(data.len() as u64 <= target, "got {} bytes", data.len());
    }

    #[test]
    fn fit_png_downscales_to_target() {
        // Noise PNG at 512x512 is far larger than 60 KB, so this exercises
        // the lossless downscale path
        let img = noise_image(512, 512);
        let target = 60 * 1024;
        let data = fit_image_to_target(&img, "png", target).unwrap();
        assert!(!data.is_empty());
        assert!(data.len() as u64 <= target, "got {} bytes", data.len());
    }

    #[test]
    fn fit_impossible_target_errors() {
        let img = noise_image(256, 256);
        assert!(fit_image_to_target(&img, "png", 50).is_err());
    }

    #[test]
    fn fit_trades_resolution_for_quality() {
        // Pick a target that fits at full res only at ugly quality (2x the
        // minimum-quality floor); the fitter should downscale instead
        let img = noise_image(512, 512);
        let floor = encode_image_to_memory(&img, "jpeg", 5).unwrap().len() as u64;
        let target = floor * 2;
        let data = fit_image_to_target(&img, "jpeg", target).unwrap();
        assert!(data.len() as u64 <= target, "got {} bytes", data.len());
        let decoded = image::load_from_memory(&data).unwrap();
        assert!(decoded.width() < 512, "expected downscale, got {}px wide", decoded.width());
    }

    #[test]
    fn fit_generous_target_needs_no_shrinking() {
        let img = noise_image(64, 64);
        let data = fit_image_to_target(&img, "jpeg", 10 * 1024 * 1024).unwrap();
        assert!(!data.is_empty());
    }

    #[test]
    fn quantized_png_is_smaller_and_decodes() {
        let img = noise_image(128, 128);
        let lossless = encode_image_to_memory(&img, "png", 100).unwrap();
        let lossy = encode_image_to_memory(&img, "png", 80).unwrap();
        assert!(lossy.len() < lossless.len(), "quantized {} >= lossless {}", lossy.len(), lossless.len());
        let decoded = image::load_from_memory(&lossy).unwrap();
        assert_eq!((decoded.width(), decoded.height()), (128, 128));
    }

    #[test]
    fn quantized_png_keeps_alpha() {
        let rgba = image::DynamicImage::ImageRgba8(image::RgbaImage::from_pixel(
            32, 32, image::Rgba([200, 100, 50, 128]),
        ));
        let data = encode_image_to_memory(&rgba, "png", 80).unwrap();
        let decoded = image::load_from_memory(&data).unwrap().to_rgba8();
        let a = decoded.get_pixel(16, 16).0[3];
        assert!((a as i16 - 128).abs() <= 8, "alpha {} drifted too far from 128", a);
    }

    #[test]
    fn jpeg_flattens_alpha() {
        let rgba = image::DynamicImage::ImageRgba8(image::RgbaImage::from_pixel(
            32, 32, image::Rgba([200, 100, 50, 128]),
        ));
        let data = encode_image_to_memory(&rgba, "jpeg", 80).unwrap();
        assert!(!data.is_empty());
    }

    #[test]
    fn probe_parses_ffmpeg_stderr() {
        let stderr = "Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'in.mp4':\n  Duration: 00:01:23.45, start: 0.000000, bitrate: 1000 kb/s\n  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(progressive), 1920x1080 [SAR 1:1 DAR 16:9], 950 kb/s, 30 fps\n  Stream #0:1[0x2](und): Audio: aac (LC) (mp4a / 0x6134706D), 44100 Hz, stereo, fltp, 128 kb/s\n";
        let p = parse_probe_output(stderr).unwrap();
        assert!((p.duration_secs - 83.45).abs() < 0.01);
        assert_eq!(p.width, 1920);
        assert_eq!(p.height, 1080);
        assert!(p.has_audio);
    }

    #[test]
    fn probe_detects_missing_audio() {
        let stderr = "  Duration: 00:00:10.00, start: 0.000000, bitrate: 500 kb/s\n  Stream #0:0: Video: vp9, yuv420p, 640x360, 30 fps\n";
        let p = parse_probe_output(stderr).unwrap();
        assert!((p.duration_secs - 10.0).abs() < 0.001);
        assert_eq!(p.width, 640);
        assert_eq!(p.height, 360);
        assert!(!p.has_audio);
    }

    #[test]
    fn probe_without_video_stream_errors() {
        let stderr = "  Duration: 00:03:00.00, start: 0.000000, bitrate: 128 kb/s\n  Stream #0:0: Audio: mp3, 44100 Hz, stereo, fltp, 128 kb/s\n";
        assert!(parse_probe_output(stderr).is_err());
    }

    #[test]
    fn probe_ignores_attached_pic_cover_art() {
        // mp3 with embedded cover art must not count as a video file
        let stderr = "  Duration: 00:03:00.00, start: 0.000000, bitrate: 320 kb/s\n  Stream #0:0: Audio: mp3, 44100 Hz, stereo, fltp, 320 kb/s\n  Stream #0:1: Video: mjpeg (Baseline), yuvj420p(pc, bt470bg/unknown/unknown), 600x600 [SAR 1:1 DAR 1:1], 90k tbr, 90k tbn (attached pic)\n";
        assert!(parse_probe_output(stderr).is_err());
    }

    #[test]
    fn probe_skips_cover_art_before_real_video() {
        let stderr = "  Duration: 00:00:30.00, start: 0.000000, bitrate: 900 kb/s\n  Stream #0:0: Video: mjpeg, yuvj420p, 1400x1400 (attached pic)\n  Stream #0:1: Video: h264 (High), yuv420p, 640x360, 800 kb/s, 30 fps\n  Stream #0:2: Audio: aac, 44100 Hz, stereo, fltp, 96 kb/s\n";
        let p = parse_probe_output(stderr).unwrap();
        assert_eq!(p.width, 640);
        assert_eq!(p.height, 360);
        assert!(p.has_audio);
    }

    #[test]
    fn auto_cap_height_tiers() {
        assert_eq!(auto_cap_height(100.0), 360);
        assert_eq!(auto_cap_height(300.0), 480);
        assert_eq!(auto_cap_height(500.0), 720);
        assert_eq!(auto_cap_height(1000.0), 1080);
        assert_eq!(auto_cap_height(2000.0), 1440);
        assert_eq!(auto_cap_height(4000.0), 2160);
        assert_eq!(auto_cap_height(8000.0), u32::MAX);
    }
}


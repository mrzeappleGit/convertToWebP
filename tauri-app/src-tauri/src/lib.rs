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
async fn convert_images(args: ConvertImageArgs) -> Result<ConvertResult, String> {
    let source = Path::new(&args.source_path);
    let dest = PathBuf::from(&args.dest_path);
    fs::create_dir_all(&dest).map_err(|e| e.to_string())?;

    let files = gather_image_files(source)?;
    let total = files.len();
    let mut completed = 0u32;
    let mut total_input_size = 0u64;
    let mut total_output_size = 0u64;

    let q = if args.compress { args.quality } else { 100 };

    for file_path in &files {
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

        save_image(&img, &out_path, &args.format, q)?;

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
    use image::ImageFormat;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    match format {
        "png" => img.save_with_format(path, ImageFormat::Png).map_err(|e| e.to_string()),
        "gif" => img.save_with_format(path, ImageFormat::Gif).map_err(|e| e.to_string()),
        "bmp" => img.save_with_format(path, ImageFormat::Bmp).map_err(|e| e.to_string()),
        "tiff" => img.save_with_format(path, ImageFormat::Tiff).map_err(|e| e.to_string()),
        "ico" => img.save_with_format(path, ImageFormat::Ico).map_err(|e| e.to_string()),
        "webp" => img.save_with_format(path, ImageFormat::WebP).map_err(|e| e.to_string()),
        "avif" => img.save_with_format(path, ImageFormat::Avif).map_err(|e| e.to_string()),
        _ => {
            // JPEG and fallback
            let mut buf = std::io::BufWriter::new(
                fs::File::create(path).map_err(|e| e.to_string())?
            );
            let encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(&mut buf, quality);
            img.write_with_encoder(encoder).map_err(|e| e.to_string())
        }
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

    let mut child = Command::new(&ffmpeg)
        .args(&cmd_args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .creation_flags(0x08000000) // CREATE_NO_WINDOW on Windows
        .spawn()
        .map_err(|e| format!("Failed to start FFmpeg: {}", e))?;

    // Stream FFmpeg stderr to frontend
    if let Some(stderr) = child.stderr.take() {
        let app_handle = app.clone();
        std::thread::spawn(move || {
            let reader = BufReader::new(stderr);
            for line in reader.lines() {
                if let Ok(line) = line {
                    let _ = app_handle.emit("ffmpeg-log", &line);
                }
            }
        });
    }

    let status = child.wait().map_err(|e| format!("FFmpeg error: {}", e))?;
    if status.success() {
        Ok(output.to_string_lossy().to_string())
    } else {
        Err(format!("FFmpeg exited with code {}", status.code().unwrap_or(-1)))
    }
}

fn find_ffmpeg(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    // Check bundled resource first
    if let Ok(resource_dir) = app.path().resource_dir() {
        let bundled = resource_dir.join("resources").join("ffmpeg.exe");
        if bundled.exists() { return Ok(bundled); }
        let bundled2 = resource_dir.join("ffmpeg.exe");
        if bundled2.exists() { return Ok(bundled2); }
    }
    // Check alongside exe
    if let Ok(exe_dir) = std::env::current_exe() {
        if let Some(dir) = exe_dir.parent() {
            let local = dir.join("ffmpeg.exe");
            if local.exists() { return Ok(local); }
        }
    }
    // Fall back to PATH
    if Command::new("ffmpeg").arg("-version").output().is_ok() {
        return Ok(PathBuf::from("ffmpeg"));
    }
    Err("FFmpeg not found. Place ffmpeg.exe next to the application or install it to PATH.".into())
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

// ── Settings persistence (%APPDATA%/mts-studios/WebWeaverKit/) ───

const SETTINGS_DIR: &str = "mts-studios";
const SETTINGS_APP: &str = "WebWeaverKit";
const SETTINGS_FILE: &str = "settings.json";

fn settings_path() -> PathBuf {
    let base = if cfg!(windows) {
        std::env::var("APPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(|_| dirs::config_dir().unwrap_or_else(|| PathBuf::from(".")))
    } else {
        dirs::config_dir().unwrap_or_else(|| PathBuf::from("."))
    };
    base.join(SETTINGS_DIR).join(SETTINGS_APP)
}

#[tauri::command]
fn load_settings() -> Result<serde_json::Value, String> {
    let path = settings_path().join(SETTINGS_FILE);
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
const CURRENT_VERSION: &str = "1.12.0";

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
        .header("User-Agent", format!("WebWeaverKit/{}", CURRENT_VERSION))
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
            preview_rename,
            execute_rename,
            convert_video,
            save_pdf_page_image,
            load_settings,
            save_settings,
            check_for_updates,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}


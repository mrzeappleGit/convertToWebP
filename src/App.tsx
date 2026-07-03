import { useState, useRef, useEffect } from "react";
import "./styles/theme.css";
import "./styles/layout.css";
import { ImageConverter } from "./components/ImageConverter";
import { FileRenamer } from "./components/FileRenamer";
import { PdfToImage } from "./components/PdfToImage";
import { VideoConverter } from "./components/VideoConverter";
import { VideoCompressor } from "./components/VideoCompressor";
import { TextFormatter } from "./components/TextFormatter";
import { SvgGenerator } from "./components/SvgGenerator";
import { ImageCropper } from "./components/ImageCropper";
import { THEMES, applyTheme } from "./themes";
import { useSettings } from "./useSettings";
import { invoke } from "./invoke";

const VERSION = "2.1.0";

const TABS = [
  { id: "converter", label: "Converter", icon: "🖼" },
  { id: "renamer", label: "File Renamer", icon: "✏" },
  { id: "pdf", label: "PDF to Image", icon: "📄" },
  { id: "video", label: "Video Converter", icon: "▶" },
  { id: "vcompress", label: "Video Compressor", icon: "🗜" },
  { id: "text", label: "Text Formatter", icon: "Aa" },
  { id: "crop", label: "Image Crop", icon: "✂" },
  { id: "svg", label: "Image Mapping", icon: "◎" },
] as const;

/** The CipherLoom weave mark — three warp threads crossed by the weft. */
function CipherLoomMark({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="128 184 768 656" aria-hidden="true">
      <line x1="352" y1="232" x2="352" y2="412" stroke="#00E5FF" strokeWidth="92" />
      <line x1="352" y1="612" x2="352" y2="792" stroke="#00E5FF" strokeWidth="92" />
      <line x1="512" y1="232" x2="512" y2="792" stroke="#00E5FF" strokeWidth="92" />
      <line x1="672" y1="232" x2="672" y2="412" stroke="#00E5FF" strokeWidth="92" />
      <line x1="672" y1="612" x2="672" y2="792" stroke="#00E5FF" strokeWidth="92" />
      <line x1="176" y1="512" x2="432" y2="512" stroke="#FF2A93" strokeWidth="132" />
      <line x1="592" y1="512" x2="848" y2="512" stroke="#FF2A93" strokeWidth="132" />
    </svg>
  );
}

type TabId = (typeof TABS)[number]["id"];

const LICENSES = [
  { name: "FFmpeg", text: "This software uses libraries from the FFmpeg project under the LGPLv2.1.", url: "http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html" },
  { name: "JPEG XL", text: 'This software includes the JPEG XL codec (libjxl) under the BSD 3-Clause License.\n\nCopyright (c) the JPEG XL Project Authors. All rights reserved.\n\nRedistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:\n\n1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.\n\n2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.\n\n3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.' },
  { name: "image (Rust)", text: "The image crate is dual-licensed under MIT and Apache 2.0.\n\nCopyright (c) 2014 PistonDevelopers.\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files.", url: "https://github.com/image-rs/image/blob/main/LICENSE-MIT" },
  { name: "pdf.js", text: "PDF.js is licensed under the Apache License 2.0.\n\nCopyright (c) Mozilla and individual contributors.", url: "https://github.com/nicolo-ribaudo/pdfjs-dist/blob/main/LICENSE" },
  { name: "Tauri", text: "Tauri is dual-licensed under MIT and Apache 2.0.\n\nCopyright (c) 2019-2025 Tauri Programme within The Commons Conservancy.", url: "https://github.com/nicolo-ribaudo/tauri/blob/dev/LICENSE_MIT" },
];

interface UpdateInfo {
  available: boolean;
  currentVersion: string;
  latestVersion: string;
  downloadUrl: string;
  releaseNotes: string;
}

async function openUrl(url: string) {
  try {
    if (window.__TAURI_INTERNALS__) {
      const { open } = await import("@tauri-apps/plugin-shell");
      await open(url);
    } else { window.open(url, "_blank"); }
  } catch { window.open(url, "_blank"); }
}

function App() {
  const { settings, updateSettings } = useSettings();
  const [tab, setTab] = useState<TabId>("converter");
  const [menuOpen, setMenuOpen] = useState(false);
  const [themeSub, setThemeSub] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [licOpen, setLicOpen] = useState(false);
  const [licIdx, setLicIdx] = useState(0);
  const menuRef = useRef<HTMLDivElement>(null);

  // Update state
  const [updateInfo, setUpdateInfo] = useState<UpdateInfo | null>(null);
  const [updateChecking, setUpdateChecking] = useState(false);
  const [updateChecked, setUpdateChecked] = useState(false);
  const [updateInstalling, setUpdateInstalling] = useState(false);
  const [updateProgress, setUpdateProgress] = useState("");

  // Listen for update progress events
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    (async () => {
      if (window.__TAURI_INTERNALS__) {
        const { listen } = await import("@tauri-apps/api/event");
        unlisten = await listen<string>("update-progress", (e) => setUpdateProgress(e.payload));
      }
    })();
    return () => { unlisten?.(); };
  }, []);

  // Apply theme from settings
  useEffect(() => { applyTheme(settings.theme); }, [settings.theme]);

  // Auto-check for updates on launch
  useEffect(() => {
    const timer = setTimeout(() => checkUpdates(true), 2000);
    return () => clearTimeout(timer);
  }, []);

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return;
    const h = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false); setThemeSub(false);
      }
    };
    setTimeout(() => document.addEventListener("mousedown", h), 0);
    return () => document.removeEventListener("mousedown", h);
  }, [menuOpen]);

  const handleThemeChange = (id: string) => {
    updateSettings({ theme: id });
    applyTheme(id);
    setMenuOpen(false); setThemeSub(false);
  };

  const checkUpdates = async (silent = false) => {
    setUpdateChecking(true);
    try {
      const info = await invoke<UpdateInfo>("check_for_updates");
      if (info) {
        setUpdateInfo(info);
        setUpdateChecked(true);
      }
      if (!silent && !info.available) {
        // Will show "up to date" in the about dialog
      }
    } catch (e) {
      if (!silent) console.error("Update check failed:", e);
    } finally {
      setUpdateChecking(false);
    }
  };

  // Window controls
  const windowMinimize = async () => {
    try {
      if (window.__TAURI_INTERNALS__) {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().minimize();
      }
    } catch {}
  };
  const windowToggleMaximize = async () => {
    try {
      if (window.__TAURI_INTERNALS__) {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().toggleMaximize();
      }
    } catch {}
  };
  const windowClose = async () => {
    try {
      if (window.__TAURI_INTERNALS__) {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().close();
      }
    } catch {}
  };

  const hasUpdate = updateInfo?.available === true;
  const activeLabel = TABS.find(t => t.id === tab)?.label ?? "";

  const startDrag = async (e: React.MouseEvent) => {
    // Only drag from the titlebar background, not from buttons
    if ((e.target as HTMLElement).closest("button")) return;
    try {
      if (window.__TAURI_INTERNALS__) {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().startDragging();
      }
    } catch {}
  };

  return (
    <div className="wwk-app">
      {/* Titlebar */}
      <div className="wwk-titlebar" onMouseDown={startDrag}>
        <div className="wwk-brand">
          <span className="glyph" style={{ display: "inline-flex", alignItems: "center" }}><CipherLoomMark size={14} /></span>
          <strong>CipherLoom</strong>
          <span style={{ marginLeft: 4, color: "var(--text-dim)" }}>· {activeLabel}</span>
        </div>
        <div style={{ flex: 1 }} />
        <div className="wwk-window-controls">
          <button className="wwk-winbtn" onClick={windowMinimize} aria-label="Minimize">
            <svg width="10" height="1" viewBox="0 0 10 1"><rect width="10" height="1" fill="currentColor"/></svg>
          </button>
          <button className="wwk-winbtn" onClick={windowToggleMaximize} aria-label="Maximize">
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.2"><rect x="0.6" y="0.6" width="8.8" height="8.8" rx="1"/></svg>
          </button>
          <button className="wwk-winbtn close" onClick={windowClose} aria-label="Close">
            <svg width="10" height="10" viewBox="0 0 10 10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"><line x1="1" y1="1" x2="9" y2="9"/><line x1="9" y1="1" x2="1" y2="9"/></svg>
          </button>
        </div>
      </div>

      {/* Tabs + Menu */}
      <div className="wwk-tabrow">
        <div className="wwk-tabs">
          {TABS.map(t => (
            <button key={t.id} className={`wwk-tab ${t.id === tab ? "active" : ""}`} onClick={() => setTab(t.id)}>
              <span className="tab-icon">{t.icon}</span> <span>{t.label}</span>
            </button>
          ))}
        </div>
        <div ref={menuRef} style={{ position: "relative", display: "flex", alignItems: "center", flexShrink: 0 }}>
          <button className={`wwk-iconbtn ${menuOpen ? "active" : ""}`}
            onClick={e => { e.stopPropagation(); setMenuOpen(!menuOpen); setThemeSub(false); }}
            style={{ position: "relative" }}>
            ☰
            {hasUpdate && (
              <span style={{
                position: "absolute", top: 4, right: 4, width: 7, height: 7,
                borderRadius: "50%", background: "var(--primary)",
                boxShadow: "0 0 8px var(--primary-glow)",
              }} />
            )}
          </button>
          {menuOpen && (
            <div className="wwk-menu">
              <div className="wwk-menu-item" onClick={() => setThemeSub(!themeSub)}>
                <span className="item-left">⚙ Theme</span>
                <span className="item-right">
                  <span>{THEMES.find(t => t.id === settings.theme)?.name}</span>
                  <span style={{ fontSize: 9, transition: "transform 0.15s", transform: themeSub ? "rotate(90deg)" : "none" }}>›</span>
                </span>
              </div>
              {themeSub && (
                <div className="wwk-submenu">
                  {THEMES.map(th => (
                    <div key={th.id} className={`wwk-theme-row ${settings.theme === th.id ? "active" : ""}`}
                      onClick={() => handleThemeChange(th.id)}>
                      <span className="wwk-theme-swatch" style={{
                        background: `linear-gradient(135deg, ${th.swatch[0]} 0 50%, ${th.swatch[1]} 50% 80%, ${th.swatch[2]} 80%)`
                      }} />
                      <span style={{ flex: 1 }}>{th.name}</span>
                      {settings.theme === th.id && <span style={{ color: "var(--primary)" }}>✓</span>}
                    </div>
                  ))}
                </div>
              )}
              <div className="wwk-menu-sep" />
              <div className="wwk-menu-item" onClick={() => { checkUpdates(); setMenuOpen(false); setAboutOpen(true); }}>
                <span className="item-left">
                  {hasUpdate ? "🔔" : "ℹ"} {hasUpdate ? "Update Available" : "About"}
                </span>
                {hasUpdate && <span style={{ color: "var(--primary)", fontSize: 11 }}>{updateInfo?.latestVersion}</span>}
              </div>
              <div className="wwk-menu-item" onClick={() => { setLicOpen(true); setLicIdx(0); setMenuOpen(false); }}>
                <span className="item-left">📋 Licenses</span>
              </div>
              <div className="wwk-menu-sep" />
              <div className="wwk-menu-item" style={{ color: "var(--text-dim)", fontSize: 11, cursor: "default" }}>
                <span>CipherLoom</span><span className="mono tnum">v{VERSION}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="wwk-content">
        {tab === "converter" && <ImageConverter />}
        {tab === "renamer" && <FileRenamer />}
        {tab === "pdf" && <PdfToImage />}
        {/* Video tools stay mounted while their FFmpeg jobs run in the backend,
            so switching tabs doesn't lose the log/result or re-enable the button */}
        <div style={{ display: tab === "video" ? "contents" : "none" }}><VideoConverter /></div>
        <div style={{ display: tab === "vcompress" ? "contents" : "none" }}><VideoCompressor /></div>
        {tab === "text" && <TextFormatter />}
        {tab === "crop" && <ImageCropper />}
        {tab === "svg" && <SvgGenerator />}
      </div>

      {/* About / Update Dialog */}
      {aboutOpen && (
        <div className="wwk-overlay" onClick={() => setAboutOpen(false)}>
          <div className="wwk-dialog" onClick={e => e.stopPropagation()}>
            <div className="wwk-dialog-head">
              <div className="row gap-3 center">
                <div style={{
                  width: 38, height: 38, display: "grid", placeItems: "center",
                  background: "var(--primary-soft)", borderRadius: 9,
                  border: "1px solid color-mix(in oklab, var(--primary) 30%, transparent)",
                  color: "var(--primary)", fontSize: 18,
                  boxShadow: "0 0 24px var(--primary-glow)",
                }}><CipherLoomMark size={22} /></div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>CipherLoom</div>
                  <div className="dim mono tnum" style={{ fontSize: 11, marginTop: 2 }}>v{VERSION}</div>
                </div>
              </div>
              <button className="wwk-iconbtn" onClick={() => setAboutOpen(false)}>✕</button>
            </div>
            <div className="wwk-dialog-body">
              <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 12.5, lineHeight: 1.6 }}>
                A small workshop of tools for designers and developers — convert and compress images,
                batch-rename files, slice PDFs, transcode and shrink video to a target size, mangle
                text, crop images, and trace SVG image maps.
              </p>

              {/* Update status */}
              <div style={{
                marginTop: 16, padding: "10px 12px", borderRadius: 8,
                background: hasUpdate ? "var(--primary-soft)" : "var(--surface-1)",
                border: `1px solid ${hasUpdate ? "color-mix(in oklab, var(--primary) 38%, transparent)" : "var(--border)"}`,
              }}>
                {updateChecking ? (
                  <div className="dim" style={{ fontSize: 12 }}>Checking for updates…</div>
                ) : hasUpdate ? (
                  <div>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--primary)", marginBottom: 4 }}>
                      Update available: {updateInfo!.latestVersion}
                    </div>
                    {updateInfo!.releaseNotes && (
                      <div className="dim" style={{ fontSize: 11, lineHeight: 1.5, maxHeight: 80, overflow: "auto", marginBottom: 8 }}>
                        {updateInfo!.releaseNotes.slice(0, 300)}
                      </div>
                    )}
                    {updateInstalling ? (
                      <div className="dim" style={{ fontSize: 12 }}>{updateProgress || "Starting update..."}</div>
                    ) : (
                      <button className="wwk-btn primary sm" onClick={async () => {
                        setUpdateInstalling(true);
                        setUpdateProgress("Starting download...");
                        try {
                          await invoke("download_and_install_update", { url: updateInfo!.downloadUrl });
                        } catch (e: any) {
                          setUpdateProgress(`Error: ${e}`);
                          setUpdateInstalling(false);
                        }
                      }}>
                        ⬇ Install Update
                      </button>
                    )}
                  </div>
                ) : updateChecked ? (
                  <div className="row between center">
                    <span className="dim" style={{ fontSize: 12 }}>You're on the latest version</span>
                    <span className="wwk-dot ok" />
                  </div>
                ) : (
                  <button className="wwk-btn sm" onClick={() => checkUpdates()}>Check for updates</button>
                )}
              </div>

              <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, fontSize: 11.5 }}>
                <div className="row between" style={{ padding: "8px 10px", background: "var(--surface-1)", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <span className="dim">Runtime</span><span className="mono tnum">Tauri 2.11</span>
                </div>
                <div className="row between" style={{ padding: "8px 10px", background: "var(--surface-1)", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <span className="dim">FFmpeg</span><span className="mono tnum">bundled</span>
                </div>
              </div>
              <div style={{ marginTop: 16, fontSize: 11 }}>
                <span className="dim" style={{ cursor: "pointer" }} onClick={() => openUrl("https://www.matthewstevens.me")}>
                  © 2025 Matthew Thomas Stevens Studios LLC
                </span>
              </div>
              <div style={{ marginTop: 6 }}>
                <span style={{ fontSize: 11, color: "var(--secondary)", cursor: "pointer" }}
                  onClick={() => openUrl("https://github.com/mrzeappleGit/convertToWebP")}>
                  GitHub Repository ↗
                </span>
              </div>
            </div>
            <div className="wwk-dialog-foot">
              <button className="wwk-btn primary" onClick={() => setAboutOpen(false)}>Done</button>
            </div>
          </div>
        </div>
      )}

      {/* Licenses */}
      {licOpen && (
        <div className="wwk-overlay" onClick={() => setLicOpen(false)}>
          <div className="wwk-dialog" style={{ width: 560 }} onClick={e => e.stopPropagation()}>
            <div className="wwk-dialog-head">
              <div style={{ fontSize: 14, fontWeight: 600 }}>Licenses</div>
              <button className="wwk-iconbtn" onClick={() => setLicOpen(false)}>✕</button>
            </div>
            <div className="wwk-dialog-body">
              <div className="wwk-license-tabs">
                {LICENSES.map((l, i) => (
                  <button key={l.name} className={`wwk-license-tab ${licIdx === i ? "active" : ""}`}
                    onClick={() => setLicIdx(i)}>{l.name}</button>
                ))}
              </div>
              <div style={{
                maxHeight: 260, overflow: "auto", background: "var(--bg)",
                borderRadius: 8, padding: 16, border: "1px solid var(--border)",
                fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-muted)",
                whiteSpace: "pre-wrap", lineHeight: 1.6,
              }}>
                {LICENSES[licIdx].text}
                {LICENSES[licIdx].url && (
                  <span style={{ display: "block", marginTop: 12, color: "var(--secondary)", cursor: "pointer" }}
                    onClick={() => openUrl(LICENSES[licIdx].url!)}>
                    View full license ↗
                  </span>
                )}
              </div>
            </div>
            <div className="wwk-dialog-foot">
              <button className="wwk-btn primary" onClick={() => setLicOpen(false)}>Done</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;

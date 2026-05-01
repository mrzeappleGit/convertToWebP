import { useState } from "react";
import { Section } from "./Section";
import { PillSelector } from "./PillSelector";
import { invoke } from "../invoke";

const ALL_FORMATS = ["WebP", "PNG", "JPEG", "JPEGLI", "AVIF", "TIFF", "BMP", "GIF", "ICO"];

function Check({ checked, onChange, label, sub }: { checked: boolean; onChange: (v: boolean) => void; label: string; sub?: string }) {
  return (
    <label className="wwk-check">
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
      <span className="wwk-check-box"><span className="check-icon">✓</span></span>
      <span>{label}{sub && <span className="dim" style={{ marginLeft: 6, fontSize: 11 }}>{sub}</span>}</span>
    </label>
  );
}

export function ImageConverter() {
  const [sourcePath, setSourcePath] = useState("");
  const [destPath, setDestPath] = useState("");
  const [format, setFormat] = useState("WebP");
  const [convert, setConvert] = useState(true);
  const [compress, setCompress] = useState(true);
  const [rename, setRename] = useState(false);
  const [resize, setResize] = useState(false);
  const [quality, setQuality] = useState(82);
  const [resizePercent, setResizePercent] = useState(75);
  const [progress, setProgress] = useState(0);
  const [running, setRunning] = useState(false);
  const [stats, setStats] = useState("");

  const browse = async (type: "file" | "folder", setter: (v: string) => void) => {
    const cmd = type === "folder" ? "pick_folder" : "pick_file";
    const args = type === "folder" ? { title: "Select folder" } : {
      title: "Select image", filters: [{ name: "Images", extensions: ["jpg","jpeg","png","gif","bmp","webp","tiff","avif"] }],
    };
    const path = await invoke<string | null>(cmd, args);
    if (path) setter(path);
  };

  const handleRun = async () => {
    if (!sourcePath || !destPath) return;
    setRunning(true); setProgress(0); setStats("");
    try {
      const r = await invoke<{ files_processed: number; total_files: number; input_size_bytes: number; output_size_bytes: number }>(
        "convert_images", { args: { sourcePath, destPath, format: format.toLowerCase(), quality, convert, compress, rename, resize, resizePercent } }
      );
      setProgress(100);
      const saved = r.input_size_bytes > 0 ? ((1 - r.output_size_bytes / r.input_size_bytes) * 100).toFixed(0) : "0";
      const inMb = (r.input_size_bytes / 1048576).toFixed(1);
      setStats(`${r.files_processed} files · saved ${saved}% (${inMb} MB input)`);
    } catch (e: any) { setStats(`Error: ${e}`); }
    finally { setRunning(false); }
  };

  return (
    <div className="wwk-twocol">
      <div className="wwk-panel">
        <div className="wwk-panel-scroll">
          <Section title="Source">
            <div className="wwk-field-row">
              <input className="wwk-input" value={sourcePath} onChange={e => setSourcePath(e.target.value)} placeholder="Drop a folder or file…" />
              <button className="wwk-btn" onClick={() => browse("folder", setSourcePath)}>📁 Folder</button>
            </div>
            <div style={{ height: 6 }} />
            <div className="wwk-field-row">
              <input className="wwk-input" value="" readOnly placeholder="Or pick a single file…" />
              <button className="wwk-btn" onClick={() => browse("file", setSourcePath)}>📄 File</button>
            </div>
          </Section>

          <Section title="Destination">
            <div className="wwk-field-row">
              <input className="wwk-input" value={destPath} onChange={e => setDestPath(e.target.value)} placeholder="Output folder" />
              <button className="wwk-btn" onClick={() => browse("folder", setDestPath)}>📁 Browse</button>
            </div>
          </Section>

          <Section title="Output Format">
            <PillSelector options={ALL_FORMATS} value={format} onChange={setFormat} />
          </Section>

          <Section title="Options">
            <Check checked={convert} onChange={setConvert} label="Convert" sub={`→ .${format.toLowerCase()}`} />
            <Check checked={compress} onChange={setCompress} label="Compress" />
            {compress && (
              <div style={{ marginLeft: 25, marginRight: 4 }}>
                <div className="dim" style={{ fontSize: 11, marginTop: -2 }}>Quality target — higher keeps more detail</div>
                <div className="wwk-slider-row">
                  <input type="range" className="wwk-slider" min={0} max={100} value={quality} onChange={e => setQuality(Number(e.target.value))} />
                  <span className="wwk-slider-val">{quality}%</span>
                </div>
              </div>
            )}
            <Check checked={rename} onChange={setRename} label="Rename to slug" sub="kebab-case, ascii-safe" />
            <Check checked={resize} onChange={setResize} label="Resize" />
            {resize && (
              <div style={{ marginLeft: 25, marginRight: 4 }}>
                <div className="dim" style={{ fontSize: 11, marginTop: -2 }}>Scale relative to original dimensions</div>
                <div className="wwk-slider-row">
                  <input type="range" className="wwk-slider" min={1} max={100} value={resizePercent} onChange={e => setResizePercent(Number(e.target.value))} />
                  <span className="wwk-slider-val">{resizePercent}%</span>
                </div>
              </div>
            )}
          </Section>
        </div>

        <div className="wwk-panel-pinned">
          <div className="row between center" style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 11.5 }}>
              {stats ? (
                <span style={{ color: "var(--primary)" }}>{stats}</span>
              ) : (
                <span className="dim">Ready to convert</span>
              )}
            </div>
            {progress > 0 && <span className="mono dim tnum">{progress}%</span>}
          </div>
          <div className="wwk-progress" style={{ marginBottom: 12 }}>
            <div className="wwk-progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <button className="wwk-btn primary block lg" onClick={handleRun} disabled={running || !sourcePath || !destPath}>
            ▶ {running ? "Converting…" : "Run"}
          </button>
        </div>
      </div>

      <div className="wwk-panel">
        <div style={{ flex: "0 0 48%", minHeight: 0, padding: 22, paddingBottom: 11, display: "flex", flexDirection: "column" }}>
          <Section title="Preview" />
          <div className="wwk-preview">IMAGE PREVIEW</div>
        </div>
        <div style={{ flex: 1, minHeight: 0, padding: "11px 22px 22px", display: "flex", flexDirection: "column" }}>
          <div className="row between center" style={{ marginBottom: 12 }}>
            <div className="wwk-section-label"><span>Queue</span></div>
            <span className="mono dim tnum" style={{ fontSize: 11 }}>No files</span>
          </div>
          <div className="wwk-queue" style={{ display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-dim)", fontSize: 12 }}>
            Select a source to populate the queue
          </div>
        </div>
      </div>
    </div>
  );
}

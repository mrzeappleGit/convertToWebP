import { useState, useEffect, useRef } from "react";
import { Section } from "./Section";
import { PillSelector } from "./PillSelector";
import { invoke } from "../invoke";

const UNIT_BYTES: Record<string, number> = { MB: 1048576, GB: 1073741824 };

interface CompressResult {
  outputPath: string;
  inputSizeBytes: number;
  outputSizeBytes: number;
  targetSizeBytes: number;
  videoKbps: number;
  audioKbps: number;
  resolution: string;
  durationSecs: number;
}

function formatSize(bytes: number): string {
  if (bytes >= 1073741824) return `${(bytes / 1073741824).toFixed(2)} GB`;
  if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}

export function VideoCompressor() {
  const [src, setSrc] = useState("");
  const [dest, setDest] = useState("");
  const [fmt, setFmt] = useState("mp4");
  const [size, setSize] = useState("25");
  const [unit, setUnit] = useState("MB");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<CompressResult | null>(null);
  const [error, setError] = useState("");
  const [log, setLog] = useState<string[]>([]);
  const logEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let cancelled = false;
    (async () => {
      if (window.__TAURI_INTERNALS__) {
        const { listen } = await import("@tauri-apps/api/event");
        const un = await listen<string>("compress-log", e => setLog(p => [...p, e.payload]));
        if (cancelled) un(); else unlisten = un;
      }
    })();
    return () => { cancelled = true; unlisten?.(); };
  }, []);
  useEffect(() => { logEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [log]);

  const browse = async (type: "file" | "folder", setter: (v: string) => void) => {
    const cmd = type === "folder" ? "pick_folder" : "pick_file";
    const a = type === "folder" ? { title: "Output folder" } : {
      title: "Select video", filters: [{ name: "Video", extensions: ["mp4","webm","avi","mkv","mov","flv","wmv"] }],
    };
    const p = await invoke<string | null>(cmd, a);
    if (p) setter(p);
  };

  const targetBytes = Math.round((Number(size) || 0) * UNIT_BYTES[unit]);
  const canRun = !!src && targetBytes > 0 && !running;

  const handleCompress = async () => {
    if (!canRun) return;
    setRunning(true); setResult(null); setError("");
    setLog([`Target: ${formatSize(targetBytes)} — quality and resolution are picked automatically`]);
    try {
      const r = await invoke<CompressResult>("compress_video", {
        args: { sourcePath: src, destPath: dest, format: fmt, targetSizeBytes: targetBytes },
      });
      setResult(r);
      setLog(p => [...p, `\n✓ Done: ${r.outputPath}`]);
    } catch (e) {
      setError(String(e));
      setLog(p => [...p, `\n✕ Error: ${e}`]);
    } finally { setRunning(false); }
  };

  return (
    <div className="wwk-twocol">
      <div className="wwk-panel">
        <div className="wwk-panel-scroll">
          <Section title="Source Video">
            <div className="wwk-field-row">
              <input className="wwk-input" value={src} onChange={e => setSrc(e.target.value)} placeholder="Select a video file…" />
              <button className="wwk-btn" onClick={() => browse("file", setSrc)}>📁 Browse</button>
            </div>
          </Section>
          <Section title="Destination">
            <div className="wwk-field-row">
              <input className="wwk-input" value={dest} onChange={e => setDest(e.target.value)} placeholder="Same as source…" />
              <button className="wwk-btn" onClick={() => browse("folder", setDest)}>📁 Browse</button>
            </div>
          </Section>
          <Section title="Format">
            <PillSelector options={["mp4", "webm"].map(v => ({ value: v, label: v.toUpperCase() }))} value={fmt} onChange={setFmt} />
          </Section>
          <Section title="Target Size">
            <div className="wwk-field-row">
              <input className="wwk-input" type="number" min={1} value={size}
                onChange={e => setSize(e.target.value)} placeholder="e.g. 25" style={{ maxWidth: 120 }} />
              <PillSelector options={["MB", "GB"]} value={unit} onChange={setUnit} />
            </div>
            <div className="dim" style={{ fontSize: 11, marginTop: 6, lineHeight: 1.5 }}>
              Bitrate and resolution are chosen automatically so the output fits the target size (two-pass encode).
            </div>
          </Section>
          {result && (
            <Section title="Result">
              <div style={{ display: "grid", gap: 6, fontSize: 12 }}>
                <div className="row between"><span className="dim">Output size</span>
                  <span className="mono tnum" style={{ color: "var(--primary)" }}>{formatSize(result.outputSizeBytes)}</span></div>
                <div className="row between"><span className="dim">Target</span>
                  <span className="mono tnum">{formatSize(result.targetSizeBytes)}</span></div>
                <div className="row between"><span className="dim">Original</span>
                  <span className="mono tnum">{formatSize(result.inputSizeBytes)}</span></div>
                <div className="row between"><span className="dim">Video / audio bitrate</span>
                  <span className="mono tnum">{result.videoKbps} / {result.audioKbps} kbps</span></div>
                <div className="row between"><span className="dim">Resolution</span>
                  <span className="mono tnum">{result.resolution}</span></div>
              </div>
            </Section>
          )}
          {error && (
            <Section title="Error">
              <div style={{ fontSize: 12, color: "#e85d5d", lineHeight: 1.5 }}>{error}</div>
            </Section>
          )}
        </div>
        <div className="wwk-panel-pinned">
          <button className="wwk-btn primary block lg" onClick={handleCompress} disabled={!canRun}>
            🗜 {running ? "Compressing…" : "Compress"}
          </button>
        </div>
      </div>

      <div className="wwk-panel">
        <div style={{ flex: 1, padding: 22, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div className="row between center" style={{ marginBottom: 12 }}>
            <div className="wwk-section-label"><span>FFmpeg Log</span></div>
            {running && <span className="row gap-1 center" style={{ fontSize: 11 }}><span className="wwk-dot active" /> live</span>}
          </div>
          <div className="wwk-log">
            {log.length === 0 ? "Output will appear here…" : log.join("\n")}
            <div ref={logEnd} />
          </div>
        </div>
      </div>
    </div>
  );
}

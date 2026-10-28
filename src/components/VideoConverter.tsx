import { useState, useEffect, useRef } from "react";
import { Section } from "./Section";
import { PillSelector } from "./PillSelector";
import { invoke } from "../invoke";
import { usePersistentState } from "../useSettings";

const V_CODECS: Record<string, string[]> = { mp4: ["H.264", "H.265 (HEVC)"], webm: ["VP9"] };
const V_MAP: Record<string, string> = { "H.264": "libx264", "H.265 (HEVC)": "libx265", "VP9": "libvpx-vp9" };
const A_CODECS = ["AAC", "Opus"];
const A_MAP: Record<string, string> = { AAC: "aac", Opus: "libopus" };
const CRF_DEF: Record<string, number> = { "H.264": 23, "H.265 (HEVC)": 28, VP9: 31 };

export function VideoConverter() {
  const [src, setSrc] = usePersistentState("cipherloom.video.src", "");
  const [dest, setDest] = usePersistentState("cipherloom.video.dest", "");
  const [fmt, setFmt] = usePersistentState("cipherloom.video.fmt", "mp4");
  const [vc, setVc] = usePersistentState("cipherloom.video.vc", "H.264");
  const [ac, setAc] = usePersistentState("cipherloom.video.ac", "AAC");
  const [crf, setCrf] = usePersistentState("cipherloom.video.crf", 23);
  const [res, setRes] = usePersistentState("cipherloom.video.res", "original");
  const [converting, setConverting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [log, setLog] = useState<string[]>([]);
  const logEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const unlisteners: (() => void)[] = [];
    (async () => {
      if (window.__TAURI_INTERNALS__) {
        const { listen } = await import("@tauri-apps/api/event");
        unlisteners.push(await listen<string>("ffmpeg-log", e => setLog(p => [...p, e.payload])));
        unlisteners.push(await listen<number>("ffmpeg-log-progress", e => setProgress(Math.round(e.payload))));
      }
    })();
    return () => unlisteners.forEach(u => u());
  }, []);
  useEffect(() => { logEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [log]);

  const onFmtChange = (f: string) => {
    setFmt(f);
    const codecs = V_CODECS[f];
    setVc(codecs[0]);
    setCrf(CRF_DEF[codecs[0]] ?? 23);
    setAc(f === "webm" ? "Opus" : "AAC");
  };

  const browse = async (type: "file" | "folder", setter: (v: string) => void) => {
    const cmd = type === "folder" ? "pick_folder" : "pick_file";
    const a = type === "folder" ? { title: "Output folder" } : {
      title: "Select video", filters: [{ name: "Video", extensions: ["mp4","webm","avi","mkv","mov","flv","wmv"] }],
    };
    const p = await invoke<string | null>(cmd, a);
    if (p) setter(p);
  };

  const handleConvert = async () => {
    if (!src) return;
    setConverting(true); setProgress(0); setLog(["Starting FFmpeg…"]);
    try {
      const r = await invoke<string>("convert_video", {
        args: { sourcePath: src, destPath: dest, format: fmt, videoCodec: V_MAP[vc], audioCodec: A_MAP[ac], crf, resolution: res },
      });
      setProgress(100);
      setLog(p => [...p, `\n✓ Done: ${r}`]);
    } catch (e: any) { setLog(p => [...p, `\n✕ Error: ${e}`]); }
    finally { setConverting(false); }
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
            <PillSelector options={["mp4", "webm"].map(v => ({ value: v, label: v.toUpperCase() }))} value={fmt} onChange={onFmtChange} />
          </Section>
          <Section title="Encoding">
            <div className="wwk-field">
              <span className="wwk-label">Video codec</span>
              <select className="wwk-input" style={{ cursor: "pointer" }} value={vc}
                onChange={e => { setVc(e.target.value); setCrf(CRF_DEF[e.target.value] ?? 23); }}>
                {(V_CODECS[fmt] ?? []).map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div className="wwk-field">
              <span className="wwk-label">Audio codec</span>
              <select className="wwk-input" style={{ cursor: "pointer" }} value={ac} onChange={e => setAc(e.target.value)}>
                {A_CODECS.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div className="wwk-field">
              <span className="wwk-label">Quality (CRF) — lower = better</span>
              <div className="wwk-slider-row">
                <input type="range" className="wwk-slider" min={0} max={51} value={crf} onChange={e => setCrf(Number(e.target.value))} />
                <span className="wwk-slider-val">{crf}</span>
              </div>
            </div>
            <div className="wwk-field">
              <span className="wwk-label">Resolution</span>
              <PillSelector options={["original","1080p","720p","480p"].map(v => ({ value: v.replace("p",""), label: v === "original" ? "Original" : v }))}
                value={res} onChange={setRes} />
            </div>
          </Section>
        </div>
        <div className="wwk-panel-pinned">
          <div className="row between center" style={{ marginBottom: 10, fontSize: 11.5 }}>
            <span className="dim">{converting ? "Converting…" : progress === 100 ? "Done" : "Ready to convert"}</span>
            {progress > 0 && <span className="mono dim tnum">{progress}%</span>}
          </div>
          <div className="wwk-progress" style={{ marginBottom: 12 }} role="progressbar"
            aria-label="Conversion progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}>
            <div className="wwk-progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <button className="wwk-btn primary block lg" onClick={handleConvert} disabled={converting || !src}>
            ▶ {converting ? "Converting…" : "Convert"}
          </button>
        </div>
      </div>

      <div className="wwk-panel">
        <div style={{ flex: 1, padding: 22, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div className="row between center" style={{ marginBottom: 12 }}>
            <div className="wwk-section-label"><span>FFmpeg Log</span></div>
            {converting && <span className="row gap-1 center" style={{ fontSize: 11 }}><span className="wwk-dot active" /> live</span>}
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

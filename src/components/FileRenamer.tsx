import { useState } from "react";
import { Section } from "./Section";
import { PillSelector } from "./PillSelector";
import { invoke } from "../invoke";

const CASE_OPTIONS = ["original", "lowercase", "UPPERCASE", "Title Case"];

interface PreviewItem { original: string; renamed: string; changed: boolean }

function Check({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="wwk-check">
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
      <span className="wwk-check-box"><span className="check-icon">✓</span></span>
      <span>{label}</span>
    </label>
  );
}

export function FileRenamer() {
  const [folderPath, setFolderPath] = useState("");
  const [filePath, setFilePath] = useState("");
  const [prefix, setPrefix] = useState("");
  const [suffix, setSuffix] = useState("");
  const [slug, setSlug] = useState(true);
  const [caseMode, setCaseMode] = useState("original");
  const [previewItems, setPreviewItems] = useState<PreviewItem[]>([]);
  const [stats, setStats] = useState({ ready: 0, modified: 0, errors: 0 });

  const args = () => ({ folderPath, singleFilePath: filePath, prefix, suffix, slug, caseMode });

  const handlePreview = async () => {
    try {
      const items = await invoke<PreviewItem[]>("preview_rename", { args: args() });
      setPreviewItems(items);
      const mod = items.filter(i => i.changed).length;
      setStats({ ready: items.length - mod, modified: mod, errors: 0 });
    } catch (e) { console.error(e); }
  };

  const handleRename = async () => {
    try {
      const r = await invoke<{ modified: number; errors: number; total: number }>("execute_rename", { args: args() });
      setStats({ ready: r.total - r.modified - r.errors, modified: r.modified, errors: r.errors });
      setPreviewItems([]);
    } catch (e) { console.error(e); }
  };

  const browse = async (type: "file" | "folder", setter: (v: string) => void) => {
    const cmd = type === "folder" ? "pick_folder" : "pick_file";
    const a = type === "folder" ? { title: "Select folder" } : { title: "Select file", filters: [{ name: "All", extensions: ["*"] }] };
    const p = await invoke<string | null>(cmd, a);
    if (p) setter(p);
  };

  return (
    <div className="wwk-single">
      <div style={{ width: "100%", maxWidth: 880 }}>
        <Section title="Rename Options">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div className="wwk-field">
              <span className="wwk-label">Prefix</span>
              <input className="wwk-input" value={prefix} onChange={e => setPrefix(e.target.value)} placeholder="e.g. img-" />
            </div>
            <div className="wwk-field">
              <span className="wwk-label">Suffix</span>
              <input className="wwk-input" value={suffix} onChange={e => setSuffix(e.target.value)} placeholder="e.g. -thumb" />
            </div>
          </div>
          <Check checked={slug} onChange={setSlug} label="Slug formatting (remove special chars, hyphens for spaces)" />
          <div style={{ marginTop: 4 }}>
            <span className="wwk-label" style={{ marginBottom: 6, display: "block" }}>Case</span>
            <PillSelector options={CASE_OPTIONS} value={caseMode} onChange={setCaseMode} />
          </div>
        </Section>

        <Section title="Source">
          <div className="wwk-field-row">
            <input className="wwk-input" value={folderPath} onChange={e => setFolderPath(e.target.value)} placeholder="Folder path…" />
            <button className="wwk-btn" onClick={() => browse("folder", setFolderPath)}>📁 Browse</button>
          </div>
          <div style={{ height: 6 }} />
          <div className="wwk-field-row">
            <input className="wwk-input" value={filePath} onChange={e => setFilePath(e.target.value)} placeholder="Or a single file…" />
            <button className="wwk-btn" onClick={() => browse("file", setFilePath)}>📄 Browse</button>
          </div>
          <div style={{ marginTop: 10 }}>
            <button className="wwk-btn" onClick={handlePreview}>Preview rename</button>
          </div>
        </Section>

        {previewItems.length > 0 && (
          <Section title="Preview" after={<span className="mono dim tnum" style={{ fontSize: 11 }}>{previewItems.length} files</span>}>
            <div style={{ borderRadius: 10, border: "1px solid var(--border)", background: "var(--surface-1)", overflow: "hidden", maxHeight: 300, overflowY: "auto" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 18px 1fr", padding: "8px 14px", borderBottom: "1px solid var(--border)" }}>
                <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--text-dim)" }}>Original</span>
                <span />
                <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--text-dim)" }}>New</span>
              </div>
              {previewItems.map((item, i) => (
                <div key={i} style={{
                  display: "grid", gridTemplateColumns: "1fr 18px 1fr", padding: "6px 14px",
                  background: i % 2 === 0 ? "var(--surface-1)" : "transparent",
                  fontFamily: "var(--font-mono)", fontSize: 12,
                }}>
                  <span className="dim" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.original}</span>
                  <span className="dimmer" style={{ textAlign: "center" }}>→</span>
                  <span style={{ color: item.changed ? "var(--primary)" : "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.renamed}</span>
                </div>
              ))}
            </div>
          </Section>
        )}

        <div className="row gap-3 center" style={{ marginTop: 8 }}>
          <button className="wwk-btn primary lg" onClick={handleRename}>✓ Rename Files</button>
          <div className="row gap-4 center" style={{ marginLeft: "auto", fontSize: 11.5 }}>
            <span className="row gap-1 center"><span className="wwk-dot ok" /> Ready: {stats.ready}</span>
            <span className="row gap-1 center"><span className="wwk-dot active" /> Modified: {stats.modified}</span>
            <span className="row gap-1 center"><span className="wwk-dot error" /> Errors: {stats.errors}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

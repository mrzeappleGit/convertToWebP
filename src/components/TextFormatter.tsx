import { useState, useMemo, useCallback } from "react";
import { Section } from "./Section";
import { PillSelector } from "./PillSelector";

const MODES = ["slug", "lowercase", "UPPERCASE", "Title Case", "camelCase", "kebab-case", "snake_case"];

function transformText(input: string, mode: string): string {
  if (!input.trim()) return "";
  switch (mode) {
    case "slug":
      return input.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
        .toLowerCase().replace(/[^\w\s-]/g, "").replace(/\s+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
    case "lowercase": return input.toLowerCase();
    case "UPPERCASE": return input.toUpperCase();
    case "Title Case": return input.replace(/\w\S*/g, t => t.charAt(0).toUpperCase() + t.slice(1).toLowerCase());
    case "camelCase": {
      const parts = input.split(/[\s\-_]+/).filter(Boolean);
      return (parts[0]?.toLowerCase() ?? "") + parts.slice(1).map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join("");
    }
    case "kebab-case": return input.toLowerCase().replace(/[\s_]+/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
    case "snake_case": return input.toLowerCase().replace(/[\s\-]+/g, "_").replace(/_+/g, "_").replace(/^_|_$/g, "");
    default: return input;
  }
}

export function TextFormatter() {
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("slug");
  const [copied, setCopied] = useState(false);
  const result = useMemo(() => transformText(input, mode), [input, mode]);
  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(result);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [result]);

  return (
    <div className="wwk-single">
      <div className="wwk-single-inner">
        <Section title="Input">
          <textarea className="wwk-textarea" rows={5} value={input}
            onChange={e => setInput(e.target.value)} placeholder="Type or paste text here…" />
          <div className="row between center" style={{ marginTop: 6 }}>
            <span className="mono dim tnum" style={{ fontSize: 11 }}>{input.length} chars · {input.trim() ? input.trim().split(/\s+/).length : 0} words</span>
            {input && <button className="wwk-btn sm" onClick={() => setInput("")}>🗑 Clear</button>}
          </div>
        </Section>

        <Section title="Format">
          <PillSelector options={MODES} value={mode} onChange={setMode} />
        </Section>

        <Section title="Result">
          <div style={{
            minHeight: 110, padding: "14px 16px",
            background: "var(--bg)", border: "1px solid var(--border)",
            borderRadius: 8, fontFamily: "var(--font-mono)", fontSize: 14,
            color: "var(--primary)", wordBreak: "break-all", whiteSpace: "pre-wrap",
            boxShadow: "inset 0 1px 0 rgba(0,0,0,0.2), 0 0 24px -8px var(--primary-glow)",
          }}>
            {result}
          </div>
        </Section>

        <button className="wwk-btn primary" onClick={handleCopy}>
          {copied ? "✓ Copied" : "📋 Copy result"}
        </button>
      </div>
    </div>
  );
}

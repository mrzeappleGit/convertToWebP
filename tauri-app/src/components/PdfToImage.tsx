import { useState, useRef, useEffect } from "react";
import { Section } from "./Section";
import { PillSelector } from "./PillSelector";
import { invoke } from "../invoke";
import * as pdfjsLib from "pdfjs-dist";

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.mjs", import.meta.url).toString();

function Check({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="wwk-check">
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
      <span className="wwk-check-box"><span className="check-icon">✓</span></span>
      <span>{label}</span>
    </label>
  );
}

export function PdfToImage() {
  const [pdfPath, setPdfPath] = useState("");
  const [fmt, setFmt] = useState("WebP");
  const [quality, setQuality] = useState(85);
  const [margins, setMargins] = useState(true);
  const [output, setOutput] = useState("");
  const [converting, setConverting] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [pageCount, setPageCount] = useState(0);
  const [page, setPage] = useState(1);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const docRef = useRef<pdfjsLib.PDFDocumentProxy | null>(null);

  useEffect(() => {
    if (!pdfPath) return;
    (async () => {
      try {
        const b64 = await invoke<string>("read_file_base64", { path: pdfPath });
        const data = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
        const doc = await pdfjsLib.getDocument({ data }).promise;
        docRef.current = doc;
        setPageCount(doc.numPages);
        setPage(1);
        renderPage(doc, 1);
      } catch (e) { console.error(e); }
    })();
  }, [pdfPath]);

  const renderPage = async (doc: pdfjsLib.PDFDocumentProxy, num: number) => {
    const pg = await doc.getPage(num);
    const vp = pg.getViewport({ scale: 1.5 });
    const c = canvasRef.current!;
    c.width = vp.width; c.height = vp.height;
    await pg.render({ canvasContext: c.getContext("2d")!, viewport: vp }).promise;
    setPreviewUrl(c.toDataURL("image/png"));
  };

  const changePage = (d: number) => {
    const n = Math.max(1, Math.min(pageCount, page + d));
    setPage(n);
    if (docRef.current) renderPage(docRef.current, n);
  };

  const handleConvert = async () => {
    if (!pdfPath || !docRef.current) return;
    setConverting(true); setOutput("");
    try {
      const pg = await docRef.current.getPage(page);
      const vp = pg.getViewport({ scale: 150 / 72 });
      const off = document.createElement("canvas");
      off.width = vp.width; off.height = vp.height;
      const ctx = off.getContext("2d")!;
      if (!margins) { ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, off.width, off.height); }
      await pg.render({ canvasContext: ctx, viewport: vp }).promise;
      const png64 = off.toDataURL("image/png").split(",")[1];
      const r = await invoke<string>("save_pdf_page_image", { pngBase64: png64, pdfPath, format: fmt.toLowerCase(), quality });
      setOutput(r);
    } catch (e: any) { setOutput(`Error: ${e}`); }
    finally { setConverting(false); }
  };

  return (
    <div className="wwk-twocol">
      <div className="wwk-panel">
        <div className="wwk-panel-scroll">
          <Section title="PDF Source">
            <div className="wwk-field-row">
              <input className="wwk-input" value={pdfPath} onChange={e => setPdfPath(e.target.value)} placeholder="Select a PDF…" />
              <button className="wwk-btn" onClick={async () => {
                const p = await invoke<string | null>("pick_file", { title: "Select PDF", filters: [{ name: "PDF", extensions: ["pdf"] }] });
                if (p) setPdfPath(p);
              }}>📄 Browse</button>
            </div>
            {pageCount > 0 && <div className="dim" style={{ fontSize: 11, marginTop: 6 }}>{pageCount} pages</div>}
          </Section>
          <Section title="Output Format">
            <PillSelector options={["WebP", "PNG", "JPEG"]} value={fmt} onChange={setFmt} />
          </Section>
          <Section title="Quality">
            <div className="wwk-slider-row">
              <input type="range" className="wwk-slider" min={0} max={100} value={quality}
                onChange={e => setQuality(Number(e.target.value))} disabled={fmt === "PNG"} />
              <span className="wwk-slider-val">{quality}%</span>
            </div>
          </Section>
          <Section title="Options">
            <Check checked={margins} onChange={setMargins} label="Include margins" />
          </Section>
        </div>
        <div className="wwk-panel-pinned">
          {output && (
            <div className="mono dim" style={{ fontSize: 11, marginBottom: 10, wordBreak: "break-all" }}>
              {output.startsWith("Error") ? <span style={{ color: "var(--error)" }}>{output}</span> : <>Saved: {output}</>}
            </div>
          )}
          <button className="wwk-btn primary block lg" onClick={handleConvert} disabled={converting || !pdfPath}>
            ⬇ {converting ? "Converting…" : "Convert PDF"}
          </button>
        </div>
      </div>

      <div className="wwk-panel">
        <div style={{ flex: 1, padding: 22, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div className="row between center" style={{ marginBottom: 12 }}>
            <div className="wwk-section-label"><span>Preview</span></div>
            {pageCount > 1 && (
              <div className="row gap-2 center" style={{ fontSize: 12 }}>
                <button className="wwk-btn sm" onClick={() => changePage(-1)} disabled={page <= 1}>‹</button>
                <span className="mono tnum">Page {page} / {pageCount}</span>
                <button className="wwk-btn sm" onClick={() => changePage(1)} disabled={page >= pageCount}>›</button>
              </div>
            )}
          </div>
          <div className="wwk-preview" style={{ flexDirection: "column" }}>
            {previewUrl ? (
              <img src={previewUrl} alt="" style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain", borderRadius: 4 }} />
            ) : "Select a PDF to preview"}
          </div>
        </div>
      </div>
      <canvas ref={canvasRef} style={{ display: "none" }} />
    </div>
  );
}

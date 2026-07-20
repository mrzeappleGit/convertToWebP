import { useState, useRef, useCallback, useEffect, useLayoutEffect } from "react";
import { Section } from "./Section";
import { PillSelector } from "./PillSelector";
import { invoke } from "../invoke";

type Rect = { x: number; y: number; w: number; h: number };

const ASPECT_OPTIONS = [
  { value: "free", label: "Free" },
  { value: "1:1", label: "1:1" },
  { value: "4:3", label: "4:3" },
  { value: "16:9", label: "16:9" },
  { value: "3:2", label: "3:2" },
  { value: "9:16", label: "9:16" },
];

const FORMAT_OPTIONS = [
  { value: "png", label: "PNG" },
  { value: "webp", label: "WebP" },
  { value: "jpeg", label: "JPEG" },
];

export function ImageCropper() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageSize, setImageSize] = useState({ w: 0, h: 0 });
  const [imagePath, setImagePath] = useState("");
  const [canvasSize, setCanvasSize] = useState({ w: 600, h: 400 });
  const [aspect, setAspect] = useState("free");
  const [format, setFormat] = useState("png");
  const [quality, setQuality] = useState(90);
  const [saving, setSaving] = useState(false);
  const [savedPath, setSavedPath] = useState("");

  // Crop rect in original image coordinates
  const [crop, setCrop] = useState<Rect | null>(null);

  // Drag state
  const dragState = useRef<{
    type: "create" | "move" | "n" | "s" | "e" | "w" | "ne" | "nw" | "se" | "sw";
    startMouse: { x: number; y: number };
    startCrop: Rect;
  } | null>(null);

  // ── Display metrics ──────────────────────────────────────
  const getMetrics = useCallback(() => {
    const img = imageRef.current;
    if (!img) return null;
    const cw = canvasSize.w, ch = canvasSize.h;
    if (cw <= 0 || ch <= 0) return null;
    const scale = Math.min(cw / img.width, ch / img.height);
    const dw = img.width * scale, dh = img.height * scale;
    const dx = (cw - dw) / 2, dy = (ch - dh) / 2;
    return { dx, dy, dw, dh, scale, ow: img.width, oh: img.height };
  }, [canvasSize]);

  const origToCanvas = useCallback((ox: number, oy: number) => {
    const m = getMetrics();
    if (!m) return { x: 0, y: 0 };
    return { x: (ox / m.ow) * m.dw + m.dx, y: (oy / m.oh) * m.dh + m.dy };
  }, [getMetrics]);

  const canvasToOrig = useCallback((cx: number, cy: number) => {
    const m = getMetrics();
    if (!m) return null;
    const ox = ((cx - m.dx) / m.dw) * m.ow;
    const oy = ((cy - m.dy) / m.dh) * m.oh;
    return { x: Math.max(0, Math.min(m.ow, ox)), y: Math.max(0, Math.min(m.oh, oy)) };
  }, [getMetrics]);

  // ── Canvas resize ───────────────────────────────────────
  useLayoutEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const update = () => {
      const rect = wrap.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) setCanvasSize({ w: Math.floor(rect.width), h: Math.floor(rect.height) });
    };
    update();
    const obs = new ResizeObserver(update);
    obs.observe(wrap);
    return () => obs.disconnect();
  }, []);

  // ── Draw ────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.width = canvasSize.w;
    canvas.height = canvasSize.h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const cw = canvasSize.w, ch = canvasSize.h;
    ctx.clearRect(0, 0, cw, ch);
    ctx.fillStyle = "#08090b";
    ctx.fillRect(0, 0, cw, ch);

    const img = imageRef.current;
    const m = getMetrics();
    if (!img || !m) return;

    // Draw image
    ctx.drawImage(img, m.dx, m.dy, m.dw, m.dh);

    // Draw crop overlay
    if (crop) {
      const tl = origToCanvas(crop.x, crop.y);
      const br = origToCanvas(crop.x + crop.w, crop.y + crop.h);
      const cw2 = br.x - tl.x, ch2 = br.y - tl.y;

      // Darken outside crop
      ctx.fillStyle = "rgba(0, 0, 0, 0.55)";
      ctx.fillRect(m.dx, m.dy, m.dw, tl.y - m.dy); // top
      ctx.fillRect(m.dx, br.y, m.dw, (m.dy + m.dh) - br.y); // bottom
      ctx.fillRect(m.dx, tl.y, tl.x - m.dx, ch2); // left
      ctx.fillRect(br.x, tl.y, (m.dx + m.dw) - br.x, ch2); // right

      // Crop border
      ctx.strokeStyle = "#6cdba4";
      ctx.lineWidth = 2;
      ctx.strokeRect(tl.x, tl.y, cw2, ch2);

      // Rule of thirds grid
      ctx.strokeStyle = "rgba(255, 255, 255, 0.2)";
      ctx.lineWidth = 1;
      for (let i = 1; i <= 2; i++) {
        const gy = tl.y + (ch2 * i) / 3;
        ctx.beginPath(); ctx.moveTo(tl.x, gy); ctx.lineTo(br.x, gy); ctx.stroke();
        const gx = tl.x + (cw2 * i) / 3;
        ctx.beginPath(); ctx.moveTo(gx, tl.y); ctx.lineTo(gx, br.y); ctx.stroke();
      }

      // Corner handles
      const hs = 8;
      ctx.fillStyle = "#6cdba4";
      for (const [hx, hy] of [[tl.x, tl.y], [br.x, tl.y], [tl.x, br.y], [br.x, br.y]]) {
        ctx.fillRect(hx - hs / 2, hy - hs / 2, hs, hs);
      }
      // Edge midpoint handles
      const smh = 6;
      ctx.fillStyle = "rgba(108, 219, 164, 0.7)";
      const mx = (tl.x + br.x) / 2, my = (tl.y + br.y) / 2;
      ctx.fillRect(mx - smh / 2, tl.y - smh / 2, smh, smh); // top
      ctx.fillRect(mx - smh / 2, br.y - smh / 2, smh, smh); // bottom
      ctx.fillRect(tl.x - smh / 2, my - smh / 2, smh, smh); // left
      ctx.fillRect(br.x - smh / 2, my - smh / 2, smh, smh); // right
    }
  }, [canvasSize, imageLoaded, crop, getMetrics, origToCanvas]);

  // ── Aspect ratio enforcement ────────────────────────────
  const enforceAspect = useCallback((r: Rect, anchor: "tl" | "br" | "center" = "tl"): Rect => {
    if (aspect === "free") return r;
    const [aw, ah] = aspect.split(":").map(Number);
    const ratio = aw / ah;
    let { x, y, w, h } = r;
    const m = getMetrics();
    if (!m) return r;
    const newH = w / ratio;
    if (anchor === "br" || anchor === "center") {
      y = y + h - newH;
    }
    h = newH;
    // Clamp to image bounds
    x = Math.max(0, Math.min(m.ow - w, x));
    y = Math.max(0, Math.min(m.oh - h, y));
    return { x, y, w, h };
  }, [aspect, getMetrics]);

  // ── Mouse handlers ──────────────────────────────────────
  const getHitZone = useCallback((cx: number, cy: number): string | null => {
    if (!crop) return null;
    const tl = origToCanvas(crop.x, crop.y);
    const br = origToCanvas(crop.x + crop.w, crop.y + crop.h);
    const margin = 8;
    const nearL = Math.abs(cx - tl.x) < margin;
    const nearR = Math.abs(cx - br.x) < margin;
    const nearT = Math.abs(cy - tl.y) < margin;
    const nearB = Math.abs(cy - br.y) < margin;
    const inX = cx > tl.x + margin && cx < br.x - margin;
    const inY = cy > tl.y + margin && cy < br.y - margin;

    if (nearT && nearL) return "nw";
    if (nearT && nearR) return "ne";
    if (nearB && nearL) return "sw";
    if (nearB && nearR) return "se";
    if (nearT && inX) return "n";
    if (nearB && inX) return "s";
    if (nearL && inY) return "w";
    if (nearR && inY) return "e";
    if (inX && inY) return "move";
    return null;
  }, [crop, origToCanvas]);

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!imageRef.current) return;
    const rect = canvasRef.current!.getBoundingClientRect();
    const cx = e.clientX - rect.left, cy = e.clientY - rect.top;

    const zone = getHitZone(cx, cy);
    if (zone && crop) {
      dragState.current = { type: zone as any, startMouse: { x: cx, y: cy }, startCrop: { ...crop } };
    } else {
      // Create new crop
      const oc = canvasToOrig(cx, cy);
      if (!oc) return;
      const newCrop = { x: oc.x, y: oc.y, w: 0, h: 0 };
      setCrop(newCrop);
      dragState.current = { type: "create", startMouse: { x: cx, y: cy }, startCrop: newCrop };
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !imageRef.current) return;
    const rect = canvas.getBoundingClientRect();
    const cx = e.clientX - rect.left, cy = e.clientY - rect.top;

    // Update cursor
    if (!dragState.current) {
      const zone = getHitZone(cx, cy);
      const cursors: Record<string, string> = {
        nw: "nw-resize", ne: "ne-resize", sw: "sw-resize", se: "se-resize",
        n: "n-resize", s: "s-resize", e: "e-resize", w: "w-resize", move: "move",
      };
      canvas.style.cursor = zone ? cursors[zone] || "crosshair" : "crosshair";
      return;
    }

    const ds = dragState.current;
    const m = getMetrics();
    if (!m) return;

    const dx = (cx - ds.startMouse.x) / m.scale;
    const dy = (cy - ds.startMouse.y) / m.scale;
    const sc = ds.startCrop;

    let newCrop: Rect;

    if (ds.type === "create") {
      const oc = canvasToOrig(cx, cy);
      if (!oc) return;
      const x = Math.min(sc.x, oc.x), y = Math.min(sc.y, oc.y);
      const w = Math.abs(oc.x - sc.x), h = Math.abs(oc.y - sc.y);
      newCrop = enforceAspect({ x, y, w, h });
    } else if (ds.type === "move") {
      let nx = sc.x + dx, ny = sc.y + dy;
      nx = Math.max(0, Math.min(m.ow - sc.w, nx));
      ny = Math.max(0, Math.min(m.oh - sc.h, ny));
      newCrop = { x: nx, y: ny, w: sc.w, h: sc.h };
    } else {
      let { x, y, w, h } = sc;
      if (ds.type.includes("e")) w = Math.max(10, sc.w + dx);
      if (ds.type.includes("w")) { x = sc.x + dx; w = Math.max(10, sc.w - dx); }
      if (ds.type.includes("s")) h = Math.max(10, sc.h + dy);
      if (ds.type.includes("n")) { y = sc.y + dy; h = Math.max(10, sc.h - dy); }
      // Clamp
      x = Math.max(0, x); y = Math.max(0, y);
      w = Math.min(m.ow - x, w); h = Math.min(m.oh - y, h);
      const anchor = ds.type.includes("n") ? "br" : "tl";
      newCrop = enforceAspect({ x, y, w, h }, anchor as any);
    }

    setCrop(newCrop);
  };

  const handleMouseUp = () => { dragState.current = null; };

  // ── Image loading ───────────────────────────────────────
  const handleLoadImage = async () => {
    const path = await invoke<string | null>("pick_file", {
      title: "Select an Image to Crop",
      filters: [{ name: "Images", extensions: ["png", "jpg", "jpeg", "bmp", "gif", "tif", "tiff", "webp"] }],
    });
    if (!path) return;
    setImagePath(path);
    setSavedPath("");
    try {
      const b64 = await invoke<string>("read_file_base64", { path });
      const ext = path.split(".").pop()?.toLowerCase() ?? "png";
      const mime = ext === "jpg" || ext === "jpeg" ? "image/jpeg" : ext === "png" ? "image/png"
        : ext === "gif" ? "image/gif" : ext === "webp" ? "image/webp" : "image/png";
      const img = new Image();
      img.onload = () => {
        imageRef.current = img;
        setImageSize({ w: img.width, h: img.height });
        setImageLoaded(true);
        // Default crop to full image
        setCrop({ x: 0, y: 0, w: img.width, h: img.height });
      };
      img.src = `data:${mime};base64,${b64}`;
    } catch (e) { console.error(e); }
  };

  // ── Save cropped image ──────────────────────────────────
  const handleSave = async () => {
    if (!crop || !imageRef.current) return;
    setSaving(true);
    setSavedPath("");
    try {
      // Render crop to offscreen canvas
      const off = document.createElement("canvas");
      off.width = Math.round(crop.w);
      off.height = Math.round(crop.h);
      const ctx = off.getContext("2d")!;
      ctx.drawImage(imageRef.current, -crop.x, -crop.y);

      const mimeMap: Record<string, string> = { png: "image/png", webp: "image/webp", jpeg: "image/jpeg" };
      const dataUrl = off.toDataURL(mimeMap[format] || "image/png", quality / 100);
      const b64 = dataUrl.split(",")[1];

      // Build output path
      const stem = imagePath.replace(/\.[^.]+$/, "");
      const outPath = `${stem}-cropped.${format === "jpeg" ? "jpg" : format}`;

      const result = await invoke<string>("save_base64_image", {
        data: b64, path: outPath, format, quality,
      });
      setSavedPath(result);
    } catch (e: any) {
      setSavedPath(`Error: ${e}`);
    } finally {
      setSaving(false);
    }
  };

  const cropW = crop ? Math.round(crop.w) : 0;
  const cropH = crop ? Math.round(crop.h) : 0;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", height: "100%", flex: 1, minWidth: 0 }}>
      {/* Canvas */}
      <div style={{ display: "flex", flexDirection: "column", minWidth: 0, borderRight: "1px solid var(--border)" }}>
        <div className="row between center" style={{ padding: "10px 16px", flexShrink: 0 }}>
          <button className="wwk-btn" onClick={handleLoadImage}>📁 Load Image</button>
          {imageLoaded && (
            <span className="mono dim tnum" style={{ fontSize: 11 }}>
              {imageSize.w}×{imageSize.h}
            </span>
          )}
        </div>
        <div ref={wrapRef} style={{ flex: 1, minHeight: 0, position: "relative" }}>
          <canvas
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            style={{
              position: "absolute", inset: 0, width: "100%", height: "100%",
              background: "var(--bg)", cursor: imageLoaded ? "crosshair" : "default",
            }}
          />
        </div>
        <p className="dim" style={{ fontSize: 12, padding: "8px 16px", flexShrink: 0 }}>
          {!imageLoaded ? "Load an image to begin cropping." :
            crop ? `Crop: ${cropW}×${cropH} — drag edges or corners to resize, drag inside to move` :
            "Click and drag to select a crop region"}
        </p>
      </div>

      {/* Controls */}
      <div className="wwk-panel">
        <div className="wwk-panel-scroll" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Section title="Aspect Ratio">
            <PillSelector options={ASPECT_OPTIONS} value={aspect} onChange={(v) => {
              setAspect(v);
              if (crop && v !== "free") {
                const [aw, ah] = v.split(":").map(Number);
                const ratio = aw / ah;
                const newH = crop.w / ratio;
                setCrop({ ...crop, h: newH });
              }
            }} />
          </Section>

          <Section title="Crop Region">
            {crop ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <div className="wwk-field">
                  <span className="wwk-label">X</span>
                  <input className="wwk-input" type="number" value={Math.round(crop.x)}
                    onChange={e => setCrop({ ...crop, x: Number(e.target.value) })} />
                </div>
                <div className="wwk-field">
                  <span className="wwk-label">Y</span>
                  <input className="wwk-input" type="number" value={Math.round(crop.y)}
                    onChange={e => setCrop({ ...crop, y: Number(e.target.value) })} />
                </div>
                <div className="wwk-field">
                  <span className="wwk-label">Width</span>
                  <input className="wwk-input" type="number" value={cropW}
                    onChange={e => setCrop({ ...crop, w: Number(e.target.value) })} />
                </div>
                <div className="wwk-field">
                  <span className="wwk-label">Height</span>
                  <input className="wwk-input" type="number" value={cropH}
                    onChange={e => setCrop({ ...crop, h: Number(e.target.value) })} />
                </div>
              </div>
            ) : (
              <p className="dim" style={{ fontSize: 12 }}>No crop selected</p>
            )}
          </Section>

          <Section title="Output Format">
            <PillSelector options={FORMAT_OPTIONS} value={format} onChange={setFormat} />
            {format !== "png" && (
              <div style={{ marginTop: 8 }}>
                <span className="wwk-label">Quality</span>
                <div className="wwk-slider-row">
                  <input type="range" className="wwk-slider" min={1} max={100} value={quality}
                    onChange={e => setQuality(Number(e.target.value))} />
                  <span className="wwk-slider-val">{quality}%</span>
                </div>
              </div>
            )}
          </Section>

          {crop && (
            <Section title="Preview">
              <div style={{
                background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 8,
                padding: 12, textAlign: "center",
              }}>
                <div className="mono tnum" style={{ fontSize: 22, color: "var(--primary)", fontWeight: 600 }}>
                  {cropW} × {cropH}
                </div>
                <div className="dim" style={{ fontSize: 11, marginTop: 4 }}>
                  {((cropW * cropH) / 1e6).toFixed(2)} MP
                  {imageSize.w > 0 && <> · {((cropW * cropH) / (imageSize.w * imageSize.h) * 100).toFixed(0)}% of original</>}
                </div>
              </div>
            </Section>
          )}
        </div>

        <div className="wwk-panel-pinned">
          {savedPath && (
            <div className="mono dim" style={{ fontSize: 11, marginBottom: 10, wordBreak: "break-all" }}>
              {savedPath.startsWith("Error") ? <span style={{ color: "var(--error)" }}>{savedPath}</span> : <>Saved: {savedPath}</>}
            </div>
          )}
          <div className="row gap-2">
            <button className="wwk-btn" onClick={() => {
              if (imageRef.current) setCrop({ x: 0, y: 0, w: imageRef.current.width, h: imageRef.current.height });
            }} disabled={!imageLoaded}>Reset</button>
            <button className="wwk-btn primary flex1" onClick={handleSave}
              disabled={saving || !crop || crop.w < 1 || crop.h < 1}>
              ✂ {saving ? "Saving…" : "Save Cropped"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

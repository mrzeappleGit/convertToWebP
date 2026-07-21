import { useState, useRef, useCallback, useEffect, useLayoutEffect } from "react";
import { Section } from "./Section";
import { PillSelector } from "./PillSelector";
import { invoke } from "../invoke";

type Point = { x: number; y: number };

const SHAPE_OPTIONS = ["Circle", "Polygon", "Rectangle"];

export function SvgGenerator() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageSize, setImageSize] = useState({ w: 0, h: 0 });
  const [mode, setMode] = useState("Circle");
  const [radius, setRadius] = useState(20);
  const [strokeWidth, setStrokeWidth] = useState(2);
  const [color, setColor] = useState("#55d8e1");
  const [svgOutput, setSvgOutput] = useState("");
  const [allElements, setAllElements] = useState<{ d: string; color: string; sw: number }[]>([]);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [canvasSize, setCanvasSize] = useState({ w: 600, h: 400 });
  // Drag-to-pan bookkeeping; `moved` distinguishes a pan from a shape-placing click
  const dragRef = useRef<{ sx: number; sy: number; px: number; py: number; moved: boolean } | null>(null);

  // Shape state stored as original-image coords so they survive redraws
  const [circleOrig, setCircleOrig] = useState<Point | null>(null);
  const [polyOrig, setPolyOrig] = useState<Point[]>([]);
  const [polyClosed, setPolyClosed] = useState(false);
  const [rectOrigA, setRectOrigA] = useState<Point | null>(null);
  const [rectOrigB, setRectOrigB] = useState<Point | null>(null);

  // ── Coordinate mapping ──────────────────────────────────────
  const getDisplayMetrics = useCallback(() => {
    const img = imageRef.current;
    if (!img) return null;
    const cw = canvasSize.w, ch = canvasSize.h;
    if (cw <= 0 || ch <= 0) return null;
    const scale = Math.min(cw / img.width, ch / img.height) * zoom;
    const dw = img.width * scale, dh = img.height * scale;
    const dx = (cw - dw) / 2 + pan.x, dy = (ch - dh) / 2 + pan.y;
    return { dx, dy, dw, dh, scale, ow: img.width, oh: img.height };
  }, [canvasSize, zoom, pan]);

  const canvasToOrig = useCallback((cx: number, cy: number): Point | null => {
    const m = getDisplayMetrics();
    if (!m) return null;
    if (cx < m.dx || cx > m.dx + m.dw || cy < m.dy || cy > m.dy + m.dh) return null;
    return {
      x: ((cx - m.dx) / m.dw) * m.ow,
      y: ((cy - m.dy) / m.dh) * m.oh,
    };
  }, [getDisplayMetrics]);

  const origToCanvas = useCallback((ox: number, oy: number): Point | null => {
    const m = getDisplayMetrics();
    if (!m) return null;
    return {
      x: (ox / m.ow) * m.dw + m.dx,
      y: (oy / m.oh) * m.dh + m.dy,
    };
  }, [getDisplayMetrics]);

  // ── Canvas resize ──────────────────────────────────────────
  useLayoutEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const update = () => {
      const rect = wrap.getBoundingClientRect();
      const w = Math.floor(rect.width);
      const h = Math.floor(rect.height);
      if (w > 0 && h > 0) setCanvasSize({ w, h });
    };
    update();
    const obs = new ResizeObserver(update);
    obs.observe(wrap);
    return () => obs.disconnect();
  }, []);

  // ── Wheel zoom (anchored at cursor) ────────────────────────
  const handleWheel = (e: WheelEvent) => {
    if (!imageRef.current) return;
    e.preventDefault();
    const m = getDisplayMetrics();
    if (!m) return;
    const rect = canvasRef.current!.getBoundingClientRect();
    const cx = e.clientX - rect.left, cy = e.clientY - rect.top;
    const newZoom = Math.min(4, Math.max(0.25, zoom * (e.deltaY < 0 ? 1.2 : 1 / 1.2)));
    const f = newZoom / zoom;
    if (f === 1) return;
    // Keep the image point under the cursor stationary
    setPan({
      x: cx - (cx - m.dx) * f - (canvasSize.w - m.dw * f) / 2,
      y: cy - (cy - m.dy) * f - (canvasSize.h - m.dh * f) / 2,
    });
    setZoom(newZoom);
  };
  const wheelRef = useRef(handleWheel);
  wheelRef.current = handleWheel;
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    // Native listener: React's onWheel can be passive, blocking preventDefault
    const h = (e: WheelEvent) => wheelRef.current(e);
    canvas.addEventListener("wheel", h, { passive: false });
    return () => canvas.removeEventListener("wheel", h);
  }, []);

  // ── Drag to pan ────────────────────────────────────────────
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!imageRef.current) return;
    dragRef.current = { sx: e.clientX, sy: e.clientY, px: pan.x, py: pan.y, moved: false };
  };
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const d = dragRef.current;
    if (!d) return;
    const dx = e.clientX - d.sx, dy = e.clientY - d.sy;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) d.moved = true;
    if (d.moved) setPan({ x: d.px + dx, y: d.py + dy });
  };
  const handleMouseLeave = () => { dragRef.current = null; };
  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    // Middle/right releases never fire onClick, which normally ends the drag
    if (e.button !== 0) dragRef.current = null;
  };

  // ── Draw ─────────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.width = canvasSize.w;
    canvas.height = canvasSize.h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const cw = canvasSize.w, ch = canvasSize.h;
    ctx.clearRect(0, 0, cw, ch);
    ctx.fillStyle = "#0d0f12";
    ctx.fillRect(0, 0, cw, ch);

    const img = imageRef.current;
    const m = getDisplayMetrics();
    if (img && m) {
      ctx.drawImage(img, m.dx, m.dy, m.dw, m.dh);
    }

    ctx.strokeStyle = color;
    ctx.lineWidth = strokeWidth;

    if (mode === "Circle" && circleOrig && m) {
      const c = origToCanvas(circleOrig.x, circleOrig.y);
      if (c) {
        const cr = radius * m.scale;
        ctx.beginPath();
        ctx.arc(c.x, c.y, cr, 0, Math.PI * 2);
        ctx.stroke();
        ctx.fillStyle = "#f2726f";
        ctx.beginPath();
        ctx.arc(c.x, c.y, 3, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    if (mode === "Polygon" && polyOrig.length > 0) {
      const pts = polyOrig.map((p) => origToCanvas(p.x, p.y)).filter(Boolean) as Point[];
      if (pts.length > 0) {
        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
        if (polyClosed) ctx.closePath();
        ctx.stroke();
        for (const p of pts) {
          ctx.fillStyle = "#f2726f";
          ctx.beginPath();
          ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }

    if (mode === "Rectangle" && rectOrigA) {
      const a = origToCanvas(rectOrigA.x, rectOrigA.y);
      if (a) {
        ctx.fillStyle = "#f2726f";
        ctx.beginPath();
        ctx.arc(a.x, a.y, 3, 0, Math.PI * 2);
        ctx.fill();
        if (rectOrigB) {
          const b = origToCanvas(rectOrigB.x, rectOrigB.y);
          if (b) {
            ctx.setLineDash([6, 4]);
            ctx.strokeRect(a.x, a.y, b.x - a.x, b.y - a.y);
            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.arc(b.x, b.y, 3, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
    }
  }, [canvasSize, imageLoaded, mode, circleOrig, polyOrig, polyClosed, rectOrigA, rectOrigB, radius, strokeWidth, color, zoom, getDisplayMetrics, origToCanvas]);

  // ── Load image ───────────────────────────────────────────────
  const handleLoadImage = async () => {
    const path = await invoke<string | null>("pick_file", {
      title: "Select an Image",
      filters: [{ name: "Image Files", extensions: ["png", "jpg", "jpeg", "bmp", "gif", "tif", "tiff", "webp"] }],
    });
    if (!path) return;
    try {
      const b64 = await invoke<string>("read_file_base64", { path });
      const ext = path.split(".").pop()?.toLowerCase() ?? "png";
      const mime = ext === "jpg" || ext === "jpeg" ? "image/jpeg" : ext === "png" ? "image/png"
        : ext === "gif" ? "image/gif" : ext === "webp" ? "image/webp" : "image/png";
      const src = `data:${mime};base64,${b64}`;
      const img = new Image();
      img.onload = () => {
        imageRef.current = img;
        setImageSize({ w: img.width, h: img.height });
        setImageLoaded(true);
        setZoom(1);
        setPan({ x: 0, y: 0 });
        clearShape();
      };
      img.src = src;
    } catch (e) {
      console.error("Failed to load image:", e);
    }
  };

  // ── Click handling ───────────────────────────────────────────
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const wasPan = dragRef.current?.moved;
    dragRef.current = null;
    if (wasPan) return;
    if (!imageRef.current) return;
    const rect = canvasRef.current!.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    const oc = canvasToOrig(cx, cy);
    if (!oc) return;

    if (mode === "Circle") {
      setCircleOrig(oc);
      // Circle as two 180° arcs starting from the top point
      const d = `M${oc.x.toFixed(2)} ${(oc.y - radius).toFixed(2)}a${radius},${radius} 0 1 0 0,${radius * 2}a${radius},${radius} 0 1 0 0,${-radius * 2}Z`;
      setSvgOutput(d);
      setAllElements((prev) => [...prev, { d, color, sw: strokeWidth }]);
    } else if (mode === "Polygon") {
      if (polyClosed) return;
      const CLOSE_DIST = 15;
      if (polyOrig.length >= 3) {
        const first = origToCanvas(polyOrig[0].x, polyOrig[0].y);
        if (first) {
          const dx = cx - first.x, dy = cy - first.y;
          if (dx * dx + dy * dy < CLOSE_DIST * CLOSE_DIST) {
            setPolyClosed(true);
            const d = polyOrig.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join("") + "Z";
            setSvgOutput(d);
            setAllElements((prev) => [...prev, { d, color, sw: strokeWidth }]);
            return;
          }
        }
      }
      const newPts = [...polyOrig, oc];
      setPolyOrig(newPts);
      // In-progress path data
      setSvgOutput(newPts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(""));
    } else if (mode === "Rectangle") {
      if (rectOrigB) return;
      if (!rectOrigA) {
        setRectOrigA(oc);
      } else {
        setRectOrigB(oc);
        const rx = Math.min(rectOrigA.x, oc.x), ry = Math.min(rectOrigA.y, oc.y);
        const rw = Math.abs(oc.x - rectOrigA.x), rh = Math.abs(oc.y - rectOrigA.y);
        const d = `M${rx.toFixed(2)} ${ry.toFixed(2)}h${rw.toFixed(2)}v${rh.toFixed(2)}h${(-rw).toFixed(2)}Z`;
        setSvgOutput(d);
        setAllElements((prev) => [...prev, { d, color, sw: strokeWidth }]);
      }
    }
  };

  const clearShape = () => {
    setCircleOrig(null);
    setPolyOrig([]);
    setPolyClosed(false);
    setRectOrigA(null);
    setRectOrigB(null);
    setSvgOutput("");
  };

  const handleExportSvg = async () => {
    if (!allElements.length) return;
    const { w, h } = imageSize.w > 0 ? imageSize : { w: 800, h: 600 };
    const paths = allElements.map(el => `<path d="${el.d}" fill="none" stroke="${el.color}" stroke-width="${el.sw}" />`);
    const content = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}">\n  ${paths.join("\n  ")}\n</svg>\n`;
    const path = await invoke<string | null>("save_file_dialog", {
      title: "Export SVG",
      defaultName: "shapes.svg",
      filters: [{ name: "SVG Files", extensions: ["svg"] }],
    });
    if (path) {
      await invoke("write_string_to_file", { content, path });
    }
  };

  const instruction = !imageLoaded
    ? "Load an image to begin."
    : mode === "Circle"
    ? circleOrig ? "Circle drawn. Clear to draw another." : "Click to place circle center."
    : mode === "Polygon"
    ? polyClosed ? `Polygon closed (${polyOrig.length} pts).`
      : polyOrig.length < 3 ? `Click to add points (${polyOrig.length} so far).`
      : `Click near first point to close (${polyOrig.length} pts).`
    : mode === "Rectangle"
    ? rectOrigB ? "Rectangle drawn. Clear to draw another."
      : rectOrigA ? "Click to set the opposite corner."
      : "Click to set the first corner."
    : "";

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", height: "100%", flex: 1, minWidth: 0 }}>
      {/* Canvas */}
      <div style={{ display: "flex", flexDirection: "column", minWidth: 0, borderRight: "1px solid var(--border)", position: "relative" }}>
        <div className="row between center" style={{ padding: "10px 16px", flexShrink: 0 }}>
          <button className="wwk-btn" onClick={handleLoadImage}>📁 Load Image</button>
          <div className="row gap-1 center" style={{
            background: "linear-gradient(180deg, var(--surface-2), var(--surface-1))",
            border: "1px solid var(--border)", borderRadius: 8, padding: 4,
          }}>
            <button className="wwk-btn sm" style={{ width: 28, padding: 0 }}
              onClick={() => setZoom(z => Math.max(0.25, z - 0.25))}>−</button>
            <span className="mono tnum dim" style={{ fontSize: 11, minWidth: 38, textAlign: "center" }}>
              {Math.round(zoom * 100)}%
            </span>
            <button className="wwk-btn sm" style={{ width: 28, padding: 0 }}
              onClick={() => setZoom(z => Math.min(4, z + 0.25))}>+</button>
          </div>
        </div>
        <div ref={wrapRef} style={{ flex: 1, minHeight: 0, position: "relative" }}>
          <canvas ref={canvasRef} onClick={handleCanvasClick}
            onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseLeave}
            style={{
            position: "absolute", inset: 0, width: "100%", height: "100%",
            background: "var(--bg)", cursor: imageLoaded ? "crosshair" : "default",
          }} />
        </div>
        <p className="dim" style={{ fontSize: 12, padding: "8px 16px", flexShrink: 0 }}>
          {instruction}{imageLoaded && " Drag to pan · scroll to zoom."}
        </p>
      </div>

      {/* Controls */}
      <div className="wwk-panel">
        <div className="wwk-panel-scroll" style={{ gap: 16, display: "flex", flexDirection: "column" }}>
          <Section title="Shape">
            <PillSelector options={SHAPE_OPTIONS} value={mode} onChange={m => { setMode(m); clearShape(); }} />
          </Section>

          <Section title="Properties">
            {mode === "Circle" && (
              <div className="wwk-field">
                <span className="wwk-label">Radius</span>
                <div className="wwk-field-row">
                  <input className="wwk-input" type="number" value={radius} min={1} onChange={e => setRadius(Number(e.target.value))} style={{ width: 80 }} />
                  <span className="dim" style={{ fontSize: 11 }}>px</span>
                </div>
              </div>
            )}
            <div className="wwk-field">
              <span className="wwk-label">Stroke width</span>
              <div className="wwk-slider-row">
                <input type="range" className="wwk-slider" min={0.5} max={10} step={0.5} value={strokeWidth} onChange={e => setStrokeWidth(Number(e.target.value))} />
                <span className="wwk-slider-val">{strokeWidth}</span>
              </div>
            </div>
            <div className="wwk-field">
              <span className="wwk-label">Color</span>
              <div className="row gap-2 center">
                <input type="color" value={color} onChange={e => setColor(e.target.value)}
                  style={{ width: 28, height: 28, border: "none", padding: 0, cursor: "pointer", borderRadius: 6 }} />
                <input className="wwk-input" value={color} onChange={e => setColor(e.target.value)} style={{ width: 90, fontFamily: "var(--font-mono)", fontSize: 11 }} />
              </div>
            </div>
          </Section>

          <Section title="SVG Output">
            <div style={{
              minHeight: 80, maxHeight: 200, overflow: "auto",
              background: "var(--bg)", padding: 12, border: "1px solid var(--border)",
              borderRadius: 8, fontFamily: "var(--font-mono)", fontSize: 11.5,
              color: "var(--text-muted)", wordBreak: "break-all", whiteSpace: "pre-wrap",
            }}>
              {svgOutput || "Draw a shape to generate SVG…"}
            </div>
          </Section>
        </div>

        <div className="wwk-panel-pinned">
          <div className="row gap-2">
            <button className="wwk-btn" onClick={clearShape}>Clear</button>
            <button className="wwk-btn" onClick={() => navigator.clipboard.writeText(svgOutput)}>📋 Copy</button>
            <button className="wwk-btn primary" onClick={handleExportSvg} style={{ marginLeft: "auto" }}>Export SVG</button>
          </div>
        </div>
      </div>
    </div>
  );
}

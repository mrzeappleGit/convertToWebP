import "@testing-library/jest-dom/vitest";

// Mock Tauri APIs
Object.defineProperty(window, "__TAURI_INTERNALS__", { value: undefined });

// Mock scrollIntoView (not available in jsdom)
Element.prototype.scrollIntoView = () => {};

// Mock ResizeObserver (not available in jsdom)
globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock canvas getContext
const noop = () => {};
const mockCtx = {
  clearRect: noop, fillRect: noop, beginPath: noop, arc: noop,
  stroke: noop, fill: noop, moveTo: noop, lineTo: noop,
  closePath: noop, setLineDash: noop, strokeRect: noop,
  drawImage: noop, save: noop, restore: noop,
  fillStyle: "", strokeStyle: "", lineWidth: 1,
  canvas: { width: 600, height: 400 },
};
HTMLCanvasElement.prototype.getContext = (() => mockCtx) as any;

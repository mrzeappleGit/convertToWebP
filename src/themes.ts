export const THEMES = [
  { id: "atelier", name: "Synthetic Atelier", swatch: ["#111317", "#6cdba4", "#55d8e1"] },
  { id: "graphite", name: "Graphite", swatch: ["#0c0c0d", "#c5cad1", "#a1a8b3"] },
  { id: "solar", name: "Solar Flare", swatch: ["#14100c", "#f5b454", "#f47953"] },
  { id: "ultraviolet", name: "Ultraviolet", swatch: ["#0c0a14", "#b794f6", "#7dd3fc"] },
  { id: "forest", name: "Forest Floor", swatch: ["#0b110e", "#84cc8a", "#d4b87a"] },
  { id: "cobalt", name: "Cobalt", swatch: ["#0a0e16", "#5b9dff", "#67e8f9"] },
  { id: "textbook", name: "Textbook", swatch: ["#0c1828", "#e21a23", "#0077c8"] },
  { id: "neon", name: "Neon City", swatch: ["#0c0b16", "#e8f030", "#ff2a6d"] },
  { id: "cipher", name: "Cipher", swatch: ["#0e141b", "#00ffcc", "#11b89c"] },
  { id: "bone", name: "Bone", swatch: ["#f6f3ec", "#3f7d4b", "#1f6b80"] },
];

export function applyTheme(themeId: string) {
  if (themeId === "atelier") {
    document.documentElement.removeAttribute("data-theme");
  } else {
    document.documentElement.setAttribute("data-theme", themeId);
  }
  localStorage.setItem("wwk-theme", themeId);
}

export function getStoredTheme(): string {
  return localStorage.getItem("wwk-theme") || "atelier";
}

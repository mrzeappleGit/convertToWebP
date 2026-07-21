import { describe, it, expect, beforeEach } from "vitest";
import { THEMES, applyTheme, getStoredTheme } from "../themes";

describe("Themes", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("has 10 theme definitions", () => {
    expect(THEMES).toHaveLength(10);
  });

  it("each theme has id, name, and 3-color swatch", () => {
    for (const theme of THEMES) {
      expect(theme.id).toBeTruthy();
      expect(theme.name).toBeTruthy();
      expect(theme.swatch).toHaveLength(3);
      for (const color of theme.swatch) {
        expect(color).toMatch(/^#[0-9a-f]{6}$/i);
      }
    }
  });

  it("default theme has unique ids", () => {
    const ids = THEMES.map(t => t.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("applyTheme sets data-theme attribute for non-default themes", () => {
    applyTheme("cobalt");
    expect(document.documentElement.getAttribute("data-theme")).toBe("cobalt");
  });

  it("applyTheme removes data-theme for default (atelier)", () => {
    applyTheme("cobalt");
    applyTheme("atelier");
    expect(document.documentElement.getAttribute("data-theme")).toBeNull();
  });

  it("applyTheme persists to localStorage", () => {
    applyTheme("solar");
    expect(localStorage.getItem("wwk-theme")).toBe("solar");
  });

  it("getStoredTheme returns default when nothing stored", () => {
    expect(getStoredTheme()).toBe("atelier");
  });

  it("getStoredTheme returns stored value", () => {
    localStorage.setItem("wwk-theme", "forest");
    expect(getStoredTheme()).toBe("forest");
  });
});

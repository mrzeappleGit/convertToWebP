import { useState, useEffect, useCallback, useRef } from "react";
import { invoke } from "./invoke";

export interface AppSettings {
  theme: string;
  converter: {
    format: string;
    quality: number;
    compress: boolean;
    rename: boolean;
    resize: boolean;
    resizePercent: number;
    lastSource: string;
    lastDest: string;
  };
  renamer: {
    slug: boolean;
    caseMode: string;
    prefix: string;
    suffix: string;
  };
  pdf: {
    format: string;
    quality: number;
    includeMargins: boolean;
  };
  video: {
    format: string;
    videoCodec: string;
    audioCodec: string;
    crf: number;
    resolution: string;
  };
  text: {
    mode: string;
  };
  crop: {
    aspect: string;
    format: string;
    quality: number;
  };
}

const DEFAULTS: AppSettings = {
  theme: "atelier",
  converter: {
    format: "WebP", quality: 82, compress: true, rename: false,
    resize: false, resizePercent: 75, lastSource: "", lastDest: "",
  },
  renamer: { slug: true, caseMode: "original", prefix: "", suffix: "" },
  pdf: { format: "WebP", quality: 85, includeMargins: true },
  video: { format: "mp4", videoCodec: "H.264", audioCodec: "AAC", crf: 23, resolution: "original" },
  text: { mode: "slug" },
  crop: { aspect: "free", format: "png", quality: 90 },
};

function deepMerge(target: any, source: any): any {
  const out = { ...target };
  for (const key of Object.keys(source)) {
    if (source[key] && typeof source[key] === "object" && !Array.isArray(source[key])) {
      out[key] = deepMerge(target[key] || {}, source[key]);
    } else {
      out[key] = source[key];
    }
  }
  return out;
}

export function useSettings() {
  const [settings, setSettingsState] = useState<AppSettings>(DEFAULTS);
  const [loaded, setLoaded] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load on mount
  useEffect(() => {
    (async () => {
      try {
        const stored = await invoke<Record<string, unknown>>("load_settings");
        if (stored && typeof stored === "object") {
          setSettingsState(deepMerge(DEFAULTS, stored));
        }
      } catch {
        // Use defaults
      }
      setLoaded(true);
    })();
  }, []);

  // Debounced save
  const persist = useCallback((next: AppSettings) => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      invoke("save_settings", { settings: next }).catch(() => {});
    }, 500);
  }, []);

  const updateSettings = useCallback((partial: Partial<AppSettings>) => {
    setSettingsState((prev) => {
      const next = deepMerge(prev, partial);
      persist(next);
      return next;
    });
  }, [persist]);

  const updateSection = useCallback(<K extends keyof AppSettings>(
    section: K,
    partial: Partial<AppSettings[K]>,
  ) => {
    setSettingsState((prev) => {
      const next = {
        ...prev,
        [section]: { ...(prev[section] as any), ...partial },
      };
      persist(next);
      return next;
    });
  }, [persist]);

  return { settings, loaded, updateSettings, updateSection };
}

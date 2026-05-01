/**
 * Type-safe wrapper around Tauri's invoke.
 * Falls back to a no-op in browser dev mode (no Tauri runtime).
 */
export async function invoke<T = void>(
  cmd: string,
  args?: Record<string, unknown>
): Promise<T> {
  if (window.__TAURI_INTERNALS__) {
    const { invoke: tauriInvoke } = await import("@tauri-apps/api/core");
    return tauriInvoke<T>(cmd, args);
  }
  console.warn(`[dev] invoke("${cmd}") — no Tauri runtime, returning null`);
  return null as T;
}

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
  }
}

import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePersistentState } from "../useSettings";

describe("usePersistentState", () => {
  beforeEach(() => localStorage.clear());

  it("restores a saved value on the next mount", () => {
    const first = renderHook(() => usePersistentState("t.dest", ""));
    act(() => first.result.current[1]("C:\out"));
    first.unmount();
    const second = renderHook(() => usePersistentState("t.dest", ""));
    expect(second.result.current[0]).toBe("C:\out");
  });

  it("falls back to the initial value on corrupt or mistyped data", () => {
    localStorage.setItem("t.bad", "{not json");
    localStorage.setItem("t.num", JSON.stringify("eighty"));
    expect(renderHook(() => usePersistentState("t.bad", true)).result.current[0]).toBe(true);
    expect(renderHook(() => usePersistentState("t.num", 82)).result.current[0]).toBe(82);
  });
});

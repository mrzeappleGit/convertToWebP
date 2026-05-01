import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PillSelector } from "../components/PillSelector";

describe("PillSelector", () => {
  it("renders all options", () => {
    render(<PillSelector options={["A", "B", "C"]} value="A" onChange={() => {}} />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    expect(screen.getByText("C")).toBeInTheDocument();
  });

  it("marks the active pill", () => {
    render(<PillSelector options={["A", "B", "C"]} value="B" onChange={() => {}} />);
    expect(screen.getByText("B").closest("button")).toHaveClass("active");
    expect(screen.getByText("A").closest("button")).not.toHaveClass("active");
  });

  it("calls onChange when a pill is clicked", () => {
    const onChange = vi.fn();
    render(<PillSelector options={["A", "B", "C"]} value="A" onChange={onChange} />);
    fireEvent.click(screen.getByText("C"));
    expect(onChange).toHaveBeenCalledWith("C");
  });

  it("supports object options with value/label", () => {
    const opts = [{ value: "webp", label: "WebP" }, { value: "png", label: "PNG" }];
    const onChange = vi.fn();
    render(<PillSelector options={opts} value="webp" onChange={onChange} />);
    expect(screen.getByText("WebP")).toBeInTheDocument();
    expect(screen.getByText("PNG")).toBeInTheDocument();
    fireEvent.click(screen.getByText("PNG"));
    expect(onChange).toHaveBeenCalledWith("png");
  });

  it("handles null value (no active pill)", () => {
    render(<PillSelector options={["A", "B"]} value={null} onChange={() => {}} />);
    expect(screen.getByText("A").closest("button")).not.toHaveClass("active");
    expect(screen.getByText("B").closest("button")).not.toHaveClass("active");
  });
});

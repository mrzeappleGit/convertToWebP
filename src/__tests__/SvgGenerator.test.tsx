import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SvgGenerator } from "../components/SvgGenerator";

// Mock ResizeObserver
globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as any;

describe("SvgGenerator", () => {
  it("renders shape selector pills", () => {
    render(<SvgGenerator />);
    expect(screen.getByText("Circle")).toBeInTheDocument();
    expect(screen.getByText("Polygon")).toBeInTheDocument();
    expect(screen.getByText("Rectangle")).toBeInTheDocument();
  });

  it("renders Properties section", () => {
    render(<SvgGenerator />);
    expect(screen.getByText("Properties")).toBeInTheDocument();
    expect(screen.getByText("Stroke width")).toBeInTheDocument();
    expect(screen.getByText("Color")).toBeInTheDocument();
  });

  it("shows Radius field for Circle mode", () => {
    render(<SvgGenerator />);
    expect(screen.getByText("Radius")).toBeInTheDocument();
  });

  it("hides Radius field for Polygon mode", () => {
    render(<SvgGenerator />);
    fireEvent.click(screen.getByText("Polygon"));
    expect(screen.queryByText("Radius")).not.toBeInTheDocument();
  });

  it("hides Radius field for Rectangle mode", () => {
    render(<SvgGenerator />);
    fireEvent.click(screen.getByText("Rectangle"));
    expect(screen.queryByText("Radius")).not.toBeInTheDocument();
  });

  it("shows SVG Output section", () => {
    render(<SvgGenerator />);
    expect(screen.getByText("SVG Output")).toBeInTheDocument();
    expect(screen.getByText(/Draw a shape/)).toBeInTheDocument();
  });

  it("has Load Image, Clear, Copy, Export buttons", () => {
    render(<SvgGenerator />);
    expect(screen.getByText(/Load Image/)).toBeInTheDocument();
    expect(screen.getByText("Clear")).toBeInTheDocument();
    expect(screen.getByText(/Copy/)).toBeInTheDocument();
    expect(screen.getByText("Export SVG")).toBeInTheDocument();
  });

  it("shows zoom controls", () => {
    render(<SvgGenerator />);
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("−")).toBeInTheDocument();
    expect(screen.getByText("+")).toBeInTheDocument();
  });

  it("adjusts zoom when + is clicked", () => {
    render(<SvgGenerator />);
    fireEvent.click(screen.getByText("+"));
    expect(screen.getByText("125%")).toBeInTheDocument();
  });

  it("adjusts zoom when − is clicked", () => {
    render(<SvgGenerator />);
    fireEvent.click(screen.getByText("−"));
    expect(screen.getByText("75%")).toBeInTheDocument();
  });

  it("ignores wheel zoom before an image is loaded", () => {
    const { container } = render(<SvgGenerator />);
    const canvas = container.querySelector("canvas")!;
    fireEvent.wheel(canvas, { deltaY: -100 });
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("shows instruction text", () => {
    render(<SvgGenerator />);
    expect(screen.getByText("Load an image to begin.")).toBeInTheDocument();
  });
});

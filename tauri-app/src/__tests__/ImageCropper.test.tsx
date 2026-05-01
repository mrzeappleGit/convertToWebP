import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ImageCropper } from "../components/ImageCropper";

// Mock ResizeObserver
globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as any;

describe("ImageCropper", () => {
  it("renders the Load Image button", () => {
    render(<ImageCropper />);
    expect(screen.getByText(/Load Image/)).toBeInTheDocument();
  });

  it("renders aspect ratio pills", () => {
    render(<ImageCropper />);
    expect(screen.getByText("Free")).toBeInTheDocument();
    expect(screen.getByText("1:1")).toBeInTheDocument();
    expect(screen.getByText("4:3")).toBeInTheDocument();
    expect(screen.getByText("16:9")).toBeInTheDocument();
    expect(screen.getByText("3:2")).toBeInTheDocument();
    expect(screen.getByText("9:16")).toBeInTheDocument();
  });

  it("renders output format pills", () => {
    render(<ImageCropper />);
    expect(screen.getByText("PNG")).toBeInTheDocument();
    expect(screen.getByText("WebP")).toBeInTheDocument();
    expect(screen.getByText("JPEG")).toBeInTheDocument();
  });

  it("starts with Free aspect selected", () => {
    render(<ImageCropper />);
    const freeBtn = screen.getByText("Free").closest("button");
    expect(freeBtn).toHaveClass("active");
  });

  it("starts with PNG format selected", () => {
    render(<ImageCropper />);
    const pngBtn = screen.getByText("PNG").closest("button");
    expect(pngBtn).toHaveClass("active");
  });

  it("shows quality slider when JPEG is selected", () => {
    render(<ImageCropper />);
    fireEvent.click(screen.getByText("JPEG"));
    expect(screen.getByText("Quality")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
  });

  it("hides quality slider when PNG is selected", () => {
    render(<ImageCropper />);
    // PNG is default, quality slider should not show
    const qualityLabels = screen.queryAllByText("Quality");
    // Quality section for output format should not have slider
    expect(qualityLabels.length).toBe(0);
  });

  it("has Reset and Save buttons", () => {
    render(<ImageCropper />);
    expect(screen.getByText("Reset")).toBeInTheDocument();
    expect(screen.getByText(/Save Cropped/)).toBeInTheDocument();
  });

  it("Save button is disabled without an image loaded", () => {
    render(<ImageCropper />);
    const saveBtn = screen.getByText(/Save Cropped/).closest("button");
    expect(saveBtn).toBeDisabled();
  });

  it("Reset button is disabled without an image loaded", () => {
    render(<ImageCropper />);
    const resetBtn = screen.getByText("Reset").closest("button");
    expect(resetBtn).toBeDisabled();
  });

  it("shows instruction text when no image is loaded", () => {
    render(<ImageCropper />);
    expect(screen.getByText("Load an image to begin cropping.")).toBeInTheDocument();
  });

  it("shows Crop Region section", () => {
    render(<ImageCropper />);
    expect(screen.getByText("Crop Region")).toBeInTheDocument();
  });

  it("shows no crop selected message initially", () => {
    render(<ImageCropper />);
    expect(screen.getByText("No crop selected")).toBeInTheDocument();
  });

  it("switches aspect ratio", () => {
    render(<ImageCropper />);
    fireEvent.click(screen.getByText("16:9"));
    const btn = screen.getByText("16:9").closest("button");
    expect(btn).toHaveClass("active");
  });
});

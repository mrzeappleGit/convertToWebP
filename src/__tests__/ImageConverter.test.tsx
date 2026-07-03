import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ImageConverter } from "../components/ImageConverter";

describe("ImageConverter", () => {
  it("renders all sections", () => {
    render(<ImageConverter />);
    expect(screen.getByText("Source")).toBeInTheDocument();
    expect(screen.getByText("Destination")).toBeInTheDocument();
    expect(screen.getByText("Output Format")).toBeInTheDocument();
    expect(screen.getByText("Options")).toBeInTheDocument();
    expect(screen.getByText("Preview")).toBeInTheDocument();
    expect(screen.getByText("Queue")).toBeInTheDocument();
  });

  it("renders all format pills", () => {
    render(<ImageConverter />);
    expect(screen.getByText("WebP")).toBeInTheDocument();
    expect(screen.getByText("PNG")).toBeInTheDocument();
    expect(screen.getByText("JPEG")).toBeInTheDocument();
    expect(screen.getByText("AVIF")).toBeInTheDocument();
    expect(screen.getByText("TIFF")).toBeInTheDocument();
    expect(screen.getByText("BMP")).toBeInTheDocument();
    expect(screen.getByText("GIF")).toBeInTheDocument();
    expect(screen.getByText("ICO")).toBeInTheDocument();
  });

  it("renders option checkboxes", () => {
    render(<ImageConverter />);
    expect(screen.getByText("Convert")).toBeInTheDocument();
    expect(screen.getByText("Compress")).toBeInTheDocument();
    expect(screen.getByText(/Rename to slug/)).toBeInTheDocument();
    expect(screen.getByText("Resize")).toBeInTheDocument();
  });

  it("shows quality slider when Compress is checked", () => {
    render(<ImageConverter />);
    // Compress is checked by default
    expect(screen.getByText(/Quality target/)).toBeInTheDocument();
    expect(screen.getByText("82%")).toBeInTheDocument();
  });

  it("shows size mode pills when Compress is checked", () => {
    render(<ImageConverter />);
    expect(screen.getByText("Quality")).toBeInTheDocument();
    expect(screen.getByText("Target size")).toBeInTheDocument();
  });

  it("switches to target size mode with KB/MB units", () => {
    render(<ImageConverter />);
    fireEvent.click(screen.getByText("Target size"));
    expect(screen.getByText(/Max size per image/)).toBeInTheDocument();
    expect(screen.getByText("KB")).toBeInTheDocument();
    expect(screen.getByText("MB")).toBeInTheDocument();
    expect(screen.queryByText(/Quality target/)).not.toBeInTheDocument();
  });

  it("defaults to 200 KB in target size mode", () => {
    render(<ImageConverter />);
    fireEvent.click(screen.getByText("Target size"));
    expect(screen.getByDisplayValue("200")).toBeInTheDocument();
    expect(screen.getByText("KB").className).toContain("active");
  });

  it("switches back to quality mode", () => {
    render(<ImageConverter />);
    fireEvent.click(screen.getByText("Target size"));
    fireEvent.click(screen.getByText("Quality"));
    expect(screen.getByText(/Quality target/)).toBeInTheDocument();
    expect(screen.queryByText(/Max size per image/)).not.toBeInTheDocument();
  });

  it("shows resize slider when Resize is checked", () => {
    render(<ImageConverter />);
    // Click Resize checkbox
    fireEvent.click(screen.getByText("Resize"));
    expect(screen.getByText(/Scale relative/)).toBeInTheDocument();
  });

  it("has the Run button", () => {
    render(<ImageConverter />);
    expect(screen.getByText(/Run/)).toBeInTheDocument();
  });

  it("Run button is disabled without source/dest paths", () => {
    render(<ImageConverter />);
    const btn = screen.getByText(/Run/).closest("button");
    expect(btn).toBeDisabled();
  });

  it("shows progress bar", () => {
    const { container } = render(<ImageConverter />);
    expect(container.querySelector(".wwk-progress")).toBeInTheDocument();
  });
});

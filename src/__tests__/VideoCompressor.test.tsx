import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VideoCompressor } from "../components/VideoCompressor";

describe("VideoCompressor", () => {
  it("renders all sections", () => {
    render(<VideoCompressor />);
    expect(screen.getByText("Source Video")).toBeInTheDocument();
    expect(screen.getByText("Destination")).toBeInTheDocument();
    expect(screen.getByText("Format")).toBeInTheDocument();
    expect(screen.getByText("Target Size")).toBeInTheDocument();
    expect(screen.getByText("FFmpeg Log")).toBeInTheDocument();
  });

  it("renders format pills (MP4/WebM)", () => {
    render(<VideoCompressor />);
    expect(screen.getByText("MP4")).toBeInTheDocument();
    expect(screen.getByText("WEBM")).toBeInTheDocument();
  });

  it("renders target size unit pills (MB/GB)", () => {
    render(<VideoCompressor />);
    expect(screen.getByText("MB")).toBeInTheDocument();
    expect(screen.getByText("GB")).toBeInTheDocument();
  });

  it("defaults to a 25 MB target", () => {
    render(<VideoCompressor />);
    expect(screen.getByDisplayValue("25")).toBeInTheDocument();
    expect(screen.getByText("MB").className).toContain("active");
  });

  it("explains that quality and resolution are automatic", () => {
    render(<VideoCompressor />);
    expect(screen.getByText(/chosen automatically/)).toBeInTheDocument();
  });

  it("Compress button is disabled without source", () => {
    render(<VideoCompressor />);
    const btn = screen.getByText(/Compress/).closest("button");
    expect(btn).toBeDisabled();
  });

  it("Compress button is disabled with an invalid target size", () => {
    render(<VideoCompressor />);
    fireEvent.change(screen.getByPlaceholderText("Select a video file…"), { target: { value: "C:/video.mp4" } });
    fireEvent.change(screen.getByDisplayValue("25"), { target: { value: "" } });
    const btn = screen.getByText(/Compress/).closest("button");
    expect(btn).toBeDisabled();
  });

  it("Compress button is enabled with source and valid target", () => {
    render(<VideoCompressor />);
    fireEvent.change(screen.getByPlaceholderText("Select a video file…"), { target: { value: "C:/video.mp4" } });
    const btn = screen.getByText(/Compress/).closest("button");
    expect(btn).not.toBeDisabled();
  });

  it("switches unit to GB", () => {
    render(<VideoCompressor />);
    fireEvent.click(screen.getByText("GB"));
    expect(screen.getByText("GB").className).toContain("active");
  });

  it("shows log placeholder", () => {
    render(<VideoCompressor />);
    expect(screen.getByText("Output will appear here…")).toBeInTheDocument();
  });
});

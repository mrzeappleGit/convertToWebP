import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { VideoConverter } from "../components/VideoConverter";

describe("VideoConverter", () => {
  it("renders all sections", () => {
    render(<VideoConverter />);
    expect(screen.getByText("Source Video")).toBeInTheDocument();
    expect(screen.getByText("Destination")).toBeInTheDocument();
    expect(screen.getByText("Format")).toBeInTheDocument();
    expect(screen.getByText("Encoding")).toBeInTheDocument();
    expect(screen.getByText("FFmpeg Log")).toBeInTheDocument();
  });

  it("renders format pills (MP4/WebM)", () => {
    render(<VideoConverter />);
    expect(screen.getByText("MP4")).toBeInTheDocument();
    expect(screen.getByText("WEBM")).toBeInTheDocument();
  });

  it("shows H.264 codec by default for MP4", () => {
    render(<VideoConverter />);
    const select = screen.getByDisplayValue("H.264");
    expect(select).toBeInTheDocument();
  });

  it("switches codec options when format changes to WebM", () => {
    render(<VideoConverter />);
    fireEvent.click(screen.getByText("WEBM"));
    expect(screen.getByDisplayValue("VP9")).toBeInTheDocument();
  });

  it("has CRF quality slider", () => {
    render(<VideoConverter />);
    expect(screen.getByText(/Quality \(CRF\)/)).toBeInTheDocument();
  });

  it("has resolution pills", () => {
    render(<VideoConverter />);
    expect(screen.getByText("Original")).toBeInTheDocument();
    expect(screen.getByText("1080p")).toBeInTheDocument();
    expect(screen.getByText("720p")).toBeInTheDocument();
    expect(screen.getByText("480p")).toBeInTheDocument();
  });

  it("Convert button is disabled without source", () => {
    render(<VideoConverter />);
    const btn = screen.getByText(/Convert/).closest("button");
    expect(btn).toBeDisabled();
  });

  it("shows log placeholder", () => {
    render(<VideoConverter />);
    expect(screen.getByText("Output will appear here…")).toBeInTheDocument();
  });
});

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import App from "../App";

describe("App shell", () => {
  it("renders the brand name in the titlebar", () => {
    render(<App />);
    expect(screen.getByText("CipherLoom")).toBeInTheDocument();
  });

  it("renders all 8 tab buttons", () => {
    render(<App />);
    expect(screen.getByText("Converter")).toBeInTheDocument();
    expect(screen.getByText("File Renamer")).toBeInTheDocument();
    expect(screen.getByText("PDF to Image")).toBeInTheDocument();
    expect(screen.getByText("Video Converter")).toBeInTheDocument();
    expect(screen.getByText("Video Compressor")).toBeInTheDocument();
    expect(screen.getByText("Text Formatter")).toBeInTheDocument();
    expect(screen.getByText("Image Crop")).toBeInTheDocument();
    expect(screen.getByText("Image Mapping")).toBeInTheDocument();
  });

  it("switches to the Video Compressor tab", () => {
    render(<App />);
    fireEvent.click(screen.getByText("Video Compressor"));
    expect(screen.getByText("· Video Compressor")).toBeInTheDocument();
  });

  it("shows active tab name in titlebar", () => {
    render(<App />);
    expect(screen.getByText("· Converter")).toBeInTheDocument();
  });

  it("switches tabs when clicked", () => {
    render(<App />);
    fireEvent.click(screen.getByText("Text Formatter"));
    expect(screen.getByText("· Text Formatter")).toBeInTheDocument();
  });

  it("opens the hamburger menu when clicked", () => {
    render(<App />);
    fireEvent.click(screen.getByText("☰"));
    // Menu items have icon prefixes
    expect(screen.getByText(/Theme/)).toBeInTheDocument();
    expect(screen.getByText(/About/)).toBeInTheDocument();
    expect(screen.getByText(/Licenses/)).toBeInTheDocument();
  });

  it("opens the About dialog from menu", () => {
    render(<App />);
    fireEvent.click(screen.getByText("☰"));
    fireEvent.click(screen.getByText(/ℹ About/));
    expect(screen.getByText(/v\d+\.\d+\.\d+/)).toBeInTheDocument();
    expect(screen.getByText(/workshop of tools/)).toBeInTheDocument();
  });

  it("closes About dialog with Done button", () => {
    render(<App />);
    fireEvent.click(screen.getByText("☰"));
    fireEvent.click(screen.getByText(/ℹ About/));
    // Find the Done button in the dialog footer
    const doneButtons = screen.getAllByText("Done");
    fireEvent.click(doneButtons[doneButtons.length - 1]);
    expect(screen.queryByText(/workshop of tools/)).not.toBeInTheDocument();
  });

  it("opens Licenses dialog from menu", () => {
    render(<App />);
    fireEvent.click(screen.getByText("☰"));
    fireEvent.click(screen.getByText(/📋 Licenses/));
    expect(screen.getByText("FFmpeg")).toBeInTheDocument();
    expect(screen.getByText("Tauri")).toBeInTheDocument();
  });

  it("switches license tabs", () => {
    render(<App />);
    fireEvent.click(screen.getByText("☰"));
    fireEvent.click(screen.getByText(/📋 Licenses/));
    fireEvent.click(screen.getByText("Tauri"));
    expect(screen.getByText(/Tauri Programme/)).toBeInTheDocument();
  });
});

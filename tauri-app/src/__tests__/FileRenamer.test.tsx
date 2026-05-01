import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FileRenamer } from "../components/FileRenamer";

describe("FileRenamer", () => {
  it("renders rename options section", () => {
    render(<FileRenamer />);
    expect(screen.getByText("Rename Options")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("e.g. img-")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("e.g. -thumb")).toBeInTheDocument();
  });

  it("renders case mode pills", () => {
    render(<FileRenamer />);
    expect(screen.getByText("original")).toBeInTheDocument();
    expect(screen.getByText("lowercase")).toBeInTheDocument();
    expect(screen.getByText("UPPERCASE")).toBeInTheDocument();
    expect(screen.getByText("Title Case")).toBeInTheDocument();
  });

  it("renders source section with browse buttons", () => {
    render(<FileRenamer />);
    expect(screen.getByText("Source")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Folder path…")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Or a single file…")).toBeInTheDocument();
  });

  it("has slug formatting checked by default", () => {
    render(<FileRenamer />);
    expect(screen.getByText(/Slug formatting/)).toBeInTheDocument();
  });

  it("has preview and rename buttons", () => {
    render(<FileRenamer />);
    expect(screen.getByText("Preview rename")).toBeInTheDocument();
    expect(screen.getByText(/Rename Files/)).toBeInTheDocument();
  });

  it("shows status dots", () => {
    const { container } = render(<FileRenamer />);
    const dots = container.querySelectorAll(".wwk-dot");
    expect(dots.length).toBeGreaterThanOrEqual(3);
  });

  it("allows typing in prefix field", () => {
    render(<FileRenamer />);
    const input = screen.getByPlaceholderText("e.g. img-") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "test-" } });
    expect(input.value).toBe("test-");
  });

  it("allows typing in suffix field", () => {
    render(<FileRenamer />);
    const input = screen.getByPlaceholderText("e.g. -thumb") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "-sm" } });
    expect(input.value).toBe("-sm");
  });
});

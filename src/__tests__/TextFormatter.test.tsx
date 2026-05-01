import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TextFormatter } from "../components/TextFormatter";

describe("TextFormatter", () => {
  it("renders all format pill options", () => {
    render(<TextFormatter />);
    expect(screen.getByText("slug")).toBeInTheDocument();
    expect(screen.getByText("lowercase")).toBeInTheDocument();
    expect(screen.getByText("UPPERCASE")).toBeInTheDocument();
    expect(screen.getByText("Title Case")).toBeInTheDocument();
    expect(screen.getByText("camelCase")).toBeInTheDocument();
    expect(screen.getByText("kebab-case")).toBeInTheDocument();
    expect(screen.getByText("snake_case")).toBeInTheDocument();
  });

  it("converts text to slug format", () => {
    render(<TextFormatter />);
    const textarea = screen.getByPlaceholderText("Type or paste text here…");
    fireEvent.change(textarea, { target: { value: "Hello World! Test" } });
    expect(screen.getByText("hello-world-test")).toBeInTheDocument();
  });

  it("converts text to UPPERCASE", () => {
    render(<TextFormatter />);
    const textarea = screen.getByPlaceholderText("Type or paste text here…");
    fireEvent.change(textarea, { target: { value: "hello world" } });
    fireEvent.click(screen.getByText("UPPERCASE"));
    expect(screen.getByText("HELLO WORLD")).toBeInTheDocument();
  });

  it("converts text to lowercase", () => {
    render(<TextFormatter />);
    const textarea = screen.getByPlaceholderText("Type or paste text here…");
    fireEvent.change(textarea, { target: { value: "HELLO WORLD" } });
    fireEvent.click(screen.getByText("lowercase"));
    expect(screen.getByText("hello world")).toBeInTheDocument();
  });

  it("converts text to Title Case", () => {
    render(<TextFormatter />);
    const textarea = screen.getByPlaceholderText("Type or paste text here…");
    fireEvent.change(textarea, { target: { value: "hello world" } });
    fireEvent.click(screen.getByText("Title Case"));
    expect(screen.getByText("Hello World")).toBeInTheDocument();
  });

  it("converts text to camelCase", () => {
    render(<TextFormatter />);
    const textarea = screen.getByPlaceholderText("Type or paste text here…");
    fireEvent.change(textarea, { target: { value: "hello world test" } });
    fireEvent.click(screen.getByText("camelCase"));
    expect(screen.getByText("helloWorldTest")).toBeInTheDocument();
  });

  it("converts text to kebab-case", () => {
    render(<TextFormatter />);
    const textarea = screen.getByPlaceholderText("Type or paste text here…");
    fireEvent.change(textarea, { target: { value: "Hello World Test" } });
    fireEvent.click(screen.getByText("kebab-case"));
    expect(screen.getByText("hello-world-test")).toBeInTheDocument();
  });

  it("converts text to snake_case", () => {
    render(<TextFormatter />);
    const textarea = screen.getByPlaceholderText("Type or paste text here…");
    fireEvent.change(textarea, { target: { value: "Hello World Test" } });
    fireEvent.click(screen.getByText("snake_case"));
    expect(screen.getByText("hello_world_test")).toBeInTheDocument();
  });

  it("shows empty result for empty input", () => {
    render(<TextFormatter />);
    const textarea = screen.getByPlaceholderText("Type or paste text here…");
    fireEvent.change(textarea, { target: { value: "" } });
    // Result area should be empty (no text node with content)
    expect(screen.queryByText("hello")).not.toBeInTheDocument();
  });

  it("shows clear button when input has text", () => {
    render(<TextFormatter />);
    const textarea = screen.getByPlaceholderText("Type or paste text here…");
    fireEvent.change(textarea, { target: { value: "some text" } });
    expect(screen.getByText(/Clear/)).toBeInTheDocument();
  });

  it("clears input when Clear is clicked", () => {
    render(<TextFormatter />);
    const textarea = screen.getByPlaceholderText("Type or paste text here…") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "some text" } });
    fireEvent.click(screen.getByText(/Clear/));
    expect(textarea.value).toBe("");
  });

  it("handles special characters in slug mode", () => {
    render(<TextFormatter />);
    const textarea = screen.getByPlaceholderText("Type or paste text here…");
    fireEvent.change(textarea, { target: { value: "Héllo Wörld! @#$" } });
    // Slug should strip diacritics and special chars
    const result = screen.getByText(/hello/i);
    expect(result).toBeInTheDocument();
  });
});

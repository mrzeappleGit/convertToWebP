import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Section } from "../components/Section";

describe("Section", () => {
  it("renders title as uppercase label", () => {
    render(<Section title="Source">content</Section>);
    expect(screen.getByText("Source")).toBeInTheDocument();
  });

  it("renders children", () => {
    render(<Section title="Test"><p>Child content</p></Section>);
    expect(screen.getByText("Child content")).toBeInTheDocument();
  });

  it("renders without children", () => {
    render(<Section title="Empty" />);
    expect(screen.getByText("Empty")).toBeInTheDocument();
  });

  it("renders after prop", () => {
    render(<Section title="Title" after={<span>Extra</span>}>body</Section>);
    expect(screen.getByText("Extra")).toBeInTheDocument();
  });
});

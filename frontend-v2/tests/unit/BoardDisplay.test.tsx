import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BoardDisplay } from "@/components/hand/BoardDisplay";

describe("BoardDisplay", () => {
  it("renders 3 cards for a flop", () => {
    render(<BoardDisplay cards={["Kh", "9d", "4c"]} />);
    expect(screen.getByText(/K♥/)).toBeInTheDocument();
    expect(screen.getByText(/9♦/)).toBeInTheDocument();
    expect(screen.getByText(/4♣/)).toBeInTheDocument();
  });

  it("renders nothing visible for empty board", () => {
    const { container } = render(<BoardDisplay cards={[]} />);
    expect(container.querySelectorAll("[class*='inline-flex']").length).toBe(0);
  });

  it("supports sm size variant", () => {
    const { container } = render(
      <BoardDisplay cards={["Ah", "Ks"]} size="sm" />,
    );
    expect(container.firstChild).toHaveClass("text-base");
  });
});

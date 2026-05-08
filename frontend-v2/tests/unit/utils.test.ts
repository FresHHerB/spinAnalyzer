import { describe, it, expect } from "vitest";
import { fmt, pct, cn } from "@/lib/utils";

describe("fmt", () => {
  it("rounds to default 1 decimal", () => {
    expect(fmt(3.14159)).toBe("3.1");
  });
  it("returns em dash for null", () => {
    expect(fmt(null)).toBe("—");
  });
  it("returns em dash for undefined", () => {
    expect(fmt(undefined)).toBe("—");
  });
  it("respects custom dp", () => {
    expect(fmt(3.14159, 3)).toBe("3.142");
  });
});

describe("pct", () => {
  it("appends % sign", () => {
    expect(pct(33.3)).toBe("33.3%");
  });
  it("handles null", () => {
    expect(pct(null)).toBe("—");
  });
});

describe("cn", () => {
  it("merges class strings", () => {
    expect(cn("a", "b")).toBe("a b");
  });
  it("dedupes tailwind classes", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });
  it("handles falsy", () => {
    expect(cn("a", false, undefined, "b")).toBe("a b");
  });
});

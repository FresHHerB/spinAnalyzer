import { test, expect } from "@playwright/test";

test.describe("smoke", () => {
  test("dashboard loads and shows villain table", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    // KPI cards show
    await expect(page.getByText("Indexed villains")).toBeVisible();
  });

  test("villains list page", async ({ page }) => {
    await page.goto("/villains");
    await expect(page.getByRole("heading", { name: "Villains" })).toBeVisible();
  });

  test("search by-decision page renders form", async ({ page }) => {
    await page.goto("/search/by-decision");
    await expect(page.getByPlaceholder(/decision/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /search/i })).toBeVisible();
  });

  test("spot builder page renders form", async ({ page }) => {
    await page.goto("/search/by-spot-builder");
    await expect(
      page.getByRole("heading", { name: "Spot builder" }),
    ).toBeVisible();
  });

  test("upload page renders dropzone", async ({ page }) => {
    await page.goto("/upload");
    await expect(page.getByText(/drop hand-history files/i)).toBeVisible();
  });

  test("sidebar navigates between pages", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /upload/i }).click();
    await expect(page).toHaveURL(/.*upload$/);
  });
});

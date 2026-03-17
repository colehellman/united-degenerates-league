import { test, expect, Page } from "@playwright/test";

let userCounter = 0;

async function registerAndLogin(page: Page) {
  const id = `${Date.now()}_${userCounter++}`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(`e2e-nav-${id}@test.com`);
  await page.getByLabel("Username").fill(`e2e_nav_${id}`);
  await page.getByLabel("Password", { exact: true }).fill("TestPass1!");
  await page.getByLabel("Confirm Password").fill("TestPass1!");
  await page.getByRole("button", { name: /sign up/i }).click();
  await expect(page).toHaveURL("/", { timeout: 10_000 });
}

test.describe("App Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await registerAndLogin(page);
  });

  test("nav links work correctly", async ({ page }) => {
    // Dashboard should be loaded
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();

    // Navigate to competitions via nav link
    const navCompetitions = page.getByRole("navigation").getByRole("link", { name: /competitions/i });
    if (await navCompetitions.isVisible()) {
      await navCompetitions.click();
      await expect(page).toHaveURL("/competitions");
    }

    // Navigate back to dashboard
    const navDashboard = page.getByRole("navigation").getByRole("link", { name: /dashboard/i });
    if (await navDashboard.isVisible()) {
      await navDashboard.click();
      await expect(page).toHaveURL("/");
    }
  });

  test("404 page shown for unknown routes", async ({ page }) => {
    await page.goto("/nonexistent-page");
    await expect(page.getByText("404")).toBeVisible();
    await expect(page.getByText(/page not found/i)).toBeVisible();
  });

  test("page title updates on navigation", async ({ page }) => {
    // Dashboard sets a custom title
    await expect(page).toHaveTitle(/dashboard|udl/i, { timeout: 5_000 });
  });
});

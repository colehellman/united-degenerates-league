import { test, expect, Page } from "@playwright/test";

const TEST_USER = {
  email: `e2e-comp-${Date.now()}@test.com`,
  username: `e2e_comp_${Date.now()}`,
  password: "TestPass1!",
};

async function registerAndLogin(page: Page) {
  await page.goto("/register");
  await page.getByLabel("Email").fill(TEST_USER.email);
  await page.getByLabel("Username").fill(TEST_USER.username);
  await page.getByLabel("Password", { exact: true }).fill(TEST_USER.password);
  await page.getByLabel("Confirm Password").fill(TEST_USER.password);
  await page.getByRole("button", { name: /sign up/i }).click();
  await expect(page).toHaveURL("/", { timeout: 10_000 });
}

test.describe("Competition Flow", () => {
  test.beforeEach(async ({ page }) => {
    await registerAndLogin(page);
  });

  test("navigate to competitions page from dashboard", async ({ page }) => {
    await page.getByRole("link", { name: /browse competitions/i }).click();
    await expect(page).toHaveURL("/competitions");
    await expect(page.getByRole("heading", { name: /competitions/i })).toBeVisible();
  });

  test("navigate to create competition form", async ({ page }) => {
    await page.getByRole("link", { name: /create competition/i }).click();
    await expect(page).toHaveURL("/competitions/create");

    // Form fields should be present
    await expect(page.getByLabel(/name/i)).toBeVisible();
    await expect(page.getByText(/daily picks/i)).toBeVisible();
  });

  test("create a daily picks competition", async ({ page }) => {
    await page.goto("/competitions/create");

    // Fill the form
    const compName = `E2E Test Comp ${Date.now()}`;
    await page.getByLabel(/^name$/i).fill(compName);
    await page.getByLabel(/description/i).fill("E2E test competition");

    // Select a league (wait for leagues to load)
    const leagueSelect = page.getByLabel(/league/i);
    await expect(leagueSelect).toBeVisible({ timeout: 10_000 });
    // Pick the first non-empty option
    const options = leagueSelect.locator("option");
    const count = await options.count();
    if (count > 1) {
      const value = await options.nth(1).getAttribute("value");
      if (value) await leagueSelect.selectOption(value);
    }

    // Set dates (30 days from now)
    const today = new Date();
    const start = new Date(today);
    start.setDate(start.getDate() + 1);
    const end = new Date(today);
    end.setDate(end.getDate() + 30);

    const fmt = (d: Date) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

    await page.getByLabel(/start date/i).fill(fmt(start));
    await page.getByLabel(/end date/i).fill(fmt(end));

    // Submit
    await page.getByRole("button", { name: /create/i }).click();

    // Should redirect to competition detail or competitions list
    await expect(page).not.toHaveURL("/competitions/create", { timeout: 10_000 });

    // The competition name should appear somewhere on the new page
    await expect(page.getByText(compName)).toBeVisible({ timeout: 5_000 });
  });
});

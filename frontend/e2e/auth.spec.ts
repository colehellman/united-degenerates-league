import { test, expect } from "@playwright/test";

let userCounter = 0;

function uniqueUser() {
  const id = `${Date.now()}_${userCounter++}`;
  return {
    email: `e2e-${id}@test.com`,
    username: `e2e_user_${id}`,
    password: "TestPass1!",
  };
}

test.describe("Authentication Flow", () => {
  test("register a new account and land on dashboard", async ({ page }) => {
    const user = uniqueUser();
    await page.goto("/register");

    await expect(page.getByRole("heading", { name: /create your account/i })).toBeVisible();

    await page.getByLabel("Email").fill(user.email);
    await page.getByLabel("Username").fill(user.username);
    await page.getByLabel("Password", { exact: true }).fill(user.password);
    await page.getByLabel("Confirm Password").fill(user.password);

    // Password checks should all be green
    await expect(page.getByText("✓ At least 8 characters")).toBeVisible();
    await expect(page.getByText("✓ One uppercase letter")).toBeVisible();
    await expect(page.getByText("✓ One digit")).toBeVisible();
    await expect(page.getByText("✓ One special character")).toBeVisible();

    await page.getByRole("button", { name: /sign up/i }).click();

    // Should redirect to dashboard
    await expect(page).toHaveURL("/", { timeout: 10_000 });
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
  });

  test("logout and login with same credentials", async ({ page }) => {
    const user = uniqueUser();

    // Register a fresh user
    await page.goto("/register");
    await page.getByLabel("Email").fill(user.email);
    await page.getByLabel("Username").fill(user.username);
    await page.getByLabel("Password", { exact: true }).fill(user.password);
    await page.getByLabel("Confirm Password").fill(user.password);
    await page.getByRole("button", { name: /sign up/i }).click();
    await expect(page).toHaveURL("/", { timeout: 10_000 });

    // Logout via nav
    await page.getByRole("button", { name: /logout/i }).click();
    await expect(page).toHaveURL("/login");

    // Login with same credentials
    await page.getByLabel("Email").fill(user.email);
    await page.getByLabel("Password").fill(user.password);
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL("/", { timeout: 10_000 });
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
  });

  test("unauthenticated user is redirected to login", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
  });

  test("login with wrong password shows error", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill("nonexistent@test.com");
    await page.getByLabel("Password").fill("WrongPass1!");
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page.getByText(/login failed|invalid|incorrect/i)).toBeVisible({ timeout: 10_000 });
  });
});

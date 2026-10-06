import { PASSWORD, unique } from "./fixtures/api";
import { ADMIN, expect, logIn, test } from "./fixtures";

test.describe("admin flow (AC4)", () => {
  test("onboard a doctor, then deactivate and reactivate a user", async ({ page }) => {
    const email = `e2e-onboard-${unique()}@example.test`;
    await logIn(page, ADMIN.email, ADMIN.password);
    await expect(page.getByRole("heading", { name: "Users" })).toBeVisible();
    await expect(page.getByTestId("user-row").first()).toBeVisible();
    await expect(page).toHaveScreenshot("user-list.png", { mask: [page.getByRole("table")] });

    await page.getByRole("link", { name: "Onboard doctor" }).click();
    await expect(page.getByRole("heading", { name: "Onboard a doctor" })).toBeVisible();
    await expect(page).toHaveScreenshot("onboard-form.png");
    await page.getByLabel("Full name").fill("E2E Onboarded Doctor");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Initial password").fill(PASSWORD);
    await page.getByLabel("Specialty").fill("Dermatology");
    await page.getByLabel("Languages (codes, comma separated)").fill("en");
    await page.getByLabel("Fee (decimal, 2 places)").fill("35.00");
    await page.getByRole("button", { name: "Onboard doctor" }).click();
    await expect(page.getByTestId("onboard-success")).toBeVisible();
    await expect(page.getByTestId("new-email")).toHaveText(email);

    await page.getByRole("link", { name: "Users" }).click();
    const row = page.getByTestId("user-row").filter({ hasText: email });
    await expect(row).toBeVisible();
    await expect(row.getByTestId("user-status")).toHaveText("ACTIVE");

    await page.getByRole("button", { name: `Deactivate ${email}` }).click();
    await expect(row.getByTestId("user-status")).toHaveText("INACTIVE");
    await page.getByRole("button", { name: `Reactivate ${email}` }).click();
    await expect(row.getByTestId("user-status")).toHaveText("ACTIVE");
  });
});

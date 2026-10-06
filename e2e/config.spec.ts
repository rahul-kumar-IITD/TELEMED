import { expect, test } from "./fixtures";

// Chromium reports the canonical alias of Asia/Kolkata; the offset check pins the actual zone.
const TIMEZONE_NAMES = ["Asia/Kolkata", "Asia/Calcutta"];

test.describe("playwright environment (AC1)", () => {
  test("the page runs in the fixed Asia/Kolkata timezone", async ({ page }) => {
    await page.goto("/login");
    const zone = await page.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone);
    expect(TIMEZONE_NAMES).toContain(zone);
    expect(await page.evaluate(() => new Date(0).getTimezoneOffset())).toBe(-330);
  });

  test("new Date() returns the fixed backend instant and does not advance", async ({ page, fixedNow }) => {
    await page.goto("/login");
    const [first, second] = await page.evaluate(async () => {
      const a = new Date().toISOString();
      await new Promise((resolve) => setTimeout(resolve, 100));
      return [a, new Date().toISOString()];
    });
    expect(first).toBe(fixedNow.toISOString());
    expect(second).toBe(fixedNow.toISOString());
  });
});

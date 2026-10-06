import { defineConfig, devices } from "@playwright/test";

/** Browser timezone; equals the backend PROVIDER_TIMEZONE started by scripts/start-e2e-backend.mjs. */
export const TIMEZONE_ID = "Asia/Kolkata";

// The fixed clock is installed per test by e2e/fixtures/index.ts (page.clock.setFixedTime) at the
// backend's own current instant, so browser and server agree on "now" while time stays frozen.
export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  snapshotPathTemplate: "{testDir}/__screenshots__/{testFileName}-snapshots/{arg}-{projectName}-{platform}{ext}",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  timeout: 60_000,
  reporter: [["list"]],
  expect: { toHaveScreenshot: { animations: "disabled", caret: "hide", maxDiffPixelRatio: 0.002 } },
  use: {
    baseURL: "http://localhost:5173",
    timezoneId: TIMEZONE_ID,
    locale: "en-GB",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } },
    },
    {
      name: "mobile",
      // Patient-facing flows only (story AC2); doctor and admin flows are desktop-only.
      testMatch: ["patient.spec.ts", "config.spec.ts"],
      use: { ...devices["Desktop Chrome"], viewport: { width: 375, height: 800 }, hasTouch: true },
    },
  ],
  webServer: [
    {
      command: "node scripts/start-e2e-backend.mjs",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: "npm --prefix frontend run dev",
      url: "http://localhost:5173",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});

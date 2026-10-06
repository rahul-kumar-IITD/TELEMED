// Shared fixtures: fixed clock + data factories over the real backend.
import { test as base, expect, type Page } from "@playwright/test";
import {
  ADMIN,
  backendNow,
  createDoctor,
  registerPatient,
  type DoctorData,
  type PatientData,
} from "./api";

interface Fixtures {
  /** The instant the browser clock is frozen at: the backend's own "now" at test start. */
  fixedNow: Date;
  makeDoctor: () => Promise<DoctorData>;
  makePatient: () => Promise<PatientData>;
}

export const test = base.extend<Fixtures>({
  fixedNow: async ({ request }, use) => {
    await use(await backendNow(request));
  },
  // Timezone comes from playwright.config (use.timezoneId); the clock is frozen before any page script runs.
  page: async ({ page, fixedNow }, use) => {
    await page.clock.setFixedTime(fixedNow);
    await use(page);
  },
  makeDoctor: async ({ request }, use) => {
    await use(() => createDoctor(request));
  },
  makePatient: async ({ request }, use) => {
    await use(() => registerPatient(request));
  },
});

export { expect, ADMIN };

export async function logIn(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
}

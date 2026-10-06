import type { Page } from "@playwright/test";
import { addNote, bookSlot, changeStatus, DOCTOR_NAME } from "./fixtures/api";
import { expect, logIn, test } from "./fixtures";

/** Dates, times and the random specialty change per run; they are masked in screenshots. */
const dynamicText = (page: Page, specialty: string) => [
  page.getByLabel("Specialty"),
  page.getByText(specialty),
  page.getByText(/Next slot:/),
  page.getByRole("heading", { level: 3 }),
  page.getByText(/^Time:/),
];

async function bookFirstSlotViaUi(page: Page, specialty: string): Promise<void> {
  await page.getByLabel("Specialty").fill(specialty);
  await expect(page.getByTestId("doctor-card")).toHaveCount(1);
  await page.getByRole("link", { name: `View ${DOCTOR_NAME}` }).click();
  await page.getByRole("button", { name: /^09:00/ }).first().click();
  await page.getByRole("button", { name: "Continue to confirm" }).click();
  await page.getByRole("button", { name: "Confirm booking" }).click();
  await expect(page.getByRole("heading", { name: "Booking confirmed" })).toBeVisible();
}

test.describe("patient flow (AC2)", () => {
  test("search, pick a slot, book, see it in My appointments, then cancel", async ({ page, makeDoctor, makePatient }) => {
    const doctor = await makeDoctor();
    const patient = await makePatient();

    await page.goto("/login");
    await expect(page).toHaveScreenshot("login.png");
    await logIn(page, patient.email, patient.password);
    await expect(page.getByRole("heading", { name: "Find a doctor" })).toBeVisible();

    await page.getByLabel("Specialty").fill(doctor.specialty);
    await expect(page.getByTestId("doctor-card")).toHaveCount(1);
    await expect(page).toHaveScreenshot("doctor-search.png", { mask: dynamicText(page, doctor.specialty) });

    await page.getByRole("link", { name: `View ${DOCTOR_NAME}` }).click();
    await expect(page.getByRole("button", { name: /^09:00/ })).toHaveCount(2);
    await page.getByRole("button", { name: /^09:00/ }).first().click();
    await expect(page).toHaveScreenshot("slot-picker.png", { mask: dynamicText(page, doctor.specialty) });
    await page.getByRole("button", { name: "Continue to confirm" }).click();
    await page.getByRole("button", { name: "Confirm booking" }).click();
    await expect(page.getByTestId("confirmation")).toContainText(DOCTOR_NAME);
    await expect(page).toHaveScreenshot("booking-confirmed.png", { mask: [page.getByText(/^Time:/)] });

    await page.getByRole("link", { name: "My appointments" }).click();
    await expect(page.getByTestId("appointment-status")).toHaveText("BOOKED");
    await expect(page).toHaveScreenshot("my-appointments.png", { mask: dynamicText(page, doctor.specialty) });

    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await page.getByRole("button", { name: "Confirm cancel" }).click();
    await expect(page.getByTestId("appointment-status")).toHaveText("CANCELLED");
  });

  test("book a slot and reschedule it to a different slot", async ({ page, makeDoctor, makePatient }) => {
    const doctor = await makeDoctor();
    const patient = await makePatient();
    await logIn(page, patient.email, patient.password);
    await expect(page.getByRole("heading", { name: "Find a doctor" })).toBeVisible();
    await bookFirstSlotViaUi(page, doctor.specialty);

    await page.getByRole("link", { name: "My appointments" }).click();
    const when = page.getByText(doctor.specialty);
    const before = await when.textContent();
    await page.getByRole("button", { name: "Reschedule" }).click();
    const panel = page.getByRole("group", { name: "Reschedule" });
    await expect(panel).toBeVisible();
    await panel.getByRole("button", { name: /^09:00/ }).click();
    await page.getByRole("button", { name: "Confirm reschedule" }).click();

    await expect(page.getByTestId("appointment-status")).toHaveText("BOOKED");
    await expect(when).not.toHaveText(before ?? "");
  });

  test("read consultation notes of a completed appointment", async ({ page, request, makeDoctor, makePatient }) => {
    const doctor = await makeDoctor();
    const patient = await makePatient();
    const appt = await bookSlot(request, patient, doctor.slots[0]!.slot_id);
    for (const status of ["CHECKED_IN", "IN_PROGRESS", "COMPLETED"]) {
      await changeStatus(request, doctor.token, appt.appointment_id, status);
    }
    await addNote(request, doctor.token, appt.appointment_id, "Rest, fluids and a follow-up in two weeks.");

    await logIn(page, patient.email, patient.password);
    await page.getByRole("link", { name: "My appointments" }).click();
    await page.getByRole("link", { name: "View consultation notes" }).click();
    await expect(page.getByTestId("note")).toContainText("Rest, fluids");
    await expect(page).toHaveScreenshot("notes.png", { mask: [page.getByTestId("note").locator("p").first()] });
  });
});

import { bookSlot, providerTimezone, zoneDate } from "./fixtures/api";
import { expect, logIn, test } from "./fixtures";

test.describe("doctor flow (AC3)", () => {
  test("queue status changes, NO_SHOW disabled before start, then add a note after COMPLETED", async ({
    page,
    request,
    makeDoctor,
    makePatient,
  }) => {
    const doctor = await makeDoctor();
    const patient = await makePatient();
    const slot = doctor.slots[0]!;
    await bookSlot(request, patient, slot.slot_id);
    const slotDay = zoneDate(slot.start_time, await providerTimezone(request));

    await logIn(page, doctor.email, doctor.password);
    await expect(page.getByRole("heading", { name: "Daily queue" })).toBeVisible();
    await page.getByLabel("Date").fill(slotDay);
    await expect(page.getByTestId("queue-row")).toHaveCount(1);

    const status = page.getByTestId("queue-status");
    await expect(status).toHaveText("BOOKED");
    await expect(page.getByRole("button", { name: "Mark NO_SHOW" })).toBeDisabled();
    await expect(page.getByText("Mark NO_SHOW is available once the start time has passed.")).toBeVisible();
    await expect(page).toHaveScreenshot("queue.png", { mask: [page.getByLabel("Date"), page.getByTestId("queue-zone")] });

    await page.getByRole("button", { name: "Check in" }).click();
    await expect(status).toHaveText("CHECKED_IN");
    await expect(page.getByRole("button", { name: "Mark NO_SHOW" })).toBeDisabled();
    await page.getByRole("button", { name: "Start consultation" }).click();
    await expect(status).toHaveText("IN_PROGRESS");
    await page.getByRole("button", { name: "Mark completed" }).click();
    await expect(status).toHaveText("COMPLETED");

    await page.getByRole("link", { name: "Details" }).click();
    await expect(page.getByTestId("detail-status")).toHaveText("COMPLETED");
    await page.getByRole("textbox", { name: "Consultation note" }).fill("Patient advised rest and fluids.");
    await page.getByRole("button", { name: "Add note" }).click();
    await expect(page.getByTestId("note")).toContainText("Patient advised rest and fluids.");
    await expect(page).toHaveScreenshot("appointment-notes.png", {
      mask: [page.getByTestId("note").locator("p").first(), page.getByText(/^\w{3} \d+ \w{3}, \d\d:\d\d/)],
    });
  });

  test("the slot calendar lists open and blocked slots", async ({ page, makeDoctor }) => {
    const doctor = await makeDoctor();
    await logIn(page, doctor.email, doctor.password);
    await page.getByRole("link", { name: "Slots" }).click();
    await expect(page.getByRole("heading", { name: "Slot calendar" })).toBeVisible();
    await expect(page.getByTestId("slot-status").filter({ hasText: "AVAILABLE" })).toHaveCount(2);
    await expect(page).toHaveScreenshot("slot-calendar.png", { mask: [page.getByTestId("slot-day")] });
  });
});

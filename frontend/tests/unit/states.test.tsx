import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AriaLiveRegion } from "../../src/components/AriaLiveRegion";
import { EmptyState } from "../../src/components/EmptyState";
import { ErrorState } from "../../src/components/ErrorState";
import { LoadingState } from "../../src/components/LoadingState";
import { json, loginAs, mockFetch, renderApp } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

describe("shared states", () => {
  it("renders loading, empty and error states", async () => {
    const onRetry = vi.fn();
    render(
      <>
        <LoadingState />
        <EmptyState />
        <ErrorState message="Oops" onRetry={onRetry} />
      </>,
    );
    expect(screen.getByTestId("loading-state")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Nothing here yet.");
    expect(screen.getByRole("alert")).toHaveTextContent("Oops");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("supports a polite status region and an error state without retry", () => {
    render(
      <>
        <AriaLiveRegion>hello</AriaLiveRegion>
        <ErrorState message="No retry" />
      </>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("hello");
    expect(screen.queryByRole("button", { name: "Retry" })).toBeNull();
  });
});

describe("shell page states", () => {
  it("shows loading, then empty", async () => {
    loginAs("PATIENT");
    let release: (r: Response) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>((r) => (release = r))),
    );
    renderApp("/doctors");
    expect(await screen.findByTestId("loading-state")).toBeInTheDocument();
    release(json(200, { items: [], total: 0 }));
    expect(await screen.findByTestId("empty-state")).toHaveTextContent("No doctors found.");
  });

  it("shows an error on 500 and recovers on retry", async () => {
    loginAs("PATIENT");
    let ok = false;
    mockFetch(() =>
      ok ? json(200, { items: [{ a: 1 }], total: 1 }) : json(500, { code: "INTERNAL_ERROR", message: "x" }),
    );
    renderApp("/doctors");
    expect(await screen.findByTestId("error-state")).toHaveTextContent("Something went wrong");
    ok = true;
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("This section is coming soon.")).toBeInTheDocument();
  });

  it("treats non-list objects as non-empty and non-JSON errors as generic", async () => {
    loginAs("PATIENT");
    mockFetch(() => json(200, { doctor_id: 1 }));
    const first = renderApp("/doctors/1");
    expect(await screen.findByText("This section is coming soon.")).toBeInTheDocument();
    first.unmount();
    mockFetch(() => new Response("<html>", { status: 502 }));
    renderApp("/doctors/1");
    expect(await screen.findByTestId("error-state")).toHaveTextContent("Something went wrong");
  });
});

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api");

vi.mock("react-router-dom", async () => ({
  ...(await vi.importActual("react-router-dom")),
  useParams: () => ({ id: "7" }),
  useNavigate: () => vi.fn(),
}));

import { apiCall, errorMessage } from "../api";
import EditCase from "./EditCase";

function aCase(overrides = {}) {
  return {
    id: 7,
    title: "Property dispute",
    case_type: "Civil",
    status: "Intake",
    version: 3,
    client: { id: 1, name: "Ramesh Kumar" },
    owner: { id: 2, name: "Ali Khan" },
    assignee: null,
    notes: [],
    assignments: [],
    status_changes: [],
    created_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T00:00:00Z",
    ...overrides,
  };
}

describe("EditCase", () => {
  beforeEach(() => {
    errorMessage.mockImplementation((res) => res?.data?.error?.message ?? "Something went wrong.");
  });

  it("form ko maujooda title aur type se bharta hai", async () => {
    apiCall.mockResolvedValue({ ok: true, status: 200, data: aCase() });

    render(<EditCase />, { wrapper: MemoryRouter });

    expect(await screen.findByLabelText("Title")).toHaveValue("Property dispute");
    expect(screen.getByLabelText("Type")).toHaveValue("Civil");
  });

  it("band case par form dikhata hi nahi", async () => {
    // The API returns 409 for editing a closed case, so showing the form would
    // offer a button that can only ever be refused. CaseDetail hides the Edit
    // link, but the URL can still be typed - this is that route.
    apiCall.mockResolvedValue({ ok: true, status: 200, data: aCase({ status: "Closed" }) });

    render(<EditCase />, { wrapper: MemoryRouter });

    expect(
      await screen.findByText("This case is closed, so it cannot be edited.")
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
  });

  it("save karte waqt wahi version wapas bhejta hai jo page dekh raha tha", async () => {
    // The front-end half of US-21: without the version the backend has nothing
    // to compare, and two people's work can collide.
    apiCall.mockResolvedValue({ ok: true, status: 200, data: aCase() });

    render(<EditCase />, { wrapper: MemoryRouter });
    await screen.findByLabelText("Title");

    apiCall.mockClear();
    screen.getByRole("button", { name: "Save" }).click();

    // The first call is the PATCH; its third argument is the body.
    const [method, path, body] = apiCall.mock.calls[0];
    expect(method).toBe("PATCH");
    expect(path).toBe("/cases/7");
    expect(body.version).toBe(3);
  });

  it("koi aur pehle save kar chuka ho to API ka 409 message dikhata hai", async () => {
    apiCall.mockResolvedValueOnce({ ok: true, status: 200, data: aCase() });

    render(<EditCase />, { wrapper: MemoryRouter });
    await screen.findByLabelText("Title");

    apiCall.mockResolvedValueOnce({
      ok: false,
      status: 409,
      data: {
        error: {
          status: 409,
          message: "This case was changed by someone else. Reload and try again.",
          fields: {},
        },
      },
    });

    screen.getByRole("button", { name: "Save" }).click();

    expect(
      await screen.findByText("This case was changed by someone else. Reload and try again.")
    ).toBeInTheDocument();
  });
});

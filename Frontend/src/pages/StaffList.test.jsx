import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api");

vi.mock("react-router-dom", async () => ({
  ...(await vi.importActual("react-router-dom")),
  useOutletContext: () => ({ id: 1, name: "Admin", role: "admin" }),
}));

import { apiCall, errorMessage } from "../api";
import StaffList from "./StaffList";

// Mocking the api module also mocks errorMessage, so reimplement it here -
// otherwise every error renders "undefined" and the test proves nothing.
function useTheRealErrorMessage() {
  errorMessage.mockImplementation((res) => {
    if (res.status === 0) return "Could not reach the server. Is it running?";
    const error = res.data && res.data.error;
    if (!error) return "Something went wrong.";
    return Object.values(error.fields || {})[0] || error.message;
  });
}

describe("StaffList", () => {
  beforeEach(() => {
    useTheRealErrorMessage();
  });

  it("staff members ki list dikhata hai", async () => {
    apiCall.mockResolvedValue({
      ok: true,
      status: 200,
      data: [
        { id: 1, name: "Admin", email: "admin@example.com", role: "admin" },
        { id: 2, name: "Ali Khan", email: "ali@example.com", role: "staff" },
      ],
    });

    render(<StaffList />, { wrapper: MemoryRouter });

    expect(await screen.findByText("Ali Khan")).toBeInTheDocument();
    expect(screen.getByText("ali@example.com")).toBeInTheDocument();
  });

  it("API 500 de to page crash nahi hota, error dikhata hai", async () => {
    // The bug this test holds down. Without the `res.ok` check, `res.data` is the
    // error envelope - an object, not an array - and `staff.map(...)` throws
    // `.map is not a function`, which takes the whole React tree down to a blank
    // screen. Every other page already had the check; only this one missed it.
    apiCall.mockResolvedValue({
      ok: false,
      status: 500,
      data: { error: { status: 500, message: "Something went wrong.", fields: {} } },
    });

    render(<StaffList />, { wrapper: MemoryRouter });

    // The page survived - the heading is still there...
    expect(await screen.findByRole("heading", { name: "Staff" })).toBeInTheDocument();
    // ...and the user was told something went wrong.
    expect(await screen.findByText("Something went wrong.")).toBeInTheDocument();
  });

  it("server band ho to bhi crash nahi hota", async () => {
    // On a network failure apiCall returns { status: 0, data: null }, so
    // `staff.map` breaks here too - and this is commoner than a 500, because
    // every page hits it when the backend is simply not running.
    apiCall.mockResolvedValue({ ok: false, status: 0, data: null });

    render(<StaffList />, { wrapper: MemoryRouter });

    expect(await screen.findByRole("heading", { name: "Staff" })).toBeInTheDocument();
    expect(
      await screen.findByText("Could not reach the server. Is it running?")
    ).toBeInTheDocument();
  });

  it("401 par koi error nahi dikhata - wahan login screen khud aa jaati hai", async () => {
    // apiCall already drops the token and redirects on a 401, so a red error on
    // top of that is noise - the user has gone.
    apiCall.mockResolvedValue({
      ok: false,
      status: 401,
      data: { error: { status: 401, message: "Not authenticated", fields: {} } },
    });

    render(<StaffList />, { wrapper: MemoryRouter });

    await screen.findByRole("heading", { name: "Staff" });
    expect(screen.queryByText("Not authenticated")).not.toBeInTheDocument();
  });
});

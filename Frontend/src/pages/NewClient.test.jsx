import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

// The whole api module is mocked. Every request goes through this one function,
// so a single line stands in for the entire backend.
vi.mock("../api");

// The page reads the logged-in user from useOutletContext(), normally supplied
// by Layout. Mocking that one hook keeps the test off /me, which is not what
// this file measures.
vi.mock("react-router-dom", async () => ({
  ...(await vi.importActual("react-router-dom")),
  useOutletContext: () => ({ id: 1, name: "Admin", role: "admin" }),
}));

import { apiCall } from "../api";
import NewClient from "./NewClient";

// The difference between two endpoints is the whole point of this test:
//
//   GET /staff        -> StaffMini: id and name only, no role.
//   GET /admin/staff  -> StaffOut:  role included.
//
// Ask for the wrong one and every row's role is undefined, so
// `.filter(s => s.role === "staff")` drops them all and the dropdown is empty.
// That was the bug, and it left the admin's "Belongs to" feature useless.
function respondLikeTheRealApi(method, path) {
  if (path === "/staff") {
    return { ok: true, status: 200, data: [{ id: 2, name: "Ali Khan" }] };
  }

  if (path === "/admin/staff") {
    return {
      ok: true,
      status: 200,
      data: [{ id: 2, name: "Ali Khan", email: "ali@example.com", role: "staff" }],
    };
  }

  return { ok: false, status: 404, data: null };
}

describe("NewClient ka 'Belongs to' picker", () => {
  beforeEach(() => {
    apiCall.mockImplementation(async (method, path) => respondLikeTheRealApi(method, path));
  });

  it("admin ko staff members dropdown me dikhata hai", async () => {
    render(<NewClient />, { wrapper: MemoryRouter });

    // findBy* waits for the async call; getBy* looks immediately and would fail.
    expect(await screen.findByRole("option", { name: "Ali Khan" })).toBeInTheDocument();
  });

  it("wo endpoint poochta hai jo role bhejta hai", async () => {
    render(<NewClient />, { wrapper: MemoryRouter });

    await screen.findByRole("option", { name: "Ali Khan" });

    const paths = apiCall.mock.calls.map(([, path]) => path);
    expect(paths).toContain("/admin/staff");
    expect(paths).not.toContain("/staff");
  });
});

describe("NewClient staff ke liye", () => {
  beforeEach(() => {
    apiCall.mockImplementation(async (method, path) => respondLikeTheRealApi(method, path));
  });

  it("staff ko picker dikhta hi nahi", async () => {
    // Staff rather than admin, for this test only - resetModules and a re-import,
    // or the admin mock above stays in place.
    vi.resetModules();
    vi.doMock("react-router-dom", async () => ({
      ...(await vi.importActual("react-router-dom")),
      useOutletContext: () => ({ id: 2, name: "Ali", role: "staff" }),
    }));

    const { default: StaffNewClient } = await import("./NewClient");
    render(<StaffNewClient />, { wrapper: MemoryRouter });

    // The name field is there, so the form rendered...
    expect(await screen.findByLabelText("Name")).toBeInTheDocument();
    // ...but no way to pick an owner. A staff member's client is always theirs.
    expect(screen.queryByLabelText("Belongs to")).not.toBeInTheDocument();
  });
});

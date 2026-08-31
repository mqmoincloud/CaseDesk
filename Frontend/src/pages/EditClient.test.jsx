import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api");

// useParams supplies the id - from the URL in the app, from here in the test.
vi.mock("react-router-dom", async () => ({
  ...(await vi.importActual("react-router-dom")),
  useParams: () => ({ id: "7" }),
  useNavigate: () => vi.fn(),
}));

import { apiCall, errorMessage } from "../api";
import EditClient from "./EditClient";

const A_CLIENT = {
  id: 7,
  name: "Ramesh Kumar",
  email: "ramesh@example.com",
  phone: "9876543210",
  address: "1 Main Road",
  owner: { id: 2, name: "Ali Khan" },
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

describe("EditClient", () => {
  beforeEach(() => {
    errorMessage.mockImplementation((res) =>
      res.status === 0 ? "Could not reach the server. Is it running?" : "Something went wrong."
    );
  });

  it("form ko maujooda values se bharta hai", async () => {
    apiCall.mockResolvedValue({ ok: true, status: 200, data: A_CLIENT });

    render(<EditClient />, { wrapper: MemoryRouter });

    // getByLabelText only works when a label is tied to its input with htmlFor,
    // so this query is itself a check on that pairing.
    expect(await screen.findByLabelText("Name")).toHaveValue("Ramesh Kumar");
    expect(screen.getByLabelText("Phone")).toHaveValue("9876543210");
    expect(screen.getByLabelText("Email")).toHaveValue("ramesh@example.com");
    expect(screen.getByLabelText("Address")).toHaveValue("1 Main Road");
  });

  it("client na mile to 404 wala message dikhata hai", async () => {
    apiCall.mockResolvedValue({ ok: false, status: 404, data: null });

    render(<EditClient />, { wrapper: MemoryRouter });

    expect(await screen.findByText("Client not found.")).toBeInTheDocument();
  });

  it("server band ho to crash nahi hota aur 'Loading...' pe nahi atakta", async () => {
    // The bug. Without the `res.ok` check the code read `res.data.name` straight
    // away, and apiCall returns `data: null` on a network failure - a TypeError
    // that also skipped `setLoading(false)`, stranding the page on "Loading...".
    apiCall.mockResolvedValue({ ok: false, status: 0, data: null });

    render(<EditClient />, { wrapper: MemoryRouter });

    expect(
      await screen.findByText("Could not reach the server. Is it running?")
    ).toBeInTheDocument();
    expect(screen.queryByText("Loading...")).not.toBeInTheDocument();
  });
});

// Runs once before every test file.

// jest-dom's matchers, without which toBeInTheDocument() does not exist.
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Clear the DOM after each test, for the same reason conftest.py empties the
// tables: one test's leftovers must not reach the next, and order must not matter.
afterEach(cleanup);

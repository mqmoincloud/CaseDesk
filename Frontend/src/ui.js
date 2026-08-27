// Shared class strings, so every page looks the same without repeating long
// Tailwind lines in nine files. Plain objects, no components - the brief asks
// for a plain front end.

// mx-auto centres the content in whatever space is left beside the sidebar,
// instead of letting it hug the left edge on a wide screen.
export const page = "p-8 max-w-5xl mx-auto";
export const heading = "text-2xl font-semibold text-slate-900";
export const subheading = "text-lg font-semibold text-slate-900";

export const card = "border border-slate-200 rounded-lg bg-white";

export const input =
  "w-full border border-slate-300 rounded px-3 py-2 text-slate-900 " +
  "focus:outline-none focus:ring-2 focus:ring-slate-900/15 focus:border-slate-400";

export const label = "block mb-1 text-sm font-medium text-slate-700";

export const button =
  "px-4 py-2 rounded bg-slate-900 text-white text-sm font-medium " +
  "hover:bg-slate-800 disabled:opacity-40 disabled:hover:bg-slate-900";

export const buttonQuiet =
  "px-4 py-2 rounded border border-slate-300 text-sm font-medium text-slate-700 " +
  "hover:bg-slate-50 disabled:opacity-40 disabled:hover:bg-transparent";

export const table = "w-full text-sm";
export const th =
  "text-left font-medium text-slate-500 text-xs uppercase tracking-wide px-4 py-3 border-b border-slate-200";
export const td = "px-4 py-3 border-b border-slate-100 text-slate-700";
export const rowLink = "font-medium text-slate-900 hover:underline";

export const muted = "text-sm text-slate-500";
export const errorText = "text-sm text-red-700";

// One colour per case status, so the list is scannable without reading it.
const STATUS_COLOURS = {
  Intake: "bg-slate-100 text-slate-700",
  Active: "bg-blue-100 text-blue-800",
  Settled: "bg-amber-100 text-amber-800",
  Closed: "bg-green-100 text-green-800",
};

export function statusBadge(status) {
  const colour = STATUS_COLOURS[status] || "bg-slate-100 text-slate-700";
  return `inline-block px-2 py-0.5 rounded-full text-xs font-medium ${colour}`;
}

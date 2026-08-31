// Shared class strings, so every page looks the same without repeating long
// Tailwind lines in nine files. Plain objects, no components - the brief asks
// for a plain front end.

// mx-auto centres the content beside the sidebar; p-4 on phones, where p-8
// would eat most of the width.
export const page = "p-4 sm:p-8 max-w-5xl mx-auto";

// For pages with columns side by side - at 5xl three columns fall under 300px.
export const pageWide = "p-4 sm:p-8 max-w-7xl mx-auto";

// A panel that sits in a row and drops to the next line when space runs out.
// basis-72 decides the wrap; min-w-0 lets it shrink rather than overflow on a
// 320px phone, which min-w-72 would not.
export const columns = "flex flex-wrap items-start gap-6";
export const column = "grow basis-72 min-w-0";
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

// Small in-table actions. buttonQuiet is too heavy when a row holds three.
export const rowAction =
  "px-2 py-1 rounded border border-slate-300 text-xs font-medium text-slate-700 " +
  "hover:bg-slate-50";

// A destructive action should stand out on hover only, not glare from every row.
export const rowActionDanger =
  "px-2 py-1 rounded border border-slate-300 text-xs font-medium text-slate-700 " +
  "hover:bg-red-50 hover:text-red-700 hover:border-red-300";

export const table = "w-full text-sm";

// Let a wide table scroll inside itself, so the page body never scrolls sideways.
export const tableWrap = "overflow-x-auto";

// sticky top-0 keeps the column names visible while a long list scrolls. The
// background belongs on the cell - thead's does not paint behind a sticky one.
export const th =
  "sticky top-0 z-10 bg-slate-50 text-left font-medium text-slate-500 text-xs " +
  "uppercase tracking-wide px-4 py-3 border-b border-slate-200";
export const td = "px-4 py-3 border-b border-slate-100 text-slate-700";
export const rowLink = "font-medium text-slate-900 hover:underline";

export const muted = "text-sm text-slate-500";

// The rest of the text scale, so a page never spells a colour out by hand.
// muted is the quiet line; bodyText is ordinary prose inside a card; metaText
// is the timestamp or byline under it; fieldValue is a read-only value shown
// where an input would otherwise be.
export const bodyText = "text-sm text-slate-800";
export const metaText = "text-xs text-slate-500";
export const fieldValue = "text-sm text-slate-900";

// Confirmation after a save. Paired with errorText below - the two are the
// only places colour carries meaning rather than emphasis.
export const successText = "text-sm text-green-700";

// A destructive action that has to sit inside a dense row, so it stays quiet
// until the pointer is on it.
export const linkDanger = "text-xs text-slate-500 hover:text-red-700";
export const errorText = "text-sm text-red-700";

export function roleBadge(role) {
  const base = "inline-block px-2 py-0.5 rounded-full text-xs font-medium";
  return role === "admin"
    ? `${base} bg-slate-900 text-white`
    : `${base} bg-slate-100 text-slate-600`;
}

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

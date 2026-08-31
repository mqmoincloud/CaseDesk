import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";

import { apiCall, errorMessage, query } from "../api";
import {
  button, buttonQuiet, card, errorText, heading, input, muted, page, rowAction,
  rowActionDanger, rowLink, table, tableWrap, td, th,
} from "../ui";

const LIMIT = 10;

export default function Clients() {
  // From Layout's /me call, only to know whether this is an admin - an admin's
  // list holds everyone's clients, so it needs the "Owner" column.
  const me = useOutletContext();

  const [clients, setClients] = useState([]);
  const [total, setTotal] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [nextCursor, setNextCursor] = useState(null);

  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  // Bumped after a delete to re-run the effect, same as CaseDetail.
  const [refresh, setRefresh] = useState(0);

  // Cursor paging. "cursor" is the id to fetch before; "trail" remembers the
  // cursors already used so Previous can walk back.
  const [cursor, setCursor] = useState(null);
  const [trail, setTrail] = useState([]);

  useEffect(() => {
    async function load() {
      // query() encodes each value, so a name with & or # in it does not cut
      // the query string in half, and empty filters are left out entirely.
      const res = await apiCall(
        "GET",
        `/clients${query({ search, limit: LIMIT, before: cursor })}`
      );

      // A 401 already sent us to the login screen. Any other failure would
      // leave res.data as the error envelope, and reading .items off that
      // gives undefined - which is a blank page one render later.
      if (!res.ok) {
        if (res.status !== 401) setError(errorMessage(res));
        return;
      }

      setError("");
      setClients(res.data.items);
      setTotal(res.data.total);
      setHasNext(res.data.has_next);
      setNextCursor(res.data.next_cursor);
    }

    // Wait 400ms before calling the server. React runs the cleanup below
    // before the next run of this effect, so every keystroke cancels the timer
    // the previous one set and only the last one actually fires.
    const timer = setTimeout(load, 400);

    return () => clearTimeout(timer);
  }, [search, cursor, refresh]);

  function handleSearch(e) {
    setSearch(e.target.value);
    // Back to the first page, otherwise a search with 3 results while sitting
    // on page 5 would show an empty table.
    setCursor(null);
    setTrail([]);
  }

  async function handleDelete(client) {
    setError("");

    // One misclick in a row would remove a client, and there is no way back
    // from here.
    if (!window.confirm(`Delete ${client.name}?`)) return;

    const res = await apiCall("DELETE", `/clients/${client.id}`);

    if (res.status === 409) {
      // The API refuses to delete a client whose cases are still live.
      setError(`${client.name} still has cases. Close or remove them first.`);
      return;
    }

    if (!res.ok) {
      setError(`Could not delete ${client.name}.`);
      return;
    }

    setRefresh((n) => n + 1);
  }

  function goNext() {
    setTrail([...trail, cursor]);
    setCursor(nextCursor);
  }

  function goPrevious() {
    const previous = trail[trail.length - 1];
    setTrail(trail.slice(0, -1));
    setCursor(previous);
  }

  return (
    <div className={page}>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className={heading}>Clients</h1>
          <p className={muted}>{total} in total</p>
        </div>
        <Link to="/clients/new" className={button}>New client</Link>
      </div>

      {error && <p className={`${errorText} mb-4`}>{error}</p>}

      <input
        value={search}
        onChange={handleSearch}
        placeholder="Search name, phone or email"
        className={`${input} w-full sm:max-w-sm mb-4`}
      />

      <div className={`${card} ${tableWrap}`}>
        <table className={table}>
          <thead className="bg-slate-50">
            <tr>
              <th className={th}>Name</th>
              <th className={th}>Phone</th>
              <th className={th}>Email</th>
              {/* Pointless for a staff member, whose clients are all their own.
                  For an admin it is the only place ownership shows. */}
              {me.role === "admin" && <th className={th}>Owner</th>}
              <th className={th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {clients.map((client) => (
              <tr key={client.id} className="hover:bg-slate-50">
                <td className={td}>
                  <Link to={`/clients/${client.id}`} className={rowLink}>
                    {client.name}
                  </Link>
                </td>
                <td className={td}>{client.phone || "—"}</td>
                <td className={td}>{client.email || "—"}</td>
                {me.role === "admin" && (
                  <td className={td}>{client.owner.name}</td>
                )}
                <td className={td}>
                  {/* Clicking the name still works - these buttons are extra,
                      not a replacement. */}
                  <div className="flex flex-wrap gap-2">
                    <Link to={`/clients/${client.id}/edit`} className={rowAction}>
                      Edit
                    </Link>
                    <Link to={`/cases?client_id=${client.id}`} className={rowAction}>
                      Cases
                    </Link>
                    <button
                      onClick={() => handleDelete(client)}
                      className={rowActionDanger}
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}

            {clients.length === 0 && (
              <tr>
                <td
                  className={`${td} text-center text-slate-500`}
                  colSpan={me.role === "admin" ? 5 : 4}
                >
                  No clients found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center gap-3 mt-4">
        <button onClick={goPrevious} disabled={trail.length === 0} className={buttonQuiet}>
          Previous
        </button>
        <span className={muted}>Page {trail.length + 1}</span>
        <button onClick={goNext} disabled={!hasNext} className={buttonQuiet}>
          Next
        </button>
      </div>
    </div>
  );
}

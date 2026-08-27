import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiCall, removeToken } from "../api";
import {
  button, buttonQuiet, card, heading, input, muted, page, rowLink, table, td, th,
} from "../ui";

const LIMIT = 10;

export default function Clients() {
  const navigate = useNavigate();

  const [clients, setClients] = useState([]);
  const [total, setTotal] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [nextCursor, setNextCursor] = useState(null);

  const [search, setSearch] = useState("");

  // Cursor paging. "cursor" is the id to fetch before; "trail" remembers the
  // cursors already used so Previous can walk back.
  const [cursor, setCursor] = useState(null);
  const [trail, setTrail] = useState([]);

  useEffect(() => {
    async function load() {
      let url = `/clients?search=${search}&limit=${LIMIT}`;
      if (cursor) url += `&before=${cursor}`;

      const res = await apiCall("GET", url);

      if (res.status === 401) {
        removeToken();
        navigate("/login");
        return;
      }

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
  }, [search, cursor, navigate]);

  function handleSearch(e) {
    setSearch(e.target.value);
    // Back to the first page, otherwise a search with 3 results while sitting
    // on page 5 would show an empty table.
    setCursor(null);
    setTrail([]);
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
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className={heading}>Clients</h1>
          <p className={muted}>{total} in total</p>
        </div>
        <Link to="/clients/new" className={button}>New client</Link>
      </div>

      <input
        value={search}
        onChange={handleSearch}
        placeholder="Search name, phone or email"
        className={`${input} max-w-sm mb-4`}
      />

      <div className={`${card} overflow-hidden`}>
        <table className={table}>
          <thead className="bg-slate-50">
            <tr>
              <th className={th}>Name</th>
              <th className={th}>Phone</th>
              <th className={th}>Email</th>
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
              </tr>
            ))}

            {clients.length === 0 && (
              <tr>
                <td className={`${td} text-center text-slate-500`} colSpan={3}>
                  No clients found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-3 mt-4">
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

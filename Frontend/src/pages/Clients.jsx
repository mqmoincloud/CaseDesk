import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiCall, removeToken } from "../api";

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

  // Runs on first render, and again whenever search or page changes.
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
    <div className="p-8">
      <h1 className="text-2xl mb-6">Clients</h1>

      <div className="flex justify-between mb-4">
        <input
          value={search}
          onChange={handleSearch}
          placeholder="Search name, phone or email"
          className="border p-2 w-80"
        />
        <Link to="/clients/new" className="border px-4 py-2">
          New client
        </Link>
      </div>

      <table className="w-full border">
        <thead>
          <tr className="bg-gray-100">
            <th className="border p-2 text-left">Name</th>
            <th className="border p-2 text-left">Phone</th>
            <th className="border p-2 text-left">Email</th>
          </tr>
        </thead>
        <tbody>
          {clients.map((client) => (
            <tr key={client.id}>
              <td className="border p-2">
                <Link to={`/clients/${client.id}`} className="underline">
                  {client.name}
                </Link>
              </td>
              <td className="border p-2">{client.phone}</td>
              <td className="border p-2">{client.email}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {clients.length === 0 && <p className="mt-4">No clients found.</p>}

      <div className="flex gap-4 items-center mt-4">
        <button
          onClick={goPrevious}
          disabled={trail.length === 0}
          className="border px-4 py-2 disabled:opacity-40"
        >
          Previous
        </button>

        <span>
          Page {trail.length + 1} — {total} clients
        </span>

        <button
          onClick={goNext}
          disabled={!hasNext}
          className="border px-4 py-2 disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}

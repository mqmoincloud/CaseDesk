import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiCall, removeToken } from "../api";

const LIMIT = 10;
const STATUSES = ["Intake", "Active", "Settled", "Closed"];

export default function Cases() {
  const navigate = useNavigate();

  const [cases, setCases] = useState([]);
  const [total, setTotal] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [nextCursor, setNextCursor] = useState(null);

  const [staff, setStaff] = useState([]);
  const [status, setStatus] = useState("");
  const [assignee, setAssignee] = useState("");
  const [cursor, setCursor] = useState(null);
  const [trail, setTrail] = useState([]);

  // The assignee dropdown needs the list of colleagues. Loaded once.
  useEffect(() => {
    async function loadStaff() {
      const res = await apiCall("GET", "/staff");
      if (res.status === 200) setStaff(res.data);
    }
    loadStaff();
  }, []);

  useEffect(() => {
    async function load() {
      // Empty filters are left out of the URL so the API treats them as "all".
      let url = `/cases?limit=${LIMIT}`;
      if (cursor) url += `&before=${cursor}`;
      if (status) url += `&status=${status}`;
      if (assignee) url += `&assignee=${assignee}`;

      const res = await apiCall("GET", url);

      if (res.status === 401) {
        removeToken();
        navigate("/login");
        return;
      }

      setCases(res.data.items);
      setTotal(res.data.total);
      setHasNext(res.data.has_next);
      setNextCursor(res.data.next_cursor);
    }

    load();
  }, [status, assignee, cursor, navigate]);

  function resetPaging() {
    setCursor(null);
    setTrail([]);
  }

  function changeStatus(e) {
    setStatus(e.target.value);
    resetPaging();
  }

  function changeAssignee(e) {
    setAssignee(e.target.value);
    resetPaging();
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
      <h1 className="text-2xl mb-6">Cases</h1>

      <div className="flex gap-4 mb-4">
        <select value={status} onChange={changeStatus} className="border p-2">
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select value={assignee} onChange={changeAssignee} className="border p-2">
          <option value="">All assignees</option>
          {staff.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>

        <Link to="/cases/new" className="border px-4 py-2 ml-auto">New case</Link>
      </div>

      <table className="w-full border">
        <thead>
          <tr className="bg-gray-100">
            <th className="border p-2 text-left">Title</th>
            <th className="border p-2 text-left">Client</th>
            <th className="border p-2 text-left">Type</th>
            <th className="border p-2 text-left">Status</th>
            <th className="border p-2 text-left">Assignee</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.id}>
              <td className="border p-2">
                <Link to={`/cases/${c.id}`} className="underline">{c.title}</Link>
              </td>
              <td className="border p-2">{c.client.name}</td>
              <td className="border p-2">{c.case_type}</td>
              <td className="border p-2">{c.status}</td>
              {/* assignee can be null, so check before reading .name */}
              <td className="border p-2">{c.assignee ? c.assignee.name : "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {cases.length === 0 && <p className="mt-4">No cases found.</p>}

      <div className="flex gap-4 items-center mt-4">
        <button
          onClick={goPrevious}
          disabled={trail.length === 0}
          className="border px-4 py-2 disabled:opacity-40"
        >
          Previous
        </button>

        <span>Page {trail.length + 1} — {total} cases</span>

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

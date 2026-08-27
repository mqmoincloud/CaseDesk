import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiCall, removeToken } from "../api";
import {
  button, buttonQuiet, card, heading, input, muted, page, rowLink, statusBadge,
  table, td, th,
} from "../ui";

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

  // Cursor paging. "cursor" is the id to fetch before; "trail" remembers the
  // cursors already used so Previous can walk back.
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
    <div className={page}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className={heading}>Cases</h1>
          <p className={muted}>{total} in total</p>
        </div>
        <Link to="/cases/new" className={button}>New case</Link>
      </div>

      <div className="flex gap-3 mb-4">
        <select value={status} onChange={changeStatus} className={`${input} max-w-48`}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select value={assignee} onChange={changeAssignee} className={`${input} max-w-48`}>
          <option value="">All assignees</option>
          {staff.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </div>

      <div className={`${card} overflow-hidden`}>
        <table className={table}>
          <thead className="bg-slate-50">
            <tr>
              <th className={th}>Title</th>
              <th className={th}>Client</th>
              <th className={th}>Type</th>
              <th className={th}>Status</th>
              <th className={th}>Assignee</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50">
                <td className={td}>
                  <Link to={`/cases/${c.id}`} className={rowLink}>{c.title}</Link>
                </td>
                <td className={td}>{c.client.name}</td>
                <td className={td}>{c.case_type}</td>
                <td className={td}>
                  <span className={statusBadge(c.status)}>{c.status}</span>
                </td>
                {/* assignee can be null, so check before reading .name */}
                <td className={td}>{c.assignee ? c.assignee.name : "—"}</td>
              </tr>
            ))}

            {cases.length === 0 && (
              <tr>
                <td className={`${td} text-center text-slate-500`} colSpan={5}>
                  No cases found.
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

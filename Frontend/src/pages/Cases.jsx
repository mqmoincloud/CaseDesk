import { useEffect, useState } from "react";
import { Link, useOutletContext, useSearchParams } from "react-router-dom";

import { apiCall, errorMessage, query } from "../api";
import {
  button, buttonQuiet, card, errorText, heading, input, metaText, muted, page,
  rowAction, rowLink, statusBadge, table, tableWrap, td, th,
} from "../ui";

const LIMIT = 10;
const STATUSES = ["Intake", "Active", "Settled", "Closed"];

export default function Cases() {
  // From Layout's /me call, so we can say whether you made an assignment or
  // someone else did without a second request.
  const me = useOutletContext();

  const [cases, setCases] = useState([]);
  const [total, setTotal] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [nextCursor, setNextCursor] = useState(null);

  const [staff, setStaff] = useState([]);
  const [status, setStatus] = useState("");
  const [assignee, setAssignee] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const [searchParams] = useSearchParams();
  const clientId = searchParams.get("client_id");
  const [clientName, setClientName] = useState("");
  const [cursor, setCursor] = useState(null);
  const [trail, setTrail] = useState([]);
  const [pagingKey, setPagingKey] = useState(clientId);

  if (pagingKey !== clientId) {
    setPagingKey(clientId);
    setCursor(null);
    setTrail([]);
    if (!clientId) setClientName("");
  }

  useEffect(() => {
    async function loadStaff() {
      const res = await apiCall("GET", "/staff");
      if (res.ok) setStaff(res.data);
    }
    loadStaff();
  }, []);

  useEffect(() => {
    if (!clientId) return;

    async function loadClient() {
      const res = await apiCall("GET", `/clients/${clientId}`);
      if (res.ok) setClientName(res.data.name);
    }
    loadClient();
  }, [clientId]);

  useEffect(() => {
    async function load() {

      const res = await apiCall(
        "GET",
        `/cases${query({
          limit: LIMIT,
          before: cursor,
          status,
          assignee,
          client_id: clientId,
          search,
        })}`
      );

      // Anything but a 2xx leaves res.data as the error envelope, and
      // res.data.items would be undefined - a blank page one render later.
      if (!res.ok) {
        if (res.status !== 401) setError(errorMessage(res));
        return;
      }

      setError("");
      setCases(res.data.items);
      setTotal(res.data.total);
      setHasNext(res.data.has_next);
      setNextCursor(res.data.next_cursor);
    }

    const timer = setTimeout(load, 400);

    return () => clearTimeout(timer);
  }, [status, assignee, search, clientId, cursor]);

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

  function changeSearch(e) {
    setSearch(e.target.value);
    resetPaging();
  }

  function goNext() {
    setTrail([...trail, cursor]);
    setCursor(nextCursor);
  }

  function lastActivity(c) {
    const events = [];

    if (c.last_status_change) {
      const sc = c.last_status_change;
      events.push({
        at: sc.created_at,
        label: sc.from_status
          ? `Status → ${sc.to_status}`
          : `Opened at ${sc.to_status}`,
      });
    }

    if (c.last_assignment) {
      const a = c.last_assignment;
      const whom = !a.assignee
        ? "Assignee removed"
        : `Assigned to ${a.assignee.id === me.id ? "you" : a.assignee.name}`;
      events.push({ at: a.created_at, label: whom });
    }

    if (events.length === 0) return null;

    return events.sort((x, y) => new Date(y.at) - new Date(x.at))[0];
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
          <h1 className={heading}>Cases</h1>
          <p className={muted}>{total} in total</p>
        </div>
        <Link to="/cases/new" className={button}>New case</Link>
      </div>

      {error && <p className={`${errorText} mb-4`}>{error}</p>}

      {clientId && (
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <span className={muted}>
            Showing cases for {clientName || `client #${clientId}`}
          </span>
          <Link to="/cases" className={rowAction}>Clear filter</Link>
        </div>
      )}

      <div className="flex flex-wrap gap-3 mb-4">
        <input
          value={search}
          onChange={changeSearch}
          placeholder="Search case title, type or client"
          className={`${input} w-full sm:w-64`}
        />

        <select value={status} onChange={changeStatus} className={`${input} w-full sm:w-48`}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select value={assignee} onChange={changeAssignee} className={`${input} w-full sm:w-48`}>
          <option value="">All assignees</option>
          {staff.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </div>

      <div className={`${card} ${tableWrap}`}>
        <table className={table}>
          <thead className="bg-slate-50">
            <tr>
              <th className={th}>Title</th>
              <th className={th}>Client</th>
              <th className={th}>Type</th>
              <th className={th}>Status</th>
              <th className={th}>Assignee</th>
              <th className={th}>Last activity</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50">
                <td className={td}>
                  <Link to={`/cases/${c.id}`} className={rowLink}>{c.title}</Link>
                </td>
              
                <td className={td}>
                  {c.owner.id === me.id || me.role === "admin" ? (
                    <Link to={`/clients/${c.client.id}`} className={rowLink}>
                      {c.client.name}
                    </Link>
                  ) : (
                    c.client.name
                  )}
                </td>
                <td className={td}>{c.case_type}</td>
                <td className={td}>
                  <span className={statusBadge(c.status)}>{c.status}</span>
                </td>
                
                <td className={td}>
                  {c.assignee ? c.assignee.name : "—"}
                
                  {c.last_assignment && (
                    <div className={metaText}>
                      {c.last_assignment.assigned_by.id === me.id
                        ? "you assigned"
                        : `${c.last_assignment.assigned_by.name} assigned`}
                    </div>
                  )}
                </td>
                <td className={td}>
                  {(() => {
                    const event = lastActivity(c);
                    if (!event) return <span className="text-slate-400">—</span>;
                    return (
                      <span title={new Date(event.at).toLocaleString()}>
                        {event.label}
                        <span className={`block ${metaText}`}>
                          {new Date(event.at).toLocaleDateString()}
                        </span>
                      </span>
                    );
                  })()}
                </td>
              </tr>
            ))}

            {cases.length === 0 && (
              <tr>
                <td className={`${td} text-center text-slate-500`} colSpan={6}>
                  No cases found.
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

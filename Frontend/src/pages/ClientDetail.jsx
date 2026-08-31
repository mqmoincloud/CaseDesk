import { useEffect, useState } from "react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";

import { apiCall, errorMessage } from "../api";
import {
  button, buttonQuiet, card, errorText, heading, muted, page, rowLink,
  statusBadge, subheading, table, tableWrap, td, th,
} from "../ui";

// The API caps a page at 100. A client with more cases than this is not
// something the screen pretends to handle - it says so instead.
const CASE_LIMIT = 100;

export default function ClientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const me = useOutletContext();

  const [client, setClient] = useState(null);
  const [cases, setCases] = useState([]);
  const [caseTotal, setCaseTotal] = useState(0);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      const res = await apiCall("GET", `/clients/${id}`);

      if (res.status === 404) {
        setNotFound(true);
        return;
      }

      // A 401 has already sent us to the login screen. Anything else leaves
      // res.data as the error envelope, not a client.
      if (!res.ok) {
        if (res.status !== 401) setError(errorMessage(res));
        return;
      }

      setClient(res.data);

      // limit is the API's maximum. If a client somehow has more cases than
      // that, say so rather than showing a count that is quietly wrong.
      const theirCases = await apiCall("GET", `/cases?client_id=${id}&limit=${CASE_LIMIT}`);

      if (theirCases.ok) {
        setCases(theirCases.data.items);
        setCaseTotal(theirCases.data.total);
      }
    }

    load();
  }, [id]);

  async function handleDelete() {
    setError("");

    // There is no undelete anywhere in this app, so every delete asks first -
    // the same as the one on the client list.
    if (!window.confirm(`Delete ${client.name}?`)) return;

    const res = await apiCall("DELETE", `/clients/${id}`);

    if (res.status === 409) {
      // The API refuses to delete a client who still has live cases.
      setError("This client still has cases. Close or remove them first.");
      return;
    }

    if (!res.ok) {
      setError("Could not delete this client.");
      return;
    }

    navigate("/clients");
  }

  if (notFound) {
    return (
      <div className={page}>
        <p className="mb-4">Client not found.</p>
        <Link to="/clients" className={buttonQuiet}>Go to clients</Link>
      </div>
    );
  }

  if (!client) {
    return <p className={`${page} ${muted}`}>Loading...</p>;
  }

  return (
    <div className={page}>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
        <h1 className={heading}>{client.name}</h1>
        <div className="flex flex-wrap gap-3">
          <Link to={`/clients/${id}/edit`} className={buttonQuiet}>Edit</Link>
          <button onClick={handleDelete} className={buttonQuiet}>Delete</button>
        </div>
      </div>

      {error && <p className={`${errorText} mb-4`}>{error}</p>}

      <div className={`${card} p-6 mb-8`}>
        <dl className="grid grid-cols-[7rem_1fr] gap-y-3 text-sm">
          <dt className="text-slate-500">Phone</dt>
          <dd className="text-slate-900">{client.phone || "—"}</dd>
          <dt className="text-slate-500">Email</dt>
          <dd className="text-slate-900">{client.email || "—"}</dd>
          <dt className="text-slate-500">Address</dt>
          <dd className="text-slate-900">{client.address || "—"}</dd>
          {/* Admin only - for a staff member the answer is always "me". */}
          {me.role === "admin" && (
            <>
              <dt className="text-slate-500">Owner</dt>
              <dd className="text-slate-900">{client.owner.name}</dd>
            </>
          )}
        </dl>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <h2 className={subheading}>Cases ({caseTotal})</h2>
        <Link to={`/cases/new?client_id=${id}`} className={button}>
          New case
        </Link>
      </div>

      <div className={`${card} ${tableWrap}`}>
        <table className={table}>
          <thead className="bg-slate-50">
            <tr>
              <th className={th}>Title</th>
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
                <td className={td}>{c.case_type}</td>
                <td className={td}>
                  <span className={statusBadge(c.status)}>{c.status}</span>
                </td>
                <td className={td}>{c.assignee ? c.assignee.name : "—"}</td>
              </tr>
            ))}

            {caseTotal > cases.length && (
              <tr>
                <td className={`${td} text-slate-500`} colSpan={4}>
                  Showing the first {cases.length} of {caseTotal}. Use the
                  Cases page to see the rest.
                </td>
              </tr>
            )}

            {cases.length === 0 && (
              <tr>
                <td className={`${td} text-center text-slate-500`} colSpan={4}>
                  No cases for this client yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

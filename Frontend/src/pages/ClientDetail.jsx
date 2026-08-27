import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { apiCall, removeToken } from "../api";
import {
  button, buttonQuiet, card, errorText, heading, muted, page, rowLink,
  statusBadge, subheading, table, td, th,
} from "../ui";

export default function ClientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [client, setClient] = useState(null);
  const [cases, setCases] = useState([]);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      const res = await apiCall("GET", `/clients/${id}`);

      if (res.status === 401) {
        removeToken();
        navigate("/login");
        return;
      }

      if (res.status === 404) {
        setNotFound(true);
        return;
      }

      setClient(res.data);

      const theirCases = await apiCall("GET", `/cases?client_id=${id}&limit=100`);
      setCases(theirCases.data.items);
    }

    load();
  }, [id, navigate]);

  async function handleDelete() {
    setError("");
    const res = await apiCall("DELETE", `/clients/${id}`);

    if (res.status === 409) {
      // The API refuses to delete a client who still has live cases.
      setError("This client still has cases. Close or remove them first.");
      return;
    }

    if (res.status !== 200) {
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
      <div className="flex items-start justify-between mb-6">
        <h1 className={heading}>{client.name}</h1>
        <div className="flex gap-3">
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
        </dl>
      </div>

      <div className="flex items-center justify-between mb-3">
        <h2 className={subheading}>Cases ({cases.length})</h2>
        <Link to={`/cases/new?client_id=${id}`} className={button}>
          New case
        </Link>
      </div>

      <div className={`${card} overflow-hidden`}>
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

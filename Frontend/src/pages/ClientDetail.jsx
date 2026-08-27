import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { apiCall, removeToken } from "../api";

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
      <div className="p-8">
        <p className="mb-4">Client not found.</p>
        <Link to="/clients" className="underline">Go to clients</Link>
      </div>
    );
  }

  if (!client) {
    return <p className="p-8">Loading...</p>;
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl mb-6">{client.name}</h1>

      <table className="mb-6">
        <tbody>
          <tr>
            <td className="pr-6 py-1 text-gray-600">Phone</td>
            <td className="py-1">{client.phone || "-"}</td>
          </tr>
          <tr>
            <td className="pr-6 py-1 text-gray-600">Email</td>
            <td className="py-1">{client.email || "-"}</td>
          </tr>
          <tr>
            <td className="pr-6 py-1 text-gray-600">Address</td>
            <td className="py-1">{client.address || "-"}</td>
          </tr>
        </tbody>
      </table>

      <div className="flex gap-4 mb-8">
        <Link to={`/clients/${id}/edit`} className="border px-4 py-2">
          Edit
        </Link>
        <button onClick={handleDelete} className="border px-4 py-2">
          Delete
        </button>
      </div>

      {error && <p className="text-red-700 mb-6">{error}</p>}

      <div className="flex justify-between items-center mb-3">
        <h2 className="text-xl">Cases ({cases.length})</h2>
        <Link to={`/cases/new?client_id=${id}`} className="border px-4 py-2">
          New case for this client
        </Link>
      </div>

      {cases.length === 0 ? (
        <p>No cases for this client yet.</p>
      ) : (
        <table className="w-full border">
          <thead>
            <tr className="bg-gray-100">
              <th className="border p-2 text-left">Title</th>
              <th className="border p-2 text-left">Type</th>
              <th className="border p-2 text-left">Status</th>
              <th className="border p-2 text-left">Assignee</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.id}>
                <td className="border p-2">
                  <Link to={`/cases/${c.id}`} className="underline">
                    {c.title}
                  </Link>
                </td>
                <td className="border p-2">{c.case_type}</td>
                <td className="border p-2">{c.status}</td>
                <td className="border p-2">{c.assignee ? c.assignee.name : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

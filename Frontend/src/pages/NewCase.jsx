import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { apiCall, errorMessage, removeToken } from "../api";

const CASE_TYPES = ["Civil", "Criminal", "Family", "Property", "Labour"];

export default function NewCase() {
  const navigate = useNavigate();

  // Coming from a client page the URL is /cases/new?client_id=7, so that
  // client starts out selected. Opened from the case list it is empty and
  // the user picks one.
  const [searchParams] = useSearchParams();
  const preselected = searchParams.get("client_id") || "";

  const [clients, setClients] = useState([]);
  const [staff, setStaff] = useState([]);

  const [clientId, setClientId] = useState(preselected);
  const [title, setTitle] = useState("");
  const [caseType, setCaseType] = useState(CASE_TYPES[0]);
  const [assigneeId, setAssigneeId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      // /clients already leaves out soft-deleted ones, so the picker cannot
      // offer a client that was removed.
      const clientRes = await apiCall("GET", "/clients?limit=100");

      if (clientRes.status === 401) {
        removeToken();
        navigate("/login");
        return;
      }

      setClients(clientRes.data.items);

      const staffRes = await apiCall("GET", "/staff");
      setStaff(staffRes.data);
    }

    load();
  }, [navigate]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    const body = {
      client_id: Number(clientId),
      title: title,
      case_type: caseType,
      // "" means nobody picked an assignee, which the API takes as null.
      assignee_id: assigneeId ? Number(assigneeId) : null,
    };

    const res = await apiCall("POST", "/cases/registration", body);

    if (res.status === 401) {
      removeToken();
      navigate("/login");
      return;
    }

    if (res.status === 404) {
      setError("That client or assignee no longer exists.");
      return;
    }

    if (res.status === 422) {
      setError(errorMessage(res));
      return;
    }

    if (res.status !== 200) {
      setError("Could not create the case.");
      return;
    }

    navigate(`/cases/${res.data.id}`);
  }

  return (
    <div className="max-w-md p-8">
      <h1 className="text-2xl mb-6">New case</h1>

      <form onSubmit={handleSubmit}>
        <label className="block mb-4">
          Client
          <select
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            required
            className="border p-2 w-full"
          >
            <option value="">Choose a client</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </label>

        <label className="block mb-4">
          Title
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className="border p-2 w-full"
          />
        </label>

        <label className="block mb-4">
          Type
          <select
            value={caseType}
            onChange={(e) => setCaseType(e.target.value)}
            className="border p-2 w-full"
          >
            {CASE_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </label>

        <label className="block mb-4">
          Assignee
          <select
            value={assigneeId}
            onChange={(e) => setAssigneeId(e.target.value)}
            className="border p-2 w-full"
          >
            <option value="">Nobody yet</option>
            {staff.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </label>

        <p className="text-sm text-gray-600 mb-4">
          New cases always start at Intake.
        </p>

        {error && <p className="text-red-700 mb-4">{error}</p>}

        <div className="flex gap-4">
          <button type="submit" className="border px-4 py-2">Create</button>
          <Link
            to={preselected ? `/clients/${preselected}` : "/cases"}
            className="border px-4 py-2"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}

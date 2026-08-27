import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { apiCall, errorMessage, removeToken } from "../api";
import { button, buttonQuiet, card, errorText, heading, input, label, muted, page } from "../ui";

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
    <div className={page}>
      <h1 className={`${heading} mb-6`}>New case</h1>

      <form onSubmit={handleSubmit} className={`${card} p-6 max-w-md`}>
        <div className="mb-4">
          <label className={label}>Client</label>
          <select
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            required
            className={input}
          >
            <option value="">Choose a client</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        <div className="mb-4">
          <label className={label}>Title</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} required className={input} />
        </div>

        <div className="mb-4">
          <label className={label}>Type</label>
          <select value={caseType} onChange={(e) => setCaseType(e.target.value)} className={input}>
            {CASE_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div className="mb-4">
          <label className={label}>Assignee</label>
          <select value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)} className={input}>
            <option value="">Nobody yet</option>
            {staff.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        <p className={`${muted} mb-4`}>New cases always start at Intake.</p>

        {error && <p className={`${errorText} mb-4`}>{error}</p>}

        <div className="flex gap-3">
          <button type="submit" className={button}>Create</button>
          <Link
            to={preselected ? `/clients/${preselected}` : "/cases"}
            className={buttonQuiet}
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}

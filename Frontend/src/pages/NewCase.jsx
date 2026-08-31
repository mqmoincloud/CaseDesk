import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { apiCall, errorMessage } from "../api";
import { button, buttonQuiet, card, errorText, heading, input, label, muted, page } from "../ui";

const CASE_TYPES = ["Civil", "Criminal", "Family", "Property", "Labour"];

export default function NewCase() {
  const navigate = useNavigate();

  const [searchParams] = useSearchParams();
  const preselected = searchParams.get("client_id") || "";

  const [clients, setClients] = useState([]);
  const [clientTotal, setClientTotal] = useState(0);
  const [staff, setStaff] = useState([]);

  const [clientId, setClientId] = useState(preselected);
  const [title, setTitle] = useState("");
  const [caseType, setCaseType] = useState(CASE_TYPES[0]);
  const [assigneeId, setAssigneeId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {

      const clientRes = await apiCall("GET", "/clients?limit=100");

      // A 401 has already sent us to the login screen.
      if (!clientRes.ok) return;

      setClients(clientRes.data.items);
      setClientTotal(clientRes.data.total);

      const staffRes = await apiCall("GET", "/staff");
      if (staffRes.ok) setStaff(staffRes.data);
    }

    load();
  }, [navigate]);

  // Set while the form is in flight, so a second click cannot send a
  // second copy of the same request.
  const [saving, setSaving] = useState(false);
  async function handleSubmit(e) {
    e.preventDefault();
    if (saving) return;

    setError("");
    setSaving(true);

    const body = {
      client_id: Number(clientId),
      title: title,
      case_type: caseType,
      assignee_id: assigneeId ? Number(assigneeId) : null,
    };

    const res = await apiCall("POST", "/cases/registration", body);
    setSaving(false);

    if (res.status === 404) {
      setError("That client or assignee no longer exists.");
      return;
    }

    if (res.status === 422) {
      setError(errorMessage(res));
      return;
    }

    if (!res.ok) {
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
          <label htmlFor="case-client" className={label}>Client</label>
          <select
            id="case-client"
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

          {/* The dropdown holds one page. Past that, a client would simply
              not be in the list with nothing to say why. */}
          {clientTotal > clients.length && (
            <p className={`${muted} mt-1`}>
              Showing {clients.length} of {clientTotal} clients. Open the
              client and use New case from there if the one you want is
              missing.
            </p>
          )}
        </div>

        <div className="mb-4">
          <label htmlFor="case-title" className={label}>Title</label>
          <input id="case-title" value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={200} className={input} />
        </div>

        <div className="mb-4">
          <label htmlFor="case-type" className={label}>Type</label>
          <select id="case-type" value={caseType} onChange={(e) => setCaseType(e.target.value)} className={input}>
            {CASE_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div className="mb-4">
          <label htmlFor="case-assignee" className={label}>Assignee</label>
          <select id="case-assignee" value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)} className={input}>
            <option value="">Nobody yet</option>
            {staff.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        <p className={`${muted} mb-4`}>New cases always start at Intake.</p>

        {error && <p className={`${errorText} mb-4`}>{error}</p>}

        <div className="flex flex-wrap gap-3">
          <button type="submit" disabled={saving} className={button}>
            {saving ? "Creating..." : "Create"}
          </button>
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

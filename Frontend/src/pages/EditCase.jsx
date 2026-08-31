import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { apiCall, errorMessage } from "../api";
import { button, buttonQuiet, card, errorText, heading, input, label, muted, page } from "../ui";

// The same list NewCase offers.
const CASE_TYPES = ["Civil", "Criminal", "Family", "Property", "Labour"];

export default function EditCase() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [caseType, setCaseType] = useState(CASE_TYPES[0]);

  const [version, setVersion] = useState(null);

  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState("");
  const [closed, setClosed] = useState(false)

  useEffect(() => {
    async function load() {
      const res = await apiCall("GET", `/cases/${id}`);

      if (res.status === 404) {
        setNotFound(true);
        setLoading(false);
        return;
      }

      if (!res.ok) {
        if (res.status !== 401) setError(errorMessage(res));
        setLoading(false);
        return;
      }

      if (res.data.status == "Closed"){
        setClosed(true)
        setLoading(false)
        return
      }
      setTitle(res.data.title);
      setCaseType(res.data.case_type);
      setVersion(res.data.version);
      setLoading(false);
    }

    load();
  }, [id]);

  // Set while the form is in flight, so a second click cannot send a
  // second copy of the same request.
  const [saving, setSaving] = useState(false);
  async function handleSubmit(e) {
    e.preventDefault();
    if (saving) return;

    setError("");
    setSaving(true);

    const res = await apiCall("PATCH", `/cases/${id}`, {
      title: title,
      case_type: caseType,
      version: version,
    });
    setSaving(false);

    if (res.status === 404) {
      setNotFound(true);
      return;
    }

    if (res.status === 409) {
      setError(errorMessage(res));
      return;
    }

    if (res.status === 422) {
      setError(errorMessage(res));
      return;
    }

    if (!res.ok) {
      setError("Could not save the changes.");
      return;
    }

    navigate(`/cases/${id}`);
  }

  if (notFound) {
    return (
      <div className={page}>
        <p className="mb-4">Case not found.</p>
        <Link to="/cases" className={buttonQuiet}>Go to cases</Link>
      </div>
    );
  }

    if (closed) {
    return (
      <div className={page}>
        <p className="mb-4">This case is closed, so it cannot be edited.</p>
        <Link to={`/cases/${id}`} className={buttonQuiet}>Back to the case</Link>
      </div>
    );
  }


  if (loading) {
    return <p className={`${page} ${muted}`}>Loading...</p>;
  }

  return (
    <div className={page}>
      <h1 className={`${heading} mb-6`}>Edit case</h1>

      <form onSubmit={handleSubmit} className={`${card} p-6 max-w-md`}>
        <div className="mb-4">
          <label htmlFor="case-title" className={label}>Title</label>
          <input
            id="case-title"
            value={title}
            maxLength={200}
            onChange={(e) => setTitle(e.target.value)}
            required
            className={input}
          />
        </div>

        <div className="mb-4">
          <label htmlFor="case-type" className={label}>Type</label>
          <select
            id="case-type"
            value={caseType}
            maxLength={50}
            onChange={(e) => setCaseType(e.target.value)}
            className={input}
          >
            {CASE_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <p className={`${muted} mb-4`}>
          Status and assignee are changed on the case page, not here.
        </p>

        {error && <p className={`${errorText} mb-4`}>{error}</p>}

        <div className="flex flex-wrap gap-3">
          <button type="submit" disabled={saving} className={button}>
            {saving ? "Saving..." : "Save"}
          </button>
          <Link to={`/cases/${id}`} className={buttonQuiet}>Cancel</Link>
        </div>
      </form>
    </div>
  );
}

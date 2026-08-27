import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { apiCall, errorMessage, removeToken } from "../api";
import {
  button, buttonQuiet, card, errorText, heading, input, muted, page, rowLink,
  statusBadge, subheading,
} from "../ui";

// The lifecycle is Intake -> Active -> Settled -> Closed, one step at a time.
// We only show the button for the step that is allowed next. The API enforces
// this too - hiding the button is a convenience, not the rule.
const NEXT_STATUS = {
  Intake: "Active",
  Active: "Settled",
  Settled: "Closed",
  Closed: null,
};

export default function CaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [caseData, setCaseData] = useState(null);
  const [staff, setStaff] = useState([]);
  const [notFound, setNotFound] = useState(false);
  const [noteBody, setNoteBody] = useState("");
  const [error, setError] = useState("");

  // Bumped after adding or deleting a note, or changing the status, to make
  // the effect below run again and pull the fresh case.
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    async function load() {
      const res = await apiCall("GET", `/cases/${id}`);

      if (res.status === 401) {
        removeToken();
        navigate("/login");
        return;
      }

      if (res.status === 404) {
        setNotFound(true);
        return;
      }

      setCaseData(res.data);
    }

    load();
  }, [id, navigate, refresh]);

  // The assignee dropdown needs the list of colleagues. Loaded once.
  useEffect(() => {
    async function loadStaff() {
      const res = await apiCall("GET", "/staff");
      if (res.status === 200) setStaff(res.data);
    }
    loadStaff();
  }, []);

  function reload() {
    setRefresh((n) => n + 1);
  }

  async function changeAssignee(e) {
    setError("");
    const value = e.target.value;

    const res = await apiCall("PATCH", `/cases/${id}`, {
      // "" means "nobody", which the API stores as null.
      assignee_id: value ? Number(value) : null,
    });

    if (res.status !== 200) {
      setError("Could not change the assignee.");
      return;
    }

    reload();
  }

  async function moveStatus() {
    setError("");
    const next = NEXT_STATUS[caseData.status];

    const res = await apiCall("PATCH", `/cases/${id}/status`, { status: next });

    if (res.status === 409) {
      setError(errorMessage(res));
      return;
    }

    if (res.status !== 200) {
      setError("Could not change the status.");
      return;
    }

    reload();
  }

  async function addNote(e) {
    e.preventDefault();
    setError("");

    const res = await apiCall("POST", `/cases/${id}/notes`, { body: noteBody });

    if (res.status !== 200) {
      setError("Could not add the note.");
      return;
    }

    setNoteBody("");
    reload();
  }

  async function deleteNote(noteId) {
    setError("");
    const res = await apiCall("DELETE", `/notes/${noteId}`);

    if (res.status !== 200) {
      setError("Could not delete the note.");
      return;
    }

    reload();
  }

  if (notFound) {
    return (
      <div className={page}>
        <p className="mb-4">Case not found.</p>
        <Link to="/cases" className={buttonQuiet}>Go to cases</Link>
      </div>
    );
  }

  if (!caseData) {
    return <p className={`${page} ${muted}`}>Loading...</p>;
  }

  const next = NEXT_STATUS[caseData.status];

  return (
    <div className={page}>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className={heading}>{caseData.title}</h1>
          <p className={`${muted} mt-1`}>
            <Link to={`/clients/${caseData.client.id}`} className={rowLink}>
              {caseData.client.name}
            </Link>
            {" · "}{caseData.case_type}
          </p>
        </div>
        <span className={statusBadge(caseData.status)}>{caseData.status}</span>
      </div>

      {error && <p className={`${errorText} mb-4`}>{error}</p>}

      <div className={`${card} p-6 mb-8 flex items-center gap-8`}>
        <div>
          <p className={`${muted} mb-1`}>Assignee</p>
          <select
            value={caseData.assignee ? caseData.assignee.id : ""}
            onChange={changeAssignee}
            className={input}
          >
            <option value="">Nobody</option>
            {staff.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        <div>
          <p className={`${muted} mb-1`}>Status</p>
          {next ? (
            <button onClick={moveStatus} className={button}>Move to {next}</button>
          ) : (
            <p className="text-sm text-slate-500 py-2">
              Closed cases cannot be reopened.
            </p>
          )}
        </div>
      </div>

      <h2 className={`${subheading} mb-3`}>Notes ({caseData.notes.length})</h2>

      <form onSubmit={addNote} className="mb-6 max-w-2xl">
        <textarea
          value={noteBody}
          onChange={(e) => setNoteBody(e.target.value)}
          required
          rows={3}
          placeholder="Write a note"
          className={`${input} mb-2`}
        />
        <button type="submit" className={button}>Add note</button>
      </form>

      {caseData.notes.length === 0 ? (
        <p className={muted}>No notes yet.</p>
      ) : (
        <ul className="max-w-2xl space-y-2">
          {caseData.notes.map((note) => (
            <li key={note.id} className={`${card} p-4`}>
              <p className="text-sm text-slate-800 mb-2">{note.body}</p>
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-500">
                  {note.author.name} · {new Date(note.created_at).toLocaleString()}
                </span>
                <button
                  onClick={() => deleteNote(note.id)}
                  className="text-xs text-slate-500 hover:text-red-700"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

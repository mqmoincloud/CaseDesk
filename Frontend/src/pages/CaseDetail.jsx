import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { apiCall, errorMessage, removeToken } from "../api";

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
      <div className="p-8">
        <p className="mb-4">Case not found.</p>
        <Link to="/cases" className="underline">Go to cases</Link>
      </div>
    );
  }

  if (!caseData) {
    return <p className="p-8">Loading...</p>;
  }

  const next = NEXT_STATUS[caseData.status];

  return (
    <div className="p-8">
      <h1 className="text-2xl mb-6">{caseData.title}</h1>

      <table className="mb-6">
        <tbody>
          <tr>
            <td className="pr-6 py-1 text-gray-600">Client</td>
            <td className="py-1">
              <Link to={`/clients/${caseData.client.id}`} className="underline">
                {caseData.client.name}
              </Link>
            </td>
          </tr>
          <tr>
            <td className="pr-6 py-1 text-gray-600">Type</td>
            <td className="py-1">{caseData.case_type}</td>
          </tr>
          <tr>
            <td className="pr-6 py-1 text-gray-600">Status</td>
            <td className="py-1">{caseData.status}</td>
          </tr>
          <tr>
            <td className="pr-6 py-1 text-gray-600">Assignee</td>
            <td className="py-1">
              <select
                value={caseData.assignee ? caseData.assignee.id : ""}
                onChange={changeAssignee}
                className="border p-1"
              >
                <option value="">Nobody</option>
                {staff.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </td>
          </tr>
        </tbody>
      </table>

      <div className="mb-8">
        {next ? (
          <button onClick={moveStatus} className="border px-4 py-2">
            Move to {next}
          </button>
        ) : (
          <p className="text-gray-600">This case is closed and cannot be reopened.</p>
        )}
      </div>

      {error && <p className="text-red-700 mb-6">{error}</p>}

      <h2 className="text-xl mb-3">Notes ({caseData.notes.length})</h2>

      <form onSubmit={addNote} className="mb-6">
        <textarea
          value={noteBody}
          onChange={(e) => setNoteBody(e.target.value)}
          required
          rows={3}
          placeholder="Write a note"
          className="border p-2 w-full max-w-2xl block mb-2"
        />
        <button type="submit" className="border px-4 py-2">Add note</button>
      </form>

      {caseData.notes.length === 0 ? (
        <p>No notes yet.</p>
      ) : (
        <ul className="max-w-2xl">
          {caseData.notes.map((note) => (
            <li key={note.id} className="border p-3 mb-2">
              <p className="mb-2">{note.body}</p>
              <div className="flex justify-between text-sm text-gray-600">
                <span>
                  {note.author.name} — {new Date(note.created_at).toLocaleString()}
                </span>
                <button onClick={() => deleteNote(note.id)} className="underline">
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

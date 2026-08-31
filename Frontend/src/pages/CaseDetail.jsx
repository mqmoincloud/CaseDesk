import { useEffect, useState } from "react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";

import { apiCall, errorMessage } from "../api";
import {
  bodyText, button, buttonQuiet, card, column, columns, errorText, fieldValue,
  heading, input, linkDanger, metaText, muted, pageWide, rowLink, statusBadge,
  subheading,
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

  // Comes from Layout, which asked /me for it.
  const user = useOutletContext();

  const [caseData, setCaseData] = useState(null);
  const [staff, setStaff] = useState([]);
  const [notFound, setNotFound] = useState(false);
  const [noteBody, setNoteBody] = useState("");
  const [error, setError] = useState("");

  // Bumped after adding or deleting a note, or changing the status, to make
  // the effect below run again and pull the fresh case.
  const [refresh, setRefresh] = useState(0);

  // An assignee can open the case and write notes on it, and that is all.
  // Changing the status, the assignee, or deleting a note belong to the owner
  // (or an admin), so those controls are not rendered for anyone else - there
  // is no point offering a button whose only outcome is a 404.
  const canManage =
    caseData !== null &&
    (user.role === "admin" || caseData.owner.id === user.id);

  useEffect(() => {
    async function load() {
      const res = await apiCall("GET", `/cases/${id}`);

      if (res.status === 404) {
        setNotFound(true);
        return;
      }

      // A 401 has already sent us to the login screen.
      if (!res.ok) {
        if (res.status !== 401) setError(errorMessage(res));
        return;
      }

      setCaseData(res.data);
    }

    load();
  }, [id, navigate, refresh]);

  // Only fetched when the assignee dropdown is going to be rendered.
  useEffect(() => {
    if (!canManage) return;

    async function loadStaff() {
      const res = await apiCall("GET", "/staff");
      if (res.ok) setStaff(res.data);
    }

    loadStaff();
  }, [canManage]);

  // Set while the note is being posted, so a double-click cannot add it
  // twice - the API accepts identical notes, and should.
  const [addingNote, setAddingNote] = useState(false);

  function reload() {
    setRefresh((n) => n + 1);
  }

  async function changeAssignee(e) {
    setError("");
    const value = e.target.value;

    const res = await apiCall("PATCH", `/cases/${id}`, {
      // "" means "nobody", which the API stores as null.
      assignee_id: value ? Number(value) : null,
      // The version this page is looking at. If someone else saved while this
      // page was open, the API refuses with a 409 rather than overwriting
      // their change (US-21).
      version: caseData.version,
    });

    if (res.status === 409) {
      setError("Someone else changed this case. Reload the page and try again.");
      return;
    }

    if (!res.ok) {
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

    if (!res.ok) {
      setError("Could not change the status.");
      return;
    }

    reload();
  }

  async function addNote(e) {
    e.preventDefault();
    if (addingNote) return;

    setError("");
    setAddingNote(true);

    const res = await apiCall("POST", `/cases/${id}/notes`, { body: noteBody });
    setAddingNote(false);

    // A closed case is readable but cannot take new work, which the API
    // answers with a 409.
    if (res.status === 409) {
      setError("This case is closed, so no more notes can be added.");
      return;
    }

    if (!res.ok) {
      setError(errorMessage(res));
      return;
    }

    setNoteBody("");
    reload();
  }

  async function deleteCase() {
    setError("");

    // Ask first, as every delete does - there is no undelete anywhere.
    if (!window.confirm(`Delete "${caseData.title}"?`)) return;

    const res = await apiCall("DELETE", `/cases/${id}`);

    if (!res.ok) {
      setError("Could not delete this case.");
      return;
    }

    navigate("/cases");
  }

  async function deleteNote(noteId) {
    setError("");

    // No undelete anywhere in this app, so ask first.
    if (!window.confirm("Delete this note?")) return;

    const res = await apiCall("DELETE", `/notes/${noteId}`);

    if (!res.ok) {
      setError("Could not delete the note.");
      return;
    }

    reload();
  }

  if (notFound) {
    return (
      <div className={pageWide}>
        <p className="mb-4">Case not found.</p>
        <Link to="/cases" className={buttonQuiet}>Go to cases</Link>
      </div>
    );
  }

  if (!caseData) {
    return <p className={`${pageWide} ${muted}`}>Loading...</p>;
  }

  const next = NEXT_STATUS[caseData.status];

  // One assignment event as a readable line. "You" when you did it or received
  // it, matching the wording on the Cases page.
  function assignmentLine(a) {
    const who = a.assigned_by.id === user.id ? "You" : a.assigned_by.name;
    if (!a.assignee) return `${who} removed the assignee`;
    const whom = a.assignee.id === user.id ? "you" : a.assignee.name;
    return `${who} assigned ${whom}`;
  }

  // The first row has no from_status - it opened, it did not transition.
  function statusLine(c) {
    const who = c.changed_by.id === user.id ? "You" : c.changed_by.name;
    if (!c.from_status) return `${who} opened the case at ${c.to_status}`;
    return `${who} moved it from ${c.from_status} to ${c.to_status}`;
  }

  return (
    <div className={pageWide}>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
        <div>
          <h1 className={heading}>{caseData.title}</h1>
          {/* Only the owner (and an admin) can open the client behind a
              case, so for an assignee the link would always land on "Client
              not found". They get the name as plain text instead. */}
          <p className={`${muted} mt-1`}>
            {canManage ? (
              <Link to={`/clients/${caseData.client.id}`} className={rowLink}>
                {caseData.client.name}
              </Link>
            ) : (
              caseData.client.name
            )}
            {" · "}{caseData.case_type}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className={statusBadge(caseData.status)}>{caseData.status}</span>
          {/* Owner and admin only - the API answers an assignee with a 404,
              so the button would lead nowhere. No Edit on a closed case
              either, since the API refuses that too; Delete stays, because a
              case opened by mistake may still need removing. */}
          {canManage && caseData.status !== "Closed" && (
            <Link to={`/cases/${id}/edit`} className={buttonQuiet}>Edit</Link>
          )}
          {canManage && (
            <button onClick={deleteCase} className={buttonQuiet}>Delete</button>
          )}
        </div>
      </div>

      {!canManage && (
        <p className={`${muted} mb-4`}>
          This case belongs to {caseData.owner.name}. You are assigned to it, so
          you can read it and add notes.
        </p>
      )}

      {error && <p className={`${errorText} mb-4`}>{error}</p>}

      <div className={`${card} p-6 mb-8 flex flex-wrap items-center gap-8`}>
        <div>
          <p className={`${muted} mb-1`}>Assignee</p>
          {/* The API refuses an assignee change on a closed case, so show the
              name instead of a dropdown that would only return 409. */}
          {canManage && caseData.status !== "Closed" ? (
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
          ) : (
            <p className={`${fieldValue} py-2`}>
              {caseData.assignee ? caseData.assignee.name : "Nobody"}
            </p>
          )}
        </div>

        {canManage && (
          <div>
            <p className={`${muted} mb-1`}>Status</p>
            {next ? (
              <button onClick={moveStatus} className={button}>Move to {next}</button>
            ) : (
              <p className={`${muted} py-2`}>
                Closed cases cannot be reopened.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Three accounts of the same case, so they sit side by side; flex-wrap
          drops them onto their own lines rather than squeezing them thin. */}
      <div className={columns}>
        <section className={column}>
          <h2 className={`${subheading} mb-3`}>
            Assignment history ({caseData.assignments.length})
          </h2>

          {/* Newest first. Cases opened before this feature have nothing here,
              because their history was never written. */}
          {caseData.assignments.length === 0 ? (
            <p className={muted}>Nothing recorded yet.</p>
          ) : (
            <ul className="space-y-2">
              {caseData.assignments.map((a) => (
                <li key={a.id} className={`${card} p-4`}>
                  <p className={bodyText}>{assignmentLine(a)}</p>
                  <span className={metaText}>
                    {new Date(a.created_at).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className={column}>
          <h2 className={`${subheading} mb-3`}>
            Status history ({caseData.status_changes.length})
          </h2>

          {caseData.status_changes.length === 0 ? (
            <p className={muted}>Nothing recorded yet.</p>
          ) : (
          <ul className="space-y-2">
            {caseData.status_changes.map((c) => (
              <li key={c.id} className={`${card} p-4`}>
                <p className={bodyText}>{statusLine(c)}</p>
                <span className={metaText}>
                  {new Date(c.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
          )}
        </section>

        {/* Notes get more room: this column also holds the compose box. */}
        <section className="grow basis-96 min-w-0">
          <h2 className={`${subheading} mb-3`}>Notes ({caseData.notes.length})</h2>

          {/* Adding a note is allowed for the assignee too, so this stays. */}
          <form onSubmit={addNote} className="mb-4">
            <textarea
              value={noteBody}
              onChange={(e) => setNoteBody(e.target.value)}
              required
              maxLength={5000}
              rows={3}
              placeholder="Write a note"
              className={`${input} mb-2`}
            />
            <button type="submit" disabled={addingNote} className={button}>
              {addingNote ? "Adding..." : "Add note"}
            </button>
          </form>

          {caseData.notes.length === 0 ? (
            <p className={muted}>No notes yet.</p>
          ) : (
            <ul className="space-y-2">
              {caseData.notes.map((note) => (
                <li key={note.id} className={`${card} p-4`}>
                  <p className={`${bodyText} mb-2`}>{note.body}</p>
                  <div className="flex flex-wrap justify-between items-center gap-2">
                    <span className={metaText}>
                      {note.author.name} · {new Date(note.created_at).toLocaleString()}
                    </span>
                    {canManage && (
                      <button
                        onClick={() => deleteNote(note.id)}
                        className={linkDanger}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

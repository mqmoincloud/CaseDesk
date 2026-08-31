import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";

import { apiCall, errorMessage } from "../api";
import {
  button, buttonQuiet, card, column, columns, errorText, heading, input, label,
  muted, pageWide, roleBadge, rowAction, rowActionDanger, successText, table,
  tableWrap, td, th,
} from "../ui";

const BLANK = { name: "", email: "", password: "", role: "staff" };

export default function StaffList() {

  const me = useOutletContext();

  const [staff, setStaff] = useState([]);
  const [refresh, setRefresh] = useState(0);

  const [editing, setEditing] = useState(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(BLANK);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function load() {
      const res = await apiCall("GET", "/admin/staff");

      if (!res.ok) {
        if (res.status !== 401) setError(errorMessage(res));
        return;
      }

      setStaff(res.data);
    }

    load();
  }, [refresh]);

  function change(field, value) {
    setForm({ ...form, [field]: value });
  }

  function startCreate() {
    setEditing(null);
    setForm(BLANK);
    setError("");
    setMessage("");
    setOpen(true);
  }

  function startEdit(person) {
    setEditing(person);
    setForm({ name: person.name, email: person.email, password: "", role: person.role });
    setError("");
    setMessage("");
    setOpen(true);
  }

  function close() {
    setOpen(false);
    setEditing(null);
    setForm(BLANK);
    setError("");
  }

  // Set while the form is in flight, so a second click cannot send a
  // second copy of the same request.
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (saving) return;

    setError("");
    setMessage("");
    setSaving(true);

    let res;

    if (editing) {
      // Send only what was filled in - an empty password would read as
      // "clear it".
      const body = { name: form.name, email: form.email, role: form.role };
      if (form.password) body.password = form.password;

      res = await apiCall("PATCH", `/staff/${editing.id}`, body);
    } else {
      res = await apiCall("POST", "/auth/register", form);
    }

    setSaving(false);

    if (res.status === 409 || res.status === 422) {

      setError(errorMessage(res));
      return;
    }

    if (!res.ok) {
      setError(editing ? "Could not save the changes." : "Could not create the account.");
      return;
    }

    setMessage(editing ? `${form.name} updated.` : `${form.name} can now log in.`);
    close();
    setRefresh((n) => n + 1);
  }

  async function handleDelete(person) {
    setError("");
    setMessage("");

    if (!window.confirm(`Remove ${person.name}?`)) return;

    const res = await apiCall("DELETE", `/staff/${person.id}`);

    if (res.status === 409) {

      setError(errorMessage(res));
      return;
    }

    if (!res.ok) {
      setError(`Could not remove ${person.name}.`);
      return;
    }

    setMessage(`${person.name} removed.`);
    setRefresh((n) => n + 1);
  }

  return (
    <div className={pageWide}>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className={heading}>Staff</h1>
          <p className={muted}>{staff.length} with access</p>
        </div>
        <button onClick={startCreate} className={button}>New staff</button>
      </div>

      {error && <p className={`${errorText} mb-4`}>{error}</p>}
      {message && <p className={`${successText} mb-4`}>{message}</p>}

      <div className={columns}>
        {open && (
          <form onSubmit={handleSubmit} className={`${card} ${column} max-w-md p-6`}>
            <h2 className="text-lg font-semibold text-slate-900 mb-4">
              {editing ? `Edit ${editing.name}` : "Add a staff member"}
            </h2>

            {/* One column - the form is a narrow panel now, and two would
                cramp the fields. */}
            <div className="grid gap-4 mb-4">
              <div>
                <label htmlFor="staff-name" className={label}>Name</label>
                <input
                  id="staff-name"
                  value={form.name}
                  maxLength={100}
                  onChange={(e) => change("name", e.target.value)}
                  required
                  className={input}
                />
              </div>

              <div>
                <label htmlFor="staff-email" className={label}>Email</label>
                <input
                  id="staff-email"
                  type="email"
                  value={form.email}
                  onChange={(e) => change("email", e.target.value)}
                  required
                  className={input}
                />
              </div>

              <div>
                <label htmlFor="staff-role" className={label}>Role</label>
                <select
                  id="staff-role"
                  value={form.role}
                  onChange={(e) => change("role", e.target.value)}
                  // The API returns 409 for changing your own role, so do not
                  // offer the door rather than refusing after the click.
                  disabled={editing && editing.id === me.id}
                  className={input}
                >
                  <option value="staff">staff</option>
                  <option value="admin">admin</option>
                </select>
                {editing && editing.id === me.id && (
                  <p className={`${muted} mt-1`}>You cannot change your own role.</p>
                )}
              </div>

              <div>
                <label htmlFor="staff-password" className={label}>
                  Password {editing && <span className="font-normal">(optional)</span>}
                </label>
                <input
                  id="staff-password"
                  type="password"
                  value={form.password}
                  maxLength={72}
                  onChange={(e) => change("password", e.target.value)}
                  required={!editing}
                  className={input}
                />
                <p className={`${muted} mt-1`}>
                  {editing
                    ? "Leave blank to keep the current one."
                    : "8 to 72 characters. There is no reset flow."}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <button type="submit" disabled={saving} className={button}>
                {saving
                  ? "Saving..."
                  : editing
                    ? "Save changes"
                    : "Create account"}
              </button>
              <button type="button" onClick={close} className={buttonQuiet}>
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* basis-[32rem]: the list has four columns and needs more room than
            the form. Both grow, so the spare width is shared. */}
        <div className={`${card} ${tableWrap} grow basis-[32rem] min-w-0`}>
          <table className={table}>
            <thead>
              <tr>
                <th className={th}>Name</th>
                <th className={th}>Email</th>
                <th className={th}>Role</th>
                <th className={th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {staff.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50">
                  <td className={td}>
                    <span className="font-medium text-slate-900">{s.name}</span>
                    {s.id === me.id && <span className={`${muted} ml-2`}>you</span>}
                  </td>
                  <td className={td}>{s.email}</td>
                  <td className={td}>
                    <span className={roleBadge(s.role)}>{s.role}</span>
                  </td>
                  <td className={td}>
                    <div className="flex flex-wrap gap-2">
                      <button onClick={() => startEdit(s)} className={rowAction}>
                        Edit
                      </button>
                      {/* The API refuses to remove your own account, so do not
                          offer the button. The rule lives in the API. */}
                      {s.id !== me.id && (
                        <button
                          onClick={() => handleDelete(s)}
                          className={rowActionDanger}
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}

              {staff.length === 0 && (
                <tr>
                  <td className={`${td} text-center text-slate-500`} colSpan={4}>
                    No staff yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

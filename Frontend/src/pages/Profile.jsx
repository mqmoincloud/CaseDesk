import { useState } from "react";
import { useOutletContext } from "react-router-dom";

import { apiCall, errorMessage, saveToken } from "../api";
import {
  button, card, column, columns, errorText, heading, input, label, muted,
  pageWide, roleBadge, subheading, successText,
} from "../ui";

export default function Profile() {
  // Comes from Layout, which asked /me for it.
  const user = useOutletContext();

  const [name, setName] = useState(user.name);
  const [nameError, setNameError] = useState("");
  const [nameSaved, setNameSaved] = useState("");

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSaved, setPasswordSaved] = useState("");

  // Set while a form is in flight, so its button cannot be pressed again.
  const [savingName, setSavingName] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  async function saveName(e) {
    e.preventDefault();
    if (savingName) return;

    setNameError("");
    setNameSaved("");
    setSavingName(true);

    const res = await apiCall("PATCH", "/me", { name });
    setSavingName(false);

    if (!res.ok) {
      setNameError(errorMessage(res));
      return;
    }

    setNameSaved("Saved.");
    // Ask Layout to read /me again, so the sidebar shows the new name. This
    // used to reload the whole document, which threw away the rest of the
    // page to move one string.
    user.reloadUser();
  }

  async function savePassword(e) {
    e.preventDefault();
    if (savingPassword) return;

    setPasswordError("");
    setPasswordSaved("");
    setSavingPassword(true);

    const res = await apiCall("POST", "/me/password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
    setSavingPassword(false);

    if (res.status === 422) {
      setPasswordError("That is not your current password.");
      return;
    }

    if (!res.ok) {
      setPasswordError(errorMessage(res));
      return;
    }

    // The change raised token_version on the server, so the token this page
    // arrived with is now dead. The endpoint hands back a replacement - save
    // it, or the next request anywhere gets a 401 and drops us at the login
    // screen while this form still says it worked.
    saveToken(res.data.access_token);

    setPasswordSaved("Password changed. Any other device you were signed in on has been signed out.");
    setCurrentPassword("");
    setNewPassword("");
  }

  return (
    <div className={pageWide}>
      <h1 className={`${heading} mb-6`}>Profile</h1>

      {/* Three panels side by side, wrapping when space runs out. The first
          card carries a heading too, so all three start at the same height. */}
      <div className={columns}>
        <section className={column}>
          <h2 className={`${subheading} mb-3`}>Account</h2>

          <div className={`${card} p-6`}>
            <dl className="grid grid-cols-[7rem_1fr] gap-y-3 text-sm">
              <dt className="text-slate-500">Email</dt>
              <dd className="text-slate-900 break-words">{user.email}</dd>
              <dt className="text-slate-500">Role</dt>
              <dd>
                <span className={roleBadge(user.role)}>{user.role}</span>
              </dd>
              <dt className="text-slate-500">Member since</dt>
              <dd className="text-slate-900">
                {new Date(user.created_at).toLocaleDateString()}
              </dd>
            </dl>
            <p className={`${muted} mt-4`}>
              Your email is your login. Ask an admin if it needs changing.
            </p>
          </div>
        </section>

        <section className={column}>
          <h2 className={`${subheading} mb-3`}>Your name</h2>

          <form onSubmit={saveName} className={`${card} p-6`}>
            <div className="mb-4">
              <label htmlFor="profile-name" className={label}>Name</label>
              <input
                id="profile-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className={input}
              />
            </div>

            {nameError && <p className={`${errorText} mb-4`}>{nameError}</p>}
            {nameSaved && <p className={`${successText} mb-4`}>{nameSaved}</p>}

            <button type="submit" disabled={savingName} className={button}>
              {savingName ? "Saving..." : "Save name"}
            </button>
          </form>
        </section>

        <section className={column}>
          <h2 className={`${subheading} mb-3`}>Change password</h2>

          <form onSubmit={savePassword} className={`${card} p-6`}>
            <div className="mb-4">
              <label htmlFor="profile-current-password" className={label}>Current password</label>
              <input
                id="profile-current-password"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                className={input}
              />
            </div>

            <div className="mb-4">
              <label htmlFor="profile-new-password" className={label}>New password</label>
              <input
                id="profile-new-password"
                type="password"
                value={newPassword}
                maxLength={72}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                className={input}
              />
              <p className={`${muted} mt-1`}>8 to 72 characters</p>
            </div>

            {passwordError && <p className={`${errorText} mb-4`}>{passwordError}</p>}
            {passwordSaved && (
              <p className={`${successText} mb-4`}>{passwordSaved}</p>
            )}

            <button type="submit" disabled={savingPassword} className={button}>
              {savingPassword ? "Changing..." : "Change password"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}

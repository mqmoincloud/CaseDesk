import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiCall, saveToken } from "../api";
import { button, card, errorText, heading, input, label, muted } from "../ui";

export default function Login() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  // Set while the form is in flight, so a second click cannot send a
  // second copy of the same request.
  const [saving, setSaving] = useState(false);
  async function handleSubmit(e) {
    e.preventDefault();
    if (saving) return;

    setError("");
    setSaving(true);

    const res = await apiCall("POST", "/auth/login", { email, password });
    setSaving(false);

    if (res.status === 401) {
      // The API gives the same message for a wrong password and an unknown
      // email on purpose, so we do not guess which one it was.
      setError("Invalid email or password.");
      return;
    }

    if (!res.ok) {
      setError("Something went wrong. Is the server running?");
      return;
    }

    saveToken(res.data.access_token);
    navigate("/clients");
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="w-full max-w-sm">
        <h1 className={`${heading} mb-6 text-center`}>CaseDesk</h1>

        <form onSubmit={handleSubmit}  className={`${card} p-6`}>
          <div className="mb-4">
            <label className={label} htmlFor="login-email">Email</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className={input}
            />
          </div>

          <div className="mb-4">
            <label className={label} htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className={input}
            />
          </div>

          {error && <p className={`${errorText} mb-4`}>{error}</p>}

          <button type="submit" disabled={saving} className={`${button} w-full`}>
            {saving ? "Signing in..." : "Log in"}
          </button>
        </form>

        <p className={`mt-6 text-center ${muted}`}>
          Accounts are created by an admin.
        </p>
      </div>
    </div>
  );
}

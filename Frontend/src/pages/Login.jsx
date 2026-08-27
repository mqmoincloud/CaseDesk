import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiCall, saveToken } from "../api";
import { button, card, errorText, heading, input, label } from "../ui";

export default function Login() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    const res = await apiCall("POST", "/auth/login", { email, password });

    if (res.status === 401) {
      // The API gives the same message for a wrong password and an unknown
      // email on purpose, so we do not guess which one it was.
      setError("Invalid email or password.");
      return;
    }

    if (res.status !== 200) {
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

        <form onSubmit={handleSubmit} className={`${card} p-6`}>
          <div className="mb-4">
            <label className={label}>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className={input}
            />
          </div>

          <div className="mb-4">
            <label className={label}>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className={input}
            />
          </div>

          {error && <p className={`${errorText} mb-4`}>{error}</p>}

          <button type="submit" className={`${button} w-full`}>
            Log in
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-600">
          No account?{" "}
          <Link to="/register" className="font-medium text-slate-900 hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}

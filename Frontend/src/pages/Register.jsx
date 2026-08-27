import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiCall, errorMessage, saveToken } from "../api";
import { button, card, errorText, heading, input, label, muted } from "../ui";

export default function Register() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    const res = await apiCall("POST", "/auth/register", { name, email, password });

    if (res.status === 409) {
      setError("That email is already registered.");
      return;
    }

    if (res.status === 422) {
      setError(errorMessage(res));
      return;
    }

    if (res.status !== 200) {
      setError("Something went wrong. Is the server running?");
      return;
    }

    // Register does not give a token back, so log in right away instead of
    // making the user type everything again.
    const login = await apiCall("POST", "/auth/login", { email, password });
    saveToken(login.data.access_token);
    navigate("/clients");
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="w-full max-w-sm">
        <h1 className={`${heading} mb-6 text-center`}>Create an account</h1>

        <form onSubmit={handleSubmit} className={`${card} p-6`}>
          <div className="mb-4">
            <label className={label}>Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className={input}
            />
          </div>

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
            <p className={`${muted} mt-1`}>8 to 72 characters</p>
          </div>

          {error && <p className={`${errorText} mb-4`}>{error}</p>}

          <button type="submit" className={`${button} w-full`}>
            Register
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-600">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-slate-900 hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}

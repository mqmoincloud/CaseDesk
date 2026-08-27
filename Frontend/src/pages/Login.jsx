import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiCall, saveToken } from "../api";

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
    <div className="max-w-sm mx-auto p-8">
      <h1 className="text-2xl mb-6">Log in to CaseDesk</h1>

      <form onSubmit={handleSubmit}>
        <label className="block mb-4">
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="border p-2 w-full"
          />
        </label>

        <label className="block mb-4">
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="border p-2 w-full"
          />
        </label>

        {error && <p className="text-red-700 mb-4">{error}</p>}

        <button type="submit" className="border px-4 py-2">
          Log in
        </button>
      </form>

      <p className="mt-6">
        No account? <Link to="/register" className="underline">Register</Link>
      </p>
    </div>
  );
}

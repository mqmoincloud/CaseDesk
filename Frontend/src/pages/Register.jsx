import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiCall, errorMessage, saveToken } from "../api";

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
    <div className="max-w-sm mx-auto p-8">
      <h1 className="text-2xl mb-6">Create an account</h1>

      <form onSubmit={handleSubmit}>
        <label className="block mb-4">
          Name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="border p-2 w-full"
          />
        </label>

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
          <span className="text-sm text-gray-600">8 to 72 characters</span>
        </label>

        {error && <p className="text-red-700 mb-4">{error}</p>}

        <button type="submit" className="border px-4 py-2">
          Register
        </button>
      </form>

      <p className="mt-6">
        Already have an account? <Link to="/login" className="underline">Log in</Link>
      </p>
    </div>
  );
}

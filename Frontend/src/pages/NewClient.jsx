import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiCall, errorMessage, removeToken } from "../api";

export default function NewClient() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    // Only name is required. The API wants null, not "", for the empty ones -
    // an empty string would fail the email format check.
    const body = {
      name: name,
      phone: phone || null,
      email: email || null,
      address: address || null,
    };

    const res = await apiCall("POST", "/clients/registration", body);

    if (res.status === 401) {
      removeToken();
      navigate("/login");
      return;
    }

    if (res.status === 422) {
      setError(errorMessage(res));
      return;
    }

    if (res.status !== 200) {
      setError("Could not save the client.");
      return;
    }

    navigate(`/clients/${res.data.id}`);
  }

  return (
    <div className="max-w-md p-8">
      <h1 className="text-2xl mb-6">New client</h1>

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
          Phone
          <input
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="border p-2 w-full"
          />
        </label>

        <label className="block mb-4">
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="border p-2 w-full"
          />
        </label>

        <label className="block mb-4">
          Address
          <input
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className="border p-2 w-full"
          />
        </label>

        {error && <p className="text-red-700 mb-4">{error}</p>}

        <div className="flex gap-4">
          <button type="submit" className="border px-4 py-2">
            Save
          </button>
          <Link to="/clients" className="border px-4 py-2">
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}

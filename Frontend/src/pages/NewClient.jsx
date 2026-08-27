import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiCall, errorMessage, removeToken } from "../api";
import { button, buttonQuiet, card, errorText, heading, input, label, page } from "../ui";

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
    <div className={page}>
      <h1 className={`${heading} mb-6`}>New client</h1>

      <form onSubmit={handleSubmit} className={`${card} p-6 max-w-md`}>
        <div className="mb-4">
          <label className={label}>Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} required className={input} />
        </div>

        <div className="mb-4">
          <label className={label}>Phone</label>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} className={input} />
        </div>

        <div className="mb-4">
          <label className={label}>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className={input} />
        </div>

        <div className="mb-4">
          <label className={label}>Address</label>
          <input value={address} onChange={(e) => setAddress(e.target.value)} className={input} />
        </div>

        {error && <p className={`${errorText} mb-4`}>{error}</p>}

        <div className="flex gap-3">
          <button type="submit" className={button}>Save</button>
          <Link to="/clients" className={buttonQuiet}>Cancel</Link>
        </div>
      </form>
    </div>
  );
}

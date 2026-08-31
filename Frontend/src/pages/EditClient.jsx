import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { apiCall, errorMessage } from "../api";
import { button, buttonQuiet, card, errorText, heading, input, label, muted, page } from "../ui";

export default function EditClient() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");

  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState("");

  // Fill the form with what is already saved.
  useEffect(() => {
    async function load() {
      const res = await apiCall("GET", `/clients/${id}`);

      if (res.status === 404) {
        setNotFound(true);
        setLoading(false);
        return;
      }

      // With the server down res.data is null, so res.data.name would throw and
      // setLoading(false) would never run, leaving the page on "Loading..."
      if (!res.ok) {
        if (res.status !== 401) setError(errorMessage(res));
        setLoading(false);
        return;
      }

      setName(res.data.name);
      setPhone(res.data.phone || "");
      setEmail(res.data.email || "");
      setAddress(res.data.address || "");
      setLoading(false);
    }

    load();
  }, [id, navigate]);

  // Set while the form is in flight, so a second click cannot send a
  // second copy of the same request.
  const [saving, setSaving] = useState(false);
  async function handleSubmit(e) {
    e.preventDefault();
    if (saving) return;

    setError("");
    setSaving(true);

    const body = {
      name: name,
      phone: phone || null,
      email: email || null,
      address: address || null,
    };

    const res = await apiCall("PATCH", `/clients/${id}`, body);
    setSaving(false);

    if (res.status === 404) {
      setNotFound(true);
      return;
    }

    if (res.status === 422) {
      setError(errorMessage(res));
      return;
    }

    if (!res.ok) {
      setError("Could not save the changes.");
      return;
    }

    navigate(`/clients/${id}`);
  }

  if (notFound) {
    return (
      <div className={page}>
        <p className="mb-4">Client not found.</p>
        <Link to="/clients" className={buttonQuiet}>Go to clients</Link>
      </div>
    );
  }

  if (loading) {
    return <p className={`${page} ${muted}`}>Loading...</p>;
  }

  return (
    <div className={page}>
      <h1 className={`${heading} mb-6`}>Edit client</h1>

      <form onSubmit={handleSubmit} className={`${card} p-6 max-w-md`}>
        <div className="mb-4">
          <label htmlFor="client-name" className={label}>Name</label>
          <input id="client-name" value={name} onChange={(e) => setName(e.target.value)} required className={input} />
        </div>

        <div className="mb-4">
          <label htmlFor="client-phone" className={label}>Phone</label>
          <input id="client-phone" value={phone} onChange={(e) => setPhone(e.target.value)} maxLength={20} className={input} />
        </div>

        <div className="mb-4">
          <label htmlFor="client-email" className={label}>Email</label>
          <input id="client-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} className={input} />
        </div>

        <div className="mb-4">
          <label htmlFor="client-address" className={label}>Address</label>
          <input id="client-address" value={address} onChange={(e) => setAddress(e.target.value)} className={input} />
        </div>

        {error && <p className={`${errorText} mb-4`}>{error}</p>}

        <div className="flex flex-wrap gap-3">
          <button type="submit" disabled={saving} className={button}>
            {saving ? "Saving..." : "Save"}
          </button>
          <Link to={`/clients/${id}`} className={buttonQuiet}>Cancel</Link>
        </div>
      </form>
    </div>
  );
}

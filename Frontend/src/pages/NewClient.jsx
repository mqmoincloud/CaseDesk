import { useEffect, useState } from "react";
import { Link, useNavigate, useOutletContext } from "react-router-dom";

import { apiCall, errorMessage } from "../api";
import { button, buttonQuiet, card, errorText, heading, input, label, page } from "../ui";

export default function NewClient() {
  const navigate = useNavigate();

  // Comes from Layout, which asked /me for it.
  const user = useOutletContext();
  const admin = user.role === "admin";

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [address, setAddress] = useState("");
  const [error, setError] = useState("");
  const [staff, setStaff] = useState([]);
  const [ownerId, setOwnerId] = useState("");

  useEffect(() => {
    if (!admin) return;

    async function loadStaff() {
      const res = await apiCall("GET", "/admin/staff");
      if (res.ok) setStaff(res.data);
    }
    loadStaff();
  }, [admin]);

  // Set while the form is in flight, so a second click cannot send a
  // second copy of the same request.
  const [saving, setSaving] = useState(false);
  async function handleSubmit(e) {
    e.preventDefault();
    if (saving) return;

    setError("");
    setSaving(true);

    // Only name is required. The API wants null, not "", for the empty ones -
    // an empty string would fail the email format check.
    const body = {
      name: name,
      phone: phone || null,
      email: email || null,
      address: address || null,
      // The API ignores this unless the caller is an admin.
      staff_id: ownerId ? Number(ownerId) : null,
    };

    const res = await apiCall("POST", "/clients/registration", body);
    setSaving(false);

    if (res.status === 422) {
      setError(errorMessage(res));
      return;
    }

    if (!res.ok) {
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

        {admin && (
          <div className="mb-4">
            <label htmlFor="client-owner" className={label}>Belongs to</label>
            <select
              id="client-owner"
              value={ownerId}
              onChange={(e) => setOwnerId(e.target.value)}
              className={input}
            >
              <option value="">Me</option>
              {staff
                .filter((s) => s.role === "staff")
                .map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
            </select>
          </div>
        )}

        {error && <p className={`${errorText} mb-4`}>{error}</p>}

        <div className="flex flex-wrap gap-3">
          <button type="submit" disabled={saving} className={button}>
            {saving ? "Saving..." : "Save"}
          </button>
          <Link to="/clients" className={buttonQuiet}>Cancel</Link>
        </div>
      </form>
    </div>
  );
}

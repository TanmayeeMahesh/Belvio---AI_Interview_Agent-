import { useState } from "react";
import API from "../api";

export default function CreateOrganization() {
  const [name, setName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim() || !adminEmail.trim()) return;
    setLoading(true);
    setMessage("");
    setError("");

    try {
      await API.post("/api/admin/create-organization", {
        organization_name: name,
        admin_email: adminEmail,
      });
      setMessage(`Organization "${name}" was successfully created.`);
      setName("");
      setAdminEmail("");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create organization.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page" style={{ maxWidth: 800 }}>
      <h1 className="page-title">Create Organization</h1>
      <p className="text-secondary" style={{ marginBottom: 32 }}>
        Add a new organization to the platform. An organization acts as a tenant
        that can have its own Org Admins and HR users.
      </p>

      <div className="card" style={{ padding: 32 }}>
        <form onSubmit={handleCreate} className="gap-20">
          <div>
            <label>Organization Name</label>
            <input
              type="text"
              placeholder="e.g. Acme Corp"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div>
            <label>Organization Admin Email</label>

            <input
              type="email"
              placeholder="admin@company.com"
              value={adminEmail}
              onChange={(e) => setAdminEmail(e.target.value)}
              required
            />
          </div>

          {error && <div className="text-danger text-sm">{error}</div>}
          {message && <div className="text-success text-sm">{message}</div>}

          <div>
            <button className="btn-primary" type="submit" disabled={loading}>
              {loading ? "Creating..." : "Create Organization"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import API from "../api";

export default function OrgAdminDashboard() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    API.get("/api/dashboard/org-admin")
      .then((res) => setStats(res.data))
      .catch(console.error);
  }, []);

  if (!stats) return <div>Loading...</div>;

  return (
    <div style={{ padding: 24 }}>
      <h1>Org Admin Dashboard</h1>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4,1fr)",
          gap: 16,
          marginTop: 24,
        }}
      >
        <div className="card">
          <h3>HRs</h3>
          <h2>{stats.hrs}</h2>
        </div>

        <div className="card">
          <h3>Job Openings</h3>
          <h2>{stats.job_openings}</h2>
        </div>

        <div className="card">
          <h3>Candidates</h3>
          <h2>{stats.candidates}</h2>
        </div>

        <div className="card">
          <h3>Interviews</h3>
          <h2>{stats.scheduled_interviews}</h2>
        </div>
      </div>
    </div>
  );
}

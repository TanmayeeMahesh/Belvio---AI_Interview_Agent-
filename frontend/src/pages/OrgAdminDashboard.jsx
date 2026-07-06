import { useEffect, useState } from "react";
import API from "../api";

export default function OrgAdminDashboard({ onNavigate }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    API.get("/api/dashboard/org-admin")
      .then((res) => setStats(res.data))
      .catch(console.error);
  }, []);

  if (!stats) return <div className="page">Loading dashboard...</div>;

  return (
    <div className="page">
      <div className="flex-between" style={{ marginBottom: 32 }}>
        <div>
          <h1 className="page-title" style={{ margin: 0 }}>Organization Dashboard</h1>
          <p className="text-secondary" style={{ marginTop: 4, marginBottom: 0, fontSize: 14 }}>High-level overview of your organization's recruitment performance.</p>
        </div>
      </div>

      <div className="grid-4" style={{ marginBottom: 40 }}>
        <div className="card stat-card" style={{ padding: 24 }}>
          <div className="text-secondary font-semibold" style={{ textTransform: "uppercase", fontSize: 12, letterSpacing: "0.05em" }}>Total HRs</div>
          <div className="stat-number mt-8">{stats.hrs}</div>
        </div>

        <div className="card stat-card" style={{ padding: 24 }}>
          <div className="text-secondary font-semibold" style={{ textTransform: "uppercase", fontSize: 12, letterSpacing: "0.05em" }}>Active Job Openings</div>
          <div className="stat-number mt-8">{stats.job_openings}</div>
        </div>

        <div className="card stat-card" style={{ padding: 24 }}>
          <div className="text-secondary font-semibold" style={{ textTransform: "uppercase", fontSize: 12, letterSpacing: "0.05em" }}>Total Candidates</div>
          <div className="stat-number mt-8">{stats.candidates}</div>
        </div>

        <div className="card stat-card" style={{ padding: 24 }}>
          <div className="text-secondary font-semibold" style={{ textTransform: "uppercase", fontSize: 12, letterSpacing: "0.05em" }}>Interviews Scheduled</div>
          <div className="stat-number mt-8">{stats.scheduled_interviews}</div>
        </div>
      </div>
      
      <div className="grid-2">
        <div className="card" onClick={() => onNavigate("hrs")} style={{ cursor: "pointer", padding: 32, display: "flex", flexDirection: "column", gap: 16, alignItems: "center", justifyContent: "center", minHeight: 250, textAlign: "center" }}>
          <div style={{ width: 48, height: 48, borderRadius: "50%", background: "rgba(37, 99, 235, 0.1)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--primary)", fontSize: 24, fontWeight: 300 }}>
            +
          </div>
          <h3 style={{ margin: 0 }}>Manage Your Team</h3>
          <p className="text-secondary" style={{ maxWidth: 300, margin: 0 }}>Navigate to HR Management to add new recruiters and organize your talent acquisition team.</p>
        </div>
        
        <div className="card" onClick={() => onNavigate("jobs")} style={{ cursor: "pointer", padding: 32, display: "flex", flexDirection: "column", gap: 16, alignItems: "center", justifyContent: "center", minHeight: 250, textAlign: "center" }}>
           <div style={{ width: 48, height: 48, borderRadius: "50%", background: "rgba(34, 197, 94, 0.1)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--success)", fontSize: 20 }}>
            ✓
          </div>
          <h3 style={{ margin: 0 }}>Recruitment Pipeline</h3>
          <p className="text-secondary" style={{ maxWidth: 300, margin: 0 }}>View all active job postings, monitor candidate progress, and manage the interview pipeline.</p>
        </div>
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import API from "../api";

export default function HRDashboard({ onOpenJob }) {
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [statsRes, jobsRes] = await Promise.all([
          API.get("/api/dashboard/hr"),
          API.get("/api/job-openings")
        ]);
        setStats(statsRes.data);
        setJobs(jobsRes.data);
      } catch (err) {
        console.error("Failed to load HR dashboard data", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) return <div className="page">Loading dashboard...</div>;

  return (
    <div className="page">
      <div className="flex-between" style={{ marginBottom: 32 }}>
        <div>
          <h1 className="page-title" style={{ margin: 0 }}>HR Overview</h1>
          <p className="text-secondary" style={{ marginTop: 4, marginBottom: 0, fontSize: 14 }}>Monitor your recruitment pipeline and interview metrics at a glance.</p>
        </div>
      </div>

      <div className="grid-3" style={{ marginBottom: 40 }}>
        <div className="card stat-card" style={{ padding: 24 }}>
          <div className="text-secondary font-semibold" style={{ textTransform: "uppercase", fontSize: 12, letterSpacing: "0.05em" }}>Total Job Openings</div>
          <div className="stat-number mt-8">{stats?.total_jobs || 0}</div>
        </div>
        <div className="card stat-card" style={{ padding: 24 }}>
          <div className="text-secondary font-semibold" style={{ textTransform: "uppercase", fontSize: 12, letterSpacing: "0.05em" }}>Total Candidates</div>
          <div className="stat-number mt-8">{stats?.total_candidates || 0}</div>
        </div>
        <div className="card stat-card" style={{ padding: 24 }}>
          <div className="text-secondary font-semibold" style={{ textTransform: "uppercase", fontSize: 12, letterSpacing: "0.05em" }}>Interviews Scheduled</div>
          <div className="stat-number mt-8">{stats?.total_interviews || 0}</div>
        </div>
      </div>

      <div style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: "var(--text)" }}>Active Job Openings</h2>
      </div>

      <div className="card">
        <div style={{ padding: 0 }}>
          {jobs.length === 0 ? (
            <div style={{ padding: 32, textAlign: "center", color: "var(--text-secondary)" }}>
              No active job openings found. Create one in the Job Openings tab.
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Job Title</th>
                  <th>Status</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map(job => (
                  <tr 
                    key={job.id} 
                    style={{ cursor: "pointer" }} 
                    onClick={() => onOpenJob(job.id, job.title)}
                  >
                    <td className="font-semibold" style={{ color: "var(--primary)" }}>{job.title}</td>
                    <td><span className="badge badge-completed">{job.status || "Open"}</span></td>
                    <td className="text-secondary" style={{ maxWidth: 300, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {job.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

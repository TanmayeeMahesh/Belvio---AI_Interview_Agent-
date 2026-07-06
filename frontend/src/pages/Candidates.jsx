import { useEffect, useState } from "react";
import API from "../api";

export default function Candidates({ role }) {
  const [candidates, setCandidates] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [jobId, setJobId] = useState("");

  useEffect(() => {
    loadCandidates();
    loadJobs();
  }, []);

  async function loadCandidates() {
    setLoading(true);
    try {
      const { data } = await API.get("/api/candidates");
      setCandidates(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function loadJobs() {
    try {
      const { data } = await API.get("/api/job-openings");
      setJobs(data);
    } catch (err) {
      console.error(err);
    }
  }

  async function createCandidate(e) {
    e.preventDefault();
    setCreating(true);
    try {
      const selectedJob = jobs.find((j) => j.id === jobId);
      await API.post("/api/candidates", {
        name,
        email,
        role: selectedJob?.title,
        job_opening_id: jobId,
      });

      setName("");
      setEmail("");
      setJobId("");
      setIsPanelOpen(false);
      loadCandidates();
    } catch (err) {
      console.error(err);
      alert("Failed to create candidate");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="page" style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingBottom: 64 }}>
      <div style={{ width: "100%", maxWidth: 1600, marginBottom: 32, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 className="page-title" style={{ margin: 0, textAlign: "left" }}>All Candidates</h1>
          <p className="text-secondary" style={{ marginTop: 4, marginBottom: 0, fontSize: 14 }}>View and manage the global talent pool across all jobs.</p>
        </div>

        {role !== "ORG_ADMIN" && (
          <div style={{ cursor: "pointer", transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)" }} onClick={() => setIsPanelOpen(true)} onMouseEnter={(e) => { e.currentTarget.style.transform = "translateY(-4px)"; e.currentTarget.children[0].style.boxShadow = "0 12px 40px 0 rgba(31, 38, 135, 0.15)"; e.currentTarget.children[0].style.background = "rgba(255, 255, 255, 0.8)"; }} onMouseLeave={(e) => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.children[0].style.boxShadow = "0 8px 32px 0 rgba(31, 38, 135, 0.1)"; e.currentTarget.children[0].style.background = "rgba(255, 255, 255, 0.6)"; }}>
            <button style={{
              background: "rgba(255, 255, 255, 0.6)",
              backdropFilter: "blur(12px)",
              WebkitBackdropFilter: "blur(12px)",
              border: "1px solid rgba(255, 255, 255, 0.8)",
              borderRadius: 16,
              width: 200,
              height: 60,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--primary)",
              boxShadow: "0 8px 32px 0 rgba(31, 38, 135, 0.1)",
              padding: 0,
              transition: "all 0.3s ease"
            }}>
              <span style={{ fontSize: 14, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase" }}>ADD CANDIDATE</span>
            </button>
          </div>
        )}
      </div>

      <div className="card" style={{ width: "100%", maxWidth: 1600 }}>
        <div style={{ padding: 0 }}>
          {loading ? (
            <div style={{ padding: 64, textAlign: "center", color: "var(--text-secondary)" }}>
              Loading candidates...
            </div>
          ) : candidates.length === 0 ? (
            <div style={{ padding: 64, textAlign: "center", color: "var(--text-secondary)" }}>
              No candidates found across any job openings.
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c) => (
                  <tr key={c.id}>
                    <td className="font-semibold">{c.name}</td>
                    <td className="text-secondary">{c.email}</td>
                    <td><span className="badge badge-in_progress">{c.role || "N/A"}</span></td>
                    <td>
                      {c.is_scheduled ? (
                        <span className="badge badge-scheduled">Scheduled</span>
                      ) : (
                        <span className="badge badge-incomplete">Pending</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Slide-Over Panel Overlay */}
      {isPanelOpen && (
        <div className="slide-over-overlay" onClick={() => setIsPanelOpen(false)}></div>
      )}
      
      {/* Slide-Over Panel */}
      <div className={`slide-over-panel ${isPanelOpen ? "open" : ""}`}>
        <div style={{ padding: "24px 32px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0, fontSize: 20 }}>Add Candidate manually</h2>
          <button className="btn-ghost" onClick={() => setIsPanelOpen(false)} style={{ padding: "4px 8px", fontSize: 20 }}>&times;</button>
        </div>
        
        <div style={{ padding: 32, flex: 1, overflowY: "auto" }}>
          <form onSubmit={createCandidate} className="gap-20">
            <div>
              <label>Candidate Name</label>
              <input
                type="text"
                placeholder="e.g. Jane Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            <div>
              <label>Candidate Email</label>
              <input
                type="email"
                placeholder="jane@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div>
              <label>Assign to Job Opening</label>
              <select value={jobId} onChange={(e) => setJobId(e.target.value)} required>
                <option value="">Select Job...</option>
                {jobs.map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.title}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginTop: 24, display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button type="button" className="btn-ghost" onClick={() => setIsPanelOpen(false)}>Cancel</button>
              <button type="submit" className="btn-primary" disabled={creating}>
                {creating ? "Adding..." : "Add Candidate"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

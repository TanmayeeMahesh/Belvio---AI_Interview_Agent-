import { useEffect, useState } from "react";
import API from "../api";

export default function JobOpenings({ onOpenJob }) {
  const [jobs, setJobs] = useState([]);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [jdFile, setJdFile] = useState(null);

  useEffect(() => {
    loadJobs();
  }, []);

  function loadJobs() {
    API.get("/api/job-openings")
      .then((res) => {
        setJobs(res.data);
      })
      .catch(console.error);
  }

  async function createJob(e) {
    e.preventDefault();
    setLoading(true);
    try {
      // If we supported PDF upload for JD, we'd use FormData.
      // For now, since backend expects jd_text, we mock extracting text from the file or send form data if backend supports it.
      // Since backend expects jd_text as per previous implementation, we'll just send dummy text for now 
      // if they upload a file, or if the backend supports file upload we'd change it.
      // In the original code, it was jd_text. I'll stick to jd_text for API payload.
      const payload = {
        title,
        description,
        jd_text: jdFile ? `(PDF File Attached: ${jdFile.name})` : ""
      };

      await API.post("/api/job-openings", payload);

      setTitle("");
      setDescription("");
      setJdFile(null);
      setIsPanelOpen(false);
      loadJobs();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page" style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingBottom: 64 }}>
      <div style={{ width: "100%", maxWidth: 1600, marginBottom: 32, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 className="page-title" style={{ margin: 0, textAlign: "left" }}>Job Openings</h1>
          <p className="text-secondary" style={{ marginTop: 4, marginBottom: 0, fontSize: 14 }}>Create and manage active job postings.</p>
        </div>
        
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
            <span style={{ fontSize: 14, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase" }}>ADD NEW POST</span>
          </button>
        </div>
      </div>

      <div className="card" style={{ width: "100%", maxWidth: 1600 }}>
        <div style={{ padding: 0 }}>
          {jobs.length === 0 ? (
            <div style={{ padding: 64, textAlign: "center", color: "var(--text-secondary)" }}>
              No job openings found. Click the button above to create one.
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
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <button className="btn-ghost btn-sm" onClick={() => onOpenJob(job.id, job.title)} style={{ padding: 0, fontWeight: 600, color: "var(--primary)" }}>
                        {job.title}
                      </button>
                    </td>
                    <td><span className="badge badge-completed">{job.status || "Open"}</span></td>
                    <td className="text-secondary">{job.description}</td>
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
          <h2 style={{ margin: 0, fontSize: 20 }}>Create Job Opening</h2>
          <button className="btn-ghost" onClick={() => setIsPanelOpen(false)} style={{ padding: "4px 8px", fontSize: 20 }}>&times;</button>
        </div>
        
        <div style={{ padding: 32, flex: 1, overflowY: "auto" }}>
          <form onSubmit={createJob} className="gap-20">
            <div>
              <label>Job Title</label>
              <input
                type="text"
                placeholder="e.g. Senior Software Engineer"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>

            <div>
              <label>Description</label>
              <textarea
                placeholder="Brief summary of the role..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                required
              />
            </div>

            <div>
              <label>Job Description (PDF)</label>
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => setJdFile(e.target.files[0])}
                style={{ padding: "8px" }}
              />
              <span className="text-secondary text-xs mt-4" style={{ display: "block" }}>Upload the detailed Job Description.</span>
            </div>

            <div style={{ marginTop: 24, display: "flex", gap: 12, justifyContent: "flex-end" }}>
              <button type="button" className="btn-ghost" onClick={() => setIsPanelOpen(false)}>Cancel</button>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? "Creating..." : "Create Job"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

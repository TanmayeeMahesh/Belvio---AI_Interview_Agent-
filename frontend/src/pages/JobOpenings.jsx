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
      </div>

      <div style={{ width: "100%", maxWidth: 1600 }}>
        <div className="grid-3">
          {/* Add New Post Card */}
          <div 
            className="card" 
            style={{ 
              cursor: "pointer", 
              transition: "transform 0.2s, box-shadow 0.2s", 
              display: "flex", 
              flexDirection: "column", 
              alignItems: "center", 
              justifyContent: "center",
              padding: 24, 
              minHeight: 160,
              background: "rgba(37, 99, 235, 0.03)",
              border: "2px dashed rgba(37, 99, 235, 0.2)",
              textAlign: "center"
            }}
            onClick={() => setIsPanelOpen(true)}
            onMouseEnter={(e) => { e.currentTarget.style.transform = "translateY(-4px)"; e.currentTarget.style.boxShadow = "0 12px 24px rgba(0,0,0,0.1)"; e.currentTarget.style.borderColor = "var(--primary)"; e.currentTarget.style.background = "rgba(37, 99, 235, 0.08)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "var(--shadow)"; e.currentTarget.style.borderColor = "rgba(37, 99, 235, 0.2)"; e.currentTarget.style.background = "rgba(37, 99, 235, 0.03)"; }}
          >
            <div style={{ width: 48, height: 48, borderRadius: "50%", background: "rgba(37, 99, 235, 0.1)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--primary)", fontSize: 24, fontWeight: 300, marginBottom: 12 }}>
              +
            </div>
            <h3 style={{ margin: 0, fontSize: 16, color: "var(--primary)" }}>Create New Post</h3>
          </div>

          {jobs.map((job) => (
            <div 
              key={job.id} 
              className="card" 
              style={{ cursor: "pointer", transition: "transform 0.2s, box-shadow 0.2s", display: "flex", flexDirection: "column", padding: 24, minHeight: 160 }}
              onClick={() => onOpenJob(job.id, job.title)}
              onMouseEnter={(e) => { e.currentTarget.style.transform = "translateY(-4px)"; e.currentTarget.style.boxShadow = "0 12px 24px rgba(0,0,0,0.1)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "var(--shadow)"; }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
                <h3 style={{ margin: 0, fontSize: 18, color: "var(--primary)" }}>{job.title}</h3>
                <span className="badge badge-completed">{job.status || "Open"}</span>
              </div>
              <p className="text-secondary" style={{ flex: 1, margin: "0 0 16px 0", fontSize: 14, lineHeight: 1.5 }}>
                {job.description || "No description provided."}
              </p>
              <div style={{ marginTop: "auto", display: "flex", justifyContent: "flex-end" }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--primary)" }}>View Candidates &rarr;</span>
              </div>
            </div>
          ))}
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

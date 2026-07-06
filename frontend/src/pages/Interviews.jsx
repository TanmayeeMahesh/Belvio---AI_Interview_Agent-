import { useEffect, useState } from "react";
import API from "../api";

export default function Interviews({ onViewReport }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();

    const interval = setInterval(() => {
      loadSessions(false);
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  async function loadSessions(showLoader = true) {
    if (showLoader) setLoading(true);
    try {
      const { data } = await API.get("/api/interviews");
      setSessions(data);
    } catch (err) {
      console.error(err);
    } finally {
      if (showLoader) setLoading(false);
    }
  }

  function getBadgeClass(status) {
    if (!status) return "badge-scheduled";
    const s = status.toLowerCase();
    if (s.includes("joining") || s.includes("waiting")) return "badge-in_progress";
    if (s.includes("in_progress") || s.includes("interviewing") || s === "in progress") return "badge-in_progress";
    if (s.includes("completed")) return "badge-completed";
    if (s.includes("no_show") || s.includes("incomplete") || s === "no show") return "badge-no_show";
    if (s.includes("time") || s.includes("limit") || s.includes("cap")) return "badge-error";
    if (s.includes("error")) return "badge-error";
    return "badge-scheduled";
  }

  function formatStatusLabel(status) {
    if (!status) return "Scheduled";
    const s = status.toLowerCase();
    
    if (s.includes("joining") || s.includes("waiting")) return "Joining Meeting / Waiting Room";
    if (s.includes("in_progress") || s.includes("interviewing") || s === "in progress") return "In Progress";
    if (s.includes("no_show") || s.includes("incomplete") || s === "no show") return "Incomplete / No Show";
    if (s.includes("time") || s.includes("limit") || s.includes("cap")) return "Time Limit Reached";
    if (s === "completed") return "Completed";
    if (s === "scheduled") return "Scheduled";
    
    // Default fallback
    return status.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
  }

  function formatDateIST(iso) {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleString("en-US", {
        timeZone: "Asia/Kolkata",
        dateStyle: "medium",
        timeStyle: "short",
      }) + " IST";
    } catch(e) {
      return new Date(iso).toLocaleString([], {
        dateStyle: "medium",
        timeStyle: "short",
      });
    }
  }

  const [statusFilter, setStatusFilter] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("");

  if (loading) return <div className="page">Loading interviews...</div>;

  const uniqueRoles = [...new Set(sessions.map((s) => s.role).filter(Boolean))];
  const uniqueStatuses = [...new Set(sessions.map((s) => s.status).filter(Boolean))];

  const filteredSessions = sessions.filter((s) => {
    if (statusFilter !== "all" && s.status !== statusFilter) return false;
    if (roleFilter !== "all" && s.role !== roleFilter) return false;
    if (dateFilter) {
      const sDate = new Date(s.scheduled_time || s.created_at).toISOString().split("T")[0];
      if (sDate !== dateFilter) return false;
    }
    return true;
  });

  return (
    <div className="page">
      <div className="flex-between" style={{ marginBottom: 20 }}>
        <div>
          <h1 className="page-title" style={{ margin: 0 }}>Interviews</h1>
          <p className="text-secondary" style={{ marginTop: 4, marginBottom: 0, fontSize: 14 }}>Track and monitor all scheduled and completed AI interviews.</p>
        </div>
        <div className="text-secondary font-semibold">Total: {sessions.length}</div>
      </div>

      <div className="card" style={{ padding: "10px 14px", marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ height: 34, flex: "1 1 140px", width: "auto" }}
          >
            <option value="all">All statuses</option>
            {uniqueStatuses.map((s) => (
              <option key={s} value={s}>
                {formatStatusLabel(s)}
              </option>
            ))}
          </select>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            style={{ height: 34, flex: "1 1 150px", width: "auto" }}
          >
            <option value="all">All roles</option>
            {uniqueRoles.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <input
            type="date"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            style={{ height: 34, flex: "1 1 150px", width: "auto", padding: "0 10px" }}
          />
          {(statusFilter !== "all" || roleFilter !== "all" || dateFilter) && (
            <button
              className="btn-ghost btn-sm"
              onClick={() => {
                setStatusFilter("all");
                setRoleFilter("all");
                setDateFilter("");
              }}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="card">
        <div style={{ padding: 0 }}>
          {filteredSessions.length === 0 ? (
             <div style={{ padding: 32, textAlign: "center", color: "var(--text-secondary)" }}>
               No interviews match the filters.
             </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Candidate</th>
                  <th>Role</th>
                  <th>Level</th>
                  <th>Scheduled Time IST</th>
                  <th>Status</th>
                  <th>Meeting Link</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredSessions.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <div className="font-semibold">{s.candidate_name}</div>
                      <div className="text-secondary text-sm">{s.candidate_email}</div>
                    </td>
                    <td><span className="text-secondary">{s.role || "—"}</span></td>
                    <td><span className="text-secondary">{s.analysis?.detectedLevel ? s.analysis.detectedLevel.charAt(0).toUpperCase() + s.analysis.detectedLevel.slice(1) : "—"}</span></td>
                    <td className="text-secondary text-sm">
                      {formatDateIST(s.scheduled_time || s.created_at)}
                    </td>
                    <td>
                      <span className={`badge ${getBadgeClass(s.status)}`}>
                        {formatStatusLabel(s.status)}
                      </span>
                    </td>
                    <td>
                      {s.meeting_url ? (
                        <a href={s.meeting_url} target="_blank" rel="noreferrer" style={{ color: "var(--primary)", textDecoration: "underline", fontSize: 13 }}>
                          Link
                        </a>
                      ) : (
                        <span className="text-secondary text-sm">—</span>
                      )}
                    </td>
                    <td>
                      {s.status === "completed" ? (
                        <button 
                          className="btn-ghost btn-sm" 
                          onClick={() => onViewReport(s.session_id || s.id)}
                          style={{ color: "var(--primary)", borderColor: "var(--primary)" }}
                        >
                          View Report
                        </button>
                      ) : (
                        <span className="text-secondary text-xs">Waiting...</span>
                      )}
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

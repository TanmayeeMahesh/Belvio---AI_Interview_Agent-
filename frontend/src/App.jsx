import { useState, useEffect } from "react";
import API, { setAuthToken } from "./api";
import Dashboard from "./pages/Dashboard";
import Sessions from "./pages/Sessions";
import Reports from "./pages/Reports";
import SuperAdminDashboard from "./pages/SuperAdminDashboard";
import OrgAdminDashboard from "./pages/OrgAdminDashboard";
import Organizations from "./pages/Organizations";
import HRDashboard from "./pages/HRDashboard";
import JobOpenings from "./pages/JobOpenings";
import HRManagement from "./pages/HRManagement";
import Candidates from "./pages/Candidates";
import Interviews from "./pages/Interviews";
import JobDetails from "./pages/JobDetails";

const TOKEN_KEY = "ib_token";
const EMAIL_KEY = "ib_email";

function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await API.post("/api/auth/login", { email, password });

      console.log("LOGIN RESPONSE =", data);

      onLogin(data.token, data.email);
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed.");
    }
    setLoading(false);
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg)",
      }}
    >
      <div className="card" style={{ width: 360, padding: 32 }}>
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 22, fontWeight: 700 }}>InterviewBot</div>
          <div className="text-secondary text-sm" style={{ marginTop: 4 }}>
            Sign in to continue
          </div>
        </div>
        <form
          onSubmit={handleLogin}
          style={{ display: "flex", flexDirection: "column", gap: 12 }}
        >
          <div>
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>
          <div>
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>
          {error && <div className="text-danger text-sm">{error}</div>}
          <button
            className="btn-primary"
            type="submit"
            disabled={loading}
            style={{ marginTop: 4 }}
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}

function Nav({ tab, setTab, email, onLogout, role }) {
  let tabs = [];

  if (role === "SUPER_ADMIN") {
    tabs = [
      { id: "dashboard", label: "Dashboard" },
      { id: "organizations", label: "Organizations" },
    ];
  }

  if (role === "ORG_ADMIN") {
    tabs = [
      { id: "dashboard", label: "Dashboard" },
      { id: "hrs", label: "HR Management" },
      { id: "jobs", label: "Job Openings" },
      { id: "reports", label: "Reports" },
    ];
  }

  if (role === "HR") {
    tabs = [
      { id: "dashboard", label: "Dashboard" },
      { id: "jobs", label: "Job Openings" },
      { id: "candidates", label: "Candidates" },
      { id: "interviews", label: "Interviews" },
      { id: "reports", label: "Reports" },
    ];
  }
  return (
    <nav
      style={{
        background: "var(--surface)",
        borderBottom: "1px solid var(--border)",
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}
    >
      <div
        style={{
          maxWidth: 1100,
          margin: "0 auto",
          padding: "0 24px",
          height: 52,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <span
            style={{ fontWeight: 700, fontSize: 15, letterSpacing: "-.02em" }}
          >
            InterviewBot
          </span>
          <div style={{ display: "flex", gap: 2 }}>
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                style={{
                  border: "none",
                  padding: "6px 12px",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontSize: 14,
                  fontWeight: tab === t.id ? 600 : 400,
                  color:
                    tab === t.id ? "var(--accent)" : "var(--text-secondary)",
                  background: tab === t.id ? "#eff0ff" : "transparent",
                }}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span className="text-secondary text-sm">{email}</span>
          <button className="btn-ghost btn-sm" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </div>
    </nav>
  );
}

export default function App() {
  const [token, setToken] = useState(
    () => localStorage.getItem(TOKEN_KEY) || "",
  );
  const [email, setEmail] = useState(
    () => localStorage.getItem(EMAIL_KEY) || "",
  );
  const [role, setRole] = useState("");
  const [loadingUser, setLoadingUser] = useState(true);
  const [tab, setTab] = useState("dashboard");
  const [reportSessionId, setReportSessionId] = useState(null);
  const [selectedJobId, setSelectedJobId] = useState(null);

  function openJob(jobId) {
    setSelectedJobId(jobId);
    setTab("job-details");
  }

  useEffect(() => {
    if (!token) {
      setLoadingUser(false);
      return;
    }

    setAuthToken(token);

    console.log("TOKEN =", token);

    API.get("/api/whoami")
      .then((res) => {
        console.log("WHOAMI =", res.data);
        setRole(res.data.role);
      })
      .catch((err) => {
        console.error("WHOAMI ERROR =", err);
      })
      .finally(() => {
        setLoadingUser(false);
      });
  }, [token]);

  function handleLogin(tok, em) {
    localStorage.setItem(TOKEN_KEY, tok);
    localStorage.setItem(EMAIL_KEY, em);
    setToken(tok);
    setEmail(em);
    setAuthToken(tok);
  }

  function handleLogout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
    setToken("");
    setEmail("");
    setAuthToken(null);
  }

  function openReport(sessionId) {
    setReportSessionId(sessionId);
    setTab("reports");
  }

  if (loadingUser) {
    return <div style={{ padding: 40 }}>Loading...</div>;
  }

  if (!token) return <Login onLogin={handleLogin} />;

  return (
    <div>
      <Nav
        tab={tab}
        setTab={setTab}
        email={email}
        onLogout={handleLogout}
        role={role}
      />
      {tab === "dashboard" && role === "SUPER_ADMIN" && <SuperAdminDashboard />}
      {tab === "organizations" && role === "SUPER_ADMIN" && <Organizations />}

      {tab === "dashboard" && role === "ORG_ADMIN" && <OrgAdminDashboard />}

      {tab === "dashboard" && role === "HR" && <HRDashboard />}
      {tab === "jobs" && <JobOpenings onOpenJob={openJob} />}
      {tab === "hrs" && <HRManagement />}
      {tab === "candidates" && <Candidates />}
      {tab === "interviews" && <Interviews />}
      {tab === "job-details" && <JobDetails jobId={selectedJobId} />}
      {tab === "sessions" && (
        <Sessions token={token} onViewReport={openReport} />
      )}
      {tab === "reports" && (
        <Reports token={token} defaultSessionId={reportSessionId} />
      )}
    </div>
  );
}

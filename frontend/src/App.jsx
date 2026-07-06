import { useState, useEffect } from "react";
import API, { setAuthToken } from "./api";
import Dashboard from "./pages/Dashboard";
import Sessions from "./pages/Sessions";
import Reports from "./pages/Reports";
import SuperAdminDashboard from "./pages/SuperAdminDashboard";
import OrgAdminDashboard from "./pages/OrgAdminDashboard";
import CreateOrganization from "./pages/CreateOrganization";
import SuperAdminProfile from "./pages/SuperAdminProfile";
import HRDashboard from "./pages/HRDashboard";
import JobOpenings from "./pages/JobOpenings";
import HRManagement from "./pages/HRManagement";
import Candidates from "./pages/Candidates";
import Interviews from "./pages/Interviews";
import JobDetails from "./pages/JobDetails";
import Login from "./pages/Login";
import OrgSettings from "./pages/OrgSettings";
import LandingPage from "./pages/LandingPage";

const TOKEN_KEY = "ib_token";
const EMAIL_KEY = "ib_email";

function Nav({ tab, setTab, email, onLogout, role, orgName }) {
  let tabs = [];

  if (role === "SUPER_ADMIN") {
    tabs = [
      { id: "dashboard", label: "Dashboard" },
      { id: "create-org", label: "Create Organization" },
      { id: "profile", label: "Profile" },
    ];
  }

  if (role === "ORG_ADMIN") {
    tabs = [
      { id: "dashboard", label: "Dashboard" },
      { id: "hrs", label: "HR Management" },
      { id: "jobs", label: "Job Openings" },
      { id: "candidates", label: "Candidates" },
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
          width: "100%",
          padding: "0 24px",
          height: 88,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 32 }}>
          <span style={{ fontWeight: 800, fontSize: 34, letterSpacing: "-.04em", color: "var(--primary)" }}>
            Belvio
          </span>
          <div style={{ display: "flex", gap: 4 }}>
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                style={{
                  border: "none",
                  padding: "10px 18px",
                  borderRadius: 8,
                  cursor: "pointer",
                  fontSize: 16,
                  fontWeight: tab === t.id ? 700 : 600,
                  color: tab === t.id ? "var(--primary)" : "var(--text-secondary)",
                  background: tab === t.id ? "rgba(37, 99, 235, 0.1)" : "transparent",
                  transition: "all 0.2s"
                }}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
        
        <div className="profile-menu" style={{ position: "relative", display: "inline-block" }}>
          <button className="btn-ghost flex-row" style={{ padding: "8px 18px 8px 10px", borderRadius: 999, border: "1px solid var(--border)", background: "var(--surface)" }}>
            <div style={{ width: 32, height: 32, borderRadius: "50%", background: "var(--primary)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: "bold", fontSize: 16 }}>
              {email?.[0]?.toUpperCase() || "U"}
            </div>
            <span style={{ fontWeight: 700, fontSize: 15, marginLeft: 4 }}>
              {orgName || role?.replace("_", " ")}
            </span>
            <span style={{ fontSize: 11, marginLeft: 6, color: "var(--text-secondary)" }}>▼</span>
          </button>

          <div className="profile-dropdown" style={{
             position: "absolute",
             top: "100%", right: 0,
             marginTop: 8,
             background: "var(--surface)",
             border: "1px solid var(--border)",
             borderRadius: 12,
             boxShadow: "var(--shadow)",
             padding: "16px",
             minWidth: 200,
             flexDirection: "column",
             gap: 12,
             zIndex: 100
          }}>
             <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
               <span style={{ fontSize: 14, fontWeight: 600 }}>{email}</span>
               <span style={{ fontSize: 12, color: "var(--text-secondary)", textTransform: "uppercase", fontWeight: 500 }}>{role?.replace("_", " ")}</span>
               {orgName && <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{orgName}</span>}
             </div>
             <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "4px 0" }} />
             {role === "ORG_ADMIN" && (
               <button className="btn-secondary btn-sm" onClick={() => setTab("settings")} style={{ width: "100%", marginBottom: "4px" }}>
                 Settings
               </button>
             )}
             <button className="btn-secondary btn-sm" onClick={onLogout} style={{ width: "100%" }}>
               Sign out
             </button>
          </div>
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
  const [orgName, setOrgName] = useState("");
  const [loadingUser, setLoadingUser] = useState(true);
  const [tab, setTab] = useState("dashboard");
  const [reportSessionId, setReportSessionId] = useState(null);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedJobName, setSelectedJobName] = useState("");
  const [showLogin, setShowLogin] = useState(false);

  function openJob(jobId, jobName) {
    setSelectedJobId(jobId);
    setSelectedJobName(jobName);
    setTab("job-details");
  }

  useEffect(() => {
    if (!token) {
      setLoadingUser(false);
      return;
    }

    setAuthToken(token);

    API.get("/api/whoami")
      .then((res) => {
        setRole(res.data.role);
        setOrgName(res.data.organization_name);
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
    return (
      <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
        Loading Belvio...
      </div>
    );
  }

  if (!token) {
    if (showLogin) {
      return <Login onLogin={handleLogin} />;
    }
    return <LandingPage onLoginClick={() => setShowLogin(true)} />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <Nav
        tab={tab}
        setTab={setTab}
        email={email}
        onLogout={handleLogout}
        role={role}
        orgName={orgName}
      />
      
      <main style={{ flex: 1 }}>
        {tab === "dashboard" && role === "SUPER_ADMIN" && <SuperAdminDashboard />}
        {tab === "create-org" && role === "SUPER_ADMIN" && <CreateOrganization />}
        {tab === "profile" && role === "SUPER_ADMIN" && <SuperAdminProfile />}
        
        {tab === "dashboard" && role === "ORG_ADMIN" && <OrgAdminDashboard onNavigate={setTab} />}
        {tab === "settings" && role === "ORG_ADMIN" && <OrgSettings />}

        {tab === "dashboard" && role === "HR" && <HRDashboard onOpenJob={openJob} />}
        {tab === "jobs" && <JobOpenings onOpenJob={openJob} />}
        {tab === "hrs" && <HRManagement />}
        {tab === "candidates" && <Candidates role={role} />}
        {tab === "interviews" && <Interviews onViewReport={openReport} />}
        {tab === "job-details" && <JobDetails jobId={selectedJobId} jobName={selectedJobName} role={role} />}
        
        {tab === "sessions" && (
          <Sessions token={token} onViewReport={openReport} />
        )}
        {tab === "reports" && (
          <Reports token={token} defaultSessionId={reportSessionId} />
        )}
      </main>

      <footer style={{ textAlign: "center", padding: "24px", background: "var(--surface)", borderTop: "1px solid var(--border)", width: "100%" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, fontSize: 14, color: "var(--text-secondary)", fontWeight: 500 }}>
          <span>Powered by</span>
          <img src="/bellurbis-logo.png" alt="Bellurbis" style={{ height: 44, filter: "brightness(0)", opacity: 0.8 }} />
        </div>
      </footer>
    </div>
  );
}

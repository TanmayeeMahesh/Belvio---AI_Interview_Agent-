import { useState } from "react";
import API from "../api";

export default function Login({ onLogin }) {
  const [step, setStep] = useState("email"); // "email", "password", "set_password"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleCheckEmail(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await API.post("/api/auth/check-email", { email });
      if (data.status === "PENDING") {
        setStep("set_password");
      } else {
        setStep("password");
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Email not found.");
    }
    setLoading(false);
  }

  async function handleLogin(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { data } = await API.post("/api/auth/login", { email, password });
      onLogin(data.token, data.email);
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed.");
    }
    setLoading(false);
  }

  async function handleCreatePassword(e) {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await API.post("/api/auth/complete-registration", { email, password });
      const { data } = await API.post("/api/auth/login", { email, password });
      onLogin(data.token, data.email);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to set password.");
    }
    setLoading(false);
  }

  const inputStyle = {
    background: "rgba(255, 255, 255, 0.1)",
    color: "#fff",
    border: "1px solid rgba(255, 255, 255, 0.2)",
  };

  return (
    <div 
      style={{ 
        display: "flex", 
        minHeight: "100vh", 
        alignItems: "center", 
        justifyContent: "center",
        position: "relative",
        padding: 24,
        overflow: "hidden"
      }}
    >
      {/* Background Image & Overlay */}
      <div style={{
        position: "absolute",
        inset: 0,
        backgroundImage: "url('/ai_interview_bot_bg.png')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        zIndex: 0
      }} />
      <div style={{
        position: "absolute",
        inset: 0,
        background: "linear-gradient(135deg, rgba(15, 23, 42, 0.7), rgba(37, 99, 235, 0.5))",
        zIndex: 1,
      }} />

      {/* Center Floating Glass Card */}
      <div 
        style={{
          position: "relative",
          zIndex: 2,
          width: "100%",
          maxWidth: 600,
          background: "rgba(255, 255, 255, 0.15)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          border: "1px solid rgba(255, 255, 255, 0.3)",
          borderRadius: 24,
          padding: "56px 64px",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.3)",
          display: "flex",
          flexDirection: "column",
          gap: 32,
          color: "#fff"
        }}
      >
        {/* Header / Product Info */}
        <div style={{ textAlign: "center" }}>
          <h1 style={{ fontSize: 28, fontFamily: "var(--font-heading)", fontWeight: 700, margin: 0, color: "#fff", letterSpacing: "-0.02em" }}>
            Belvio - The AI Interview Agent
          </h1>
          <p style={{ fontSize: 14, marginTop: 12, color: "#fff", lineHeight: 1.5, opacity: 0.9 }}>
            The intelligent interviewing assistant that autonomously conducts, evaluates, and scores candidate interviews with human-like precision.
          </p>
        </div>

        {/* Login / Registration Flow */}
        {step === "email" && (
          <form onSubmit={handleCheckEmail} className="gap-20">
            <div>
              <label style={{ color: "#fff", opacity: 0.9 }}>Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                style={inputStyle}
              />
            </div>
            {error && <div style={{ color: "#f87171", fontSize: 14 }}>{error}</div>}
            <button type="submit" className="btn-primary" disabled={loading} style={{ width: "100%", justifyContent: "center" }}>
              {loading ? "Checking..." : "Continue"}
            </button>
          </form>
        )}

        {step === "password" && (
          <form onSubmit={handleLogin} className="gap-20">
            <div>
              <label style={{ color: "#fff", opacity: 0.9 }}>Welcome back, {email}</label>
              <button 
                type="button" 
                onClick={() => setStep("email")}
                style={{ background: "none", border: "none", color: "#60a5fa", cursor: "pointer", fontSize: 12, padding: 0, marginTop: 4, display: "block" }}
              >
                Not you? Change email
              </button>
            </div>
            <div>
              <label style={{ color: "#fff", opacity: 0.9 }}>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={inputStyle}
              />
            </div>
            {error && <div style={{ color: "#f87171", fontSize: 14 }}>{error}</div>}
            <button type="submit" className="btn-primary" disabled={loading} style={{ width: "100%", justifyContent: "center" }}>
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>
        )}

        {step === "set_password" && (
          <form onSubmit={handleCreatePassword} className="gap-20">
            <div>
              <label style={{ color: "#fff", opacity: 0.9 }}>Set your password</label>
              <p style={{ fontSize: 13, color: "rgba(255,255,255,0.7)", margin: "4px 0 16px" }}>
                Looks like it's your first time logging in! Please set a password for {email}.
              </p>
            </div>
            <div>
              <label style={{ color: "#fff", opacity: 0.9 }}>New Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={inputStyle}
              />
            </div>
            <div>
              <label style={{ color: "#fff", opacity: 0.9 }}>Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={inputStyle}
              />
            </div>
            {error && <div style={{ color: "#f87171", fontSize: 14 }}>{error}</div>}
            <button type="submit" className="btn-primary" disabled={loading} style={{ width: "100%", justifyContent: "center" }}>
              {loading ? "Saving..." : "Save Password & Sign In"}
            </button>
          </form>
        )}

        <div className="divider" style={{ margin: "8px 0", borderColor: "rgba(255, 255, 255, 0.2)" }} />

        {/* Bellurbis Footer */}
        <div style={{ textAlign: "center" }}>
          <h3 style={{ margin: 0, color: "#fff", fontSize: 13, fontFamily: "var(--font-heading)" }}>
            About the application
          </h3>
          <p style={{ fontSize: 12, color: "#fff", opacity: 0.8, marginTop: 4, margin: 0 }}>
            Powered by Bellurbis organization.
          </p>
          <p style={{ fontSize: 12, color: "#fff", opacity: 0.7, marginTop: 8, margin: 0 }}>
            Contact <strong>Bellurbis Technologies</strong> for more information.
          </p>
        </div>
      </div>
    </div>
  );
}

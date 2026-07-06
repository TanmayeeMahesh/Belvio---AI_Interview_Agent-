import React from "react";

export default function HeroSection({ onLoginClick }) {
  return (
    <header style={{ position: "relative", padding: "120px 24px", textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
      <div style={{
        position: "absolute",
        inset: 0,
        backgroundImage: "url('/ai_interview_bot_bg.png')",
        backgroundSize: "cover",
        backgroundPosition: "center",
        opacity: 0.2,
        zIndex: 0
      }} />
      <div style={{
        position: "absolute",
        inset: 0,
        
        zIndex: 1
      }} />
      
      <div style={{ position: "relative", zIndex: 2, maxWidth: 900 }}>
        <h1 style={{ fontSize: 56, fontWeight: 800, lineHeight: 1.1, marginBottom: 24, letterSpacing: "-0.03em" }}>
          AI Interviews. Smarter Hiring. <br/> <span style={{ color: "var(--accent)" }}>Better Decisions.</span>
        </h1>
        <p style={{ fontSize: 20, color: "rgba(255,255,255,0.8)", marginBottom: 40, lineHeight: 1.6, maxWidth: 700, margin: "0 auto 40px" }}>
          Automate technical interviews, evaluate candidates with AI, and help recruiters hire faster with confidence.
        </p>
        <div style={{ display: "flex", gap: 16, justifyContent: "center" }}>
          <button onClick={onLoginClick} style={{ background: "var(--primary)", color: "#fff", border: "none", padding: "16px 32px", borderRadius: 12, fontSize: 16, fontWeight: 600, boxShadow: "0 10px 25px -5px rgba(37, 99, 235, 0.5)" }}>
            Get Started
          </button>
          <button onClick={onLoginClick} style={{ background: "rgba(255,255,255,0.1)", color: "#fff", border: "1px solid rgba(255,255,255,0.2)", padding: "16px 32px", borderRadius: 12, fontSize: 16, fontWeight: 600, backdropFilter: "blur(8px)" }}>
            Login
          </button>
          <button onClick={onLoginClick} style={{ background: "transparent", color: "#fff", border: "1px solid transparent", padding: "16px 32px", borderRadius: 12, fontSize: 16, fontWeight: 600, textDecoration: "underline" }}>
            Request Demo
          </button>
        </div>
      </div>
    </header>
  );
}

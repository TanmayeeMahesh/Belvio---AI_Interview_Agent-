import { useEffect, useState } from "react";
import API from "../api";

export default function Interviews() {
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    loadSessions();

    const interval = setInterval(() => {
      loadSessions();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  async function loadSessions() {
    const { data } = await API.get("/api/interviews");

    console.log("FIRST INTERVIEW =", data[0]);

    setSessions(data);
  }

  console.log("SESSIONS STATE =", sessions);
  return (
    <div style={{ padding: 24 }}>
      <h1>Interviews</h1>

      <h3>Total Interviews: {sessions.length}</h3>

      {sessions.map((s) => (
        <div
          key={s.id}
          style={{
            border: "1px solid black",
            padding: 10,
            marginBottom: 10,
          }}
        >
          <div>Name: {s.candidate_name}</div>
          <div>Email: {s.candidate_email}</div>
          <div>Role: {s.role}</div>
          <div>
            Meeting:{" "}
            <a href={s.meeting_url} target="_blank" rel="noreferrer">
              Open Meeting
            </a>
          </div>
          <div>
            Status:
            <span
              style={{
                marginLeft: 8,
                padding: "4px 10px",
                borderRadius: 12,
                background:
                  s.status === "completed"
                    ? "#dcfce7"
                    : s.status === "scheduled"
                      ? "#fef3c7"
                      : s.status?.includes("incomplete")
                        ? "#fee2e2"
                        : "#dbeafe",
              }}
            >
              {s.status}
            </span>
          </div>
          <div>
            Scheduled:{" "}
            {s.scheduled_for ? new Date(s.scheduled_for).toLocaleString() : "-"}
          </div>
          {s.status === "completed" && (
            <button
              onClick={async () => {
                try {
                  const { data } = await API.get(
                    `/api/hr/report/${s.session_id || s.id}`,
                  );

                  console.log("REPORT =", data);
                } catch (err) {
                  console.error(err);
                }
              }}
            >
              View Report
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

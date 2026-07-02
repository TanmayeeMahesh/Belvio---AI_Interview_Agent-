import { useEffect, useState } from "react";
import API from "../api";

export default function Candidates() {
  const [candidates, setCandidates] = useState([]);
  const [jobs, setJobs] = useState([]);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [jobId, setJobId] = useState("");

  useEffect(() => {
    loadCandidates();
    loadJobs();
  }, []);

  async function loadCandidates() {
    const { data } = await API.get("/api/candidates");
    setCandidates(data);
  }

  async function loadJobs() {
    const { data } = await API.get("/api/job-openings");
    setJobs(data);
  }

  async function createCandidate() {
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

    loadCandidates();
  }

  return (
    <div style={{ padding: 24 }}>
      <h1>Candidates</h1>

      <div style={{ marginBottom: 20 }}>
        <input
          placeholder="Candidate Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <input
          placeholder="Candidate Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <select value={jobId} onChange={(e) => setJobId(e.target.value)}>
          <option value="">Select Job</option>

          {jobs.map((job) => (
            <option key={job.id} value={job.id}>
              {job.title}
            </option>
          ))}
        </select>

        <button onClick={createCandidate}>Create Candidate</button>
      </div>

      <table style={{ width: "100%" }}>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
          </tr>
        </thead>

        <tbody>
          {candidates.map((c) => (
            <tr key={c.id}>
              <td>{c.name}</td>
              <td>{c.email}</td>
              <td>{c.role}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

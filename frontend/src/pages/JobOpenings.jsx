import { useEffect, useState } from "react";
import API from "../api";

export default function JobOpenings({ onOpenJob }) {
  const [jobs, setJobs] = useState([]);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [jdText, setJdText] = useState("");

  useEffect(() => {
    API.get("/api/job-openings")
      .then((res) => {
        setJobs(res.data);
      })
      .catch(console.error);
  }, []);

  async function createJob() {
    try {
      const { data } = await API.post("/api/job-openings", {
        title,
        description,
        jd_text: jdText,
      });

      setJobs([...jobs, data]);

      setTitle("");
      setDescription("");
      setJdText("");
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <h1>Job Openings</h1>
      <div
        style={{
          marginTop: 20,
          marginBottom: 30,
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <input
          placeholder="Job Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />

        <input
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        <textarea
          placeholder="JD Text"
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
        />

        <button onClick={createJob}>Create Job Opening</button>
      </div>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          marginTop: 20,
        }}
      >
        <thead>
          <tr>
            <th>Title</th>
            <th>Status</th>
            <th>Description</th>
          </tr>
        </thead>

        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td>
                <button onClick={() => onOpenJob(job.id)}>{job.title}</button>
              </td>
              <td>{job.status}</td>
              <td>{job.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

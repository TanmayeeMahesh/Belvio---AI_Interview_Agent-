import { useEffect, useState } from "react";
import API from "../api";

export default function JobDetails({ jobId }) {
  const [candidates, setCandidates] = useState([]);
  const [resume, setResume] = useState(null);
  const [scheduleData, setScheduleData] = useState({});
  const [loadingCandidate, setLoadingCandidate] = useState({});

  useEffect(() => {
    loadCandidates();
  }, [jobId]);

  async function createCandidate() {
    try {
      const formData = new FormData();

      formData.append("resume", resume);
      formData.append("job_opening_id", jobId);

      await API.post("/api/candidates/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      alert("Candidate added successfully");

      loadCandidates();
    } catch (err) {
      console.error(err);
    }
  }

  async function loadCandidates() {
    try {
      const { data } = await API.get(`/api/job-openings/${jobId}/candidates`);

      setCandidates(data);
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <h1>Job Candidates</h1>

      <div style={{ marginBottom: 20 }}>
        <h3>Add Candidate</h3>

        <input
          type="file"
          accept=".pdf,.doc,.docx"
          onChange={(e) => setResume(e.target.files[0])}
        />

        <button onClick={createCandidate}>Add Candidate</button>
      </div>

      <table style={{ width: "100%" }}>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Action</th>
          </tr>
        </thead>

        <tbody>
          {candidates.map((c) => (
            <tr key={c.id}>
              <td>{c.name}</td>
              <td>{c.email}</td>
              <td>{c.role}</td>

              <td>
                <input
                  placeholder="Meet Link"
                  value={scheduleData[c.id]?.meeting_url || ""}
                  onChange={(e) =>
                    setScheduleData({
                      ...scheduleData,
                      [c.id]: {
                        ...scheduleData[c.id],
                        meeting_url: e.target.value,
                      },
                    })
                  }
                />

                <input
                  type="number"
                  placeholder="Questions"
                  value={scheduleData[c.id]?.question_count || 12}
                  onChange={(e) =>
                    setScheduleData({
                      ...scheduleData,
                      [c.id]: {
                        ...scheduleData[c.id],
                        question_count: Number(e.target.value),
                      },
                    })
                  }
                />

                <input
                  type="number"
                  placeholder="Delay"
                  value={scheduleData[c.id]?.delay_minutes || 30}
                  onChange={(e) =>
                    setScheduleData({
                      ...scheduleData,
                      [c.id]: {
                        ...scheduleData[c.id],
                        delay_minutes: Number(e.target.value),
                      },
                    })
                  }
                />

                <button
                  disabled={loadingCandidate[c.id]}
                  onClick={async () => {
                    try {
                      setLoadingCandidate({
                        ...loadingCandidate,
                        [c.id]: true,
                      });
                      console.log(scheduleData);
                      console.log(scheduleData[c.id]);
                      if (!scheduleData[c.id]?.meeting_url) {
                        alert("Please enter meeting link");
                        return;
                      }
                      await API.post(`/api/candidate/${c.id}/schedule`, {
                        meeting_url: scheduleData[c.id]?.meeting_url || "",
                        question_count:
                          scheduleData[c.id]?.question_count || 12,
                        delay_minutes: scheduleData[c.id]?.delay_minutes || 30,
                      });

                      alert("Interview Scheduled Successfully");
                      loadCandidates();
                    } catch (err) {
                      console.error(err);

                      alert(err.response?.data?.detail || "Scheduling Failed");
                    } finally {
                      setLoadingCandidate({
                        ...loadingCandidate,
                        [c.id]: false,
                      });
                    }
                  }}
                >
                  {loadingCandidate[c.id]
                    ? "Scheduling..."
                    : "Schedule Interview"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

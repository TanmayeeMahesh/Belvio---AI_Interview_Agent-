import { useEffect, useState } from "react";
import API from "../api";

export default function HRManagement() {
  const [hrs, setHrs] = useState([]);
  const [email, setEmail] = useState("");

  useEffect(() => {
    loadHRs();
  }, []);

  async function loadHRs() {
    const { data } = await API.get("/api/org-admin/hrs");
    setHrs(data);
  }

  async function createHR() {
    try {
      await API.post("/api/org-admin/create-hr", {
        email,
      });

      setEmail("");
      loadHRs();
    } catch (err) {
      console.error(err);
    }
  }

  async function deleteHR(userId) {
    try {
      await API.delete(`/api/org-admin/hr/${userId}`);
      loadHRs();
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <h1>HR Management</h1>

      <div style={{ marginBottom: 20 }}>
        <input
          placeholder="hr@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <button onClick={createHR}>Create HR</button>
      </div>

      <table style={{ width: "100%" }}>
        <thead>
          <tr>
            <th>Email</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>

        <tbody>
          {hrs.map((hr) => {
            console.log("HR =", hr);

            return (
              <tr key={hr.id}>
                <td>{hr.email}</td>
                <td>{hr.status}</td>
                <td>
                  <button onClick={() => deleteHR(hr.id)}>Delete</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

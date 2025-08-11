import React, { useState } from "react";
import axios from "axios";

const API_URL = "http://127.0.0.1:8000/process_resume/";

function ResumeForm() {
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState("SDE");
  const [minScore, setMinScore] = useState(80);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      alert("Please upload a resume file.");
      return;
    }
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("resume_file", file);
    formData.append("job_description", jobDescription);
    formData.append("min_score_for_interview", minScore);

    try {
      const response = await axios.post(API_URL, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(response.data);
    } catch (error) {
      setResult({ error: error.response?.data?.detail || "Error processing resume." });
    }
    setLoading(false);
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>Resume (PDF/DOCX/TXT): </label>
        <input type="file" accept=".pdf,.docx,.txt" onChange={e => setFile(e.target.files[0])} />
      </div>
      <div>
        <label>Job Description: </label>
        <input value={jobDescription} onChange={e => setJobDescription(e.target.value)} />
      </div>
      <div>
        <label>Minimum Suitability Score: </label>
        <input type="number" value={minScore} onChange={e => setMinScore(e.target.value)} min={0} max={100} />
      </div>
      <button type="submit" disabled={loading} style={{ marginTop: 10 }}>
        {loading ? "Processing..." : "Submit"}
      </button>
      {result && (
        <div style={{ marginTop: 20, background: "#f8f9fa", padding: 15, borderRadius: 8 }}>
          {result.error ? (
            <div style={{ color: "red" }}>{result.error}</div>
          ) : (
            <>
              <div><b>Suitability Score:</b> {result.suitability_score}</div>
              <div><b>Explanation:</b> <pre style={{ whiteSpace: "pre-wrap" }}>{result.screening_result}</pre></div>
              <div><b>Email Status:</b> {result.email_sending_status}</div>
            </>
          )}
        </div>
      )}
    </form>
  );
}

export default ResumeForm;
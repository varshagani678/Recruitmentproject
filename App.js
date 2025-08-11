import React from "react";
import ResumeForm from "./components/ResumeForm";

function App() {
  return (
    <div style={{ maxWidth: 600, margin: "40px auto", fontFamily: "Arial" }}>
      <h2>CrewAI Resume Screening</h2>
      <ResumeForm />
    </div>
  );
}

export default App;
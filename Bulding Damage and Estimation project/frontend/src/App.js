import React, { useState } from "react";
import axios from "axios";
import { FaMoon, FaSun, FaDownload, FaCommentDots } from "react-icons/fa";
import { motion } from "framer-motion";
import WeatherPanel from "./WeatherPanel";
import Chatbot from "./Chatbot";
import "./neon.css";

function App() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [inspection, setInspection] = useState(null);
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(true);
  const [isChatOpen, setIsChatOpen] = useState(false);

  // Theme Constants
  const theme = {
    bg: darkMode
      ? "linear-gradient(180deg, #0b0f1a 0%, #071026 50%, #05030a 100%)"
      : "linear-gradient(180deg, #f0f4f8 0%, #e2e8f0 100%)",
    text: darkMode ? "#dbeafe" : "#1e293b",
    cardBg: darkMode ? "rgba(255,255,255,0.02)" : "rgba(255,255,255,0.8)",
    cardBorder: darkMode ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.05)",
    heading: darkMode ? "#e6f7ff" : "#0f172a",
    subtext: darkMode ? "#9fb7d8" : "#64748b",
    navBg: darkMode ? "rgba(255,255,255,0.02)" : "rgba(255,255,255,0.7)",
    shadow: darkMode ? "0 10px 40px rgba(2,6,23,0.5)" : "0 10px 30px rgba(0,0,0,0.05)"
  };

  const upload = async () => {
    if (!file) return alert("Choose an image first");
    const form = new FormData();
    form.append("file", file);
    setLoading(true);
    try {
      const res = await axios.post(
        "http://127.0.0.1:8000/api/inspect/upload",
        form,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setInspection(res.data.inspection);
    } catch (err) {
      console.error(err);
      alert("Upload failed: " + (err.response ? err.response.data.detail : err.message));
    } finally {
      setLoading(false);
    }
  };

  const downloadReport = (type) => {
    if (!inspection?.inspection_id) return alert("No inspection to download");
    const id = inspection.inspection_id;
    const url = `http://127.0.0.1:8000/api/report/${type}/${id}`;

    // Create temporary link to force download
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `${type}_report_${id}.pdf`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div
      style={{
        height: "100vh",
        width: "100vw",
        overflow: "hidden",
        background: theme.bg,
        color: theme.text,
        fontFamily: "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial",
        display: "flex",
        flexDirection: "column",
        padding: 20,
        boxSizing: "border-box"
      }}
    >
      {/* NAVBAR */}
      <div
        style={{
          flex: "0 0 auto",
          display: "flex",
          gap: 20,
          alignItems: "center",
          justifyContent: "space-between",
          padding: "15px 28px",
          borderRadius: 14,
          background: theme.navBg,
          boxShadow: theme.shadow,
          backdropFilter: "blur(10px)",
          marginBottom: 20,
          border: `1px solid ${theme.cardBorder}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div
            style={{
              fontSize: 32,
              padding: 6,
              borderRadius: 10,
              background: "linear-gradient(135deg, rgba(58,117,255,0.1), rgba(142,45,226,0.1))",
              color: "#9be2ff",
            }}
          >
            🏗
          </div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: theme.heading }}>
              BuildSenseAI
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button
            onClick={() => setDarkMode(!darkMode)}
            style={{
              border: `1px solid ${theme.cardBorder}`,
              padding: 8,
              borderRadius: 10,
              background: theme.cardBg,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center"
            }}
          >
            {darkMode ? <FaSun color="#ffd86b" /> : <FaMoon color="#64748b" />}
          </button>
        </div>
      </div>

      {/* MAIN CONTENT GRID */}
      <div style={{
        flex: 1,
        display: "grid",
        gridTemplateColumns: isChatOpen ? "300px 1fr 350px" : "300px 1fr",
        gridTemplateRows: "1fr",
        gap: 20,
        overflow: "hidden",
        transition: "grid-template-columns 0.3s ease"
      }}>

        {/* LEFT COLUMN: Weather & Info */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20, overflowY: "auto" }}>
          <WeatherPanel darkMode={darkMode} />

          <div style={{
            padding: 20,
            borderRadius: 16,
            background: theme.cardBg,
            border: `1px solid ${theme.cardBorder}`,
            backdropFilter: "blur(8px)",
          }}>
            <h3 style={{ margin: "0 0 10px", color: theme.heading }}>About</h3>
            <p style={{ fontSize: 13, color: theme.subtext, lineHeight: 1.5 }}>
              Upload building images to detect structural damage using AI. Get instant reports and repair estimates.
            </p>
          </div>
        </div>

        {/* MIDDLE COLUMN: Analysis */}
        <div style={{
          display: "flex",
          flexDirection: "column",
          borderRadius: 16,
          background: theme.cardBg,
          border: `1px solid ${theme.cardBorder}`,
          backdropFilter: "blur(8px)",
          padding: 24,
          overflowY: "auto",
          boxShadow: theme.shadow
        }}>
          <h2 style={{ margin: "0 0 20px", color: theme.heading }}>Damage Analysis</h2>

          <label
            htmlFor="file"
            style={{
              display: "block",
              padding: "20px",
              borderRadius: 12,
              marginBottom: 20,
              border: `2px dashed ${darkMode ? "rgba(155,200,255,0.1)" : "rgba(0,0,0,0.1)"}`,
              background: darkMode ? "rgba(255,255,255,0.01)" : "rgba(0,0,0,0.02)",
              cursor: "pointer",
              transition: "all 0.2s"
            }}
          >
            <input
              id="file"
              type="file"
              accept="image/*"
              onChange={(e) => {
                const f = e.target.files[0];
                setFile(f);
                setPreview(f ? URL.createObjectURL(f) : null);
              }}
              style={{ display: "none" }}
            />
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 40, marginBottom: 10 }}>📤</div>
              <div style={{ fontWeight: 600, color: theme.heading }}>Click to Upload Image</div>
              <div style={{ fontSize: 13, color: theme.subtext }}>or drag and drop</div>
            </div>
          </label>

          {preview && (
            <div style={{
              marginBottom: 20,
              borderRadius: 12,
              overflow: "hidden",
              border: `1px solid ${theme.cardBorder}`,
              maxHeight: "300px",
              display: "flex",
              justifyContent: "center",
              background: "#000"
            }}>
              <img src={preview} alt="preview" style={{ height: "100%", objectFit: "contain" }} />
            </div>
          )}

          <button
            onClick={upload}
            disabled={!file || loading}
            style={{
              width: "100%",
              padding: "14px",
              borderRadius: 12,
              border: "none",
              fontWeight: 700,
              color: "white",
              background: loading ? "#ccc" : "linear-gradient(90deg,#39a2ff,#8e2de2)",
              cursor: loading ? "default" : "pointer",
              marginBottom: 20,
              opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? "Analyzing..." : "Analyze Image"}
          </button>

          {inspection && (
            <div style={{ marginTop: "auto" }}>
              <h3 style={{ margin: "0 0 15px", color: theme.heading }}>Results</h3>
              <div style={{ display: "grid", gap: 10, marginBottom: 20 }}>
                <ResultRow label="Damage Type" value={inspection.result?.damage_type} theme={theme} />
                <ResultRow label="Severity" value={inspection.result?.severity} theme={theme} />
                <div style={{ display: "flex", flexDirection: "column", gap: 4, padding: "8px 0", borderBottom: `1px solid ${theme.cardBorder}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: theme.subtext }}>Confidence</span>
                    <span style={{ fontWeight: 600, color: theme.heading }}>{inspection.result?.confidence}</span>
                  </div>
                  {inspection.result?.confidence_explanation && (
                    <span style={{ fontSize: 11, color: theme.subtext, fontStyle: "italic" }}>
                      {inspection.result.confidence_explanation[0]}
                    </span>
                  )}
                </div>
                <div style={{ padding: "8px 0", fontSize: 11, color: theme.subtext }}>
                  * All results are image-based estimates only.
                </div>
              </div>

              <div style={{ display: "flex", gap: 10 }}>
                <button onClick={() => downloadReport("remedy")} style={accentBtn}>
                  <FaDownload style={{ marginRight: 8 }} /> Repair Estimation
                </button>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Chatbot */}
        {isChatOpen && (
          <div style={{ height: "100%", overflow: "hidden", maxHeight: "100%" }}>
            <Chatbot darkMode={darkMode} />
          </div>
        )}

      </div>

      {/* Floating Chat Button */}
      <button
        onClick={() => setIsChatOpen(!isChatOpen)}
        style={{
          position: "fixed",
          bottom: 30,
          right: 30,
          width: 60,
          height: 60,
          borderRadius: "50%",
          background: "linear-gradient(135deg, #39a2ff, #8e2de2)",
          color: "white",
          border: "none",
          boxShadow: "0 10px 30px rgba(57, 162, 255, 0.4)",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 24,
          zIndex: 1000,
          transition: "transform 0.2s"
        }}
        onMouseEnter={(e) => e.currentTarget.style.transform = "scale(1.1)"}
        onMouseLeave={(e) => e.currentTarget.style.transform = "scale(1)"}
      >
        <FaCommentDots />
      </button>
    </div>
  );
}

const ResultRow = ({ label, value, theme }) => (
  <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: `1px solid ${theme.cardBorder}` }}>
    <span style={{ color: theme.subtext }}>{label}</span>
    <span style={{ fontWeight: 600, color: theme.heading }}>{value ?? "N/A"}</span>
  </div>
);

const ghostBtn = (theme) => ({
  flex: 1,
  padding: "12px",
  borderRadius: 10,
  background: "transparent",
  border: `1px solid ${theme.cardBorder}`,
  color: theme.heading,
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontWeight: 600
});

const accentBtn = {
  flex: 1,
  padding: "12px",
  borderRadius: 10,
  background: "linear-gradient(90deg,#39a2ff,#8e2de2)",
  color: "white",
  border: "none",
  cursor: "pointer",
  fontWeight: 600
};

export default App;

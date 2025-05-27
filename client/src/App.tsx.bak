import React from "react";
import barChartImg from "./assets/graph.png";
import lineChartImg from "./assets/bar_charts.jpg";

const agentList = [
  "Nifi Agents", "DBx Agents", "Confluence Agents", "AWS Agents",
  "RDS Agents", "Alteryx Agents", "Qlik Agents", "Thoughtspot Agents"
];

const rightPanelItems = [
  "Conversation Settings",
  "Agent Priorities",
  "Execution Plan",
  "Connected Sources"
];

const App: React.FC = () => (
  <div style={{ height: "100vh", display: "flex", flexDirection: "column", fontFamily: "Arial, sans-serif", background: "#f9f9f9" }}>
    {/* Header */}
    <header style={{ background: "#163452", color: "white", padding: "1.2rem 0 1.2rem 2rem", fontSize: "1.5rem", letterSpacing: 1 }}>
      CCB - Consumer Analytics and Reporting Infrastructure
    </header>

    {/* Main Section */}
    <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
      {/* Left Sidebar */}
      <aside style={{ width: 220, minWidth: 180, background: "#e6e9ed", padding: "1rem 0", borderRight: "2px solid #bfc5c9", display: "flex", flexDirection: "column", gap: "0.7rem" }}>
        {/* Add Agents / Add Tools */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", margin: "0 1rem 0.7rem 1rem" }}>
          <button style={{ fontWeight: "bold", border: "2px solid #222", background: "#fff", borderRadius: 2, padding: "0.3rem 0.8rem" }}>Add Agents</button>
          <button style={{ fontWeight: "bold", border: "2px solid #222", background: "#fff", borderRadius: 2, padding: "0.3rem 0.8rem" }}>Add Tools</button>
        </div>
        {/* Agent List */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.7rem" }}>
          {agentList.map(agent => (
            <div key={agent} style={{ background: "#fff", border: "2px solid #222", fontWeight: "bold", margin: "0 1rem", padding: "0.5rem 0.7rem", borderRadius: "4px" }}>
              {agent}
            </div>
          ))}
        </div>
      </aside>

      {/* Center Content */}
      <main style={{ flex: 1, padding: "1rem 0.5rem", display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Top Controls - right justified */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.7rem", justifyContent: "flex-end" }}>
          <button style={{ background: "#1b88c2", color: "#fff", fontWeight: "bold", border: "2px solid #222", borderRadius: 2, padding: "0.3rem 1rem" }}>+ NEW CHAT</button>
          <button style={{ fontWeight: "bold", border: "2px solid #222", background: "#fff", borderRadius: 2, padding: "0.3rem 1rem" }}>Conversation History</button>
          <div style={{ marginLeft: 15, fontSize: "0.9rem", color: "#666" }}>
            <span style={{ marginRight: 15 }}>Settings</span>
            <span>Documents</span>
          </div>
        </div>

        {/* Main Panels */}
        <div style={{ flex: 1, display: "flex", minHeight: 0, gap: "0.5rem" }}>
          {/* Center Panels */}
          <section style={{ flex: 3, display: "flex", flexDirection: "column", gap: "0.8rem" }}>
            {/* First Chart Panel (Bar Chart) */}
            <div style={{ background: "#fff", border: "2px solid #222", borderRadius: 5, minHeight: 320, padding: "0.7rem", position: "relative", display: "flex", flexDirection: "column" }}>
              {/* Bar Chart Image - fill area but keep aspect ratio */}
              <div style={{
                height: 260,
                width: "100%",
                background: "#e3eef8",
                borderRadius: 4,
                overflow: "hidden",
                marginBottom: "1rem",
                padding: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}>
                <img
                  src={barChartImg}
                  alt="Bar Chart"
                  style={{
                    maxWidth: "100%",
                    maxHeight: "100%",
                    width: "auto",
                    height: "auto",
                    objectFit: "contain",
                    display: "block"
                  }}
                />
              </div>
              <span style={{
                position: "absolute",
                left: 18,
                bottom: 10,
                background: "yellow",
                border: "2px solid #222",
                borderRadius: "15px",
                padding: "0.2rem 0.8rem",
                fontWeight: "bold",
                fontSize: "1rem"
              }}>Chat Session</span>
            </div>
            {/* Second Chart Panel (Line Chart) */}
            <div style={{ background: "#fff", border: "2px solid #222", borderRadius: 5, minHeight: 260, padding: "0.7rem", position: "relative", display: "flex", flexDirection: "column" }}>
              {/* Line Chart Image - fill area but keep aspect ratio */}
              <div style={{
                height: 200,
                width: "100%",
                background: "#e5fbe1",
                borderRadius: 4,
                overflow: "hidden",
                marginBottom: "1rem",
                padding: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}>
                <img
                  src={lineChartImg}
                  alt="Line Chart"
                  style={{
                    maxWidth: "100%",
                    maxHeight: "100%",
                    width: "auto",
                    height: "auto",
                    objectFit: "contain",
                    display: "block"
                  }}
                />
              </div>
              <span style={{
                position: "absolute",
                left: 18,
                bottom: 44,
                background: "yellow",
                border: "2px solid #222",
                borderRadius: "15px",
                padding: "0.2rem 0.8rem",
                fontWeight: "bold",
                fontSize: "1rem"
              }}>Chat Session</span>
              <span style={{
                position: "absolute",
                left: 18,
                bottom: 10,
                background: "yellow",
                border: "2px solid #222",
                borderRadius: "15px",
                padding: "0.2rem 0.8rem",
                fontWeight: "bold",
                fontSize: "1rem"
              }}>Chat Session</span>
            </div>
          </section>
          {/* Right Sidebar */}
          <aside style={{ width: 220, minWidth: 180, background: "#fff", display: "flex", flexDirection: "column", gap: "0.7rem" }}>
            {rightPanelItems.map(item => (
              <div key={item} style={{
                border: "2px solid #222",
                margin: "0.7rem 0.5rem 0 0.5rem",
                padding: "0.7rem 0.7rem",
                background: "#fff",
                fontWeight: "bold"
              }}>
                {item}
              </div>
            ))}
          </aside>
        </div>
      </main>
    </div>
  </div>
);

export default App;
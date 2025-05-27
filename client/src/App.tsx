import React, { useState } from "react";
import barChartImg from "./assets/graph.png";
import lineChartImg from "./assets/bar_charts.jpg";
import Button from '@mui/material/Button';
import ChatWindow from './components/ChatWindow';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';

const agentList = [
  "Nifi Agents", "DBx Agents", "Confluence Agents", "AWS Agents",
  "RDS Agents", "Alteryx Agents", "Qlik Agents", "Thoughtspot Agents"
];

const agentColors = [
  '#1877f2', // Nifi Agents - Facebook blue
  '#42b72a', // DBx Agents - green
  '#f7b928', // Confluence Agents - yellow
  '#ff5a5f', // AWS Agents - red
  '#8b5cf6', // RDS Agents - purple
  '#00bcd4', // Alteryx Agents - cyan
  '#ff9800', // Qlik Agents - orange
  '#34495e', // Thoughtspot Agents - dark blue
];

const rightPanelItems = [
  "Conversation Settings",
  "Agent Priorities",
  "Execution Plan",
  "Connected Sources"
];

const App: React.FC = () => {
  const [tabIndex, setTabIndex] = useState(0);
  const [sidebarWidth, setSidebarWidth] = useState(220);
  const [isResizing, setIsResizing] = useState(false);
  const [rightSidebarWidth, setRightSidebarWidth] = useState(220);
  const [isRightResizing, setIsRightResizing] = useState(false);

  // Mouse event handlers for resizing
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsResizing(true);
    e.preventDefault();
  };
  React.useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizing) {
        const newWidth = Math.max(160, Math.min(400, e.clientX));
        setSidebarWidth(newWidth);
      }
    };
    const handleMouseUp = () => setIsResizing(false);
    if (isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  // Mouse event handlers for right sidebar resizing
  const handleRightMouseDown = (e: React.MouseEvent) => {
    setIsRightResizing(true);
    e.preventDefault();
  };
  React.useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isRightResizing) {
        const windowWidth = window.innerWidth;
        const newWidth = Math.max(160, Math.min(400, windowWidth - e.clientX));
        setRightSidebarWidth(newWidth);
      }
    };
    const handleMouseUp = () => setIsRightResizing(false);
    if (isRightResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isRightResizing]);

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "#f9f9f9" }}>
      {/* Header */}
      <header style={{ background: "#163452", color: "white", padding: "1.2rem 0 1.2rem 2rem", fontSize: "1.5rem", letterSpacing: 1 }}>
        CCB - Consumer Analytics and Reporting Infrastructure
      </header>

      {/* Main Section */}
      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        {/* Left Sidebar with resizable pane */}
        <aside style={{ width: sidebarWidth, minWidth: 160, maxWidth: 400, background: "#e6e9ed", padding: "1rem 0", borderRight: "2px solid #bfc5c9", display: "flex", flexDirection: "column", gap: "0.7rem", position: 'relative' }}>
          {/* Add Agents / Add Tools */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", margin: "0 1rem 0.7rem 1rem" }}>
            <Button variant="contained" color="primary" fullWidth size="medium">Add Agents</Button>
            <Button variant="contained" color="primary" fullWidth size="medium">Add Tools</Button>
          </div>
          <Divider sx={{ margin: '0.5rem 0' }} />
          {/* Agent List - scrollable if needed */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", flex: 1, overflowY: 'auto', marginBottom: '1rem' }}>
            {agentList.map((agent, idx) => (
              <Button
                key={agent}
                variant="contained"
                fullWidth
                size="small"
                sx={{
                  backgroundColor: agentColors[idx],
                  color: '#fff',
                  fontWeight: 'bold',
                  border: '2px solid #222',
                  borderRadius: 2,
                  boxShadow: 'none',
                  '&:hover': {
                    backgroundColor: agentColors[idx],
                    opacity: 0.9,
                  },
                  textAlign: 'left',
                  minHeight: 32,
                  fontSize: '0.95rem',
                  padding: '0.2rem 0.7rem',
                }}
                onClick={() => {/* TODO: Show existing agent details */}}
              >
                {agent}
              </Button>
            ))}
          </div>
          {/* Resizer handle */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              right: -5,
              width: 10,
              height: '100%',
              cursor: 'col-resize',
              zIndex: 10,
            }}
            onMouseDown={handleMouseDown}
          />
        </aside>

        {/* Center Content */}
        <main style={{ flex: 1, padding: "1rem 0.5rem", display: "flex", flexDirection: "column", minWidth: 0 }}>
          {/* Top Controls - right justified */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.7rem", justifyContent: "flex-end" }}>
            <Button variant="contained" color="primary">+ NEW CHAT</Button>
            <Button variant="outlined" color="primary">Conversation History</Button>
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
                <ChatWindow placeholder="Ask about this bar chart..." />
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
                <ChatWindow placeholder="Ask about this line chart..." />
              </div>
            </section>

            {/* Right Sidebar with resizable pane */}
            <aside style={{ width: rightSidebarWidth, minWidth: 160, maxWidth: 400, background: "#fff", display: "flex", flexDirection: "column", gap: "0.7rem", position: 'relative' }}>
              <Box sx={{ width: '100%' }}>
                <Tabs
                  value={tabIndex}
                  onChange={(_, v) => setTabIndex(v)}
                  textColor="primary"
                  indicatorColor="primary"
                  variant="fullWidth"
                  sx={{ width: '100%' }}
                >
                  <Tab label="Settings" sx={{ flex: 1, minWidth: 0 }} />
                  <Tab label="Documents" sx={{ flex: 1, minWidth: 0 }} />
                </Tabs>
              </Box>
              {tabIndex === 0 && (
                rightPanelItems.map(item => (
                  <Button
                    key={item}
                    variant="contained"
                    fullWidth
                    sx={{
                      backgroundColor: '#e0e0e0',
                      color: '#222',
                      fontWeight: 'bold',
                      border: '2px solid #222',
                      borderRadius: 2,
                      boxShadow: 'none',
                      '&:hover': {
                        backgroundColor: '#bdbdbd',
                      },
                      margin: '0 0.5rem',
                      padding: '0.7rem 0.7rem',
                      textAlign: 'left',
                    }}
                    onClick={() => {/* TODO: Show panel details */}}
                  >
                    {item}
                  </Button>
                ))
              )}
              {tabIndex === 1 && (
                <Box sx={{ margin: '1rem', color: '#888', textAlign: 'center' }}>No documents.</Box>
              )}
              {/* Resizer handle for right sidebar */}
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: -5,
                  width: 10,
                  height: '100%',
                  cursor: 'col-resize',
                  zIndex: 10,
                }}
                onMouseDown={handleRightMouseDown}
              />
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
};

export default App;

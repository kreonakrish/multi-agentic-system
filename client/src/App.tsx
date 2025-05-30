import React, { useState, useEffect } from "react";
import barChartImg from "./assets/graph.png";
import lineChartImg from "./assets/bar_charts.jpg";
import Button from '@mui/material/Button';
import ChatWindow from './components/ChatWindow';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';
import ToolConfigModal from './components/ToolConfigModal';
import AgentConfigModal from './components/AgentConfigModal';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import ConversationSettingsModal from './components/ConversationSettingsModal';
import TeamSettingsModal from './components/TeamSettingsModal';
import ExecutionPlanModal from './components/ExecutionPlanModal';
import ConnectedSourcesModal from './components/ConnectedSourcesModal';
import IconButton from '@mui/material/IconButton';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import TextField from '@mui/material/TextField';

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
  "Team Settings",
  "Execution Plan",
  "Connected Sources"
];

const defaultAgentConfigs = [
  {
    name: "Nifi Agents",
    memoryType: "Graph",
    foundationModel: "OpenAI",
    tools: ["Sample DB Tool"]
  },
  {
    name: "DBx Agents",
    memoryType: "JSON",
    foundationModel: "Claude",
    tools: ["Sample API Tool"]
  },
  {
    name: "Confluence Agents",
    memoryType: "Short Term",
    foundationModel: "GPT",
    tools: ["Sample DB Tool", "Sample API Tool"]
  },
  {
    name: "AWS Agents",
    memoryType: "Long Term",
    foundationModel: "Gemini",
    tools: ["Sample API Tool"]
  },
  {
    name: "RDS Agents",
    memoryType: "Graph",
    foundationModel: "OpenAI",
    tools: ["Sample DB Tool"]
  },
  {
    name: "Alteryx Agents",
    memoryType: "JSON",
    foundationModel: "Claude",
    tools: ["Sample API Tool"]
  },
  {
    name: "Qlik Agents",
    memoryType: "Short Term",
    foundationModel: "GPT",
    tools: ["Sample DB Tool"]
  },
  {
    name: "Thoughtspot Agents",
    memoryType: "Long Term",
    foundationModel: "Gemini",
    tools: ["Sample API Tool"]
  }
];

const defaultToolConfigs = [
  {
    toolName: "Sample DB Tool",
    toolType: "Database",
    hostname: "db.example.com",
    username: "dbuser",
    password: "********",
    authMethod: "Basic"
  },
  {
    toolName: "Sample API Tool",
    toolType: "API",
    hostname: "api.example.com",
    username: "apiuser",
    password: "********",
    authMethod: "API Key"
  }
];

// Enhanced conversation step type
export type ConversationStep = {
  role: 'user' | 'agent' | 'tool' | 'bot';
  content: string;
  agentName?: string;
  toolName?: string;
  parentIdx?: number; // for hierarchy
};

// Save the current conversation to the backend
type ConversationRecord = {
  id?: number;
  team_id?: number;
  started_at?: string;
  ended_at?: string;
  title: string;
  temperature?: number;
  token_limit?: number;
  start_prompt?: string;
  end_prompt?: string;
  style?: string;
  conversation_data: any;
};

async function saveConversationToBackend(conv: any) {
  const res = await fetch('/api/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(conv)
  });
  return res.json();
}

const App: React.FC = () => {
  const [tabIndex, setTabIndex] = useState(0);
  const [sidebarWidth, setSidebarWidth] = useState(220);
  const [isResizing, setIsResizing] = useState(false);
  const [rightSidebarWidth, setRightSidebarWidth] = useState(220);
  const [isRightResizing, setIsRightResizing] = useState(false);
  const [toolModalOpen, setToolModalOpen] = useState(false);
  const [agentModalOpen, setAgentModalOpen] = useState(false);
  const [editAgentModalOpen, setEditAgentModalOpen] = useState(false);
  const [editToolModalOpen, setEditToolModalOpen] = useState(false);
  const [agents, setAgents] = useState<any[]>([...defaultAgentConfigs]);
  const [selectedAgent, setSelectedAgent] = useState<any | null>(null);
  const [agentToEdit, setAgentToEdit] = useState<any | null>(null);
  const [tools, setTools] = useState<any[]>([...defaultToolConfigs]);
  const [selectedTool, setSelectedTool] = useState<any | null>(null);
  const [toolToEdit, setToolToEdit] = useState<any | null>(null);
  const [sidebarTab, setSidebarTab] = useState(0);
  const [conversationSettingsOpen, setConversationSettingsOpen] = useState(false);
  const [conversationSettings, setConversationSettings] = useState({
    temperature: 0.7,
    tokenLimit: 512,
    startPrompt: '',
    endPrompt: '',
    style: ''
  });
  const [teamSettingsOpen, setTeamSettingsOpen] = useState(false);
  const [teams, setTeams] = useState<any[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<any | null>(null);
  const [executionPlanOpen, setExecutionPlanOpen] = useState(false);
  const [connectedSourcesOpen, setConnectedSourcesOpen] = useState(false);
  const [executionPlanDefinition] = useState<string>(
    `graph TD
      A[User Query] --> B[Intent Detection]
      B --> C[Agent 1: Data Retrieval]
      B --> D[Agent 2: Data Processing]
      C --> E[Result Aggregation]
      D --> E
      E --> F[Response Generation]
      F --> G[User]
    `
  );
  const [conversationHistory, setConversationHistory] = useState<ConversationStep[]>([]);
  const [conversationHistoryList, setConversationHistoryList] = useState<any[]>([]);
  // Toggle for showing conversation history in right sidebar
  const [showConversationHistory, setShowConversationHistory] = useState(false);

  // For renaming conversation
  const [renamingIdx, setRenamingIdx] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState('');

  const canChat = selectedTeam && selectedTeam.agents && selectedTeam.agents.length > 0;

  function generateMermaidFromConversation(history: ConversationStep[]) {
    if (!history.length) {
      const defaultMermaid = `graph TD\nA[No conversation yet]\nA --> B[Sample Step 1]\nB --> C[Sample Step 2]\nC --> D[Sample Step 3]`;
      console.log('Mermaid (default):', defaultMermaid);
      return defaultMermaid;
    }
    let mermaid = 'graph TD\n';
    let nodeIds: string[] = [];
    // Create nodes
    history.forEach((step, idx) => {
      let label = '';
      if (step.role === 'user') label = `User: ${step.content}`;
      else if (step.role === 'agent') label = `Agent: ${step.agentName || ''}`;
      else if (step.role === 'tool') label = `Tool: ${step.toolName || ''}`;
      else label = `Bot: ${step.content}`;
      label = label.replace(/\n/g, ' ').slice(0, 40) + (label.length > 40 ? '...' : '');
      mermaid += `N${idx}[${label}]\n`;
      nodeIds.push(`N${idx}`);
    });
    // Create edges (hierarchy: user->agent->tool->bot)
    history.forEach((step, idx) => {
      if (step.parentIdx !== undefined && step.parentIdx >= 0) {
        mermaid += `N${step.parentIdx} --> N${idx}\n`;
      } else if (idx > 0) {
        mermaid += `N${idx - 1} --> N${idx}\n`;
      }
    });
    // If the generated diagram is empty or invalid, fallback to sample
    if (mermaid.trim() === 'graph TD') {
      const defaultMermaid = `graph TD\nA[No conversation yet]\nA --> B[Sample Step 1]\nB --> C[Sample Step 2]\nC --> D[Sample Step 3]`;
      console.log('Mermaid (fallback):', defaultMermaid);
      return defaultMermaid;
    }
    console.log('Mermaid (generated):', mermaid);
    return mermaid;
  }

  // Helper to generate a random summary title
  function generateRandomSummary(history: ConversationStep[]) {
    if (!history.length) return 'Empty Conversation';
    // Try to use the first user message as a summary, or fallback
    const firstUser = history.find(h => h.role === 'user');
    if (firstUser && firstUser.content) {
      return firstUser.content.slice(0, 30) + (firstUser.content.length > 30 ? '...' : '');
    }
    return 'Conversation ' + (conversationHistoryList.length + 1);
  }

  // Delete conversation
  const handleDeleteConversation = (timestamp: number) => {
    setConversationHistoryList(prev => prev.filter(conv => conv.timestamp !== timestamp));
  };

  // Start renaming
  const handleStartRename = (idx: number, currentTitle: string) => {
    setRenamingIdx(idx);
    setRenameValue(currentTitle);
  };

  // Save rename
  const handleSaveRename = (timestamp: number) => {
    setConversationHistoryList(prev => prev.map((conv, idx) => idx === renamingIdx ? { ...conv, title: renameValue } : conv));
    setRenamingIdx(null);
    setRenameValue('');
  };

  // Export conversation as JSON
  const handleExportConversation = (conv: any) => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(conv, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `${conv.title.replace(/[^a-z0-9]/gi, '_') || 'conversation'}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  // Save conversation to backend
  const handleSaveConversation = async () => {
    if (conversationHistory.length > 0) {
      const conv = {
        title: generateRandomSummary(conversationHistory),
        conversation_data: conversationHistory,
        settings: {
          team_id: selectedTeam?.id,
          temperature: conversationSettings.temperature,
          token_limit: conversationSettings.tokenLimit,
          start_prompt: conversationSettings.startPrompt,
          end_prompt: conversationSettings.endPrompt,
          style: conversationSettings.style
        }
      };
      await saveConversationToBackend(conv);
      // Refresh conversation list from backend
      fetch('/api/conversations').then(res => res.json()).then(setConversationHistoryList);
    }
  };

  // Load conversation from history
  const handleLoadConversation = async (conv: any) => {
    console.log('handleLoadConversation called with:', conv);
    // If the conversation has an id, fetch from backend for latest data
    if (conv.id) {
      try {
        const res = await fetch(`/api/conversations/${conv.id}`);
        if (res.ok) {
          const data = await res.json();
          console.log('Fetched conversation from backend:', data);
          setConversationHistory(data.conversation_data || []);
          setConversationSettings({
            temperature: data.temperature,
            tokenLimit: data.token_limit,
            startPrompt: data.start_prompt,
            endPrompt: data.end_prompt,
            style: data.style
          });
          return;
        } else {
          console.error('Failed to fetch conversation from backend:', res.status);
        }
      } catch (e) {
        console.error('Error fetching conversation from backend:', e);
      }
    }
    // fallback to local data if no id or fetch fails
    if (conv.conversation_data) {
      setConversationHistory(conv.conversation_data);
    } else if (conv.history) {
      setConversationHistory(conv.history);
    }
    setConversationSettings({
      temperature: conv.temperature,
      tokenLimit: conv.token_limit,
      startPrompt: conv.start_prompt,
      endPrompt: conv.end_prompt,
      style: conv.style
    });
  };

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

  // Fetch agents, tools, teams, conversations from backend
  useEffect(() => {
    fetch('/api/agents').then(res => res.json()).then(setAgents);
    fetch('/api/tools').then(res => res.json()).then(data => {
      // Map snake_case to camelCase for tools
      setTools(data.map((tool: any) => ({
        ...tool,
        toolName: tool.tool_name,
        toolType: tool.tool_type,
        authMethod: tool.auth_method,
        // keep other fields as is
      })));
    });
    fetch('/api/teams').then(res => res.json()).then(setTeams);
    fetch('/api/conversations').then(res => res.json()).then(setConversationHistoryList);
  }, []);

  const fetchAgents = () => {
    fetch('/api/agents').then(res => res.json()).then(setAgents);
  };

  const handleAddAgent = (agent: any) => {
    fetchAgents();
  };

  const handleEditAgent = (agent: any) => {
    setAgentToEdit(agent);
    setEditAgentModalOpen(true);
  };

  const handleUpdateAgent = (updatedAgent: any) => {
    fetchAgents();
    setEditAgentModalOpen(false);
    setAgentToEdit(null);
    setSelectedAgent(null);
  };

  const handleEditTool = (tool: any) => {
    setToolToEdit(tool);
    setEditToolModalOpen(true);
  };

  const handleUpdateTool = (updatedTool: any) => {
    setTools(prev => prev.map(t => t.toolName === toolToEdit.toolName ? updatedTool : t));
    setEditToolModalOpen(false);
    setToolToEdit(null);
    setSelectedTool(null);
  };

  // Handler for New Chat
  const handleNewChat = async () => {
    if (conversationHistory.length > 0) {
      const conv = {
        title: generateRandomSummary(conversationHistory),
        conversation_data: conversationHistory,
        settings: {
          team_id: selectedTeam?.id,
          temperature: conversationSettings.temperature,
          token_limit: conversationSettings.tokenLimit,
          start_prompt: conversationSettings.startPrompt,
          end_prompt: conversationSettings.endPrompt,
          style: conversationSettings.style
        }
      };
      await saveConversationToBackend(conv);
      // Refresh conversation list from backend
      fetch('/api/conversations').then(res => res.json()).then(setConversationHistoryList);
    }
    setConversationHistory([]); // Always clear center pane
  };

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
          {/* Agents/Tools Tabs */}
          <Tabs value={sidebarTab} onChange={(_, v) => setSidebarTab(v)} variant="fullWidth" sx={{ mb: 1 }}>
            <Tab label="Agents" />
            <Tab label="Tools" />
          </Tabs>
          {/* Add + List for Agents */}
          {sidebarTab === 0 && (
            <>
              <Button variant="contained" color="primary" fullWidth size="medium" sx={{ mb: 1 }} onClick={() => setAgentModalOpen(true)}>Add Agent</Button>
              <Divider sx={{ margin: '0.5rem 0' }} />
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", flex: 1, overflowY: 'auto', marginBottom: '1rem' }}>
                {agents.map((agent, idx) => (
                  <Button
                    key={agent.name}
                    variant="contained"
                    fullWidth
                    size="small"
                    sx={{
                      backgroundColor: agentColors[idx % agentColors.length],
                      color: '#fff',
                      fontWeight: 'bold',
                      border: '2px solid #222',
                      borderRadius: 2,
                      boxShadow: 'none',
                      '&:hover': {
                        backgroundColor: agentColors[idx % agentColors.length],
                        opacity: 0.9,
                      },
                      textAlign: 'left',
                      minHeight: 32,
                      fontSize: '0.95rem',
                      padding: '0.2rem 0.7rem',
                    }}
                    onClick={() => setSelectedAgent(agent)}
                  >
                    {agent.name}
                  </Button>
                ))}
              </div>
              {/* Agent details modal */}
              {selectedAgent && (
                <Dialog open={!!selectedAgent} onClose={() => setSelectedAgent(null)} maxWidth="xs" fullWidth>
                  <DialogTitle>Agent Details</DialogTitle>
                  <DialogContent>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
                      <Box><b>Name:</b> {selectedAgent.name}</Box>
                      <Box><b>Type of Memory:</b> {selectedAgent.memoryType}</Box>
                      <Box><b>Foundation Model:</b> {selectedAgent.foundationModel}</Box>
                      <Box><b>Tools:</b> {selectedAgent.tools && selectedAgent.tools.length > 0 ? selectedAgent.tools.join(', ') : 'None'}</Box>
                    </Box>
                  </DialogContent>
                  <DialogActions>
                    <Button onClick={() => setSelectedAgent(null)}>Close</Button>
                    <Button onClick={() => handleEditAgent(selectedAgent)} color="primary" variant="contained">Edit</Button>
                  </DialogActions>
                </Dialog>
              )}
              <AgentConfigModal open={agentModalOpen} onClose={() => setAgentModalOpen(false)} onSave={handleAddAgent} tools={tools} />
              <AgentConfigModal open={editAgentModalOpen} onClose={() => setEditAgentModalOpen(false)} onSave={handleUpdateAgent} tools={tools} initialValues={agentToEdit || {}} mode="edit" />
            </>
          )}
          {/* Add + List for Tools */}
          {sidebarTab === 1 && (
            <>
              <Button variant="contained" color="primary" fullWidth size="medium" sx={{ mb: 1 }} onClick={() => setToolModalOpen(true)}>Add Tool</Button>
              <Divider sx={{ margin: '0.5rem 0' }} />
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", flex: 1, overflowY: 'auto', marginBottom: '1rem' }}>
                {tools.map((tool, idx) => (
                  <Button
                    key={tool.toolName}
                    variant="contained"
                    fullWidth
                    size="small"
                    sx={{
                      backgroundColor: agentColors[idx % agentColors.length],
                      color: '#fff',
                      fontWeight: 'bold',
                      border: '2px solid #222',
                      borderRadius: 2,
                      boxShadow: 'none',
                      '&:hover': {
                        backgroundColor: agentColors[idx % agentColors.length],
                        opacity: 0.9,
                      },
                      textAlign: 'left',
                      minHeight: 32,
                      fontSize: '0.95rem',
                      padding: '0.2rem 0.7rem',
                    }}
                    onClick={() => setSelectedTool(tool)}
                  >
                    {tool.toolName}
                  </Button>
                ))}
              </div>
              {/* Tool details modal */}
              {selectedTool && (
                <Dialog open={!!selectedTool} onClose={() => setSelectedTool(null)} maxWidth="xs" fullWidth>
                  <DialogTitle>Tool Details</DialogTitle>
                  <DialogContent>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
                      <Box><b>Name:</b> {selectedTool.toolName}</Box>
                      <Box><b>Type:</b> {selectedTool.toolType}</Box>
                      <Box><b>Hostname:</b> {selectedTool.hostname}</Box>
                      <Box><b>Username:</b> {selectedTool.username}</Box>
                      <Box><b>Authentication:</b> {selectedTool.authMethod}</Box>
                    </Box>
                  </DialogContent>
                  <DialogActions>
                    <Button onClick={() => setSelectedTool(null)}>Close</Button>
                    <Button onClick={() => handleEditTool(selectedTool)} color="primary" variant="contained">Edit</Button>
                  </DialogActions>
                </Dialog>
              )}
              <ToolConfigModal open={toolModalOpen} onClose={() => setToolModalOpen(false)} onSave={tool => setTools(prev => [...prev, tool])} />
              <ToolConfigModal open={editToolModalOpen} onClose={() => setEditToolModalOpen(false)} onSave={handleUpdateTool} initialValues={toolToEdit || {}} mode="edit" />
            </>
          )}
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
            <Button variant="contained" color="primary" onClick={handleNewChat}>+ NEW CHAT</Button>
            <Button variant="outlined" color="primary" onClick={() => setShowConversationHistory(v => !v)}>
              Conversation History
            </Button>
          </div>

          {/* Main Panels */}
          <div style={{ flex: 1, display: "flex", minHeight: 0, gap: "0.5rem" }}>
            {/* Center Panels - now a single chat panel with scrollable chat and chart responses */}
            <section style={{ flex: 3, display: "flex", flexDirection: "column", gap: "0.8rem", height: '100%' }}>
              <div style={{
                background: "#fff",
                border: "2px solid #222",
                borderRadius: 5,
                minHeight: 320,
                padding: "0.7rem",
                position: "relative",
                display: "flex",
                flexDirection: "column",
                height: '100%'
              }}>
                <ChatWindow
                  placeholder="Ask your analytics questions..."
                  conversationHistory={conversationHistory}
                  setConversationHistory={setConversationHistory}
                  selectedTeam={selectedTeam}
                  canChat={canChat}
                />
              </div>
            </section>

            {/* Right Sidebar with resizable pane */}
            <aside style={{ width: rightSidebarWidth, minWidth: 160, maxWidth: 400, background: "#fff", display: "flex", flexDirection: "column", gap: "0.7rem", position: 'relative' }}>
              {/* Show only conversation history when toggled */}
              {showConversationHistory ? (
                <Box sx={{ mt: 2, background: '#f5f5f5', borderRadius: 2, p: 1, flex: 1, overflowY: 'auto' }}>
                  <b>Conversation History</b>
                  {conversationHistoryList.length === 0 && (
                    <Box sx={{ color: '#888', mt: 2 }}>No conversations yet.</Box>
                  )}
                  {conversationHistoryList.map((conv, idx) => (
                    <Box key={conv.timestamp} sx={{ mt: 1, p: 1, border: '1px solid #ccc', borderRadius: 1, background: '#fff', display: 'flex', alignItems: 'center', gap: 1 }}>
                      {/* Title or rename field */}
                      <Box sx={{ flex: 1, cursor: renamingIdx === idx ? 'auto' : 'pointer' }}
                        onClick={() => {
                          if (renamingIdx !== idx) {
                            handleLoadConversation(conv);
                            setShowConversationHistory(false);
                          }
                        }}
                      >
                        {renamingIdx === idx ? (
                          <TextField
                            value={renameValue}
                            onChange={e => setRenameValue(e.target.value)}
                            size="small"
                            onBlur={() => handleSaveRename(conv.timestamp)}
                            onKeyDown={e => { if (e.key === 'Enter') handleSaveRename(conv.timestamp); }}
                            autoFocus
                            sx={{ minWidth: 120 }}
                          />
                        ) : (
                          <span>{conv.title}</span>
                        )}
                        <div style={{ fontSize: '0.8rem', color: '#888' }}>{new Date(conv.timestamp).toLocaleString()}</div>
                      </Box>
                      {/* Action buttons */}
                      <IconButton size="small" onClick={() => handleStartRename(idx, conv.title)} title="Rename"><EditIcon fontSize="small" /></IconButton>
                      <IconButton size="small" onClick={() => handleDeleteConversation(conv.timestamp)} title="Delete"><DeleteIcon fontSize="small" /></IconButton>
                      <IconButton size="small" onClick={() => handleExportConversation(conv)} title="Export"><DownloadIcon fontSize="small" /></IconButton>
                    </Box>
                  ))}
                </Box>
              ) : (
                <>
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
                  {tabIndex === 0 && !showConversationHistory && (
                    <>
                      {/* Team Settings button first */}
                      <Button
                        key="Team Settings"
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
                        onClick={() => setTeamSettingsOpen(true)}
                      >
                        Team Settings
                      </Button>
                      {/* Conversation Settings button second */}
                      <Button
                        key="Conversation Settings"
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
                        onClick={() => setConversationSettingsOpen(true)}
                      >
                        Conversation Settings
                      </Button>
                      {/* The rest of the rightPanelItems */}
                      {rightPanelItems.filter(item => item !== 'Team Settings' && item !== 'Conversation Settings').map(item => (
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
                          onClick={() => {
                            if (item === 'Execution Plan') setExecutionPlanOpen(true);
                            if (item === 'Connected Sources') setConnectedSourcesOpen(true);
                            // TODO: Show panel details for other items
                          }}
                        >
                          {item}
                        </Button>
                      ))}
                    </>
                  )}
                  {tabIndex === 1 && (
                    <Box sx={{ margin: '1rem', color: '#888', textAlign: 'center' }}>No documents.</Box>
                  )}
                </>
              )}
              <ConversationSettingsModal
                open={conversationSettingsOpen}
                onClose={() => setConversationSettingsOpen(false)}
                onSave={async (settings, selectedTeamId) => {
                  setConversationSettings(settings);
                  // Always fetch the latest team with agents from backend after saving settings
                  try {
                    const res = await fetch(`/api/teams`);
                    const allTeams = await res.json();
                    const team = allTeams.find((t: any) => (t.id || t.name) === selectedTeamId);
                    console.log('DEBUG selectedTeam after save:', team);
                    setSelectedTeam(team || null);
                  } catch {
                    setSelectedTeam(null);
                  }
                }}
                initialValues={conversationSettings}
                teams={teams}
                selectedTeamId={selectedTeam ? (selectedTeam.id || selectedTeam.name) : ''}
                onTeamChange={teamId => {
                  const team = teams.find(t => (t.id || t.name) === teamId);
                  setSelectedTeam(team || null);
                }}
              />
              <TeamSettingsModal
                open={teamSettingsOpen}
                onClose={() => setTeamSettingsOpen(false)}
                agents={agents}
                teams={teams}
                setTeams={setTeams}
                selectedTeam={selectedTeam}
                setSelectedTeam={setSelectedTeam}
              />
              <ExecutionPlanModal
                open={executionPlanOpen}
                onClose={() => setExecutionPlanOpen(false)}
                mermaidDefinition={generateMermaidFromConversation(conversationHistory)}
              />
              <ConnectedSourcesModal
                open={connectedSourcesOpen}
                onClose={() => setConnectedSourcesOpen(false)}
                teamId={selectedTeam?.id}
              />
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

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
import DocumentList, { Document } from './components/DocumentList';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import ListItemSecondaryAction from '@mui/material/ListItemSecondaryAction';
import Drawer from '@mui/material/Drawer';
import Toolbar from '@mui/material/Toolbar';
import ListItemIcon from '@mui/material/ListItemIcon';
import GroupIcon from '@mui/icons-material/Group';
import SettingsIcon from '@mui/icons-material/Settings';
import AgentSettingsModal from './components/AgentSettingsModal';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';

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

// Helper function to display tool names robustly
function getToolDisplayNames(agentTools: any[], allTools: any[]): string {
  if (!Array.isArray(agentTools) || !agentTools.length) return 'None';
  return agentTools
      .map(tool => {
        if (tool && typeof tool === 'object') {
          return tool.toolName || tool.tool_name ||
              (tool.id ? (allTools.find((t: any) => t.id === tool.id)?.toolName || tool.id) : JSON.stringify(tool));
        }
        if (typeof tool === 'number') {
          const t = allTools.find((tt: any) => tt.id === tool);
          return t ? t.toolName : tool;
        }
        if (typeof tool === 'string') {
          const t = allTools.find((tt: any) => tt.toolName === tool);
          return t ? t.toolName : tool;
        }
        return '';
      })
      .filter(Boolean)
      .join(', ');
}

// Enhanced conversation step type
export type ConversationStep = {
  role: 'user' | 'agent' | 'tool' | 'bot';
  content: string;
  agentName?: string;
  toolName?: string;
  parentIdx?: number; // for hierarchy
  data?: {
    type: 'bar' | 'line' | 'pie';
    labels: string[];
    values: number[];
  };
  attachments?: Document[];
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

const drawerWidth = 240;

const App = () => {
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

  const [documents, setDocuments] = useState<Document[]>([]);

  const canChat = selectedTeam && selectedTeam.agents && selectedTeam.agents.length > 0;

  // Add this state near other modal states
  const [agentSettingsOpen, setAgentSettingsOpen] = useState(false);

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
  const handleDeleteConversation = async (conv: any) => {
    try {
      // Delete from backend
      const response = await fetch(`/api/conversations/${conv.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete conversation');
      }

      // Update local state
      setConversationHistoryList(prev => prev.filter(c => c.id !== conv.id));
    } catch (error) {
      console.error('Error deleting conversation:', error);
      alert('Failed to delete conversation. Please try again.');
    }
  };

  // Start renaming
  const handleStartRename = (idx: number, currentTitle: string) => {
    setRenamingIdx(idx);
    setRenameValue(currentTitle);
  };

  // Save rename
  const handleSaveRename = async (conv: any) => {
    try {
      // Update the conversation title in the backend
      const response = await fetch(`/api/conversations/${conv.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...conv,
          title: renameValue
        })
      });

      if (!response.ok) {
        throw new Error('Failed to update conversation title');
      }

      // Update local state
      setConversationHistoryList(prev => 
        prev.map(c => c.id === conv.id ? { ...c, title: renameValue } : c)
      );
    setRenamingIdx(null);
    setRenameValue('');
    } catch (error) {
      console.error('Error updating conversation title:', error);
      alert('Failed to update conversation title. Please try again.');
    }
  };

  // Export conversation as JSON
  const handleExportConversation = (conv: any) => {
    try {
      // Prepare the export data
      const exportData = {
        id: conv.id,
        title: conv.title,
        started_at: conv.started_at,
        ended_at: conv.ended_at,
        team_id: conv.team_id,
        temperature: conv.temperature,
        token_limit: conv.token_limit,
        start_prompt: conv.start_prompt,
        end_prompt: conv.end_prompt,
        style: conv.style,
        conversation_data: conv.conversation_data
      };

      // Create the download
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportData, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
      downloadAnchorNode.setAttribute("download", `conversation_${conv.title.replace(/[^a-z0-9]/gi, '_')}_${new Date().toISOString().split('T')[0]}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
    } catch (error) {
      console.error('Error exporting conversation:', error);
      alert('Failed to export conversation. Please try again.');
    }
  };

  // Load conversation from history
  const handleLoadConversation = async (conv: any) => {
    console.log('handleLoadConversation called with:', conv);
      try {
      // Always try to fetch from backend first if we have an ID
      if (conv.id) {
        const res = await fetch(`/api/conversations/${conv.id}`);
        if (res.ok) {
          const data = await res.json();
          console.log('Fetched conversation from backend:', data);
          
          // Parse conversation_data if it's a string
          let conversationData;
          if (typeof data.conversation_data === 'string') {
            try {
              conversationData = JSON.parse(data.conversation_data);
            } catch (e) {
              console.error('Failed to parse conversation data:', e);
              conversationData = [];
            }
          } else {
            conversationData = data.conversation_data || [];
          }
          
          // Ensure it's an array
          if (!Array.isArray(conversationData)) {
            console.error('Conversation data is not an array:', conversationData);
            conversationData = [];
          }
          
          setConversationHistory(conversationData);
          
          // Update conversation settings from either settings table or conversation table
          setConversationSettings({
            temperature: Number(data.temperature) || 0.7,
            tokenLimit: Number(data.token_limit) || 512,
            startPrompt: data.start_prompt || '',
            endPrompt: data.end_prompt || '',
            style: data.style || ''
          });
          
          // Close conversation history panel
          setShowConversationHistory(false);
          return;
        } else {
          console.error('Failed to fetch conversation:', await res.text());
        }
      }
      
      // Fallback to local data if no id or fetch fails
      let conversationData;
      if (typeof conv.conversation_data === 'string') {
        try {
          conversationData = JSON.parse(conv.conversation_data);
      } catch (e) {
          console.error('Failed to parse local conversation data:', e);
          conversationData = [];
        }
      } else {
        conversationData = conv.conversation_data || conv.history || [];
      }
      
      // Ensure it's an array
      if (!Array.isArray(conversationData)) {
        console.error('Local conversation data is not an array:', conversationData);
        conversationData = [];
      }
      
      setConversationHistory(conversationData);
      
    setConversationSettings({
        temperature: Number(conv.temperature) || 0.7,
        tokenLimit: Number(conv.token_limit) || 512,
        startPrompt: conv.start_prompt || '',
        endPrompt: conv.end_prompt || '',
        style: conv.style || ''
      });
      
      // Close conversation history panel
      setShowConversationHistory(false);
    } catch (error) {
      console.error('Error loading conversation:', error);
      alert('Failed to load conversation. Please try again.');
    }
  };

  // Save conversation to backend
  const handleSaveConversation = async () => {
    if (conversationHistory.length > 0) {
      try {
        // Validate team selection
        if (!selectedTeam?.id) {
          alert('Please select a team before saving the conversation.');
          setConversationSettingsOpen(true);
          return;
        }

        const now = new Date().toISOString();
        const title = generateRandomSummary(conversationHistory);
        
        // Log the conversation history before saving
        console.log('Current conversation history:', conversationHistory);
        console.log('Current conversation settings:', conversationSettings);
        console.log('Selected team:', selectedTeam);
        
        // Save the conversation with settings at root level
        const response = await fetch('/api/conversations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            title,
            started_at: now,
            ended_at: now,
            conversation_data: conversationHistory,
            team_id: selectedTeam.id,
            temperature: Number(conversationSettings.temperature),
            token_limit: Number(conversationSettings.tokenLimit),
            start_prompt: conversationSettings.startPrompt,
            end_prompt: conversationSettings.endPrompt,
            style: conversationSettings.style
          })
        });
        
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Failed to save conversation: ${errorText}`);
        }
        
        const savedConv = await response.json();
        console.log('Successfully saved conversation:', savedConv);
        
        // Refresh conversation list from backend
        const listResponse = await fetch('/api/conversations');
        if (!listResponse.ok) {
          throw new Error(`Failed to fetch conversations: ${await listResponse.text()}`);
        }
        
        const conversations = await listResponse.json();
        console.log('Updated conversation list:', conversations);
        setConversationHistoryList(conversations);
        
      } catch (error) {
        console.error('Error saving conversation:', error);
        alert('Failed to save conversation. Please try again.');
      }
    } else {
      console.log('No conversation to save');
    }
  };

  // Handle new chat
  const handleNewChat = async () => {
    try {
      // Save current conversation if it exists
      if (conversationHistory.length > 0) {
        console.log('Saving current conversation before starting new chat');
        await handleSaveConversation();
      } else {
        console.log('No conversation to save before new chat');
      }
      // Clear the chat
      setConversationHistory([]);
    } catch (error) {
      console.error('Error in new chat:', error);
      // Still clear the chat even if save fails
      setConversationHistory([]);
    }
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
    // Fetch agents first
    fetch('/api/agents')
      .then(res => res.json())
      .then(agentData => {
        setAgents(agentData);
        // Then fetch teams to ensure we have the latest agent data
        return fetch('/api/teams');
      })
      .then(res => res.json())
      .then(teamData => {
        console.log('Fetched teams with agents:', teamData);
        setTeams(teamData);
      })
      .catch(error => {
        console.error('Error fetching data:', error);
      });

    fetch('/api/tools').then(res => res.json()).then(data => {
      // Map snake_case to camelCase for tools
      setTools(data.map((tool: any) => ({
        ...tool,
        toolName: tool.tool_name,
        toolType: tool.tool_type,
        authMethod: tool.auth_method,
      })));
    });
    
    // Fetch and log conversations
    fetch('/api/conversations')
      .then(res => res.json())
      .then(data => {
        console.log('Fetched conversations:', data);
        setConversationHistoryList(data);
      })
      .catch(error => {
        console.error('Error fetching conversations:', error);
      });
  }, []);

  // Add effect to log conversation list changes
  useEffect(() => {
    console.log('Current conversation list:', conversationHistoryList);
  }, [conversationHistoryList]);

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

  // Handle file upload
  const handleFileUpload = async (file: File): Promise<Document> => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('team_id', selectedTeam?.id);

      const response = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Failed to upload file');
      }

      const uploadedDoc = await response.json();
      setDocuments(prev => [...prev, uploadedDoc]);
      return uploadedDoc;
    } catch (error) {
      console.error('Error uploading file:', error);
      throw error;
    }
  };

  // Handle document deletion
  const handleDeleteDocument = async (id: string) => {
    try {
      const response = await fetch(`/api/documents/${id}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to delete document');
      }

      setDocuments(prev => prev.filter(doc => doc.id !== id));
    } catch (error) {
      console.error('Error deleting document:', error);
      alert('Failed to delete document. Please try again.');
    }
  };

  // Handle document download
  const handleDownloadDocument = async (doc: Document) => {
    try {
      const response = await fetch(doc.url);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = doc.name;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (error) {
      console.error('Error downloading document:', error);
      alert('Failed to download document. Please try again.');
    }
  };

  // Fetch documents on mount and when team changes
  useEffect(() => {
    if (selectedTeam?.id) {
      fetch(`/api/documents?team_id=${selectedTeam.id}`)
        .then(res => res.json())
        .then(setDocuments)
        .catch(console.error);
    }
  }, [selectedTeam?.id]);

  // Add these new handler functions before the return statement
  const handleConversationSettingsSave = async (settings: any, teamId: string) => {
    try {
      // Update local state
      setConversationSettings(settings);

      // Convert string ID to number for API calls
      const numericTeamId = parseInt(teamId, 10);
      if (isNaN(numericTeamId)) {
        throw new Error('Invalid team ID');
      }

      // If there's a team ID, save settings to backend
      const response = await fetch(`/api/teams/${numericTeamId}/conversation-settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings)
      });

      if (!response.ok) {
        throw new Error('Failed to save conversation settings');
      }

      // Close the modal
      setConversationSettingsOpen(false);
    } catch (error) {
      console.error('Error saving conversation settings:', error);
      alert('Failed to save conversation settings. Please try again.');
    }
  };

  const handleTeamChange = async (teamId: string) => {
    try {
      // Convert string ID to number
      const numericTeamId = parseInt(teamId, 10);
      if (isNaN(numericTeamId)) {
        throw new Error('Invalid team ID');
      }

      // Find the selected team
      const team = teams.find(t => t.id === numericTeamId);
      if (!team) {
        throw new Error('Team not found');
      }

      // Update selected team
      setSelectedTeam(team);

      // Fetch team-specific conversation settings if they exist
      const response = await fetch(`/api/teams/${numericTeamId}/conversation-settings`);
      if (response.ok) {
        const settings = await response.json();
        setConversationSettings({
          temperature: settings.temperature || 0.7,
          tokenLimit: settings.token_limit || 512,
          startPrompt: settings.start_prompt || '',
          endPrompt: settings.end_prompt || '',
          style: settings.style || ''
        });
      }

      // Fetch team-specific documents
      const docsResponse = await fetch(`/api/documents?team_id=${numericTeamId}`);
      if (docsResponse.ok) {
        const docs = await docsResponse.json();
        setDocuments(docs);
      }
    } catch (error) {
      console.error('Error changing team:', error);
      alert('Failed to change team. Please try again.');
    }
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
                            <Box><b>Type of Memory:</b> {selectedAgent.memoryType || selectedAgent.memory_type || ''}</Box>
                            <Box><b>Foundation Model:</b> {selectedAgent.foundationModel || selectedAgent.foundation_model || ''}</Box>
                            <Box>
                              <b>Tools:</b> {getToolDisplayNames(selectedAgent.tools, tools)}
                            </Box>
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

          {/* Main Content Area */}
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
                  onFileUpload={handleFileUpload}
                  />
                </div>
              </section>

              {/* Right Sidebar with resizable pane */}
            <Box
              component="aside"
              sx={{
                width: rightSidebarWidth,
                minWidth: 160,
                maxWidth: 400,
                bgcolor: 'background.paper',
                display: 'flex',
                flexDirection: 'column',
                position: 'relative',
                overflow: 'hidden'
              }}
            >
                {/* Show only conversation history when toggled */}
                {showConversationHistory ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', overflow: 'hidden' }}>
                  <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
                    <Typography variant="h6">Conversation History</Typography>
                  </Box>
                  <List sx={{ width: '100%', flex: 1, overflow: 'auto', p: 1, position: 'relative' }}>
                    {conversationHistoryList.length === 0 ? (
                      <Typography color="text.secondary" align="center" sx={{ p: 2 }}>
                        No conversations yet.
                      </Typography>
                    ) : (
                      conversationHistoryList.map((conv, idx) => (
                        <Box key={conv.id || idx} sx={{ position: 'relative', mb: 1 }}>
                          <ListItem
                                 onClick={() => {
                                   if (renamingIdx !== idx) {
                                     handleLoadConversation(conv);
                                     setShowConversationHistory(false);
                                   }
                                 }}
                            sx={{
                              cursor: renamingIdx === idx ? 'default' : 'pointer',
                              pr: 15,
                              p: 2,
                              position: 'relative',
                              overflow: 'visible',
                              bgcolor: 'background.paper',
                              border: '1px solid',
                              borderColor: 'divider',
                              borderRadius: 1,
                              '&:hover': {
                                bgcolor: 'action.hover',
                              },
                            }}
                          >
                            <ListItemText
                              primary={
                                renamingIdx === idx ? (
                                  <TextField
                                      value={renameValue}
                                    onChange={(e) => setRenameValue(e.target.value)}
                                      size="small"
                                    fullWidth
                                      autoFocus
                                    onBlur={() => handleSaveRename(conv)}
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter') handleSaveRename(conv);
                                    }}
                                    onClick={(e) => e.stopPropagation()}
                                    sx={{ mb: 1 }}
                                  />
                              ) : (
                                  conv.title
                                )
                              }
                              secondary={conv.started_at ? new Date(conv.started_at).toLocaleString() : 'No date'}
                            />
                            <div className="action-buttons" style={{
                              position: 'absolute',
                              right: 8,
                              top: '50%',
                              transform: 'translateY(-50%)',
                              display: 'flex',
                              gap: '8px',
                              background: '#fff',
                              padding: '4px',
                              borderRadius: '4px',
                              opacity: 0.9,
                              transition: 'opacity 0.2s',
                              zIndex: 9999,
                              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                              isolation: 'isolate',
                              pointerEvents: 'auto'
                            }}>
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  handleStartRename(idx, conv.title);
                                }}
                                sx={{
                                  bgcolor: 'background.paper',
                                  '&:hover': { bgcolor: 'action.hover' },
                                  zIndex: 10000
                                }}
                              >
                                <EditIcon fontSize="small" />
                              </IconButton>
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  if (window.confirm('Are you sure you want to delete this conversation?')) {
                                    handleDeleteConversation(conv);
                                  }
                                }}
                                sx={{
                                  bgcolor: 'background.paper',
                                  '&:hover': { bgcolor: 'action.hover' },
                                  zIndex: 10000
                                }}
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  handleExportConversation(conv);
                                }}
                                sx={{
                                  bgcolor: 'background.paper',
                                  '&:hover': { bgcolor: 'action.hover' },
                                  zIndex: 10000
                                }}
                              >
                                <DownloadIcon fontSize="small" />
                              </IconButton>
                            </div>
                          </ListItem>
                        </Box>
                      ))
                    )}
                  </List>
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
                      {/* Agent Settings button */}
                      <Button
                        key="Agent Settings"
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
                          margin: '0.5rem',
                          padding: '0.7rem 0.7rem',
                          textAlign: 'left',
                        }}
                        onClick={() => setAgentSettingsOpen(true)}
                      >
                        Agent Settings
                      </Button>
                      {/* Conversation Settings button */}
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
                      {rightPanelItems.filter(item => !['Team Settings', 'Conversation Settings'].includes(item)).map(item => (
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
                                    }}
                                >
                                  {item}
                                </Button>
                            ))}
                          </>
                      )}
                      {tabIndex === 1 && (
                    <Box sx={{ p: 2, height: '100%', overflow: 'auto' }}>
                      <DocumentList
                        documents={documents}
                        onDelete={handleDeleteDocument}
                        onDownload={handleDownloadDocument}
                      />
                    </Box>
                      )}
                    </>
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
            </Box>
          </div>
        </main>
      </div>

      {/* Modals */}
                <ConversationSettingsModal
                    open={conversationSettingsOpen}
                    onClose={() => setConversationSettingsOpen(false)}
        onSave={handleConversationSettingsSave}
                    initialValues={conversationSettings}
                    teams={teams}
        selectedTeamId={selectedTeam?.id?.toString() || ''}
        onTeamChange={handleTeamChange}
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
      <AgentSettingsModal
        open={agentSettingsOpen}
        onClose={() => setAgentSettingsOpen(false)}
        teams={teams}
      />
      </div>
  );
};

export default App;

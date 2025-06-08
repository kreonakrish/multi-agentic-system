import React, { useState, useEffect } from "react";
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Typography,
  Paper,
  Stack,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Drawer,
  Toolbar,
  ListItemIcon,
  TextField,
  Divider,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  Group as GroupIcon,
  Settings as SettingsIcon,
  SmartToy as SmartToyIcon,
  Build as BuildIcon,
  Add as AddIcon,
  Storage as StorageIcon,
  Api as ApiIcon,
  Cloud as CloudIcon,
  Chat as ChatIcon,
  Groups as GroupsIcon,
  AccountTree as AccountTreeIcon,
  Link as LinkIcon,
  Hub as HubIcon,
} from '@mui/icons-material';
import { BrowserRouter as Router } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { getTheme } from './theme';

// Import our components
import TopBar from './components/layout/TopBar';
import LeftSidebar from './components/layout/LeftSidebar';
import MainContent from './components/layout/MainContent';
import RightSidebar from './components/layout/RightSidebar';
import ChatControls from './components/layout/ChatControls';
import ChatWindow from './components/chat/ChatWindow';
import ToolConfigModal from './components/modals/ToolConfigModal';
import AgentConfigModal from './components/modals/AgentConfigModal';
import ConversationSettingsModal from './components/modals/ConversationSettingsModal';
import TeamSettingsModal from './components/modals/TeamSettingsModal';
import ExecutionPlanModal from './components/modals/ExecutionPlanModal';
import ConnectedSourcesModal from './components/modals/ConnectedSourcesModal';
import AgentSettingsModal from './components/modals/AgentSettingsModal';
import DocumentList from './components/documents/DocumentList';

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

import type {
  Document,
  Team,
  ConversationStep,
  Conversation,
  ConversationSettings,
  Tool,
  Agent,
  ToolType
} from './store/types';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

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
    tool_name: "Sample DB Tool",
    tool_type: "Database",
    hostname: "db.example.com",
    username: "dbuser",
    password: "********",
    auth_method: "Basic"
  },
  {
    tool_name: "Sample API Tool",
    tool_type: "API",
    hostname: "api.example.com",
    username: "apiuser",
    password: "********",
    auth_method: "API Key"
  }
];

const toolColors = {
  'Database': '#4caf50',  // Green
  'API': '#2196f3',       // Blue
  'WebService': '#ff9800', // Orange
  'default': '#e0e0e0'    // Default gray
};

interface AppProps {
  // Empty for now as we don't have any props
}

interface AgentFormData {
  id?: string;
  name: string;
  memoryType: string;
  foundationModel: string;
  tools: Tool[];
}

// Save the current conversation to the backend
interface ConversationRecord {
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
  conversation_data: ConversationStep[];
}

interface ConnectedSourcesResponse {
  [type: string]: Array<{
    id: number;
    tool_name: string;
    hostname: string;
    auth_method: string;
    permission_level: string;
  }>;
}

const App: React.FC<AppProps> = () => {
  const [mode, setMode] = useState<'light' | 'dark'>('light');
  const [tabIndex, setTabIndex] = useState(0);
  const [sidebarWidth, setSidebarWidth] = useState(220);
  const [isResizing, setIsResizing] = useState(false);
  const [rightSidebarWidth, setRightSidebarWidth] = useState(300);
  const [isRightResizing, setIsRightResizing] = useState(false);
  const [toolModalOpen, setToolModalOpen] = useState(false);
  const [agentModalOpen, setAgentModalOpen] = useState(false);
  const [editAgentModalOpen, setEditAgentModalOpen] = useState(false);
  const [editToolModalOpen, setEditToolModalOpen] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [agentToEdit, setAgentToEdit] = useState<AgentFormData | undefined>(undefined);
  const [tools, setTools] = useState<Tool[]>([]);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [toolToEdit, setToolToEdit] = useState<Tool | null>(null);
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
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
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
  const [selectedEdge, setSelectedEdge] = useState<{ sourceId: number | null; targetId: number | null }>({ 
    sourceId: null, 
    targetId: null 
  });

    const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [rightSidebarTabIndex, setRightSidebarTabIndex] = useState(0);

  const toolTypes = [
    { name: 'Database', displayName: 'Database' },
    { name: 'APIService', displayName: 'API Service' },
    { name: 'WebService', displayName: 'Web Service' },
    { name: 'Python', displayName: 'Python' },
    { name: 'React', displayName: 'React' }
  ];

  const getToolDisplayType = (toolType: string): string => {
    const match = toolTypes.find(type => 
      type.name.toLowerCase() === toolType?.toLowerCase()
    );
    return match?.displayName || toolType;
  };

  const getToolDisplayNames = (agentTools: Tool[], allTools: Tool[]): string => {
    if (!agentTools || !agentTools.length) return '';

    return agentTools.map(tool => {
      if (typeof tool === 'string') {
        const t = allTools.find((tt: Tool) => tt.tool_name === tool);
        return t ? t.tool_name : tool;
      }
      return tool.tool_name ||
        (tool.id ? (allTools.find((t: Tool) => t.id === tool.id)?.tool_name || tool.id) : JSON.stringify(tool));
    }).join(', ');
  };

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
      else if (step.role === 'agent') label = `Agent: ${step.agent_name || ''}`;
      else if (step.role === 'tool') label = `Tool: ${step.tool_name || ''}`;
      else label = `Bot: ${step.content}`;
      label = label.replace(/\n/g, ' ').slice(0, 40) + (label.length > 40 ? '...' : '');
      mermaid += `N${idx}[${label}]\n`;
      nodeIds.push(`N${idx}`);
    });
    // Create edges (hierarchy: user->agent->tool->bot)
    history.forEach((step, idx) => {
      if (step.parent_idx !== undefined && step.parent_idx >= 0) {
        mermaid += `N${step.parent_idx} --> N${idx}\n`;
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
        const newWidth = Math.max(300, Math.min(500, windowWidth - e.clientX));
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

  const handleAddAgent = async (agent: any) => {
    try {
      const response = await fetch('/api/agents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: agent.name,
          memory_type: agent.memoryType,
          foundation_model: agent.foundationModel
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create agent');
      }

      const newAgent = await response.json();

      // If the agent has tools, assign them
      if (agent.tools && agent.tools.length > 0) {
        for (const toolName of agent.tools) {
          const tool = tools.find(t => t.tool_name === toolName);
          if (tool) {
            await fetch('/api/agent-tools', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                agent_id: newAgent.id,
                tool_id: tool.id
              })
            });
          }
        }
      }

      // Refresh the agents list
      fetchAgents();
    } catch (error) {
      console.error('Error adding agent:', error);
      alert('Failed to add agent. Please try again.');
    }
  };

  const handleEditAgent = (agent: Agent) => {
    const formData: AgentFormData = {
        id: agent.id.toString(),
        name: agent.name,
        memoryType: agent.memory_type,
        foundationModel: agent.foundation_model,
        tools: agent.tools
    };
    setAgentToEdit(formData);
    setEditAgentModalOpen(true);
    setSelectedAgent(null);
  };

  const handleUpdateAgent = async (agent: { 
    id?: string; 
    name: string; 
    memoryType: string; 
    foundationModel: string; 
    tools: Tool[];
  }): Promise<void> => {
    try {
      if (!agent.id) {
        throw new Error('Agent ID is required for update');
      }

      console.log('Updating agent with data:', agent); // Debug log
      const response = await fetch(`/api/agents/${agent.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: agent.name,
          memory_type: agent.memoryType,
          foundation_model: agent.foundationModel,
          tools: agent.tools
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update agent');
      }

      const updatedAgent = await response.json();
      setAgents(prevAgents => 
        prevAgents.map(a => 
          a.id === parseInt(agent.id!) ? updatedAgent : a
        )
      );
      setEditAgentModalOpen(false);
      setAgentToEdit(undefined);
      setSelectedAgent(null);
    } catch (error) {
      console.error('Error updating agent:', error);
      // Handle error appropriately
    }
  };

  const handleEditTool = (tool: Tool) => {
    setToolToEdit(tool);
    setEditToolModalOpen(true);
  };

  const handleUpdateTool = async (updatedTool: Tool) => {
    try {
      const response = await fetch(`/api/tools/${updatedTool.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tool_name: updatedTool.tool_name,
          tool_type: updatedTool.tool_type,
          hostname: updatedTool.hostname,
          username: updatedTool.username,
          password: updatedTool.password,
          auth_method: updatedTool.auth_method,
          description: updatedTool.description
        })
      });

      if (!response.ok) {
        throw new Error('Failed to update tool');
      }

      // Update tools list
      setTools(prevTools =>
        prevTools.map(tool =>
          tool.id === updatedTool.id ? updatedTool : tool
        )
      );
    } catch (error) {
      console.error('Error updating tool:', error);
      alert('Failed to update tool. Please try again.');
    }
  };

  const handleAddTool = async (tool: Tool) => {
    try {
      const response = await fetch('/api/tools', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tool_name: tool.tool_name,
          tool_type: tool.tool_type,
          hostname: tool.hostname,
          username: tool.username,
          password: tool.password,
          auth_method: tool.auth_method,
          description: tool.description
        })
      });

      if (!response.ok) {
        throw new Error('Failed to add tool');
      }

      const newTool = await response.json();
      setTools(prevTools => [...prevTools, newTool]);
    } catch (error) {
      console.error('Error adding tool:', error);
      alert('Failed to add tool. Please try again.');
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

  // Fetch documents on mount and when team or conversation changes
  useEffect(() => {
    if (selectedTeam?.id) {
      let url = `/api/documents?team_id=${selectedTeam.id}`;
      if (currentConversation?.id) {
        url += `&conversation_id=${currentConversation.id}`;
      }
      
      fetch(url)
        .then(res => {
          if (!res.ok) {
            throw new Error('Failed to fetch documents');
          }
          return res.json();
        })
        .then(data => {
          if (!Array.isArray(data)) {
            console.error('Expected array of documents but got:', data);
            setDocuments([]);
            return;
          }
          setDocuments(data);
        })
        .catch(error => {
          console.error('Error fetching documents:', error);
          setDocuments([]);
        });
    }
  }, [selectedTeam?.id, currentConversation?.id]);

  // Update the handleConversationSettingsSave function
  const handleConversationSettingsSave = async (settings: ConversationSettings) => {
    try {
      // Update local state
      setConversationSettings(settings);

      // If there's a team ID, save settings to backend
      if (selectedTeam?.id) {
        const response = await fetch(`/api/teams/${selectedTeam.id}/conversation-settings`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            temperature: settings.temperature,
            tokenLimit: settings.tokenLimit,
            startPrompt: settings.startPrompt,
            endPrompt: settings.endPrompt,
            style: settings.style
          })
        });

        if (!response.ok) {
          throw new Error('Failed to save conversation settings');
        }

        // Fetch updated settings to ensure we have the latest data
        const updatedResponse = await fetch(`/api/teams/${selectedTeam.id}/conversation-settings`);
        if (updatedResponse.ok) {
          const updatedSettings = await updatedResponse.json();
          setConversationSettings({
            temperature: updatedSettings.temperature,
            tokenLimit: updatedSettings.token_limit,
            startPrompt: updatedSettings.start_prompt,
            endPrompt: updatedSettings.end_prompt,
            style: updatedSettings.style
          });
        }
      }

      // Close the modal
      setConversationSettingsOpen(false);
    } catch (error) {
      console.error('Error saving conversation settings:', error);
      alert('Failed to save conversation settings. Please try again.');
    }
  };

  // Update handleTeamChange to fetch connected sources
  const handleTeamChange = async (teamId: number) => {
    try {
      console.log('Handling team change for team ID:', teamId);
      
      // Find the selected team
      const team = teams.find(t => t.id === teamId);
      if (!team) {
        throw new Error('Team not found');
      }

      // Update selected team
      setSelectedTeam(team);
      console.log('Set selected team:', team);

      // Fetch connected sources for the team
      await fetchConnectedSources(teamId);

      // Fetch team-specific conversation settings
      const response = await fetch(`/api/teams/${teamId}/conversation-settings`);
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
      const docsResponse = await fetch(`/api/documents?team_id=${teamId}`);
      if (docsResponse.ok) {
        const docs = await docsResponse.json();
        setDocuments(docs);
      }
    } catch (error) {
      console.error('Error changing team:', error);
      alert('Failed to change team. Please try again.');
    }
  };

  // Add function to fetch connected sources
  const fetchConnectedSources = async (teamId: number) => {
    try {
      console.log('Fetching connected sources for team:', teamId);
      console.log('Current selected team:', selectedTeam);
      
      // First, fetch the team data which includes tools
      const teamResponse = await fetch(`/api/teams/${teamId}`);
      if (!teamResponse.ok) {
        console.error('Failed to fetch team data:', teamResponse.status, teamResponse.statusText);
        const errorText = await teamResponse.text();
        console.error('Error response:', errorText);
        throw new Error('Failed to fetch team data');
      }
      
      const teamData = await teamResponse.json();
      console.log('Received team data:', teamData);

      if (teamData.tools && teamData.tools.length > 0) {
        // Update the teams state
        setTeams(prevTeams => {
          const updatedTeams = prevTeams.map(team =>
            team.id === teamId
              ? {
                  ...team,
                  tools: teamData.tools
                }
              : team
          );
          console.log('Updated teams:', updatedTeams);
          console.log('Updated team tools:', updatedTeams.find(t => t.id === teamId)?.tools);
          return updatedTeams;
        });
        
        // Also update the selected team directly
        setSelectedTeam(prev => prev && prev.id === teamId ? { ...prev, tools: teamData.tools } : prev);
      } else {
        console.log('No tools found for team:', teamId);
      }
      
    } catch (error) {
      console.error('Error fetching connected sources:', error);
    }
  };

  const handleEdgeClick = (sourceId: number, targetId: number) => {
    // If sourceId is -1, it means we're clearing the selection
    if (sourceId === -1) {
      setSelectedEdge({ sourceId: null, targetId: null });
    } else {
      setSelectedEdge({ sourceId, targetId });
    }
  };

  // Add the handleDisconnectSource function
  const handleDisconnectSource = async (sourceId: string) => {
    try {
      if (!selectedTeam?.id) return;

      const response = await fetch(`/api/teams/${selectedTeam.id}/sources/${sourceId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to disconnect source');
      }

      // Update the team's tools list with proper type
      setTeams(prevTeams =>
        prevTeams.map(team =>
          team.id === selectedTeam.id
            ? {
                ...team,
                tools: team.tools.filter((tool: Tool) => tool.id.toString() !== sourceId)
              }
            : team
        )
      );
    } catch (error) {
      console.error('Error disconnecting source:', error);
      alert('Failed to disconnect source. Please try again.');
    }
  };

  const handleAddAgentClick = () => {
    setAgentModalOpen(true);
  };

  const handleAddToolClick = () => {
    setToolModalOpen(true);
  };

  const handleAgentClick = (agent: any) => {
    setSelectedAgent(agent);
  };

  const handleToolClick = (tool: any) => {
    setSelectedTool(tool);
  };

  // Handle file upload
  const handleFileUpload = async (file: File): Promise<Document> => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('team_id', selectedTeam?.id?.toString() || '');
      if (currentConversation?.id) {
        formData.append('conversation_id', currentConversation.id.toString());
      }

      const response = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Failed to upload file');
      }

      const document = await response.json();
      setDocuments(prev => [document, ...prev]);
      return document;
    } catch (error) {
      console.error('Error uploading file:', error);
      throw new Error('Failed to upload file. Please try again.');
    }
  };

  const handleCreateAgent = async (formData: {
    name: string;
    memoryType: string;
    foundationModel: string;
    tools: Tool[];
  }): Promise<void> => {
    try {
      const response = await fetch('/api/agents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: formData.name,
          memory_type: formData.memoryType,
          foundation_model: formData.foundationModel,
          tools: formData.tools.map(tool => ({
            id: tool.id
          }))
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create agent');
      }

      const newAgent = await response.json();
      setAgents(prevAgents => [...prevAgents, newAgent]);
      setAgentModalOpen(false);
    } catch (error) {
      console.error('Error creating agent:', error);
      // Handle error appropriately
    }
  };

  const toggleTheme = () => {
    setMode(prevMode => prevMode === 'light' ? 'dark' : 'light');
  };

  return (
    <ThemeProvider theme={getTheme(mode)}>
      <CssBaseline />
      <Router>
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
          <TopBar onThemeToggle={toggleTheme} mode={mode} />
          {/* Main Content */}
          <Box sx={{ flex: 1, display: 'flex', minHeight: 0 }}>
            {/* Left Sidebar */}
            <LeftSidebar
              width={sidebarWidth}
              onResize={(e) => {
                if (e.buttons === 1) {
                  setIsResizing(true);
                }
              }}
              onAddAgentClick={handleAddAgentClick}
              onAddToolClick={handleAddToolClick}
              onAgentClick={handleAgentClick}
              onToolClick={handleToolClick}
              agents={agents}
              tools={tools}
            />

            {/* Main Content Area with Chat Controls */}
            <Box sx={{ 
              flex: 1, 
              display: 'flex', 
              flexDirection: 'column', 
              minWidth: 0,
              maxWidth: `calc(100% - ${sidebarWidth}px - ${rightSidebarWidth}px)` 
            }}>
              <ChatControls
                onNewChat={handleNewChat}
              />
              <MainContent
                conversationHistory={conversationHistory}
                setConversationHistory={setConversationHistory}
                selectedTeam={selectedTeam}
                onFileUpload={handleFileUpload}
              />
            </Box>

            {/* Right Sidebar */}
            <RightSidebar
              width={rightSidebarWidth}
              onResize={handleRightMouseDown}
              showConversationHistory={showConversationHistory}
              tabIndex={rightSidebarTabIndex}
              setTabIndex={setRightSidebarTabIndex}
              documents={documents}
              conversationHistoryList={conversationHistoryList}
              onLoadConversation={handleLoadConversation}
              onDeleteConversation={handleDeleteConversation}
              onDeleteDocument={handleDeleteDocument}
              onDownloadDocument={handleDownloadDocument}
              onTeamSettings={() => setTeamSettingsOpen(true)}
              onAgentSettings={() => setAgentSettingsOpen(true)}
              onExecutionPlan={() => setExecutionPlanOpen(true)}
              onConnectedSources={() => setConnectedSourcesOpen(true)}
              onConversationSettings={() => setConversationSettingsOpen(true)}
              renamingIdx={renamingIdx}
              renameValue={renameValue}
              onStartRename={handleStartRename}
              onSaveRename={handleSaveRename}
              setRenameValue={setRenameValue}
              team={selectedTeam}
              onDisconnect={handleDisconnectSource}
            />
          </Box>

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
            team={selectedTeam}
            onDisconnect={handleDisconnectSource}
          />
          <AgentSettingsModal
            open={agentSettingsOpen}
            onClose={() => {
              setAgentSettingsOpen(false);
              setSelectedEdge({ sourceId: null, targetId: null });
            }}
            teams={teams}
            selectedEdge={selectedEdge}
            onEdgeClick={handleEdgeClick}
          />

          {/* Agent Details Dialog */}
          {selectedAgent && (
            <Dialog open={!!selectedAgent} onClose={() => setSelectedAgent(null)} maxWidth="xs" fullWidth>
              <DialogTitle>Agent Details</DialogTitle>
              <DialogContent>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
                  <Box><b>Name:</b> {selectedAgent.name}</Box>
                  <Box><b>Type of Memory:</b> {selectedAgent.memory_type}</Box>
                  <Box><b>Foundation Model:</b> {selectedAgent.foundation_model}</Box>
                  <Box>
                    <b>Tools:</b> {getToolDisplayNames(selectedAgent.tools || [], tools)}
                  </Box>
                </Box>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setSelectedAgent(null)}>Close</Button>
                <Button onClick={() => handleEditAgent(selectedAgent)} color="primary" variant="contained">Edit</Button>
              </DialogActions>
            </Dialog>
          )}

          {/* Tool Details Dialog */}
          {selectedTool && (
            <Dialog open={!!selectedTool} onClose={() => setSelectedTool(null)} maxWidth="xs" fullWidth>
              <DialogTitle>Tool Details</DialogTitle>
              <DialogContent>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
                  <Box><b>Name:</b> {selectedTool.tool_name}</Box>
                  <Box><b>Type:</b> {getToolDisplayType(selectedTool.tool_type)}</Box>
                  <Box><b>Host:</b> {selectedTool.hostname}</Box>
                  <Box><b>Auth Method:</b> {selectedTool.auth_method}</Box>
                </Box>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setSelectedTool(null)}>Close</Button>
                <Button onClick={() => handleEditTool(selectedTool)} color="primary" variant="contained">Edit</Button>
              </DialogActions>
            </Dialog>
          )}

          {/* Add/Edit Agent Modal */}
          <AgentConfigModal 
            open={agentModalOpen} 
            onClose={() => setAgentModalOpen(false)} 
            onSave={handleCreateAgent} 
            tools={tools} 
          />
          <AgentConfigModal 
            open={editAgentModalOpen} 
            onClose={() => setEditAgentModalOpen(false)} 
            onSave={handleUpdateAgent} 
            tools={tools} 
            initialValues={agentToEdit} 
            mode="edit" 
          />

          {/* Add/Edit Tool Modal */}
          <ToolConfigModal 
            open={toolModalOpen} 
            onClose={() => setToolModalOpen(false)} 
            onSave={handleAddTool} 
          />
          <ToolConfigModal 
            open={editToolModalOpen} 
            onClose={() => setEditToolModalOpen(false)} 
            onSave={handleUpdateTool} 
            initialValues={toolToEdit || undefined} 
            mode="edit" 
          />
        </Box>
      </Router>
    </ThemeProvider>
  );
};

export default App;

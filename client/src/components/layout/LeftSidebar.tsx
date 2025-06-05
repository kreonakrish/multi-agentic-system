import React, { useState, useEffect } from 'react';
import { Box, Button, Tab, Tabs } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import StorageIcon from '@mui/icons-material/Storage';
import ApiIcon from '@mui/icons-material/Api';
import CloudIcon from '@mui/icons-material/Cloud';
import CodeIcon from '@mui/icons-material/Code';
import HttpIcon from '@mui/icons-material/Http';
import JavascriptIcon from '@mui/icons-material/Javascript';

// Use appropriate Material-UI icons as substitutes
const RestIcon = HttpIcon;
const PythonIcon = CodeIcon;
const ReactIcon = JavascriptIcon;

interface LeftSidebarProps {
  width: number;
  onResize: (e: React.MouseEvent) => void;
  onAddAgentClick?: () => void;
  onAddToolClick?: () => void;
  onAgentClick?: (agent: any) => void;
  onToolClick?: (tool: any) => void;
  agents: any[];
  tools: any[];
}

const agentTypes = [
  { name: 'DBx', color: '#42b72a', icon: <StorageIcon /> },
  { name: 'Nifi', color: '#1877f2', icon: <ApiIcon /> },
  { name: 'AWS', color: '#ff5a5f', icon: <CloudIcon /> },
  { name: 'RDS', color: '#8b5cf6', icon: <StorageIcon /> },
  { name: 'Confluence', color: '#f7b928', icon: <ApiIcon /> },
  { name: 'Caspian', color: '#00bcd4', icon: <CloudIcon /> },
  { name: 'Sender', color: '#ff9800', icon: <ApiIcon /> },
  { name: 'Receiver', color: '#34495e', icon: <SmartToyIcon /> }
];

const toolTypes = [
  { name: 'Database', color: '#4caf50', icon: <StorageIcon /> },
  { name: 'APIService', color: '#2196f3', icon: <ApiIcon /> },
  { name: 'WebService', color: '#ff9800', icon: <CloudIcon /> },
  { name: 'DB', color: '#4caf50', icon: <StorageIcon /> },
  { name: 'REST', color: '#e91e63', icon: <RestIcon /> },
  { name: 'Python', color: '#ffd600', icon: <PythonIcon /> },
  { name: 'React', color: '#00bcd4', icon: <ReactIcon /> },
  { name: 'Cloud', color: '#ff9800', icon: <CloudIcon /> }
];

const getAgentColor = (agentName: string): string => {
  // Find the first matching agent type
  const agentType = agentTypes.find(type => 
    agentName.toLowerCase().includes(type.name.toLowerCase())
  );
  return agentType?.color || '#5b8aca'; // Default color if no match
};

const getAgentIcon = (agentName: string) => {
  // Find the first matching agent type
  const agentType = agentTypes.find(type => 
    agentName.toLowerCase().includes(type.name.toLowerCase())
  );
  return agentType?.icon || <SmartToyIcon />;
};

const getToolColor = (toolName: string, toolType: string): string => {
  // First try to match by tool type
  const toolTypeMatch = toolTypes.find(type => 
    toolType?.toLowerCase().includes(type.name.toLowerCase())
  );
  if (toolTypeMatch) return toolTypeMatch.color;

  // If no match by type, try to match by name
  const toolNameMatch = toolTypes.find(type => 
    toolName.toLowerCase().includes(type.name.toLowerCase())
  );
  return toolNameMatch?.color || '#f0f2f5'; // Default color if no match
};

const getToolIcon = (toolName: string, toolType: string) => {
  // First try to match by tool type
  const toolTypeMatch = toolTypes.find(type => 
    toolType?.toLowerCase().includes(type.name.toLowerCase())
  );
  if (toolTypeMatch) return toolTypeMatch.icon;

  // If no match by type, try to match by name
  const toolNameMatch = toolTypes.find(type => 
    toolName.toLowerCase().includes(type.name.toLowerCase())
  );
  return toolNameMatch?.icon || <CloudIcon />;
};

const LeftSidebar: React.FC<LeftSidebarProps> = ({ 
  width, 
  onResize,
  onAddAgentClick = () => {},
  onAddToolClick = () => {},
  onAgentClick = () => {},
  onToolClick = () => {},
  agents = [],
  tools = []
}) => {
  const [selectedTab, setSelectedTab] = useState(0);

  return (
    <Box
      sx={{
        width,
        minWidth: 300,
        maxWidth: 400,
        height: '100%',
        bgcolor: '#fff',
        borderRight: '1px solid',
        borderColor: 'divider',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative'
      }}
    >
      <Tabs
        value={selectedTab}
        onChange={(_, value) => setSelectedTab(value)}
        sx={{
          minHeight: 48,
          borderBottom: 1,
          borderColor: 'divider',
          '& .MuiTab-root': {
            minHeight: 48,
            color: '#65676b',
            fontWeight: 600,
            '&.Mui-selected': {
              color: '#1877f2'
            }
          }
        }}
      >
        <Tab label="Agents" sx={{ flex: 1 }} />
        <Tab label="Tools" sx={{ flex: 1 }} />
      </Tabs>

      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {selectedTab === 0 && (
          <>
            <Button
              variant="contained"
              fullWidth
              startIcon={<AddIcon />}
              onClick={onAddAgentClick}
              sx={{
                mb: 2,
                bgcolor: '#1877f2',
                color: '#fff',
                fontWeight: 600,
                '&:hover': {
                  bgcolor: '#166fe5'
                }
              }}
            >
              Add Agent
            </Button>

            {agents.map((agent) => (
              <Button
                key={agent.id}
                variant="contained"
                fullWidth
                startIcon={getAgentIcon(agent.name)}
                onClick={() => onAgentClick(agent)}
                sx={{
                  mb: 1,
                  bgcolor: getAgentColor(agent.name),
                  color: '#fff',
                  justifyContent: 'flex-start',
                  textAlign: 'left',
                  fontWeight: 600,
                  '&:hover': {
                    filter: 'brightness(0.9)'
                  }
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: '100%' }}>
                  <div>{agent.name}</div>
                  {agent.tools && agent.tools.length > 0 && (
                    <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.8)' }}>
                      Tools: {agent.tools.map((tool: any) => 
                        typeof tool === 'object' && tool !== null
                          ? tool.toolName || tool.tool_name
                          : tool
                      ).filter(Boolean).join(', ')}
                    </div>
                  )}
                </Box>
              </Button>
            ))}
          </>
        )}

        {selectedTab === 1 && (
          <>
            <Button
              variant="contained"
              fullWidth
              startIcon={<AddIcon />}
              onClick={onAddToolClick}
              sx={{
                mb: 2,
                bgcolor: '#1877f2',
                color: '#fff',
                fontWeight: 600,
                '&:hover': {
                  bgcolor: '#166fe5'
                }
              }}
            >
              Add Tool
            </Button>

            {tools.map((tool) => {
              const toolName = tool.tool_name;
              const toolType = tool.tool_type;
              return (
                <Button
                  key={tool.id}
                  variant="contained"
                  fullWidth
                  startIcon={getToolIcon(toolName, toolType)}
                  onClick={() => onToolClick(tool)}
                  sx={{
                    mb: 1,
                    bgcolor: getToolColor(toolName, toolType),
                    color: '#fff',
                    justifyContent: 'flex-start',
                    textAlign: 'left',
                    fontWeight: 600,
                    '&:hover': {
                      filter: 'brightness(0.9)'
                    }
                  }}
                >
                  <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: '100%' }}>
                    <div>{toolName}</div>
                    <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.8)' }}>
                      Type: {toolType}
                    </div>
                  </Box>
                </Button>
              );
            })}
          </>
        )}
      </Box>

      <div
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          bottom: 0,
          width: '4px',
          cursor: 'col-resize',
          background: 'transparent'
        }}
        onMouseDown={onResize}
      />
    </Box>
  );
};

export default LeftSidebar; 
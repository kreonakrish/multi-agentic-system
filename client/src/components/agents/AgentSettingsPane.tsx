import React from 'react';
import { Box, Typography, Paper, List, ListItem, ListItemText, Divider } from '@mui/material';
import { Agent } from '../../store/types';

interface AgentSettingsPaneProps {
  selectedEdge: { sourceId: number | null; targetId: number | null };
  agents: Agent[];
}

const AgentSettingsPane: React.FC<AgentSettingsPaneProps> = ({
  selectedEdge,
  agents,
}) => {
  const sourceAgent = agents.find(a => a.id === selectedEdge.sourceId);
  const targetAgent = agents.find(a => a.id === selectedEdge.targetId);

  if (!sourceAgent || !targetAgent) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="body1" color="text.secondary">
          Select an edge to view agent settings
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Agent Settings
      </Typography>
      
      <Paper sx={{ mb: 2, p: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          Source Agent: {sourceAgent.name}
        </Typography>
        <List dense>
          <ListItem>
            <ListItemText
              primary="Memory Type"
              secondary={sourceAgent.memory_type}
            />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="Foundation Model"
              secondary={sourceAgent.foundation_model}
            />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="Status"
              secondary={sourceAgent.status}
            />
          </ListItem>
        </List>
      </Paper>

      <Divider sx={{ my: 2 }} />

      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          Target Agent: {targetAgent.name}
        </Typography>
        <List dense>
          <ListItem>
            <ListItemText
              primary="Memory Type"
              secondary={targetAgent.memory_type}
            />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="Foundation Model"
              secondary={targetAgent.foundation_model}
            />
          </ListItem>
          <ListItem>
            <ListItemText
              primary="Status"
              secondary={targetAgent.status}
            />
          </ListItem>
        </List>
      </Paper>
    </Box>
  );
};

export default AgentSettingsPane; 
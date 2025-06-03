import React, { useState, useEffect } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import AgentHierarchyGraph from './AgentHierarchyGraph';
import AgentInteractions from './AgentInteractions';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';

interface AgentSettingsModalProps {
  open: boolean;
  onClose: () => void;
  teams: any[];
  selectedEdge: { sourceId: number | null; targetId: number | null };
  onEdgeClick: (sourceId: number, targetId: number) => void;
}

const AgentSettingsModal: React.FC<AgentSettingsModalProps> = ({ 
  open, 
  onClose, 
  teams,
  selectedEdge,
  onEdgeClick
}) => {
  const [selectedTeam, setSelectedTeam] = useState<number | undefined>();
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [teamAgents, setTeamAgents] = useState<any[]>([]);

  useEffect(() => {
    // Fetch team agents when a team is selected
    if (selectedTeam) {
      fetch(`/api/teams/${selectedTeam}`)
        .then(res => res.json())
        .then(data => {
          setTeamAgents(data.agents.map((agent: any) => ({
            id: agent.id,
            name: agent.name,
            priority: agent.priority || 1,
            accuracy: agent.accuracy || 100,
            success: agent.success || 100
          })));
        })
        .catch(error => {
          console.error('Error fetching team agents:', error);
        });
    }
  }, [selectedTeam]);

  // Handle edge click from the hierarchy graph
  const handleEdgeClick = (sourceId: number, targetId: number) => {
    onEdgeClick(sourceId, targetId);
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="xl"
      fullWidth
      PaperProps={{
        sx: { height: '80vh' }
      }}
    >
      <DialogTitle>Agent Settings</DialogTitle>
      <DialogContent>
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
          <FormControl fullWidth>
            <InputLabel>Select Team</InputLabel>
            <Select
              value={selectedTeam || ''}
              label="Select Team"
              onChange={(e) => setSelectedTeam(e.target.value as number)}
            >
              {teams.map(team => (
                <MenuItem key={team.id} value={team.id}>
                  {team.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {selectedTeam && (
            <PanelGroup direction="horizontal">
              <Panel defaultSize={50} minSize={30}>
                <Box sx={{ height: '100%', p: 2 }}>
                  <AgentHierarchyGraph
                    agents={teamAgents}
                    selectedAgents={selectedAgents}
                    onEdgeClick={handleEdgeClick}
                    onBackgroundClick={() => onEdgeClick(-1, -1)}
                  />
                </Box>
              </Panel>
              
              <PanelResizeHandle 
                style={{
                  width: '8px',
                  background: '#f0f0f0',
                  border: '1px solid #ddd',
                  borderTop: 'none',
                  borderBottom: 'none',
                  cursor: 'col-resize'
                }}
              />
              
              <Panel defaultSize={50} minSize={30}>
                <Box sx={{ height: '100%', p: 2, bgcolor: 'background.paper' }}>
                  <AgentInteractions
                    teamId={selectedTeam}
                    sourceId={selectedEdge.sourceId}
                    targetId={selectedEdge.targetId}
                  />
                </Box>
              </Panel>
            </PanelGroup>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default AgentSettingsModal; 
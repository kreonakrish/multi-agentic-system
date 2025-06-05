import React, { useState, useEffect } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Box, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import AgentHierarchyGraph from '../agents/AgentHierarchyGraph';
import AgentInteractions from '../agents/AgentInteractions';
import { Team } from '../../store/types';

export interface AgentSettingsModalProps {
  open: boolean;
  onClose: () => void;
  teams: Team[];
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
  const [teamAgents, setTeamAgents] = useState<any[]>([]);

  useEffect(() => {
    // Reset selected team when modal opens
    if (open) {
      setSelectedTeam(undefined);
      setTeamAgents([]);
    }
  }, [open]);

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

  const handleTeamChange = (event: any) => {
    const teamId = event.target.value;
    setSelectedTeam(teamId);
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
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2, p: 2 }}>
          <FormControl fullWidth>
            <InputLabel>Select Team</InputLabel>
            <Select
              value={selectedTeam || ''}
              label="Select Team"
              onChange={handleTeamChange}
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
                    onEdgeClick={onEdgeClick}
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
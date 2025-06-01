import React, { useState, useEffect } from 'react';
import { Box, FormControl, InputLabel, Select, MenuItem, Typography, Checkbox, FormControlLabel } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import AgentHierarchyGraph from './AgentHierarchyGraph';
import CloseIcon from '@mui/icons-material/Close';
import IconButton from '@mui/material/IconButton';

interface TeamAgent {
  id: number;
  name: string;
  accuracy: number;
  success: number;
  priority: number;
}

interface Team {
  id: number;
  name: string;
  agents: TeamAgent[];
}

interface AgentInteraction {
  id: number;
  source_agent_id: number;
  target_agent_id: number;
  interaction_type: string;
  timestamp: string;
  success_rate: number;
  details: string;
}

interface AgentSettingsPaneProps {
  teams: Team[];
  onAgentSelection?: (agents: string[]) => void;
  onTeamChange?: (teamId: number) => void;
}

const AgentSettingsPane: React.FC<AgentSettingsPaneProps> = ({ 
  teams, 
  onAgentSelection = () => {}, 
  onTeamChange = () => {} 
}) => {
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [interactions, setInteractions] = useState<AgentInteraction[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (teams.length > 0 && !selectedTeam) {
      setSelectedTeam(teams[0]);
      onTeamChange(teams[0].id);
    }
  }, [teams]);

  const handleTeamChange = (event: any) => {
    const team = teams.find(t => t.id === event.target.value);
    if (team) {
      setSelectedTeam(team);
      setSelectedAgents([]);
      onTeamChange(team.id);
    }
  };

  const handleAgentToggle = (agentName: string) => {
    const newSelectedAgents = selectedAgents.includes(agentName)
      ? selectedAgents.filter(name => name !== agentName)
      : [...selectedAgents, agentName];
    
    setSelectedAgents(newSelectedAgents);
    onAgentSelection(newSelectedAgents);
  };

  const fetchTeamData = async (teamId: number) => {
    try {
      const response = await fetch(`/api/teams/${teamId}`);
      const data = await response.json();
      setSelectedTeam(data);
    } catch (error) {
      console.error('Error fetching team data:', error);
    }
  };

  const handleEdgeClick = async (sourceId: number, targetId: number) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/agent-interactions?source=${sourceId}&target=${targetId}`);
      const data = await response.json();
      setInteractions(data);
    } catch (error) {
      console.error('Error fetching interactions:', error);
    } finally {
      setLoading(false);
    }
  };

  const columns: GridColDef[] = [
    { field: 'id', headerName: 'ID', width: 90 },
    { field: 'source_agent', headerName: 'Source Agent', width: 150 },
    { field: 'target_agent', headerName: 'Target Agent', width: 150 },
    { field: 'interaction_type', headerName: 'Type', width: 130 },
    { field: 'timestamp', headerName: 'Timestamp', width: 180 },
    { field: 'success_rate', headerName: 'Success Rate', width: 130 },
    { field: 'details', headerName: 'Details', width: 300 },
  ];

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="h6">Agent Settings</Typography>
      
      <FormControl fullWidth>
        <InputLabel>Select Team</InputLabel>
        <Select
          value={selectedTeam?.id || ''}
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
        <>
          <Typography variant="h6" gutterBottom>
            Agent Selection
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {selectedTeam.agents.map(agent => (
              <FormControlLabel
                key={agent.name}
                control={
                  <Checkbox
                    checked={selectedAgents.includes(agent.name)}
                    onChange={() => handleAgentToggle(agent.name)}
                  />
                }
                label={agent.name}
              />
            ))}
          </Box>

          <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
            Agent Hierarchy
          </Typography>
          <Box sx={{ flex: 1, minHeight: 0 }}>
            <AgentHierarchyGraph
              agents={selectedTeam.agents}
              selectedAgents={selectedAgents}
            />
          </Box>

          <Typography variant="h6" sx={{ mt: 2 }}>Agent Interactions</Typography>
          <Box sx={{ height: '40%', minHeight: 300 }}>
            <DataGrid
              rows={interactions}
              columns={columns}
              loading={loading}
              pageSizeOptions={[5, 10, 25]}
              initialState={{
                pagination: { paginationModel: { pageSize: 5 } },
              }}
            />
          </Box>
        </>
      )}
    </Box>
  );
};

export default AgentSettingsPane; 
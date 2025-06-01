import React, { useState, useEffect } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import MenuItem from '@mui/material/MenuItem';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import Checkbox from '@mui/material/Checkbox';
import axios, { AxiosError } from 'axios';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { Rnd } from 'react-rnd';
import AgentHierarchyGraph from './AgentHierarchyGraph';

interface TeamAgent {
  id: number;
  name: string;
  accuracy: number;
  success: number;
  priority: number; // Add priority property
}

interface Team {
  id: number;
  name: string;
  agents: TeamAgent[];
}

interface TeamResponse {
  id: number;
  name: string;
  agents: {
    id: number;
    name: string;
    accuracy: number;
    success: number;
    priority: number;
  }[];
}

interface TeamSettingsModalProps {
  open: boolean;
  onClose: () => void;
  agents: any[];
  teams: Team[];
  setTeams: (teams: Team[]) => void;
  selectedTeam: Team | null;
  setSelectedTeam: (team: Team | null) => void;
}

const TeamSettingsModal: React.FC<TeamSettingsModalProps> = ({
                                                               open,
                                                               onClose,
                                                               agents,
                                                               teams,
                                                               setTeams,
                                                               selectedTeam,
                                                               setSelectedTeam
                                                             }) => {
  const [newTeamName, setNewTeamName] = useState('');
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [teamAgents, setTeamAgents] = useState<TeamAgent[]>([]);
  const [editMode, setEditMode] = useState(false);

  useEffect(() => {
    if (selectedTeam) {
      setEditMode(true);
      setNewTeamName(selectedTeam.name);
      // Get fresh team data when selecting a team
      fetch(`/api/teams/${selectedTeam.id}`)
        .then(res => res.json())
        .then(teamData => {
          const initializedAgents = (teamData.agents || []).map((agent: TeamAgent) => ({
            ...agent,
            accuracy: Number(agent.accuracy),
            success: Number(agent.success),
            priority: Number(agent.priority)
          }));
          console.log('Initialized agents from DB:', initializedAgents);
          setTeamAgents(initializedAgents);
          setSelectedAgents(initializedAgents.map((a: TeamAgent) => a.name));
        })
        .catch(error => {
          console.error('Error fetching team data:', error);
          // Fallback to existing data if fetch fails
          const initializedAgents = (selectedTeam.agents || []).map((agent: TeamAgent) => ({
            ...agent,
            accuracy: Number(agent.accuracy),
            success: Number(agent.success),
            priority: Number(agent.priority)
          }));
          setTeamAgents(initializedAgents);
          setSelectedAgents(initializedAgents.map((a: TeamAgent) => a.name));
        });
    } else {
      setEditMode(false);
      setNewTeamName('');
      setTeamAgents([]);
      setSelectedAgents([]);
    }
  }, [selectedTeam, open]);

  const handleAddAgent = (agentName: string) => {
    if (!teamAgents.find(a => a.name === agentName)) {
      setTeamAgents([
        ...teamAgents,
        { id: Date.now(), name: agentName, accuracy: 100, success: 100, priority: 1 }
      ]);
    }
  };

  const handleRemoveAgent = async (agentName: string) => {
    const agent = teamAgents.find(a => a.name === agentName);
    if (agent && selectedTeam) {
      try {
        await axios.delete('/api/team-agents', {
          data: { team_id: selectedTeam.id, agent_id: agent.id }
        });
        setTeamAgents(teamAgents.filter(a => a.name !== agentName));
      } catch (err) {
        alert('Failed to remove agent from team');
      }
    } else {
      setTeamAgents(teamAgents.filter(a => a.name !== agentName));
    }
  };

  const handleMoveAgent = (index: number, direction: 'up' | 'down') => {
    const newAgents = [...teamAgents];
    if (direction === 'up' && index > 0) {
      [newAgents[index - 1], newAgents[index]] = [newAgents[index], newAgents[index - 1]];
    } else if (direction === 'down' && index < newAgents.length - 1) {
      [newAgents[index + 1], newAgents[index]] = [newAgents[index], newAgents[index + 1]];
    }
    setTeamAgents(newAgents);
  };

  const handleAccuracyChange = (index: number, value: number) => {
    const newAgents = [...teamAgents];
    newAgents[index].accuracy = value;
    console.log(`Setting accuracy for ${newAgents[index].name} to:`, value);
    setTeamAgents(newAgents);
  };

  const handleSuccessChange = (index: number, value: number) => {
    const newAgents = [...teamAgents];
    newAgents[index].success = value;
    console.log(`Setting success for ${newAgents[index].name} to:`, value);
    setTeamAgents(newAgents);
  };

  const handlePriorityChange = (index: number, value: number) => {
    const newAgents = [...teamAgents];
    newAgents[index].priority = value;
    console.log(`Setting priority for ${newAgents[index].name} to:`, value);
    setTeamAgents(newAgents);
  };

  const handleCreateTeam = async () => {
    if (!newTeamName) return;
    try {
      // Map agents with their correct IDs and metrics
      const agentsWithMetrics = teamAgents.map(agent => {
        const originalAgent = agents.find(a => a.name === agent.name);
        if (!originalAgent) {
          throw new Error(`Agent ${agent.name} not found in available agents`);
        }
        return {
          id: originalAgent.id,
          accuracy: Number(agent.accuracy),
          success: Number(agent.success),
          priority: Number(agent.priority)
        };
      });

      // Create the team with all data in one request
      const response = await axios.post('/api/teams', {
        name: newTeamName,
        agents: agentsWithMetrics
      });

      if (response.data) {
        // Fetch the newly created team to ensure we have the correct data
        const teamResponse = await axios.get(`/api/teams/${response.data.id}`);
        const newTeam = teamResponse.data;

        setTeams([...teams, newTeam]);
        setNewTeamName('');
        setTeamAgents([]);
        setSelectedAgents([]);
        onClose();
      }
    } catch (err) {
      console.error('Failed to create team:', err);
      alert('Failed to create team. Please try again.');
    }
  };

  const handleUpdateTeam = async () => {
    if (!selectedTeam) return;
    try {
      // Map the agents to include only the necessary data and ensure values are numbers
      const agentsData = teamAgents.map(agent => {
        // Find the corresponding agent from the agents prop to get the correct ID
        const originalAgent = agents.find(a => a.name === agent.name);
        const data = {
          id: originalAgent?.id || agent.id,
          accuracy: Number(agent.accuracy) || 100,
          success: Number(agent.success) || 100,
          priority: Number(agent.priority) || 1
        };
        console.log('Agent data being sent:', agent.name, data);
        return data;
      });

      console.log('Sending team update with data:', { name: newTeamName, agents: agentsData });

      const response = await axios.put<TeamResponse>(`/api/teams/${selectedTeam.id}`, {
        name: newTeamName,
        agents: agentsData
      });

      console.log('Received response:', response.data);

      if (response.data) {
        // Update local state with the response data
        const updatedTeam = {
          ...selectedTeam,
          name: newTeamName,
          agents: response.data.agents.map((agent: TeamResponse['agents'][0]) => ({
            id: agent.id,
            name: agent.name,
            accuracy: Number(agent.accuracy) || 100,
            success: Number(agent.success) || 100,
            priority: Number(agent.priority) || 1
          }))
        };

        console.log('Updated team state:', updatedTeam);
        setTeams(teams.map(t => t.id === selectedTeam.id ? updatedTeam : t));
        setSelectedTeam(updatedTeam);
        onClose();
      }
    } catch (error) {
      const err = error as AxiosError<{ error: string; details?: string }>;
      console.error('Failed to update team:', err);
      const errorMessage = err.response?.data?.details || err.message || 'An unknown error occurred';
      alert(`Failed to update team: ${errorMessage}`);
    }
  };

  const handleDeleteTeam = async (teamId: number) => {
    try {
      await axios.delete(`/api/teams/${teamId}`);
      setTeams(teams.filter(t => t.id !== teamId));
      setSelectedTeam(null);
    } catch (err) {
      alert('Failed to delete team');
    }
  };

  const handleAssignAgent = async (teamId: number, agentId: number) => {
    try {
      await axios.post('/api/team-agents', { team_id: teamId, agent_id: agentId });
    } catch (err) {
      alert('Failed to assign agent to team');
    }
  };

  const handleAgentSelection = (event: SelectChangeEvent<string[]>) => {
    const value = event.target.value as string[];
    setSelectedAgents(value);
    
    const updatedAgents = value.map((agentName: string) => {
      const existingAgent = teamAgents.find(a => a.name === agentName);
      const originalAgent = agents.find(a => a.name === agentName);
      
      if (existingAgent) {
        return {
          ...existingAgent,
          accuracy: Number(existingAgent.accuracy),
          success: Number(existingAgent.success),
          priority: Number(existingAgent.priority)
        };
      }
      
      // For new agents, use default values
      const newAgent = {
        id: originalAgent?.id || Date.now(),
        name: agentName,
        accuracy: 100,
        success: 100,
        priority: 1
      };
      console.log('Creating new agent:', newAgent);
      return newAgent;
    });
    
    console.log('Updated team agents:', updatedAgents);
    setTeamAgents(updatedAgents);
  };

  return (
      <Rnd
          default={{ x: 100, y: 100, width: 800, height: 600 }}
          minWidth={500}
          minHeight={400}
          bounds="window"
          enableResizing={{
            top: true,
            right: true,
            bottom: true,
            left: true,
            topRight: true,
            bottomRight: true,
            bottomLeft: true,
            topLeft: true
          }}
          dragHandleClassName="team-settings-modal-title"
          style={{ zIndex: 1300, position: 'fixed' }}
      >
        <div style={{ width: '100%', height: '100%' }}>
          <Dialog
              open={open}
              onClose={onClose}
              maxWidth={false}
              fullWidth={false}
              PaperProps={{
                style: {
                  height: '80%',
                  width: '80%',
                  margin: 'auto',
                  minHeight: 0,
                  minWidth: 0,
                  boxSizing: 'border-box',
                  display: 'flex',
                  flexDirection: 'column',
                }
              }}
          >
            <DialogTitle className="team-settings-modal-title">Team Settings</DialogTitle>
            <DialogContent>
              <PanelGroup direction="horizontal" style={{ height: 500 }}>
                <Panel minSize={20} defaultSize={70} style={{ overflow: 'auto' }}>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, height: '100%' }}>
                    <TextField
                        label="New Team Name"
                        value={newTeamName}
                        onChange={e => setNewTeamName(e.target.value)}
                        fullWidth
                    />
                    <Select<string[]>
                        multiple
                        value={selectedAgents}
                        onChange={(event: SelectChangeEvent<string[]>) => {
                          const value = event.target.value as string[];
                          setSelectedAgents(value);
                          
                          const updatedAgents = value.map((agentName: string) => {
                            const existingAgent = teamAgents.find(a => a.name === agentName);
                            const originalAgent = agents.find(a => a.name === agentName);
                            
                            if (existingAgent) {
                              return {
                                ...existingAgent,
                                accuracy: Number(existingAgent.accuracy),
                                success: Number(existingAgent.success),
                                priority: Number(existingAgent.priority)
                              };
                            }
                            
                            const newAgent = {
                              id: originalAgent?.id || Date.now(),
                              name: agentName,
                              accuracy: 100,
                              success: 100,
                              priority: 1
                            };
                            console.log('Creating new agent:', newAgent);
                            return newAgent;
                          });
                          
                          console.log('Updated team agents:', updatedAgents);
                          setTeamAgents(updatedAgents);
                        }}
                        renderValue={(selected) => selected.join(', ')}
                        fullWidth
                        displayEmpty
                    >
                      {agents.map(agent => (
                          <MenuItem key={agent.name} value={agent.name}>
                            <Checkbox checked={selectedAgents.indexOf(agent.name) > -1} />
                            {agent.name}
                          </MenuItem>
                      ))}
                    </Select>
                    <List>
                      {teamAgents.map((agent, idx) => (
                          <ListItem
                              key={agent.name}
                              secondaryAction={
                                <>
                                  <IconButton onClick={() => handleMoveAgent(idx, 'up')} disabled={idx === 0}>
                                    <ArrowUpwardIcon />
                                  </IconButton>
                                  <IconButton
                                      onClick={() => handleMoveAgent(idx, 'down')}
                                      disabled={idx === teamAgents.length - 1}
                                  >
                                    <ArrowDownwardIcon />
                                  </IconButton>
                                  <Button color="error" onClick={() => handleRemoveAgent(agent.name)}>
                                    Remove
                                  </Button>
                                </>
                              }
                          >
                            <ListItemText
                                primary={agent.name}
                                secondary={
                                  <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                                    <TextField
                                        label="Accuracy %"
                                        type="number"
                                        value={agent.accuracy}
                                        onChange={e => handleAccuracyChange(idx, Number(e.target.value))}
                                        inputProps={{ min: 0, max: 100 }}
                                        size="small"
                                        sx={{ width: 100 }}
                                    />
                                    <TextField
                                        label="Success %"
                                        type="number"
                                        value={agent.success}
                                        onChange={e => handleSuccessChange(idx, Number(e.target.value))}
                                        inputProps={{ min: 0, max: 100 }}
                                        size="small"
                                        sx={{ width: 100 }}
                                    />
                                    <TextField
                                        label="Priority"
                                        type="number"
                                        value={agent.priority}
                                        onChange={e => handlePriorityChange(idx, Number(e.target.value))}
                                        inputProps={{ min: 1 }}
                                        size="small"
                                        sx={{ width: 80 }}
                                    />
                                  </Box>
                                }
                            />
                          </ListItem>
                      ))}
                    </List>
                    <Button variant="contained" color="primary" onClick={handleCreateTeam} disabled={!newTeamName || teamAgents.length === 0}>
                      Create Team
                    </Button>
                    <Box sx={{ mt: 2 }}>
                      <strong>Existing Teams:</strong>
                      <List>
                        {teams.map(team => (
                            <ListItem key={team.id} button onClick={() => setSelectedTeam(team)} selected={selectedTeam?.id === team.id}>
                              <ListItemText primary={team.name} secondary={(team.agents || []).map(a => a.name).join(', ')} />
                            </ListItem>
                        ))}
                      </List>
                    </Box>
                  </Box>
                </Panel>
                <PanelResizeHandle className="PanelResizeHandle" />
                <Panel minSize={20} defaultSize={30} style={{ overflow: 'auto', paddingLeft: 16 }}>
                  <strong>Agent Hierarchy</strong>
                  <AgentHierarchyGraph 
                    agents={teamAgents.map(agent => ({
                      id: agent.id,
                      name: agent.name,
                      priority: agent.priority,
                      accuracy: agent.accuracy,
                      success: agent.success
                    }))}
                    selectedAgents={selectedAgents}
                    onEdgeClick={(sourceId, targetId) => {
                      // Handle edge click if needed
                      console.log('Edge clicked:', sourceId, targetId);
                    }}
                  />
                </Panel>
              </PanelGroup>
            </DialogContent>
            <DialogActions>
              <Button onClick={onClose}>Close</Button>
              {editMode ? (
                  <>
                    <Button onClick={handleUpdateTeam} variant="contained" color="primary">
                      Update
                    </Button>
                    <Button
                        onClick={() => selectedTeam && handleDeleteTeam(selectedTeam.id)}
                        variant="outlined"
                        color="secondary"
                        disabled={!selectedTeam}
                    >
                      Delete
                    </Button>
                  </>
              ) : (
                  <Button onClick={handleCreateTeam} variant="contained" color="primary" disabled={!newTeamName || teamAgents.length === 0}>
                    Create Team
                  </Button>
              )}
            </DialogActions>
          </Dialog>
        </div>
      </Rnd>
  );
};

export default TeamSettingsModal;

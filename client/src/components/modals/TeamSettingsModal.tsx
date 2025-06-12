import React, { useState, useEffect } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Box, TextField, Select, MenuItem, FormControl, InputLabel, Button, List, ListItem, ListItemText, Checkbox, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Slider, Typography, IconButton, Collapse, Switch, FormControlLabel } from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import AgentHierarchyGraph from '../agents/AgentHierarchyGraph';
import { Team, Agent } from '../../store/types';
import axios from 'axios';
import DeleteIcon from '@mui/icons-material/Delete';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AddIcon from '@mui/icons-material/Add';

interface TeamAgent {
  id: number;
  name: string;
  accuracy: number;
  success: number;
  priority: number;
}

export interface TeamSettingsModalProps {
  open: boolean;
  onClose: () => void;
  agents: Agent[];
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
  const [isCreateFormOpen, setIsCreateFormOpen] = useState(false);
  const [useSmartWorkflow, setUseSmartWorkflow] = useState(false);

  useEffect(() => {
    if (selectedTeam) {
      setEditMode(true);
      setNewTeamName(selectedTeam.name);
      // Initialize from selectedTeam first
      setUseSmartWorkflow(selectedTeam.use_smart_workflow || selectedTeam.configuration?.use_smart_workflow || false);
      
      // Get fresh team data when selecting a team
      fetch(`/api/teams/${selectedTeam.id}`)
        .then(res => res.json())
        .then(teamData => {
          console.log('Fetched team data:', teamData);
          // Update smart workflow state from fetched data - check both locations
          setUseSmartWorkflow(teamData.use_smart_workflow || teamData.configuration?.use_smart_workflow || false);
          
          const initializedAgents = (teamData.agents || []).map((agent: any) => ({
            id: agent.id,
            name: agent.name,
            accuracy: Number(agent.accuracy) || 100,
            success: Number(agent.success) || 100,
            priority: Number(agent.priority) || 1
          }));
          console.log('Initialized agents from DB:', initializedAgents);
          setTeamAgents(initializedAgents);
          setSelectedAgents(initializedAgents.map((a: { name: string }) => a.name));
        })
        .catch(error => {
          console.error('Error fetching team data:', error);
          // Fallback to existing data if fetch fails
          setUseSmartWorkflow(selectedTeam.use_smart_workflow || selectedTeam.configuration?.use_smart_workflow || false);
          
          const initializedAgents = (selectedTeam.agents || []).map((agent: any) => ({
            id: agent.id,
            name: agent.name,
            accuracy: Number(agent.accuracy) || 100,
            success: Number(agent.success) || 100,
            priority: Number(agent.priority) || 1
          }));
          setTeamAgents(initializedAgents);
          setSelectedAgents(initializedAgents.map((a: { name: string }) => a.name));
        });
    } else {
      setEditMode(false);
      setNewTeamName('');
      setTeamAgents([]);
      setSelectedAgents([]);
      setUseSmartWorkflow(false);
    }
  }, [selectedTeam, open]);

  // Reset form when modal opens
  useEffect(() => {
    if (open) {
      if (!selectedTeam) {
        setSelectedTeam(null);
        setEditMode(false);
        setNewTeamName('');
        setTeamAgents([]);
        setSelectedAgents([]);
        setUseSmartWorkflow(false);
      }
    }
  }, [open, selectedTeam]);

  const handleEscapeTeamSelection = () => {
    setSelectedTeam(null);
    setEditMode(false);
    setNewTeamName('');
    setTeamAgents([]);
    setSelectedAgents([]);
    setUseSmartWorkflow(false);
  };

  const handleCreateTeam = async () => {
    if (!newTeamName) return;
    try {
      console.log('Creating team with smart workflow:', useSmartWorkflow);
      
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

      const payload = {
        name: newTeamName,
        description: 'Team for processing chat messages and generating responses',
        team_config: {
          name: newTeamName,
          description: 'Team for processing chat messages and generating responses',
          use_smart_workflow: useSmartWorkflow,
          agents: agentsWithMetrics
        },
        agents: agentsWithMetrics
      };

      console.log('Create team payload:', payload);

      // Create the team with all data in one request
      const response = await axios.post('/api/teams', payload);

      console.log('Create team response:', response.data);

      if (response.data) {
        // Fetch the newly created team to ensure we have the correct data
        const teamResponse = await axios.get(`/api/teams/${response.data.id}`);
        const newTeam = teamResponse.data;

        console.log('Fetched new team data:', newTeam);
        console.log('New team config:', newTeam.team_config);

        // Update teams list with the new team
        setTeams([...teams, newTeam]);
        
        // Reset form
        setNewTeamName('');
        setTeamAgents([]);
        setSelectedAgents([]);
        setUseSmartWorkflow(false);
        onClose();
      }
    } catch (err) {
      console.error('Failed to create team:', err);
      alert('Failed to create team. Please try again.');
    }
  };

  const handleUpdateTeam = async () => {
    if (!selectedTeam || !newTeamName) return;
    try {
      console.log('Updating team with smart workflow:', useSmartWorkflow);
      console.log('Current team config:', selectedTeam.configuration);
      
      // Map agents with their correct IDs and metrics
      const agentsWithMetrics = teamAgents.map(agent => ({
        id: agent.id,
        accuracy: Number(agent.accuracy),
        success: Number(agent.success),
        priority: Number(agent.priority)
      }));

      const payload = {
        name: newTeamName,
        description: selectedTeam.description || 'Team for processing chat messages and generating responses',
        team_config: {
          name: newTeamName,
          description: selectedTeam.description || 'Team for processing chat messages and generating responses',
          use_smart_workflow: useSmartWorkflow,
          agents: agentsWithMetrics
        },
        agents: agentsWithMetrics
      };

      console.log('Update team payload:', payload);

      // Update the team with all data in one request
      const response = await axios.put(`/api/teams/${selectedTeam.id}`, payload);

      console.log('Update team response:', response.data);

      if (response.data) {
        // Fetch the updated team to ensure we have the correct data
        const teamResponse = await axios.get(`/api/teams/${selectedTeam.id}`);
        const updatedTeam = teamResponse.data;

        console.log('Fetched updated team data:', updatedTeam);
        console.log('Updated team config:', updatedTeam.configuration);

        // Update the local state with the new value
        setUseSmartWorkflow(updatedTeam.use_smart_workflow || updatedTeam.configuration?.use_smart_workflow || false);
        
        // Update teams list and selected team
        const newTeam = {
          ...updatedTeam,
          use_smart_workflow: updatedTeam.use_smart_workflow || updatedTeam.configuration?.use_smart_workflow || false
        };
        
        setTeams(teams.map(t => t.id === selectedTeam.id ? newTeam : t));
        setSelectedTeam(newTeam);
      }
    } catch (err) {
      console.error('Failed to update team:', err);
      alert('Failed to update team. Please try again.');
    }
  };

  const handleAgentSelection = (event: SelectChangeEvent<string[]>) => {
    const value = Array.isArray(event.target.value) ? event.target.value : [event.target.value];
    console.log('Selected agents:', value);
    setSelectedAgents(value);
    
    const updatedAgents = value.map(agentName => {
      const existingAgent = teamAgents.find(a => a.name === agentName);
      const originalAgent = agents.find(a => a.name === agentName);
      
      if (existingAgent) {
        return existingAgent;
      }
      
      // For new agents, use default values
      const newAgent = {
        id: originalAgent?.id || Date.now(),
        name: agentName,
        accuracy: 100,
        success: 100,
        priority: 1
      };
      console.log('Adding new agent:', newAgent);
      return newAgent;
    });
    
    console.log('Setting team agents:', updatedAgents);
    setTeamAgents(updatedAgents);
  };

  const handleMetricChange = (agentName: string, metric: 'accuracy' | 'success' | 'priority', value: number) => {
    setTeamAgents(prevAgents =>
      prevAgents.map(agent =>
        agent.name === agentName
          ? { ...agent, [metric]: value }
          : agent
      )
    );
  };

  const handleEdgeClick = (sourceId: number, targetId: number) => {
    console.log('Edge clicked:', sourceId, targetId);
    // Handle edge click if needed
  };

  const handleDeleteTeam = async () => {
    if (!selectedTeam) return;
    
    if (window.confirm(`Are you sure you want to delete the team "${selectedTeam.name}"?`)) {
      try {
        await axios.delete(`/api/teams/${selectedTeam.id}`);
        setTeams(teams.filter(t => t.id !== selectedTeam.id));
        setSelectedTeam(null);
        onClose();
      } catch (err) {
        console.error('Failed to delete team:', err);
        alert('Failed to delete team. Please try again.');
      }
    }
  };

  // Add logging to the smart workflow toggle handler
  const handleSmartWorkflowToggle = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.checked;
    console.log('Smart workflow toggle changed:', newValue);
    setUseSmartWorkflow(newValue);
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
      <DialogTitle>Team Settings</DialogTitle>
      <DialogContent>
        <PanelGroup direction="horizontal" style={{ height: 'calc(80vh - 120px)' }}>
          <Panel minSize={20} defaultSize={70} style={{ overflow: 'auto' }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, height: '100%', p: 2 }}>
              {/* Team Details Form Section */}
              <Box sx={{ 
                p: 2,
                border: '1px solid #e0e0e0', 
                borderRadius: 1,
                bgcolor: 'background.paper',
                boxShadow: 1
              }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">
                    {selectedTeam ? `Edit Team: ${selectedTeam.name}` : 'Create New Team'}
                  </Typography>
                  {selectedTeam && (
                    <Button
                      size="small"
                      onClick={handleEscapeTeamSelection}
                      startIcon={<AddIcon />}
                    >
                      Create New
                    </Button>
                  )}
                </Box>
                <TextField
                  label="Team Name"
                  value={newTeamName}
                  onChange={e => setNewTeamName(e.target.value)}
                  fullWidth
                  sx={{ mb: 2 }}
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={useSmartWorkflow}
                      onChange={handleSmartWorkflowToggle}
                      color="primary"
                    />
                  }
                  label="Use Smart Workflow"
                  sx={{ mb: 2 }}
                />
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Select Agents</InputLabel>
                  <Select
                    multiple
                    value={selectedAgents}
                    onChange={handleAgentSelection}
                    renderValue={(selected) => selected.join(', ')}
                  >
                    {agents.map(agent => (
                      <MenuItem key={agent.name} value={agent.name}>
                        <Checkbox checked={selectedAgents.indexOf(agent.name) > -1} />
                        <ListItemText primary={agent.name} />
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {teamAgents.length > 0 && (
                  <Box>
                    <Typography variant="subtitle1" gutterBottom>
                      Agent Metrics
                    </Typography>
                    <TableContainer component={Paper}>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Agent</TableCell>
                            <TableCell align="center">Accuracy (0-100)</TableCell>
                            <TableCell align="center">Success (0-100)</TableCell>
                            <TableCell align="center">Priority (1-10)</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {teamAgents.map((agent) => (
                            <TableRow key={agent.name}>
                              <TableCell>{agent.name}</TableCell>
                              <TableCell align="center">
                                <Slider
                                  value={agent.accuracy}
                                  onChange={(_, value) => handleMetricChange(agent.name, 'accuracy', value as number)}
                                  min={0}
                                  max={100}
                                  step={1}
                                  sx={{ width: 100 }}
                                  valueLabelDisplay="auto"
                                />
                              </TableCell>
                              <TableCell align="center">
                                <Slider
                                  value={agent.success}
                                  onChange={(_, value) => handleMetricChange(agent.name, 'success', value as number)}
                                  min={0}
                                  max={100}
                                  step={1}
                                  sx={{ width: 100 }}
                                  valueLabelDisplay="auto"
                                />
                              </TableCell>
                              <TableCell align="center">
                                <Slider
                                  value={agent.priority}
                                  onChange={(_, value) => handleMetricChange(agent.name, 'priority', value as number)}
                                  min={1}
                                  max={10}
                                  step={1}
                                  sx={{ width: 100 }}
                                  valueLabelDisplay="auto"
                                />
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Box>
                )}
              </Box>

              {/* Existing Teams Section */}
              <Box sx={{ flex: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="h6">
                    Existing Teams
                  </Typography>
                  {selectedTeam && (
                    <IconButton
                      onClick={handleDeleteTeam}
                      color="error"
                      size="small"
                      title="Delete selected team"
                    >
                      <DeleteIcon />
                    </IconButton>
                  )}
                </Box>

                <List sx={{ 
                  border: '1px solid #e0e0e0',
                  borderRadius: 1,
                  bgcolor: 'background.paper',
                  maxHeight: '200px',
                  overflow: 'auto'
                }}>
                  {teams.map(team => (
                    <ListItem
                      key={team.id}
                      button
                      onClick={() => setSelectedTeam(team)}
                      selected={selectedTeam?.id === team.id}
                    >
                      <ListItemText
                        primary={team.name}
                        secondary={(team.agents || []).map(a => a.name).join(', ')}
                      />
                    </ListItem>
                  ))}
                </List>
              </Box>
            </Box>
          </Panel>
          <PanelResizeHandle className="PanelResizeHandle" />
          <Panel minSize={20} defaultSize={30} style={{ overflow: 'auto', paddingLeft: 16 }}>
            <Box sx={{ height: '100%', p: 2 }}>
              <strong>Agent Hierarchy</strong>
              <AgentHierarchyGraph
                agents={teamAgents.map(agent => ({
                  id: agent.id,
                  name: agent.name,
                  priority: agent.priority,
                  accuracy: agent.accuracy,
                  success: agent.success
                }))}
                onEdgeClick={handleEdgeClick}
                onBackgroundClick={() => {}}
              />
            </Box>
          </Panel>
        </PanelGroup>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          color="primary"
          onClick={selectedTeam ? handleUpdateTeam : handleCreateTeam}
          disabled={!newTeamName || teamAgents.length === 0}
        >
          {selectedTeam ? 'Update Team' : 'Create New Team'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TeamSettingsModal; 
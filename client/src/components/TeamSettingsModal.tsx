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
import Select from '@mui/material/Select';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import Checkbox from '@mui/material/Checkbox';
import axios from 'axios';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { Rnd } from 'react-rnd';
import AgentHierarchyGraph from './AgentHierarchyGraph';

interface TeamAgent {
  id: number;
  name: string;
  accuracy: number;
  success: number;
}

interface Team {
  id: number;
  name: string;
  agents: TeamAgent[];
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
      setTeamAgents(selectedTeam.agents || []);
      setSelectedAgents((selectedTeam.agents || []).map(a => a.name));
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
        { id: Date.now(), name: agentName, accuracy: 100, success: 100 }
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
    setTeamAgents(newAgents);
  };

  const handleSuccessChange = (index: number, value: number) => {
    const newAgents = [...teamAgents];
    newAgents[index].success = value;
    setTeamAgents(newAgents);
  };

  const handleCreateTeam = async () => {
    if (!newTeamName) return;
    try {
      const agentIds = agents.filter(a => selectedAgents.includes(a.name)).map(a => a.id);
      const res = await axios.post('/api/teams', { name: newTeamName, agent_ids: agentIds });
      setTeams([
        ...teams,
        {
          id: res.data.id,
          name: newTeamName,
          agents: agents.filter(a => agentIds.includes(a.id))
        }
      ]);
      setNewTeamName('');
    } catch (err) {
      alert('Failed to create team');
    }
  };

  const handleUpdateTeam = async () => {
    if (!selectedTeam) return;
    try {
      const agentIds = agents.filter(a => selectedAgents.includes(a.name)).map(a => a.id);
      await axios.put(`/api/teams/${selectedTeam.id}`, {
        name: newTeamName,
        agent_ids: agentIds
      });
      setTeams(
          teams.map(t =>
              t.id === selectedTeam.id
                  ? {
                    ...t,
                    name: newTeamName,
                    agents: agents.filter(a => agentIds.includes(a.id))
                  }
                  : t
          )
      );
      setSelectedTeam({
        ...selectedTeam,
        name: newTeamName,
        agents: agents.filter(a => agentIds.includes(a.id))
      });
    } catch (err) {
      alert('Failed to update team');
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
                    <Select
                        multiple
                        value={selectedAgents}
                        onChange={e => {
                          const value =
                              typeof e.target.value === 'string'
                                  ? e.target.value.split(',')
                                  : (e.target.value as string[]);
                          setSelectedAgents(value);
                          setTeamAgents(
                              value.map(agentName => {
                                const existing = teamAgents.find(a => a.name === agentName);
                                return existing || {
                                  id: Date.now(),
                                  name: agentName,
                                  accuracy: 100,
                                  success: 100
                                };
                              })
                          );
                        }}
                        renderValue={selected => (selected as string[]).join(', ')}
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
                  <AgentHierarchyGraph agents={teamAgents.map(a => ({ id: a.id, name: a.name }))} />
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

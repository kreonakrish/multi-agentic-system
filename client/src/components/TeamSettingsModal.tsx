import React, { useState } from 'react';
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

interface TeamAgent {
  name: string;
  accuracy: number;
  success: number;
}

interface Team {
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

const TeamSettingsModal: React.FC<TeamSettingsModalProps> = ({ open, onClose, agents, teams, setTeams, selectedTeam, setSelectedTeam }) => {
  const [newTeamName, setNewTeamName] = useState('');
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [teamAgents, setTeamAgents] = useState<TeamAgent[]>([]);

  const handleAddAgent = (agentName: string) => {
    if (!teamAgents.find(a => a.name === agentName)) {
      setTeamAgents([
        ...teamAgents,
        { name: agentName, accuracy: 100, success: 100 }
      ]);
    }
  };

  const handleRemoveAgent = (agentName: string) => {
    setTeamAgents(teamAgents.filter(a => a.name !== agentName));
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

  const handleCreateTeam = () => {
    if (!newTeamName || teamAgents.length === 0) return;
    setTeams([...teams, { name: newTeamName, agents: teamAgents }]);
    setNewTeamName('');
    setTeamAgents([]);
    setSelectedAgents([]);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Team Settings</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField
            label="New Team Name"
            value={newTeamName}
            onChange={e => setNewTeamName(e.target.value)}
            fullWidth
          />
          <Select
            multiple
            value={selectedAgents}
            onChange={e => setSelectedAgents(typeof e.target.value === 'string' ? e.target.value.split(',') : e.target.value as string[])}
            renderValue={selected => (selected as string[]).join(', ')}
            fullWidth
            displayEmpty
          >
            {agents.map(agent => (
              <MenuItem key={agent.name} value={agent.name} onClick={() => handleAddAgent(agent.name)}>
                {agent.name}
              </MenuItem>
            ))}
          </Select>
          <List>
            {teamAgents.map((agent, idx) => (
              <ListItem key={agent.name} secondaryAction={
                <>
                  <IconButton onClick={() => handleMoveAgent(idx, 'up')} disabled={idx === 0}>
                    <ArrowUpwardIcon />
                  </IconButton>
                  <IconButton onClick={() => handleMoveAgent(idx, 'down')} disabled={idx === teamAgents.length - 1}>
                    <ArrowDownwardIcon />
                  </IconButton>
                  <Button color="error" onClick={() => handleRemoveAgent(agent.name)}>Remove</Button>
                </>
              }>
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
                <ListItem key={team.name}>
                  <ListItemText
                    primary={team.name}
                    secondary={team.agents.map(a => a.name).join(', ')}
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default TeamSettingsModal;


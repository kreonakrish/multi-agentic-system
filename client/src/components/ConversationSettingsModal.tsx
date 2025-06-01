import React, { useState, useEffect } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Slider from '@mui/material/Slider';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import axios from 'axios';

interface ConversationSettings {
  temperature: number;
  tokenLimit: number;
  startPrompt: string;
  endPrompt: string;
  style: string;
}

interface ConversationSettingsModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (settings: ConversationSettings, selectedTeamId: string) => void;
  initialValues?: ConversationSettings;
  teams: any[];
  selectedTeamId: string;
  onTeamChange: (teamId: string) => void;
}

const ConversationSettingsModal: React.FC<ConversationSettingsModalProps> = ({ open, onClose, onSave, initialValues, teams, selectedTeamId, onTeamChange }) => {
  const [temperature, setTemperature] = useState(initialValues?.temperature ?? 0.7);
  const [tokenLimit, setTokenLimit] = useState(initialValues?.tokenLimit ?? 512);
  const [startPrompt, setStartPrompt] = useState(initialValues?.startPrompt ?? '');
  const [endPrompt, setEndPrompt] = useState(initialValues?.endPrompt ?? '');
  const [style, setStyle] = useState(initialValues?.style ?? '');

  useEffect(() => {
    if (open) {
      setTemperature(initialValues?.temperature ?? 0.7);
      setTokenLimit(initialValues?.tokenLimit ?? 512);
      setStartPrompt(initialValues?.startPrompt ?? '');
      setEndPrompt(initialValues?.endPrompt ?? '');
      setStyle(initialValues?.style ?? '');
    }
  }, [open, initialValues]);

  const handleSave = () => {
    // Just pass the settings to the parent component
    onSave(
      { 
        temperature, 
        tokenLimit, 
        startPrompt, 
        endPrompt, 
        style 
      },
      selectedTeamId
    );
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Conversation Settings</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 1 }}>
          {/* Team selection dropdown */}
          <Box>
            <Typography gutterBottom>Team</Typography>
            <Select
              value={selectedTeamId}
              onChange={e => onTeamChange(e.target.value)}
              fullWidth
            >
              {teams.map(team => (
                <MenuItem key={team.id || team.name} value={team.id || team.name}>
                  {team.name}
                </MenuItem>
              ))}
            </Select>
          </Box>
          <Box>
            <Typography gutterBottom>Response Temperature</Typography>
            <Slider
              value={temperature}
              min={0}
              max={1}
              step={0.01}
              onChange={(_, v) => setTemperature(v as number)}
              valueLabelDisplay="auto"
            />
          </Box>
          <TextField
            label="Token Size Limit"
            type="number"
            value={tokenLimit}
            onChange={e => setTokenLimit(Number(e.target.value))}
            fullWidth
          />
          <TextField
            label="Static Start Prompt"
            value={startPrompt}
            onChange={e => setStartPrompt(e.target.value)}
            fullWidth
            multiline
            minRows={2}
          />
          <TextField
            label="Static End Prompt"
            value={endPrompt}
            onChange={e => setEndPrompt(e.target.value)}
            fullWidth
            multiline
            minRows={2}
          />
          <TextField
            label="Styling (CSS or theme name)"
            value={style}
            onChange={e => setStyle(e.target.value)}
            fullWidth
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" color="primary">
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ConversationSettingsModal;


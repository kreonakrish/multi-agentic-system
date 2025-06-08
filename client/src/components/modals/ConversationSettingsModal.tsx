import React, { useEffect } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Box, TextField, Select, MenuItem, FormControl, InputLabel, Button } from '@mui/material';
import { Team, ConversationSettings } from '../../store/types';

export interface ConversationSettingsModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (settings: ConversationSettings) => void;
  initialValues: ConversationSettings;
  teams: Team[];
  selectedTeamId: string;
  onTeamChange: (teamId: number) => void;
}

const ConversationSettingsModal: React.FC<ConversationSettingsModalProps> = ({
  open,
  onClose,
  onSave,
  initialValues,
  teams,
  selectedTeamId,
  onTeamChange
}) => {
  const [settings, setSettings] = React.useState<ConversationSettings>(initialValues);

  // Update settings when initialValues change
  useEffect(() => {
    setSettings(initialValues);
  }, [initialValues]);

  // Update settings when modal opens
  useEffect(() => {
    if (open) {
      setSettings(initialValues);
    }
  }, [open, initialValues]);

  const handleSave = () => {
    // Validate settings before saving
    const validatedSettings: ConversationSettings = {
      temperature: Number(settings.temperature) || 0.7,
      tokenLimit: Number(settings.tokenLimit) || 512,
      startPrompt: settings.startPrompt || '',
      endPrompt: settings.endPrompt || '',
      style: settings.style || ''
    };
    onSave(validatedSettings);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>Conversation Settings</DialogTitle>
      <DialogContent>
        <Box sx={{ p: 2 }}>
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Team</InputLabel>
            <Select
              value={selectedTeamId}
              onChange={(e) => onTeamChange(Number(e.target.value))}
              label="Team"
            >
              {teams.map((team) => (
                <MenuItem key={team.id} value={team.id}>
                  {team.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            fullWidth
            label="Temperature"
            type="number"
            inputProps={{ min: 0, max: 1, step: 0.1 }}
            value={settings.temperature}
            onChange={(e) => setSettings({ ...settings, temperature: Number(e.target.value) })}
            sx={{ mb: 2 }}
            helperText="Controls randomness in responses (0-1)"
          />
          <TextField
            fullWidth
            label="Token Limit"
            type="number"
            inputProps={{ min: 1, step: 1 }}
            value={settings.tokenLimit}
            onChange={(e) => setSettings({ ...settings, tokenLimit: Number(e.target.value) })}
            sx={{ mb: 2 }}
            helperText="Maximum number of tokens per response"
          />
          <TextField
            fullWidth
            label="Start Prompt"
            multiline
            rows={2}
            value={settings.startPrompt}
            onChange={(e) => setSettings({ ...settings, startPrompt: e.target.value })}
            sx={{ mb: 2 }}
            helperText="Prompt to be added at the start of each conversation"
          />
          <TextField
            fullWidth
            label="End Prompt"
            multiline
            rows={2}
            value={settings.endPrompt}
            onChange={(e) => setSettings({ ...settings, endPrompt: e.target.value })}
            sx={{ mb: 2 }}
            helperText="Prompt to be added at the end of each conversation"
          />
          <TextField
            fullWidth
            label="Style"
            value={settings.style}
            onChange={(e) => setSettings({ ...settings, style: e.target.value })}
            helperText="Conversation style or theme"
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="inherit">
          Close
        </Button>
        <Button onClick={handleSave} variant="contained" color="primary">
          Save Changes
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ConversationSettingsModal; 
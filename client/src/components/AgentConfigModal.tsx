import React, { useState } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import InputLabel from '@mui/material/InputLabel';
import FormControl from '@mui/material/FormControl';
import Box from '@mui/material/Box';
import Checkbox from '@mui/material/Checkbox';
import ListItemText from '@mui/material/ListItemText';

const MEMORY_TYPES = ['Graph', 'JSON', 'Short Term', 'Long Term'];
const FOUNDATION_MODELS = ['OpenAI', 'Claude', 'GPT', 'Gemini'];

interface AgentConfigModalProps {
  open: boolean;
  onClose: () => void;
  onSave?: (agent: any) => void;
  toolsList: string[];
  initialValues?: {
    name: string;
    memoryType: string;
    foundationModel: string;
    tools: string[];
  };
  mode?: 'create' | 'edit';
}

const AgentConfigModal: React.FC<AgentConfigModalProps> = ({ open, onClose, onSave, toolsList, initialValues, mode = 'create' }) => {
  const [name, setName] = useState(initialValues?.name || '');
  const [memoryType, setMemoryType] = useState(initialValues?.memoryType || MEMORY_TYPES[0]);
  const [foundationModel, setFoundationModel] = useState(initialValues?.foundationModel || FOUNDATION_MODELS[0]);
  const [selectedTools, setSelectedTools] = useState<string[]>(initialValues?.tools || []);

  React.useEffect(() => {
    if (open) {
      setName(initialValues?.name || '');
      setMemoryType(initialValues?.memoryType || MEMORY_TYPES[0]);
      setFoundationModel(initialValues?.foundationModel || FOUNDATION_MODELS[0]);
      setSelectedTools(initialValues?.tools || []);
    }
  }, [open, initialValues]);

  const handleSave = () => {
    if (onSave) {
      onSave({ name, memoryType, foundationModel, tools: selectedTools });
    }
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{mode === 'edit' ? 'Edit Agent' : 'Create New Agent'}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField label="Agent Name" value={name} onChange={e => setName(e.target.value)} fullWidth />
          <FormControl fullWidth>
            <InputLabel>Type of Memory</InputLabel>
            <Select
              value={memoryType}
              label="Type of Memory"
              onChange={e => setMemoryType(e.target.value as string)}
            >
              {MEMORY_TYPES.map(type => (
                <MenuItem key={type} value={type}>{type}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Foundation Model</InputLabel>
            <Select
              value={foundationModel}
              label="Foundation Model"
              onChange={e => setFoundationModel(e.target.value as string)}
            >
              {FOUNDATION_MODELS.map(model => (
                <MenuItem key={model} value={model}>{model}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Tools</InputLabel>
            <Select
              multiple
              value={selectedTools}
              onChange={e => setSelectedTools(typeof e.target.value === 'string' ? e.target.value.split(',') : e.target.value as string[])}
              renderValue={selected => (selected as string[]).join(', ')}
            >
              {toolsList.map(tool => (
                <MenuItem key={tool} value={tool}>
                  <Checkbox checked={selectedTools.indexOf(tool) > -1} />
                  <ListItemText primary={tool} />
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" color="primary">{mode === 'edit' ? 'Update' : 'Save'}</Button>
      </DialogActions>
    </Dialog>
  );
};

export default AgentConfigModal;


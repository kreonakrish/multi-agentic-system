import React, { useState, useEffect } from 'react';
import { 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  Button,
  TextField,
  MenuItem,
  Select,
  InputLabel,
  FormControl,
  Box,
  Checkbox,
  ListItemText
} from '@mui/material';

const MEMORY_TYPES = ['Graph', 'JSON', 'Short Term', 'Long Term'];
const FOUNDATION_MODELS = ['OpenAI', 'Claude', 'GPT', 'Gemini'];

interface Tool {
  id: number;
  tool_name: string;
}

interface AgentConfigModalProps {
  open: boolean;
  onClose: () => void;
  onSave?: (agent: any) => void;
  tools: Tool[];
  initialValues?: {
    id?: string;
    name: string;
    memoryType: string;
    foundationModel: string;
    tools: Tool[];
  };
  mode?: 'create' | 'edit';
}

const AgentConfigModal: React.FC<AgentConfigModalProps> = ({
  open,
  onClose,
  onSave,
  tools,
  initialValues,
  mode = 'create'
}) => {
  const [name, setName] = useState(initialValues?.name || '');
  const [memoryType, setMemoryType] = useState(initialValues?.memoryType || MEMORY_TYPES[0]);
  const [foundationModel, setFoundationModel] = useState(initialValues?.foundationModel || FOUNDATION_MODELS[0]);
  const [selectedTools, setSelectedTools] = useState<Tool[]>(initialValues?.tools || []);

  useEffect(() => {
    if (open) {
      setName(initialValues?.name || '');
      setMemoryType(initialValues?.memoryType || MEMORY_TYPES[0]);
      setFoundationModel(initialValues?.foundationModel || FOUNDATION_MODELS[0]);
      setSelectedTools(initialValues?.tools || []);
    }
  }, [open, initialValues]);

  const handleSave = async () => {
    try {
      if (!name.trim()) {
        alert('Please enter an agent name');
        return;
      }

      const agentData = {
        id: initialValues?.id,
        name,
        memoryType,
        foundationModel,
        tools: selectedTools
      };

      if (onSave) {
        await onSave(agentData);
      }
    } catch (error) {
      console.error('Error saving agent:', error);
      alert('Failed to save agent. Please try again.');
    }
  };

  const handleDelete = async () => {
    if (!initialValues?.id) return;
    try {
      const response = await fetch(`/api/agents/${initialValues.id}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to delete agent');
      }

      onClose();
    } catch (error) {
      console.error('Error deleting agent:', error);
      alert('Failed to delete agent. Please try again.');
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{mode === 'edit' ? 'Edit Agent' : 'Add New Agent'}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField
            label="Agent Name"
            value={name}
            onChange={e => setName(e.target.value)}
            fullWidth
            required
          />
          <FormControl fullWidth>
            <InputLabel>Memory Type</InputLabel>
            <Select
              value={memoryType}
              label="Memory Type"
              onChange={e => setMemoryType(e.target.value)}
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
              onChange={e => setFoundationModel(e.target.value)}
            >
              {FOUNDATION_MODELS.map(model => (
                <MenuItem key={model} value={model}>{model}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Tools</InputLabel>
            <Select<number[]>
              multiple
              value={selectedTools.map(tool => tool.id)}
              onChange={(e) => {
                const value = e.target.value as number[];
                const newSelectedTools = tools.filter(tool => value.includes(tool.id));
                setSelectedTools(newSelectedTools);
              }}
              renderValue={(selected) => {
                const selectedToolNames = tools
                  .filter(tool => selected.includes(tool.id))
                  .map(tool => tool.tool_name)
                  .join(', ');
                return selectedToolNames;
              }}
            >
              {tools.map(tool => (
                <MenuItem key={tool.id} value={tool.id}>
                  <Checkbox checked={selectedTools.some(t => t.id === tool.id)} />
                  <ListItemText primary={tool.tool_name} />
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" color="primary" disabled={!name.trim()}>
          {mode === 'edit' ? 'Update' : 'Save'}
        </Button>
        {mode === 'edit' && (
          <Button onClick={handleDelete} variant="outlined" color="error">
            Delete
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default AgentConfigModal; 
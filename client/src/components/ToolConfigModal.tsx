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
import axios from 'axios';

const TOOL_TYPES = ['Database', 'API', 'WebService'];
const AUTH_METHODS = ['Basic', 'OAuth', 'API Key', 'None'];

interface ToolConfigModalProps {
  open: boolean;
  onClose: () => void;
  onSave?: (tool: any) => void;
  initialValues?: {
    id?: string;
    toolName: string;
    toolType: string;
    hostname: string;
    username: string;
    password: string;
    authMethod: string;
  };
  mode?: 'create' | 'edit';
}

const ToolConfigModal: React.FC<ToolConfigModalProps> = ({ open, onClose, onSave, initialValues, mode = 'create' }) => {
  const [toolName, setToolName] = useState(initialValues?.toolName || '');
  const [toolType, setToolType] = useState(initialValues?.toolType || 'Database');
  const [hostname, setHostname] = useState(initialValues?.hostname || '');
  const [username, setUsername] = useState(initialValues?.username || '');
  const [password, setPassword] = useState(initialValues?.password || '');
  const [authMethod, setAuthMethod] = useState(initialValues?.authMethod || 'Basic');

  React.useEffect(() => {
    if (open) {
      setToolName(initialValues?.toolName || '');
      setToolType(initialValues?.toolType || 'Database');
      setHostname(initialValues?.hostname || '');
      setUsername(initialValues?.username || '');
      setPassword(initialValues?.password || '');
      setAuthMethod(initialValues?.authMethod || 'Basic');
    }
  }, [open, initialValues]);

  const handleSave = async () => {
    try {
      if (mode === 'create') {
        await axios.post('/api/tools', {
          tool_name: toolName,
          tool_type: toolType,
          hostname,
          username,
          password,
          auth_method: authMethod
        });
      } else if (mode === 'edit' && initialValues?.id) {
        await axios.put(`/api/tools/${initialValues.id}`, {
          tool_name: toolName,
          tool_type: toolType,
          hostname,
          username,
          password,
          auth_method: authMethod
        });
      }
      if (onSave) onSave({ toolName, toolType, hostname, username, password, authMethod });
      onClose();
    } catch (err) {
      alert('Failed to save tool');
    }
  };

  const handleDelete = async () => {
    if (!initialValues?.id) return;
    try {
      await axios.delete(`/api/tools/${initialValues.id}`);
      onClose();
    } catch (err) {
      alert('Failed to delete tool');
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{mode === 'edit' ? 'Edit Tool' : 'Configure New Tool'}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField label="Tool Name" value={toolName} onChange={e => setToolName(e.target.value)} fullWidth />
          <FormControl fullWidth>
            <InputLabel>Tool Type</InputLabel>
            <Select
              value={toolType}
              label="Tool Type"
              onChange={e => setToolType(e.target.value as string)}
            >
              {TOOL_TYPES.map(type => (
                <MenuItem key={type} value={type}>{type}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField label="Hostname" value={hostname} onChange={e => setHostname(e.target.value)} fullWidth />
          <TextField label="Server Username" value={username} onChange={e => setUsername(e.target.value)} fullWidth />
          <TextField label="Password" value={password} onChange={e => setPassword(e.target.value)} type="password" fullWidth />
          <FormControl fullWidth>
            <InputLabel>Authentication Method</InputLabel>
            <Select
              value={authMethod}
              label="Authentication Method"
              onChange={e => setAuthMethod(e.target.value as string)}
            >
              {AUTH_METHODS.map(method => (
                <MenuItem key={method} value={method}>{method}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" color="primary">{mode === 'edit' ? 'Update' : 'Save'}</Button>
        {mode === 'edit' && <Button onClick={handleDelete} variant="outlined" color="secondary">Delete</Button>}
      </DialogActions>
    </Dialog>
  );
};

export default ToolConfigModal;


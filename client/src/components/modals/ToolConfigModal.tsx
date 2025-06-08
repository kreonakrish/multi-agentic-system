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
  Box
} from '@mui/material';
import { Tool, ToolType } from '../../store/types';

const TOOL_TYPES: Array<{ value: ToolType; display: string }> = [
  { value: 'APIService', display: 'API Service' },
  { value: 'WebService', display: 'Web Service' },
  { value: 'Database', display: 'Database' },
  { value: 'Python', display: 'Python' },
  { value: 'React', display: 'React' }
];

const AUTH_METHODS = ['Basic', 'OAuth', 'API Key', 'None'];

interface ToolConfigModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (tool: Tool) => void;
  mode?: 'create' | 'edit';
  initialValues?: Partial<Tool>;
}

const ToolConfigModal: React.FC<ToolConfigModalProps> = ({
  open,
  onClose,
  onSave,
  initialValues
}) => {
  const [tool_name, setToolName] = useState(initialValues?.tool_name || '');
  const [tool_type, setToolType] = useState<ToolType>(initialValues?.tool_type || TOOL_TYPES[0].value);
  const [hostname, setHostname] = useState(initialValues?.hostname || '');
  const [username, setUsername] = useState(initialValues?.username || '');
  const [password, setPassword] = useState(initialValues?.password || '');
  const [auth_method, setAuthMethod] = useState(initialValues?.auth_method || AUTH_METHODS[0]);
  const [description, setDescription] = useState(initialValues?.description || '');

  useEffect(() => {
    if (initialValues) {
      setToolName(initialValues.tool_name || '');
      setToolType(initialValues.tool_type || TOOL_TYPES[0].value);
      setHostname(initialValues.hostname || '');
      setUsername(initialValues.username || '');
      setPassword(initialValues.password || '');
      setAuthMethod(initialValues.auth_method || AUTH_METHODS[0]);
      setDescription(initialValues.description || '');
    }
  }, [initialValues]);

  const handleSave = () => {
    if (!tool_name.trim()) {
      alert('Tool name is required');
      return;
    }

    const toolData: Tool = {
      id: initialValues?.id || 0,
      tool_name,
      tool_type,
      hostname,
      username,
      password,
      auth_method,
      description
    };

    onSave(toolData);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{initialValues ? 'Edit Tool' : 'Add Tool'}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField
            label="Tool Name"
            value={tool_name}
            onChange={e => setToolName(e.target.value)}
            required
          />
          <FormControl>
            <InputLabel>Tool Type</InputLabel>
            <Select
              value={tool_type}
              label="Tool Type"
              onChange={e => setToolType(e.target.value as ToolType)}
            >
              {TOOL_TYPES.map(type => (
                <MenuItem key={type.value} value={type.value}>
                  {type.display}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="Hostname"
            value={hostname}
            onChange={e => setHostname(e.target.value)}
          />
          <TextField
            label="Username"
            value={username}
            onChange={e => setUsername(e.target.value)}
          />
          <TextField
            label="Password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
          />
          <FormControl>
            <InputLabel>Auth Method</InputLabel>
            <Select
              value={auth_method}
              label="Auth Method"
              onChange={e => setAuthMethod(e.target.value)}
            >
              {AUTH_METHODS.map(method => (
                <MenuItem key={method} value={method}>{method}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="Description"
            value={description}
            onChange={e => setDescription(e.target.value)}
            multiline
            rows={3}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained" color="primary" disabled={!tool_name.trim()}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ToolConfigModal; 
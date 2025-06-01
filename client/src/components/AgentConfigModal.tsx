import React, { useState } from 'react';
import axios from 'axios';
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

interface Tool {
  id: number;
  toolName: string;
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
    tools: (string | { toolName?: string; tool_name?: string })[];
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
  const [selectedTools, setSelectedTools] = useState<string[]>(
      (initialValues?.tools || []).map(tool =>
          typeof tool === 'object' && tool !== null ? tool.toolName || tool.tool_name || '' : tool
      )
  );

  React.useEffect(() => {
    if (open) {
      setName(initialValues?.name || '');
      setMemoryType(initialValues?.memoryType || MEMORY_TYPES[0]);
      setFoundationModel(initialValues?.foundationModel || FOUNDATION_MODELS[0]);
      setSelectedTools(
          (initialValues?.tools || []).map(tool =>
              typeof tool === 'object' && tool !== null ? tool.toolName || tool.tool_name || '' : tool
          )
      );
    }
  }, [open, initialValues]);

  // 🟢 Helper: Always shows tool names, never [object Object]
  function renderToolNames(toolArr: any[]) {
    if (!Array.isArray(toolArr) || !toolArr.length) return 'None';
    return toolArr
        .map(tool => {
          if (tool && typeof tool === 'object') {
            // Prefer toolName, fallback to tool_name, fallback to JSON
            return tool.toolName || tool.tool_name || JSON.stringify(tool);
          }
          if (typeof tool === 'string') {
            const t = tools.find(tt => tt.toolName === tool);
            return t ? t.toolName : tool;
          }
          return '';
        })
        .filter(Boolean)
        .join(', ');
  }

  const handleSave = async () => {
    try {
      let agentId = initialValues?.id;
      let agentData: any = {};
      if (mode === 'create') {
        const res = await axios.post('/api/agents', {
          name,
          memory_type: memoryType,
          foundation_model: foundationModel
        });
        agentId = res.data.id;
        agentData = res.data;
      } else if (mode === 'edit' && agentId) {
        await axios.put(`/api/agents/${agentId}`, {
          name,
          memory_type: memoryType,
          foundation_model: foundationModel
        });
        agentData = { id: agentId, name, memory_type: memoryType, foundation_model: foundationModel };
      }
      // Map selected tool names to IDs
      const selectedToolIds = selectedTools
          .map(toolName => {
            const tool = tools.find(t => t.toolName === toolName);
            return tool ? tool.id : null;
          })
          .filter(Boolean);
      // Assign tools to agent
      if (agentId) {
        if (mode === 'edit' && initialValues?.tools) {
          for (const toolName of initialValues.tools) {
            const toolStr =
                typeof toolName === 'object' && toolName !== null
                    ? toolName.toolName || toolName.tool_name || ''
                    : toolName;
            const tool = tools.find(t => t.toolName === toolStr);
            if (tool && !selectedToolIds.includes(tool.id)) {
              await axios.delete('/api/agent-tools', { data: { agent_id: agentId, tool_id: tool.id } });
            }
          }
        }
        for (const toolId of selectedToolIds) {
          if (
              !initialValues?.tools ||
              !initialValues.tools.some(name => {
                const toolStr =
                    typeof name === 'object' && name !== null ? name.toolName || name.tool_name || '' : name;
                const tool = tools.find(t => t.toolName === toolStr);
                return tool && tool.id === toolId;
              })
          ) {
            await axios.post('/api/agent-tools', { agent_id: agentId, tool_id: toolId });
          }
        }
      }
      // Map backend fields to frontend format
      const mappedAgent = {
        id: agentId,
        name: agentData.name,
        memoryType: agentData.memory_type || memoryType,
        foundationModel: agentData.foundation_model || foundationModel,
        tools: tools.filter(tool => selectedTools.includes(tool.toolName))
      };
      if (onSave) onSave(mappedAgent);
      onClose();
    } catch (err: any) {
      console.error('Failed to save agent:', err?.response?.data || err);
      alert('Failed to save agent');
    }
  };

  const handleDelete = async () => {
    if (!initialValues?.id) return;
    try {
      await axios.delete(`/api/agents/${initialValues.id}`);
      onClose();
    } catch (err) {
      alert('Failed to delete agent');
    }
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
                  onChange={e =>
                      setSelectedTools(
                          typeof e.target.value === 'string'
                              ? e.target.value.split(',')
                              : (e.target.value as string[])
                      )
                  }
                  renderValue={selected => (selected as string[]).join(', ')}
              >
                {tools.map(tool => (
                    <MenuItem key={tool.id} value={tool.toolName}>
                      <Checkbox checked={selectedTools.indexOf(tool.toolName) > -1} />
                      <ListItemText primary={tool.toolName} />
                    </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          {/* Show selected tools in edit mode */}
          {mode === 'edit' && initialValues && (
              <Box sx={{ mt: 2 }}>
                <strong>Tools:</strong> {renderToolNames(initialValues.tools)}
              </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" color="primary" disabled={!name.trim()}>
            {mode === 'edit' ? 'Update' : 'Save'}
          </Button>
          {mode === 'edit' && (
              <Button onClick={handleDelete} variant="outlined" color="secondary">
                Delete
              </Button>
          )}
        </DialogActions>
      </Dialog>
  );
};

export default AgentConfigModal;

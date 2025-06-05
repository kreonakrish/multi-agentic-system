import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, List, ListItem, ListItemText, ListItemSecondaryAction, IconButton, Box, Typography, Divider } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import { Team } from '../../store/types';

interface Tool {
  id: number;
  hostname: string | null;
  toolName: string;
  username: string | null;
  authMethod: string;
  permissionLevel: string;
}

interface ToolsData {
  [key: string]: Tool[];
}

export interface ConnectedSourcesModalProps {
  open: boolean;
  onClose: () => void;
  team: Team | null;
  onDisconnect: (sourceId: string) => void;
}

const ConnectedSourcesModal: React.FC<ConnectedSourcesModalProps> = ({
  open,
  onClose,
  team,
  onDisconnect
}) => {
  // State to hold the tools data
  const [toolsData, setToolsData] = React.useState<ToolsData>({});

  console.log('ConnectedSourcesModal rendered with:', {
    open,
    team: team ? {
      id: team.id,
      name: team.name
    } : null
  });

  // Effect to fetch tools when modal opens
  React.useEffect(() => {
    if (open && team?.id) {
      console.log('Modal opened for team:', team.id);
      // Fetch connected sources
      fetch(`/api/tools/connected-sources/${team.id}`)
        .then(response => response.json())
        .then(data => {
          console.log('Fetched connected sources:', {
            data,
            firstTool: data[Object.keys(data)[0]]?.[0],
            toolTypes: Object.keys(data)
          });
          setToolsData(data);
        })
        .catch(error => console.error('Error fetching connected sources:', error));
    }
  }, [open, team?.id]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>Connected Sources</DialogTitle>
      <DialogContent>
        <Box sx={{ p: 2 }}>
          {team ? (
            Object.keys(toolsData).length > 0 ? (
              <Box>
                {Object.entries(toolsData).map(([type, tools]) => (
                  <Box key={type} sx={{ mb: 3 }}>
                    <Typography variant="h6" gutterBottom>
                      {type}
                    </Typography>
                    <List>
                      {tools.map((tool: Tool) => (
                        <ListItem key={tool.id}>
                          <ListItemText
                            primary={tool.toolName}
                            secondary={
                              <React.Fragment>
                                <Typography component="span" variant="body2" color="textSecondary">
                                  Host: {tool.hostname ?? 'N/A'}<br />
                                  Auth Method: {tool.authMethod ?? 'N/A'}<br />
                                  Permission Level: {tool.permissionLevel ?? 'N/A'}
                                </Typography>
                              </React.Fragment>
                            }
                          />
                          <ListItemSecondaryAction>
                            <IconButton edge="end" onClick={() => onDisconnect(tool.id.toString())}>
                              <DeleteIcon />
                            </IconButton>
                          </ListItemSecondaryAction>
                        </ListItem>
                      ))}
                    </List>
                    <Divider sx={{ mt: 2 }} />
                  </Box>
                ))}
              </Box>
            ) : (
              <Typography variant="body1" color="textSecondary">
                No sources connected to this team
              </Typography>
            )
          ) : (
            <Typography variant="body1" color="textSecondary">
              No team selected
            </Typography>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default ConnectedSourcesModal;
import React, { useEffect, useState } from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';

interface ConnectedSourcesModalProps {
  open: boolean;
  onClose: () => void;
  teamId: number | string | undefined;
}

const ConnectedSourcesModal: React.FC<ConnectedSourcesModalProps> = ({ open, onClose, teamId }) => {
  const [sources, setSources] = useState<{ hostname: string; tool_type: string }[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && teamId) {
      setLoading(true);
      fetch(`/api/connected-sources/${teamId}`)
        .then(res => res.json())
        .then(data => setSources(data))
        .finally(() => setLoading(false));
    } else {
      setSources([]);
    }
  }, [open, teamId]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Connected Sources</DialogTitle>
      <DialogContent>
        {loading ? (
          <div>Loading...</div>
        ) : (
          <List>
            {sources.length > 0 ? (
              sources.map((source, idx) => (
                <ListItem key={idx}>
                  <ListItemText 
                    primary={`Type: ${source.tool_type}`}
                    secondary={`Hostname: ${source.hostname}`} 
                  />
                </ListItem>
              ))
            ) : (
              <ListItem><ListItemText primary="No connected sources." /></ListItem>
            )}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default ConnectedSourcesModal;


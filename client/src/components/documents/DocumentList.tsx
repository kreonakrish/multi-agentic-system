import React from 'react';
import { Box, List, ListItem, ListItemText, IconButton, Typography } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import { Document } from '../../store/types';

interface DocumentListProps {
  documents: Document[];
  onDelete?: (id: string) => void;
  onDownload?: (doc: Document) => void;
}

const DocumentList: React.FC<DocumentListProps> = ({ documents, onDelete, onDownload }) => {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Documents
      </Typography>
      <List>
        {documents.length === 0 ? (
          <Typography color="text.secondary" align="center">
            No documents uploaded yet.
          </Typography>
        ) : (
          documents.map((doc) => (
            <ListItem
              key={doc.id}
              sx={{
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1,
                mb: 1,
                bgcolor: 'background.paper'
              }}
            >
              <ListItemText
                primary={doc.name}
                secondary={`${doc.file_type} • ${(doc.file_size / 1024).toFixed(1)} KB • ${new Date(doc.uploaded_at).toLocaleString()}`}
              />
              {onDownload && (
                <IconButton onClick={() => onDownload(doc)} size="small">
                  <DownloadIcon />
                </IconButton>
              )}
              {onDelete && (
                <IconButton onClick={() => onDelete(doc.id)} size="small" color="error">
                  <DeleteIcon />
                </IconButton>
              )}
            </ListItem>
          ))
        )}
      </List>
    </Box>
  );
};

export default DocumentList; 
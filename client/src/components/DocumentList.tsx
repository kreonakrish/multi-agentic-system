import React from 'react';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

export type Document = {
    id: string;
    name: string;
    url: string;
    uploadedAt?: string;
    size?: number;
};

interface DocumentListProps {
    documents: Document[];
    onDelete: (id: string) => void;
    onDownload: (doc: Document) => void;
}

const DocumentList: React.FC<DocumentListProps> = ({ documents, onDelete, onDownload }) => {
    return (
        <List sx={{
            width: '100%',
            bgcolor: 'background.paper',
            position: 'relative',
            '& .MuiListItem-root': {
                mb: 1,
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1,
                '&:hover': {
                    bgcolor: 'action.hover',
                },
            }
        }}>
            {documents.length === 0 ? (
                <Typography 
                    color="text.secondary" 
                    align="center"
                    sx={{ p: 2 }}
                >
                    No documents uploaded yet.
                </Typography>
            ) : (
                documents.map((doc) => (
                    <Box
                        key={doc.id}
                        sx={{
                            position: 'relative',
                            mb: 1,
                            '&:hover .action-buttons': {
                                opacity: 1,
                            }
                        }}
                    >
                        <ListItem
                            sx={{
                                pr: 15,
                                p: 2,
                                position: 'relative',
                                overflow: 'visible'
                            }}
                        >
                            <ListItemText
                                primary={doc.name}
                                secondary={
                                    <>
                                        {doc.uploadedAt && new Date(doc.uploadedAt).toLocaleString()}
                                        {doc.size && ` • ${(doc.size / 1024).toFixed(2)} KB`}
                                    </>
                                }
                            />
                            <div 
                                className="action-buttons"
                                style={{
                                    position: 'absolute',
                                    right: 8,
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    display: 'flex',
                                    gap: '8px',
                                    background: '#fff',
                                    padding: '4px',
                                    borderRadius: '4px',
                                    opacity: 0.9,
                                    transition: 'opacity 0.2s',
                                    zIndex: 9999,
                                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                                    isolation: 'isolate',
                                    pointerEvents: 'auto'
                                }}
                                onClick={e => e.stopPropagation()}
                            >
                                <div style={{ position: 'relative', zIndex: 10000 }}>
                                    <IconButton
                                        size="small"
                                        onClick={(e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            onDownload(doc);
                                        }}
                                        sx={{
                                            bgcolor: 'background.paper',
                                            '&:hover': {
                                                bgcolor: 'action.hover',
                                            },
                                            zIndex: 10000
                                        }}
                                    >
                                        <DownloadIcon fontSize="small" />
                                    </IconButton>
                                </div>
                                <div style={{ position: 'relative', zIndex: 10000 }}>
                                    <IconButton
                                        size="small"
                                        onClick={(e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            if (window.confirm('Are you sure you want to delete this document?')) {
                                                onDelete(doc.id);
                                            }
                                        }}
                                        sx={{
                                            bgcolor: 'background.paper',
                                            '&:hover': {
                                                bgcolor: 'action.hover',
                                            },
                                            zIndex: 10000
                                        }}
                                    >
                                        <DeleteIcon fontSize="small" />
                                    </IconButton>
                                </div>
                            </div>
                        </ListItem>
                    </Box>
                ))
            )}
        </List>
    );
};

export default DocumentList; 
import React from 'react';
import {
  Box,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  TextField,
  Typography,
  Button,
  Divider
} from '@mui/material';
import {
  Delete as DeleteIcon,
  Edit as EditIcon,
  Download as DownloadIcon,
  Settings as SettingsIcon,
  Description as DescriptionIcon
} from '@mui/icons-material';
import { Document } from '../store/types';

interface RightSidebarProps {
  width: number;
  onResize: (e: React.MouseEvent) => void;
  showConversationHistory: boolean;
  tabIndex: number;
  setTabIndex: (index: number) => void;
  documents: Document[];
  conversationHistoryList: any[];
  onLoadConversation: (conv: any) => void;
  onDeleteConversation: (conv: any) => void;
  onTeamSettings: () => void;
  onAgentSettings: () => void;
  onExecutionPlan: () => void;
  onConnectedSources: () => void;
  renamingIdx: number | null;
  renameValue: string;
  onStartRename: (idx: number, currentTitle: string) => void;
  onSaveRename: (conv: any) => void;
  setRenameValue: (value: string) => void;
}

const RightSidebar: React.FC<RightSidebarProps> = ({
  width,
  onResize,
  showConversationHistory,
  tabIndex,
  setTabIndex,
  documents,
  conversationHistoryList,
  onLoadConversation,
  onDeleteConversation,
  onTeamSettings,
  onAgentSettings,
  onExecutionPlan,
  onConnectedSources,
  renamingIdx,
  renameValue,
  onStartRename,
  onSaveRename,
  setRenameValue
}) => {
  return (
    <Box
      sx={{
        width: width,
        minWidth: 160,
        maxWidth: 400,
        height: '100%',
        bgcolor: 'background.paper',
        borderLeft: '1px solid',
        borderColor: 'divider',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative'
      }}
    >
      {/* Conversation History Section */}
      {showConversationHistory && (
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6" gutterBottom>
            Conversation History
          </Typography>
          <List dense>
            {conversationHistoryList.map((conv, idx) => (
              <ListItem key={conv.id || idx} button onClick={() => onLoadConversation(conv)}>
                {renamingIdx === idx ? (
                  <TextField
                    fullWidth
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onBlur={() => onSaveRename(conv)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        onSaveRename(conv);
                      }
                    }}
                    autoFocus
                  />
                ) : (
                  <>
                    <ListItemText primary={conv.title} />
                    <ListItemSecondaryAction>
                      <IconButton edge="end" onClick={() => onStartRename(idx, conv.title)}>
                        <EditIcon />
                      </IconButton>
                      <IconButton edge="end" onClick={() => onDeleteConversation(conv)}>
                        <DeleteIcon />
                      </IconButton>
                      <IconButton edge="end" onClick={() => onLoadConversation(conv)}>
                        <DownloadIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </>
                )}
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {/* Settings and Documents Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabIndex} onChange={(_, v) => setTabIndex(v)}>
          <Tab icon={<SettingsIcon />} label="Settings" />
          <Tab icon={<DescriptionIcon />} label="Documents" />
        </Tabs>
      </Box>

      {/* Settings Panel */}
      {tabIndex === 0 && (
        <Box sx={{ p: 2 }}>
          <List>
            <ListItem button onClick={onTeamSettings}>
              <ListItemText primary="Team Settings" />
            </ListItem>
            <ListItem button onClick={onAgentSettings}>
              <ListItemText primary="Agent Settings" />
            </ListItem>
            <ListItem button onClick={onExecutionPlan}>
              <ListItemText primary="Execution Plan" />
            </ListItem>
            <ListItem button onClick={onConnectedSources}>
              <ListItemText primary="Connected Sources" />
            </ListItem>
          </List>
        </Box>
      )}

      {/* Documents Panel */}
      {tabIndex === 1 && (
        <Box sx={{ p: 2 }}>
          <List>
            {documents.map((doc) => (
              <ListItem key={doc.id}>
                <ListItemText primary={doc.name} />
                <ListItemSecondaryAction>
                  <IconButton edge="end" onClick={() => onDeleteConversation(doc)}>
                    <DeleteIcon />
                  </IconButton>
                  <IconButton edge="end" onClick={() => onLoadConversation(doc)}>
                    <DownloadIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {/* Resize Handle */}
      <Box
        sx={{
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: '4px',
          cursor: 'col-resize',
          '&:hover': {
            backgroundColor: 'action.hover'
          }
        }}
        onMouseDown={onResize}
      />
    </Box>
  );
};

export default RightSidebar; 
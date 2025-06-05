import React from 'react';
import { Box, Button, Tabs, Tab, Typography, List, ListItem, ListItemText, ListItemSecondaryAction, IconButton, TextField } from '@mui/material';
import { Edit as EditIcon, Delete as DeleteIcon, Download as DownloadIcon } from '@mui/icons-material';
import GroupsIcon from '@mui/icons-material/Groups';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import SettingsIcon from '@mui/icons-material/Settings';
import LinkIcon from '@mui/icons-material/Link';
import ChatIcon from '@mui/icons-material/Chat';
import DescriptionIcon from '@mui/icons-material/Description';
import DocumentList from '../documents/DocumentList';
import { Document, Conversation, Tool } from '../../store/types';

interface RightSidebarProps {
  width: number;
  onResize: (e: React.MouseEvent) => void;
  showConversationHistory: boolean;
  tabIndex: number;
  setTabIndex: (index: number) => void;
  documents: Document[];
  conversationHistoryList: Conversation[];
  onLoadConversation: (conv: Conversation) => void;
  onDeleteConversation: (conv: Conversation) => void;
  onDeleteDocument: (id: string) => void;
  onDownloadDocument: (doc: Document) => void;
  onTeamSettings: () => void;
  onAgentSettings: () => void;
  onExecutionPlan: () => void;
  onConnectedSources: () => void;
  onConversationSettings: () => void;
  renamingIdx: number | null;
  renameValue: string;
  onStartRename: (idx: number, currentTitle: string) => void;
  onSaveRename: (conv: Conversation) => void;
  setRenameValue: (value: string) => void;
  team: { tools: Tool[] } | null;
  onDisconnect: (sourceId: string) => void;
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
  onDeleteDocument,
  onDownloadDocument,
  onTeamSettings,
  onAgentSettings,
  onExecutionPlan,
  onConnectedSources,
  onConversationSettings,
  renamingIdx,
  renameValue,
  onStartRename,
  onSaveRename,
  setRenameValue,
  team,
  onDisconnect
}) => {
  return (
    <Box
      sx={{
        position: 'relative',
        width,
        height: '100%',
        borderLeft: 1,
        borderColor: 'divider',
        bgcolor: 'background.paper',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {/* Conversation History */}
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
      <Box>
        <Tabs value={tabIndex} onChange={(_, v) => setTabIndex(v)}>
          <Tab icon={<SettingsIcon />} label="Settings" />
          <Tab icon={<ChatIcon />} label="History" />
          <Tab icon={<DescriptionIcon />} label="Documents" />
          <Tab icon={<LinkIcon />} label="Sources" />
        </Tabs>
      </Box>

      {/* Settings Panel */}
      {tabIndex === 0 && (
        <Box sx={{ p: 2 }}>
          <Button
            fullWidth
            startIcon={<SettingsIcon />}
            onClick={onConversationSettings}
            sx={{
              py: 1.5,
              color: '#050505',
              bgcolor: '#f0f2f5',
              justifyContent: 'flex-start',
              fontWeight: 600,
              '&:hover': {
                bgcolor: '#e4e6eb'
              },
              mb: 1
            }}
          >
            Conversation Settings
          </Button>
          <Button
            fullWidth
            startIcon={<GroupsIcon />}
            onClick={onTeamSettings}
            sx={{
              py: 1.5,
              color: '#050505',
              bgcolor: '#f0f2f5',
              justifyContent: 'flex-start',
              fontWeight: 600,
              '&:hover': {
                bgcolor: '#e4e6eb'
              },
              mb: 1
            }}
          >
            Team Settings
          </Button>
          <Button
            fullWidth
            startIcon={<AccountTreeIcon />}
            onClick={onAgentSettings}
            sx={{
              py: 1.5,
              color: '#050505',
              bgcolor: '#f0f2f5',
              justifyContent: 'flex-start',
              fontWeight: 600,
              '&:hover': {
                bgcolor: '#e4e6eb'
              },
              mb: 1
            }}
          >
            Agent Settings
          </Button>
          <Button
            fullWidth
            startIcon={<SettingsIcon />}
            onClick={onExecutionPlan}
            sx={{
              py: 1.5,
              color: '#050505',
              bgcolor: '#f0f2f5',
              justifyContent: 'flex-start',
              fontWeight: 600,
              '&:hover': {
                bgcolor: '#e4e6eb'
              },
              mb: 1
            }}
          >
            Execution Plan
          </Button>
          <Button
            fullWidth
            startIcon={<LinkIcon />}
            onClick={onConnectedSources}
            sx={{
              py: 1.5,
              color: '#050505',
              bgcolor: '#f0f2f5',
              justifyContent: 'flex-start',
              fontWeight: 600,
              '&:hover': {
                bgcolor: '#e4e6eb'
              }
            }}
          >
            Connected Sources
          </Button>
        </Box>
      )}

      {/* History Panel */}
      {tabIndex === 1 && (
        <Box sx={{ p: 2, flexGrow: 1, overflowY: 'auto' }}>
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

      {/* Documents Panel */}
      {tabIndex === 2 && (
        <Box sx={{ p: 2, flexGrow: 1, overflowY: 'auto' }}>
          <DocumentList
            documents={documents}
            onDelete={onDeleteDocument}
            onDownload={onDownloadDocument}
          />
        </Box>
      )}

      {/* Connected Sources Panel */}
      {tabIndex === 3 && (
        <Box sx={{ p: 2, flexGrow: 1, overflowY: 'auto' }}>
          {team ? (
            team.tools && team.tools.length > 0 ? (
              <List>
                {team.tools.map((tool: Tool) => (
                  <ListItem key={tool.id}>
                    <ListItemText
                      primary={tool.tool_name}
                      secondary={
                        <>
                          <Typography component="span" variant="body2" color="textSecondary">
                            Type: {tool.tool_type}<br />
                            Host: {tool.hostname}<br />
                            Auth: {tool.auth_method}
                          </Typography>
                        </>
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
      )}

      {/* Resize Handle */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          bottom: 0,
          width: '4px',
          cursor: 'col-resize',
          background: 'transparent'
        }}
        onMouseDown={onResize}
      />
    </Box>
  );
};

export default RightSidebar; 
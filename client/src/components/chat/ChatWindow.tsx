import React, { useState, useRef, useEffect } from 'react';
import { Box, TextField, IconButton, Typography, Paper, Link, useTheme } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import { Team, ConversationStep, ConversationSettings, Document } from '../../store/types';
import ChatMessage from './ChatMessage';
import './ChatWindow.css';

// Document Preview Component
const DocumentPreview: React.FC<{ document: Document }> = ({ document }) => {
  const getFileIcon = () => {
    return <InsertDriveFileIcon />;
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        p: 1,
        bgcolor: 'background.paper',
        borderRadius: 1,
        border: '1px solid',
        borderColor: 'divider',
        maxWidth: 'fit-content'
      }}
    >
      {getFileIcon()}
      <Link
        href={document.url}
        target="_blank"
        rel="noopener noreferrer"
        sx={{ textDecoration: 'none', color: 'primary.main' }}
      >
        {document.name}
      </Link>
      <Typography variant="caption" color="text.secondary">
        ({(document.file_size / 1024).toFixed(1)} KB • {new Date(document.uploaded_at).toLocaleString()})
      </Typography>
    </Box>
  );
};

interface ChatWindowProps {
  placeholder: string;
  conversationHistory: ConversationStep[];
  setConversationHistory: React.Dispatch<React.SetStateAction<ConversationStep[]>>;
  selectedTeam: Team | null;
  canChat: boolean;
  onFileUpload: (file: File) => Promise<Document>;
}

const ChatWindow: React.FC<ChatWindowProps> = ({
  placeholder,
  conversationHistory,
  setConversationHistory,
  selectedTeam,
  canChat,
  onFileUpload
}) => {
  const [message, setMessage] = useState('');
  const [messageHistory, setMessageHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const theme = useTheme();

  // Update message history when a message is sent
  useEffect(() => {
    // Extract only user messages from conversation history
    const userMessages = conversationHistory
      .filter(step => step.role === 'user')
      .map(step => step.content);
    setMessageHistory(userMessages);
  }, [conversationHistory]);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversationHistory]);

  const handleSend = async () => {
    if (message.trim() && canChat) {
      const currentMessage = message;
      setMessage('');
      setHistoryIndex(-1); // Reset history index after sending
      
      const userStep: ConversationStep = { 
        role: 'user', 
        content: currentMessage,
        timestamp: new Date().toISOString()
      };
      
      setConversationHistory(prev => [...prev, userStep]);
      
      try {
        const response = await fetch('/api/chat/message', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            content: currentMessage,
            userId: 'user-1',
            sessionId: selectedTeam?.id || 'default-session',
            context: {
              team_id: selectedTeam?.id,
              team_config: selectedTeam?.config || {
                name: selectedTeam?.name || "Chat Response Team",
                description: selectedTeam?.description || "Team for processing chat messages and generating responses",
                agents: selectedTeam?.agents?.map(agent => ({
                  agent_id: agent.id,
                  priority: agent.priority || 1,
                  accuracy_threshold: agent.accuracy_threshold || 0.8,
                  success_rate: agent.success_rate || 0.9,
                  role: agent.role || 'assistant'
                })) || []
              },
              conversation_settings: selectedTeam?.conversation_settings || {
                temperature: 0.7,
                tokenLimit: 2000,
                startPrompt: '',
                endPrompt: '',
                style: 'default',
                model: "gpt-4"
              },
              conversation_history: conversationHistory.map(step => ({
                role: step.role,
                content: step.content,
                metadata: step.metadata,
                attachments: step.attachments,
                timestamp: step.timestamp || new Date().toISOString()
              })),
              documents: conversationHistory
                .filter(step => step.attachments)
                .flatMap(step => step.attachments || [])
                .map(doc => ({
                  id: doc.id,
                  name: doc.name,
                  type: doc.type,
                  url: doc.url,
                  content: doc.content || '',
                  metadata: doc.metadata || {},
                  file_type: doc.file_type,
                  file_size: doc.file_size,
                  created_at: doc.created_at
                }))
            }
          })
        });

        if (!response.ok) {
          throw new Error('Failed to send message');
        }

        const responseData = await response.json();
        
        if (responseData.status === 'success' && responseData.data) {
          const agentStep: ConversationStep = {
            role: 'agent',
            content: responseData.data.content,
            timestamp: responseData.data.timestamp || new Date().toISOString(),
            metadata: responseData.data.metadata || {}
          };
          
          setConversationHistory(prev => [...prev, agentStep]);
        }
      } catch (error) {
        console.error('Error sending message:', error);
        // Handle error appropriately
      }
    }
  };

  const handleKeyPress = async (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      await handleSend();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Only handle arrow keys if there's message history
    if (messageHistory.length === 0) return;

    if (e.key === 'ArrowUp') {
      e.preventDefault();
      // If we're not in history yet, save current input
      if (historyIndex === -1 && message) {
        setMessageHistory(prev => [...prev, message]);
      }
      
      // Move up in history if not at the start
      if (historyIndex < messageHistory.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setMessage(messageHistory[messageHistory.length - 1 - newIndex]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        // Move down in history
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setMessage(messageHistory[messageHistory.length - 1 - newIndex]);
      } else if (historyIndex === 0) {
        // Clear message when going past the most recent history
        setHistoryIndex(-1);
        setMessage('');
      }
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      try {
        const uploadedDocs = await Promise.all(
          Array.from(event.target.files).map(file => onFileUpload(file))
        );

        const newStep: ConversationStep = {
          role: 'user',
          content: `Uploaded ${uploadedDocs.length} file(s)`,
          timestamp: new Date().toISOString(),
          attachments: uploadedDocs
        };

        setConversationHistory(prev => [...prev, newStep]);
      } catch (error) {
        console.error('Error uploading files:', error);
        // Handle error appropriately
      }
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        position: 'relative',
        bgcolor: theme.palette.background.paper
      }}
    >
      {/* Chat Messages */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          width: '100%',
          height: 'calc(100% - 80px)', // Leave space for input
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: theme.palette.background.default,
          },
          '&::-webkit-scrollbar-thumb': {
            background: theme.palette.divider,
            borderRadius: '4px',
          },
        }}
      >
        {conversationHistory.map((step, index) => (
          <Box
            key={index}
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: step.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '80%',
              alignSelf: step.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            {step.attachments?.map((doc, docIndex) => (
              <DocumentPreview key={docIndex} document={doc} />
            ))}
            <ChatMessage 
              message={step.content} 
              isUser={step.role === 'user'} 
            />
          </Box>
        ))}
        <div ref={chatEndRef} />
      </Box>

      {/* Input Area */}
      <Box
        sx={{
          p: 2,
          borderTop: `1px solid ${theme.palette.divider}`,
          bgcolor: theme.palette.background.paper,
          position: 'sticky',
          bottom: 0,
          width: '100%',
          height: '80px',
          display: 'flex',
          alignItems: 'center',
          gap: 1
        }}
      >
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={handleFileUpload}
          multiple
        />
        <IconButton
          color="primary"
          onClick={() => fileInputRef.current?.click()}
          disabled={!canChat}
        >
          <AttachFileIcon />
        </IconButton>
        <TextField
          fullWidth
          placeholder={canChat ? placeholder : "Please select a team with agents to start chatting"}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          onKeyDown={handleKeyDown}
          disabled={!canChat}
          variant="outlined"
          size="small"
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 2,
            }
          }}
        />
        <IconButton
          color="primary"
          onClick={handleSend}
          disabled={!message.trim() || !canChat}
        >
          <SendIcon />
        </IconButton>
      </Box>
    </Box>
  );
};

export default ChatWindow; 
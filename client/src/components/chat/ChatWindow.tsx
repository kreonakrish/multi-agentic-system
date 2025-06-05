import React, { useState, useRef, useEffect } from 'react';
import { Box, TextField, IconButton, Typography, Paper, Link } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import mermaid from 'mermaid';
import { Team, ConversationStep, ConversationSettings, Document } from '../../store/types';
import './ChatWindow.css';

// Initialize mermaid
mermaid.initialize({
  startOnLoad: true,
  theme: 'default',
  securityLevel: 'loose',
});

// Helper function to detect if content is a Mermaid diagram
const isMermaidDiagram = (content: string): boolean => {
  const mermaidStart = content.trim().startsWith('```mermaid');
  const mermaidEnd = content.trim().endsWith('```');
  return mermaidStart && mermaidEnd;
};

// Helper function to extract Mermaid content
const extractMermaidContent = (content: string): string => {
  return content
    .trim()
    .replace('```mermaid', '')
    .replace('```', '')
    .trim();
};

interface ChatWindowProps {
  placeholder: string;
  conversationHistory: ConversationStep[];
  setConversationHistory: React.Dispatch<React.SetStateAction<ConversationStep[]>>;
  selectedTeam: Team | null;
  canChat: boolean;
  onFileUpload: (file: File) => Promise<Document>;
}

// Document Preview Component
const DocumentPreview: React.FC<{ document: Document }> = ({ document }) => {
  const getFileIcon = () => {
    // You can add more file type specific icons here
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

const ChatWindow: React.FC<ChatWindowProps> = ({
  placeholder,
  conversationHistory,
  setConversationHistory,
  selectedTeam,
  canChat,
  onFileUpload
}) => {
  const [message, setMessage] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mermaidRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversationHistory]);

  // Debug logging for conversation history
  useEffect(() => {
    console.log('Conversation history updated:', conversationHistory);
  }, [conversationHistory]);

  // Render Mermaid diagrams after component updates
  useEffect(() => {
    if (mermaidRef.current) {
      mermaid.init(undefined, document.querySelectorAll('.mermaid'));
    }
  }, [conversationHistory]);

  const handleSend = async () => {
    if (message.trim() && canChat) {
      const currentMessage = message;
      setMessage(''); // Clear the input immediately
      
      // Add user message to conversation history
      const userStep: ConversationStep = { 
        role: 'user', 
        content: currentMessage,
        timestamp: new Date().toISOString()
      };
      
      setConversationHistory(prev => [...prev, userStep]);
      
      try {
        // Call the backend API
        const response = await fetch('/api/chat/message', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            content: currentMessage,
            userId: 'user-1', // TODO: Replace with actual user ID
            sessionId: selectedTeam?.id || 'default-session',
            context: {
              team_id: selectedTeam?.id,
              // Include complete team configuration
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
              // Include conversation settings
              conversation_settings: selectedTeam?.conversation_settings || {
                // Required fields
                temperature: 0.7,
                tokenLimit: 2000,
                startPrompt: '',
                endPrompt: '',
                style: 'default',
                // Optional fields
                start_prompt: '',
                system_prompt: '',
                max_tokens: 2000,
                model: "gpt-4"
              },
              // Include complete conversation history
              conversation_history: conversationHistory.map(step => ({
                role: step.role,
                content: step.content,
                metadata: step.metadata,
                attachments: step.attachments,
                timestamp: step.timestamp || new Date().toISOString()
              })),
              // Include any documents that were attached to the conversation
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
        console.log('Received response from server:', responseData);
        
        // The actual response is in the data field
        const data = responseData.data;
        
        // Add bot response to conversation history if we have a valid response
        if (data && data.content) {
          const newStep: ConversationStep = { 
            role: 'bot', 
            content: data.content,
            metadata: {
              team_id: data.metadata?.team_id,
              processing_time: data.metadata?.processing_time,
              confidence_score: data.metadata?.confidence_score,
              agent_contributions: data.metadata?.agent_contributions,
              timestamp: data.timestamp || new Date().toISOString()
            }
          };
          console.log('Adding new conversation step:', newStep);
          setConversationHistory(prev => {
            const newHistory = [...prev, newStep];
            console.log('New conversation history:', newHistory);
            return newHistory;
          });
        } else {
          console.error('Invalid response format:', responseData);
          throw new Error('Invalid response format from server');
        }
      } catch (error) {
        console.error('Error sending message:', error);
        setConversationHistory(prev => [...prev, { 
          role: 'bot', 
          content: 'Sorry, there was an error processing your message. Please try again.',
          metadata: {
            team_id: selectedTeam?.id?.toString(),
            timestamp: new Date().toISOString()
          }
        }]);
      }
    }
  };

  const handleKeyPress = async (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      await handleSend();
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && canChat) {
      try {
        // First, add a message showing that we're uploading
        const uploadingStep: ConversationStep = {
          role: 'user',
          content: `Uploading file: ${file.name}...`,
          timestamp: new Date().toISOString()
        };
        setConversationHistory(prev => [...prev, uploadingStep]);

        // Upload the file and get the document data
        const uploadedDoc = await onFileUpload(file);

        // Create success message with the actual document data
        const successStep: ConversationStep = {
          role: 'user',
          content: `Uploaded file: ${uploadedDoc.name}`,
          timestamp: new Date().toISOString(),
          attachments: [uploadedDoc]
        };

        // Replace the uploading message with the success message
        setConversationHistory(prev => 
          prev.slice(0, -1).concat(successStep)
        );

      } catch (error) {
        console.error('Error uploading file:', error);
        // Update the message to show error
        setConversationHistory(prev => 
          prev.slice(0, -1).concat({
            role: 'bot',
            content: `Error uploading file: ${file.name}. Please try again.`,
            timestamp: new Date().toISOString()
          })
        );
      }
    }
  };

  // Custom renderer for code blocks
  const renderers = {
    code({ node, inline, className, children, ...props }: any) {
      const match = /language-(\w+)/.exec(className || '');
      const language = match ? match[1] : '';
      
      if (inline) {
        return <code className={className} {...props}>{children}</code>;
      }

      const content = String(children).replace(/\n$/, '');
      
      // Check if it's a Mermaid diagram
      if (language === 'mermaid') {
        return (
          <div ref={mermaidRef} className="mermaid">
            {content}
          </div>
        );
      }

      return (
        <SyntaxHighlighter
          style={vscDarkPlus}
          language={language}
          PreTag="div"
          {...props}
        >
          {content}
        </SyntaxHighlighter>
      );
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        overflow: 'hidden'
      }}
    >
      {/* Chat Messages */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 3,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          bgcolor: '#f0f2f5'
        }}
      >
        {conversationHistory.map((step, index) => (
          <Paper
            key={index}
            elevation={0}
            sx={{
              p: 2,
              maxWidth: '70%',
              alignSelf: step.role === 'user' ? 'flex-end' : 'flex-start',
              bgcolor: step.role === 'user' ? '#1877f2' : '#fff',
              color: step.role === 'user' ? '#fff' : '#050505',
              borderRadius: 2,
              boxShadow: '0 1px 2px rgba(0,0,0,0.07), 0 0.5px 1.5px rgba(0,0,0,0.13)'
            }}
          >
            <Box sx={{ mb: step.attachments?.length ? 2 : 0 }}>
              {step.role === 'user' ? (
                <Typography
                  variant="body1"
                  sx={{
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    lineHeight: 1.4
                  }}
                >
                  {step.content}
                </Typography>
              ) : (
                <Box className="markdown-body">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={renderers}
                  >
                    {step.content}
                  </ReactMarkdown>
                </Box>
              )}
            </Box>
            {step.attachments?.map((doc, docIndex) => (
              <Box key={docIndex} sx={{ mt: 1 }}>
                <DocumentPreview document={doc} />
              </Box>
            ))}
          </Paper>
        ))}
        <div ref={chatEndRef} />
      </Box>

      {/* Input Area */}
      <Box
        sx={{
          p: 2,
          bgcolor: '#fff',
          borderTop: '1px solid',
          borderColor: 'divider'
        }}
      >
        <Box
          sx={{
            display: 'flex',
            gap: 1,
            alignItems: 'flex-end'
          }}
        >
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={canChat ? placeholder : "Please select a team with agents to start chatting"}
            disabled={!canChat}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
                bgcolor: '#f0f2f5',
                '&:hover': {
                  bgcolor: '#e4e6eb'
                },
                '&.Mui-focused': {
                  bgcolor: '#fff'
                }
              }
            }}
          />
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
          <IconButton
            onClick={() => fileInputRef.current?.click()}
            disabled={!canChat}
            sx={{
              color: '#1877f2',
              '&:hover': {
                bgcolor: 'rgba(24, 119, 242, 0.04)'
              }
            }}
          >
            <AttachFileIcon />
          </IconButton>
          <IconButton
            onClick={handleSend}
            disabled={!message.trim() || !canChat}
            sx={{
              color: '#1877f2',
              '&:hover': {
                bgcolor: 'rgba(24, 119, 242, 0.04)'
              }
            }}
          >
            <SendIcon />
          </IconButton>
        </Box>
      </Box>
    </Box>
  );
};

export default ChatWindow; 
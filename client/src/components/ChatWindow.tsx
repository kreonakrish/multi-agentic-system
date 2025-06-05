import React, { useState, useRef, useEffect } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import SendIcon from '@mui/icons-material/Send';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { docco } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import python from 'react-syntax-highlighter/dist/esm/languages/hljs/python';
import javascript from 'react-syntax-highlighter/dist/esm/languages/hljs/javascript';
import java from 'react-syntax-highlighter/dist/esm/languages/hljs/java';
import bash from 'react-syntax-highlighter/dist/esm/languages/hljs/bash';
import typescript from 'react-syntax-highlighter/dist/esm/languages/hljs/typescript';
import sql from 'react-syntax-highlighter/dist/esm/languages/hljs/sql';
import BarChartComponent from './BarChartComponent';
import LineChartComponent from './LineChartComponent';
import PieChartComponent from './PieChartComponent';
import { ConversationStep } from '../store/types';
import { Document } from './DocumentList';

// Register languages for syntax highlighting
SyntaxHighlighter.registerLanguage('python', python);
SyntaxHighlighter.registerLanguage('javascript', javascript);
SyntaxHighlighter.registerLanguage('java', java);
SyntaxHighlighter.registerLanguage('bash', bash);
SyntaxHighlighter.registerLanguage('typescript', typescript);
SyntaxHighlighter.registerLanguage('sql', sql);

interface Message {
  sender: 'user' | 'bot';
  text: string;
  data?: any; // If present, this is chart data
  attachments?: Document[];
}

export interface ChatWindowProps {
  placeholder?: string;
  onDataResponse?: (data: any) => void; // Callback to show chart if data is present
  conversationHistory?: ConversationStep[];
  setConversationHistory?: React.Dispatch<React.SetStateAction<ConversationStep[]>>;
  selectedTeam?: any;
  canChat?: boolean;
  onFileUpload?: (file: File) => Promise<Document>;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ placeholder = "Type your question...", onDataResponse, conversationHistory, setConversationHistory, selectedTeam, canChat, onFileUpload }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Sync messages with conversationHistory
  useEffect(() => {
    if (conversationHistory && conversationHistory.length > 0) {
      // Map ConversationStep[] to Message[] for display
      const mapped = conversationHistory.map(step => {
        let sender: 'user' | 'bot' = step.role === 'user' ? 'user' : 'bot';
        // Use (step as any).data to avoid TS error, or just undefined if not present
        let data = (step as any).data || undefined;
        // Try to infer chart type from content if possible
        if (!data && sender === 'bot' && step.content) {
          if (/bar chart/i.test(step.content)) {
            data = {
              type: 'bar',
              labels: ['A', 'B', 'C', 'D'],
              values: [12, 19, 3, 5]
            };
          } else if (/line chart/i.test(step.content)) {
            data = {
              type: 'line',
              labels: ['Jan', 'Feb', 'Mar', 'Apr'],
              values: [5, 9, 7, 14]
            };
          } else if (/pie chart/i.test(step.content)) {
            data = {
              type: 'pie',
              labels: ['X', 'Y', 'Z'],
              values: [30, 50, 20]
            };
          }
        }
        return { sender, text: step.content, data };
      });
      setMessages(mapped);
    } else if (conversationHistory && conversationHistory.length === 0) {
      setMessages([]);
    }
  }, [conversationHistory]);

  // Chart data helpers
  function toBarChartData(labels: string[], values: number[]): any[] {
    return labels.map((name, i) => ({ name, uv: values[i] ?? 0, pv: Math.round(Math.random() * 20) }));
  }
  function toLineChartData(labels: string[], values: number[]): any[] {
    return labels.map((name, i) => ({ name, sent: values[i] ?? 0, received: Math.round(Math.random() * 20) }));
  }
  function toPieChartData(labels: string[], values: number[]): any[] {
    return labels.map((name, i) => ({ name, value: values[i] ?? 0 }));
  }

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    try {
      if (onFileUpload) {
        const uploadedDoc = await onFileUpload(file);
        const fileMsg: Message = {
          sender: 'user',
          text: `Uploaded file: ${file.name}`,
          attachments: [uploadedDoc]
        };
        setMessages(msgs => [...msgs, fileMsg]);
        
        if (setConversationHistory) {
          const fileStep: ConversationStep = {
            role: 'user',
            content: `Uploaded file: ${file.name}`,
            attachments: [uploadedDoc]
          };
          setConversationHistory(prev => [...prev, fileStep]);
        }
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      const errorMsg: Message = {
        sender: 'bot',
        text: 'Failed to upload file. Please try again.'
      };
      setMessages(msgs => [...msgs, errorMsg]);
    }

    // Clear the input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;
    
    // Create user message
    const userMsg: Message = { sender: 'user', text: input };
    const userStep: ConversationStep = { role: 'user', content: input };
    
    // Update local messages and conversation history
    setMessages(msgs => [...msgs, userMsg]);
    if (setConversationHistory) {
      setConversationHistory((prev: ConversationStep[]) => [...prev, userStep]);
    }
    
    setInput('');
    setLoading(true);
    
    try {
      // Call the backend API
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: input,
          userId: 'user-1', // TODO: Replace with actual user ID
          sessionId: selectedTeam?.team_id || 'default-session',
          context: {
            team_id: selectedTeam?.team_id,
            team_config: selectedTeam?.config || {
              name: "Chat Response Team",
              description: "Team for processing chat messages and generating responses",
              members: [
                {
                  agent_id: 10,
                  priority: 3,
                  accuracy_threshold: 0.9,
                  success_rate: 0.95,
                  role: "context_analyzer"
                },
                {
                  agent_id: 11,
                  priority: 2,
                  accuracy_threshold: 0.8,
                  success_rate: 0.9,
                  role: "response_generator"
                }
              ]
            },
            conversation_history: conversationHistory || []
          }
        })
      });

      if (!response.ok) {
        throw new Error(`Server responded with status ${response.status}`);
      }

      const result = await response.json();
      
      // Handle the orchestrator response format
      const botResponse = result.data?.content || 'I apologize, but I could not generate a proper response.';
      const metadata = result.data?.metadata || {};
      
      // Create bot message with metadata
      const botMsg: Message = {
        sender: 'bot',
        text: botResponse,
        data: {
          team_id: metadata.team_id,
          processing_time: metadata.processing_time,
          confidence_score: metadata.confidence_score,
          agent_contributions: metadata.agent_contributions,
          timestamp: result.data?.timestamp
        }
      };

      const botStep: ConversationStep = {
        role: 'bot',
        content: botResponse,
        metadata: botMsg.data
      };

      // Update both messages and conversation history
      setMessages(msgs => [...msgs, botMsg]);
      if (setConversationHistory) {
        setConversationHistory(prev => [...prev, botStep]);
      }

      // If there's a data response handler, call it with the metadata
      if (onDataResponse) {
        onDataResponse(botMsg.data);
      }

    } catch (error) {
      console.error('Error sending message:', error);
      
      // Add error message to chat
      const errorMsg: Message = {
        sender: 'bot',
        text: error instanceof Error ? error.message : 'Sorry, I encountered an error processing your message. Please try again.'
      };
      
      setMessages(msgs => [...msgs, errorMsg]);
      
      if (setConversationHistory) {
        const errorStep: ConversationStep = {
          role: 'bot',
          content: error instanceof Error ? error.message : 'Sorry, I encountered an error processing your message. Please try again.'
        };
        setConversationHistory(prev => [...prev, errorStep]);
      }
    } finally {
      setLoading(false);
    }
  };

  // Function to detect and format code blocks
  const formatMessageText = (text: string) => {
    // Split text into segments based on code blocks
    const segments = text.split(/(```[a-z]*\n[\s\S]*?\n```)/g);
    
    return segments.map((segment, index) => {
      // Check if this is a code block
      const codeBlockMatch = segment.match(/```([a-z]*)\n([\s\S]*?)\n```/);
      if (codeBlockMatch) {
        const language = codeBlockMatch[1] || 'text';
        const code = codeBlockMatch[2];
        return (
          <Box key={index} sx={{ my: 1 }}>
            <SyntaxHighlighter
              language={language}
              style={docco}
              customStyle={{
                borderRadius: '4px',
                padding: '12px',
                margin: '0',
                backgroundColor: '#f5f5f5'
              }}
            >
              {code}
            </SyntaxHighlighter>
          </Box>
        );
      }
      // Regular text
      return <span key={index}>{segment}</span>;
    });
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ flex: 1, overflowY: 'auto', mb: 1 }}>
        {messages.map((msg, idx) => (
          <Box key={idx} sx={{
            display: 'flex',
            justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start',
            mb: 1
          }}>
            <Paper sx={{
              p: 1.2,
              bgcolor: msg.sender === 'user' ? '#e3f2fd' : '#f1f8e9',
              maxWidth: msg.data ? '100%' : '70%',
              width: msg.data ? '100%' : undefined,
              wordBreak: 'break-word',
              boxShadow: 'none',
              mb: 1,
            }}>
              {formatMessageText(msg.text)}
              {/* Render chart if data is present */}
              {msg.data && msg.data.type === 'bar' && (
                <Box sx={{ width: '100%', mt: 1 }}>
                  <BarChartComponent data={toBarChartData(msg.data.labels, msg.data.values)} />
                </Box>
              )}
              {msg.data && msg.data.type === 'line' && (
                <Box sx={{ width: '100%', mt: 1 }}>
                  <LineChartComponent data={toLineChartData(msg.data.labels, msg.data.values)} />
                </Box>
              )}
              {msg.data && msg.data.type === 'pie' && (
                <Box sx={{ width: '100%', mt: 1 }}>
                  <PieChartComponent data={toPieChartData(msg.data.labels, msg.data.values)} />
                </Box>
              )}
              {/* Render attachments if present */}
              {msg.attachments && msg.attachments.length > 0 && (
                <Box sx={{ mt: 1 }}>
                  {msg.attachments.map((doc) => (
                    <Box key={doc.id} sx={{ 
                      display: 'flex', 
                      alignItems: 'center',
                      bgcolor: 'rgba(0,0,0,0.04)',
                      p: 0.5,
                      borderRadius: 1
                    }}>
                      <AttachFileIcon sx={{ mr: 1, fontSize: 20 }} />
                      {doc.name}
                    </Box>
                  ))}
                </Box>
              )}
            </Paper>
          </Box>
        ))}
        <div ref={chatEndRef} />
      </Box>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={handleFileSelect}
          accept="image/*,application/pdf,.doc,.docx,.txt"
        />
        <IconButton 
          onClick={() => fileInputRef.current?.click()}
          disabled={loading || !canChat}
          sx={{ alignSelf: 'center' }}
        >
          <AttachFileIcon />
        </IconButton>
        <TextField
          fullWidth
          placeholder={placeholder}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handleSend(); }}
          disabled={loading || !canChat}
        />
        <Button 
          variant="contained" 
          color="primary"
          onClick={handleSend} 
          disabled={loading || !input.trim() || !canChat}
          sx={{
            fontWeight: 'bold',
            border: '2px solid #222',
            borderRadius: 2,
            boxShadow: 'none',
            minWidth: 'auto',
            width: 56,
            height: '100%',
            padding: '8px 16px',
            '&:hover': {
              opacity: 0.9,
            },
            '&.Mui-disabled': {
              border: '2px solid rgba(34, 34, 34, 0.3)',
            }
          }}
        >
          {loading ? <CircularProgress size={24} sx={{ color: '#fff' }} /> : <SendIcon />}
        </Button>
      </Box>
    </Box>
  );
};

export default ChatWindow;

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
import BarChartComponent from './BarChartComponent';
import LineChartComponent from './LineChartComponent';
import PieChartComponent from './PieChartComponent';
import { ConversationStep } from '../App';

interface Message {
  sender: 'user' | 'bot';
  text: string;
  data?: any; // If present, this is chart data
}

export interface ChatWindowProps {
  placeholder?: string;
  onDataResponse?: (data: any) => void; // Callback to show chart if data is present
  conversationHistory?: ConversationStep[];
  setConversationHistory?: (history: ConversationStep[]) => void;
  selectedTeam?: any;
  canChat?: boolean;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ placeholder = "Type your question...", onDataResponse, conversationHistory, setConversationHistory, selectedTeam, canChat }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

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

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg: Message = { sender: 'user', text: input };
    setMessages(msgs => [...msgs, userMsg]);
    setInput('');
    setLoading(true);
    // Simulate backend response with chart detection
    setTimeout(() => {
      let botMsg: Message;
      if (/bar chart/i.test(input)) {
        botMsg = {
          sender: 'bot',
          text: 'Here is a bar chart based on your question.',
          data: {
            type: 'bar',
            labels: ['A', 'B', 'C', 'D'],
            values: [12, 19, 3, 5]
          }
        };
      } else if (/line chart/i.test(input)) {
        botMsg = {
          sender: 'bot',
          text: 'Here is a line chart based on your question.',
          data: {
            type: 'line',
            labels: ['Jan', 'Feb', 'Mar', 'Apr'],
            values: [5, 9, 7, 14]
          }
        };
      } else if (/pie chart/i.test(input)) {
        botMsg = {
          sender: 'bot',
          text: 'Here is a pie chart based on your question.',
          data: {
            type: 'pie',
            labels: ['X', 'Y', 'Z'],
            values: [30, 50, 20]
          }
        };
      } else {
        botMsg = { sender: 'bot', text: 'This is a response from the bot.' };
      }
      setMessages(msgs => [...msgs, botMsg]);
      setLoading(false);
    }, 1000);
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
              {msg.text}
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
            </Paper>
          </Box>
        ))}
        <div ref={chatEndRef} />
      </Box>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          placeholder={placeholder}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handleSend(); }}
          disabled={loading || !canChat}
        />
        <Button variant="contained" onClick={handleSend} disabled={loading || !input.trim() || !canChat}>
          {loading ? <CircularProgress size={22} /> : 'Send'}
        </Button>
      </Box>
    </Box>
  );
};

export default ChatWindow;

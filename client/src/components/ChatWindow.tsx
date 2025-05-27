import React, { useState, useRef, useEffect } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
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
    if (conversationHistory && conversationHistory.length === 0) {
      setMessages([]);
    }
  }, [conversationHistory]);

  // Mock backend call for Node API
  const mockBackend = async (question: string) => {
    // Simulate network delay
    await new Promise(res => setTimeout(res, 900));
    // Simple mock: if question contains 'bar', return bar chart data; if 'line', return line chart data; if 'pie', return pie chart data; else text only
    if (/bar/i.test(question)) {
      return {
        text: 'Here is a bar chart based on your question.',
        data: {
          type: 'bar',
          labels: ['A', 'B', 'C', 'D'],
          values: [12, 19, 3, 5]
        }
      };
    } else if (/line/i.test(question)) {
      return {
        text: 'Here is a line chart based on your question.',
        data: {
          type: 'line',
          labels: ['Jan', 'Feb', 'Mar', 'Apr'],
          values: [5, 9, 7, 14]
        }
      };
    } else if (/pie/i.test(question)) {
      return {
        text: 'Here is a pie chart based on your question.',
        data: {
          type: 'pie',
          labels: ['X', 'Y', 'Z'],
          values: [30, 50, 20]
        }
      };
    } else {
      return {
        text: 'This is a text response. Ask about a bar, line, or pie chart to see a chart.',
        data: null
      };
    }
  };

  // Helper to convert mock data to recharts format
  function toBarChartData(labels: string[], values: number[]): any[] {
    return labels.map((name, i) => ({ name, uv: values[i] ?? 0, pv: Math.round(Math.random() * 20) }));
  }
  function toLineChartData(labels: string[], values: number[]): any[] {
    return labels.map((name, i) => ({ name, sent: values[i] ?? 0, received: Math.round(Math.random() * 20) }));
  }
  function toPieChartData(labels: string[], values: number[]): any[] {
    return labels.map((name, i) => ({ name, value: values[i] ?? 0 }));
  }

  // Group consecutive messages from the same sender
  function groupMessages(msgs: Message[]) {
    const groups: { sender: 'user' | 'bot'; items: Message[] }[] = [];
    for (const msg of msgs) {
      if (groups.length && groups[groups.length - 1].sender === msg.sender) {
        groups[groups.length - 1].items.push(msg);
      } else {
        groups.push({ sender: msg.sender, items: [msg] });
      }
    }
    return groups;
  }

  const handleSend = async () => {
    if (!input.trim() || !canChat || !selectedTeam || !selectedTeam.agents || selectedTeam.agents.length === 0) return;
    const userMsg: Message = { sender: 'user', text: input };
    setMessages(msgs => [...msgs, userMsg]);
    let newHistory = conversationHistory ? [...conversationHistory] : [];
    const userIdx = newHistory.length;
    // Add user step
    newHistory.push({ role: 'user', content: input });
    // Use first agent in priority order
    const agentObj = selectedTeam.agents[0];
    const agentName = agentObj?.name || 'Unknown Agent';
    const agentIdx = newHistory.length;
    newHistory.push({ role: 'agent', content: `Processing: ${input}`, agentName, parentIdx: userIdx });
    // Use first tool of the agent if available
    const toolName = agentObj?.tools && agentObj.tools.length > 0 ? agentObj.tools[0] : undefined;
    const toolIdx = newHistory.length;
    if (toolName) {
      newHistory.push({ role: 'tool', content: `Querying: ${input}`, toolName, parentIdx: agentIdx });
    }
    setInput('');
    setLoading(true);
    try {
      // Use mock backend for now
      const result = await mockBackend(input);
      const botMsg: Message = { sender: 'bot', text: result.text, data: result.data };
      setMessages(msgs => [...msgs, botMsg]);
      // Add bot step
      newHistory.push({ role: 'bot', content: result.text, parentIdx: toolName ? toolIdx : agentIdx });
      if (setConversationHistory) setConversationHistory(newHistory);
      if (result.data && onDataResponse) onDataResponse(result.data);
    } catch (e) {
      setMessages(msgs => [...msgs, { sender: 'bot', text: 'Sorry, there was an error.' }]);
      newHistory.push({ role: 'bot', content: 'Sorry, there was an error.', parentIdx: toolName ? toolIdx : agentIdx });
      if (setConversationHistory) setConversationHistory(newHistory);
    }
    setLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Paper elevation={2} sx={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 220, mt: 1 }}>
      <Box sx={{ flex: 1, overflowY: 'auto', p: 1, background: '#f7f7fa', display: 'flex', flexDirection: 'column' }}>
        {/* Chat messages */}
        <Box sx={{ flex: 1 }}>
          {groupMessages(messages).map((group, gIdx) => (
            <Box key={gIdx} sx={{ mb: 1 }}>
              {/* Grouped message bubbles */}
              {group.items.map((msg, idx) => (
                <React.Fragment key={idx}>
                  <Box sx={{
                    display: 'flex',
                    justifyContent: group.sender === 'user' ? 'flex-end' : 'flex-start',
                    mb: 0.5
                  }}>
                    <Box sx={{
                      bgcolor: group.sender === 'user' ? '#1877f2' : '#e0e0e0',
                      color: group.sender === 'user' ? '#fff' : '#222',
                      px: 1.5, py: 0.7, borderRadius: 2, maxWidth: '80%',
                      fontSize: '0.98rem',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}>
                      {msg.text}
                    </Box>
                  </Box>
                  {/* Render chart if data is present and from bot */}
                  {group.sender === 'bot' && msg.data && (
                    <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 1, mt: 0.5 }}>
                      {msg.data.type === 'bar' && <BarChartComponent data={toBarChartData(msg.data.labels, msg.data.values)} />}
                      {msg.data.type === 'line' && <LineChartComponent data={toLineChartData(msg.data.labels, msg.data.values)} />}
                      {msg.data.type === 'pie' && <PieChartComponent data={toPieChartData(msg.data.labels, msg.data.values)} />}
                    </Box>
                  )}
                </React.Fragment>
              ))}
            </Box>
          ))}
          <div ref={chatEndRef} />
        </Box>
      </Box>
      {/* Input box always at the bottom */}
      <Box sx={{ display: 'flex', alignItems: 'center', p: 1, borderTop: '1px solid #eee', gap: 1, bgcolor: '#fff' }}>
        <TextField
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          size="small"
          fullWidth
          disabled={loading || !canChat}
        />
        <Button onClick={handleSend} variant="contained" color="primary" disabled={loading || !input.trim() || !canChat} size="small">
          {loading ? <CircularProgress size={20} /> : 'Send'}
        </Button>
      </Box>
    </Paper>
  );
};

export default ChatWindow;


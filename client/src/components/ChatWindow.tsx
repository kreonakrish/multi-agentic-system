import React, { useState, useRef, useEffect } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';

interface Message {
  sender: 'user' | 'bot';
  text: string;
  data?: any; // If present, this is chart data
}

interface ChatWindowProps {
  placeholder?: string;
  onDataResponse?: (data: any) => void; // Callback to show chart if data is present
}

const ChatWindow: React.FC<ChatWindowProps> = ({ placeholder = "Type your question...", onDataResponse }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg: Message = { sender: 'user', text: input };
    setMessages(msgs => [...msgs, userMsg]);
    setInput('');
    setLoading(true);
    // Simulate backend call
    try {
      // Replace this with your real backend call
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input })
      });
      const result = await response.json();
      const botMsg: Message = { sender: 'bot', text: result.text, data: result.data };
      setMessages(msgs => [...msgs, botMsg]);
      if (result.data && onDataResponse) onDataResponse(result.data);
    } catch (e) {
      setMessages(msgs => [...msgs, { sender: 'bot', text: 'Sorry, there was an error.' }]);
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
    <Paper elevation={2} sx={{ display: 'flex', flexDirection: 'column', height: 220, mt: 1 }}>
      <Box sx={{ flex: 1, overflowY: 'auto', p: 1, background: '#f7f7fa' }}>
        {messages.map((msg, idx) => (
          <Box key={idx} sx={{
            display: 'flex',
            justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start',
            mb: 0.5
          }}>
            <Box sx={{
              bgcolor: msg.sender === 'user' ? '#1877f2' : '#e0e0e0',
              color: msg.sender === 'user' ? '#fff' : '#222',
              px: 1.5, py: 0.7, borderRadius: 2, maxWidth: '80%',
              fontSize: '0.98rem',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}>
              {msg.text}
            </Box>
          </Box>
        ))}
        <div ref={chatEndRef} />
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', p: 1, borderTop: '1px solid #eee', gap: 1 }}>
        <TextField
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          size="small"
          fullWidth
          disabled={loading}
        />
        <Button onClick={handleSend} variant="contained" color="primary" disabled={loading || !input.trim()} size="small">
          {loading ? <CircularProgress size={20} /> : 'Send'}
        </Button>
      </Box>
    </Paper>
  );
};

export default ChatWindow;


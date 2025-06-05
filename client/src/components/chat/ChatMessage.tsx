import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import ChatDataChart from './ChatDataChart';

interface ChatMessageProps {
  message: string;
  isUser: boolean;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, isUser }) => {
  const tryParseJSON = (text: string) => {
    try {
      const data = JSON.parse(text);
      // Check if it's an array of objects with at least one numeric value
      if (Array.isArray(data) && data.length > 0 && typeof data[0] === 'object') {
        const firstObj = data[0];
        const numericKey = Object.keys(firstObj).find(key => typeof firstObj[key] === 'number');
        if (numericKey) {
          return {
            data,
            xKey: Object.keys(firstObj)[0],
            yKey: numericKey
          };
        }
      }
      return null;
    } catch (e) {
      return null;
    }
  };

  const jsonData = tryParseJSON(message);

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 2
      }}
    >
      <Paper
        sx={{
          p: 2,
          maxWidth: '70%',
          bgcolor: isUser ? 'primary.main' : 'background.paper',
          color: isUser ? 'primary.contrastText' : 'text.primary'
        }}
      >
        <Typography component="div">
          {jsonData ? (
            <>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{message}</pre>
              <ChatDataChart
                data={jsonData.data}
                xKey={jsonData.xKey}
                yKey={jsonData.yKey}
                title="Data Visualization"
              />
            </>
          ) : (
            <span style={{ whiteSpace: 'pre-wrap' }}>{message}</span>
          )}
        </Typography>
      </Paper>
    </Box>
  );
};

export default ChatMessage; 
import React from 'react';
import { Box, Button } from '@mui/material';

interface ChatControlsProps {
  onNewChat: () => void;
}

const ChatControls: React.FC<ChatControlsProps> = ({
  onNewChat
}) => {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "flex-end",
        gap: 2,
        p: 2,
        borderBottom: '1px solid',
        borderColor: 'divider',
        bgcolor: '#fff'
      }}
    >
      <Button
        variant="contained"
        onClick={onNewChat}
        sx={{
          bgcolor: '#1877f2',
          color: '#fff',
          fontWeight: 600,
          '&:hover': {
            bgcolor: '#166fe5',
          },
          px: 3,
          py: 1
        }}
      >
        + NEW CHAT
      </Button>
    </Box>
  );
};

export default ChatControls; 
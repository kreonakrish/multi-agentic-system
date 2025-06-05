import React from 'react';
import { Button } from '@mui/material';

interface ChatSessionButtonProps {
  onClick: () => void;
  active: boolean;
  children: React.ReactNode;
}

const ChatSessionButton: React.FC<ChatSessionButtonProps> = ({
  onClick,
  active,
  children,
}) => {
  return (
    <Button
      variant={active ? 'contained' : 'outlined'}
      onClick={onClick}
      fullWidth
      sx={{
        justifyContent: 'flex-start',
        mb: 1,
        textAlign: 'left',
      }}
    >
      {children}
    </Button>
  );
};

export default ChatSessionButton; 
import React from 'react';
import { Box } from '@mui/material';
import ChatWindow from '../chat/ChatWindow';
import { Team, ConversationStep, Document } from '../../store/types';

interface MainContentProps {
  conversationHistory: ConversationStep[];
  setConversationHistory: React.Dispatch<React.SetStateAction<ConversationStep[]>>;
  selectedTeam: Team | null;
  onFileUpload: (file: File) => Promise<Document>;
}

const MainContent: React.FC<MainContentProps> = ({
  conversationHistory,
  setConversationHistory,
  selectedTeam,
  onFileUpload
}) => {
  const canChat = Boolean(selectedTeam?.agents?.length);

  return (
    <Box
      component="main"
      sx={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        width: '100%',
        height: 'calc(100vh - 64px)', // Subtract the TopBar height
        overflow: 'hidden',
        bgcolor: '#f0f2f5',
        p: 2
      }}
    >
      {/* Main Chat Area */}
      <Box
        sx={{
          flex: 1,
          display: "flex",
          width: '100%',
          height: '100%',
          overflow: 'hidden',
          bgcolor: '#fff',
          borderRadius: 3,
          boxShadow: '0 1px 2px rgba(0,0,0,0.07), 0 0.5px 1.5px rgba(0,0,0,0.13)'
        }}
      >
        <ChatWindow
          placeholder="Ask your analytics questions..."
          conversationHistory={conversationHistory}
          setConversationHistory={setConversationHistory}
          selectedTeam={selectedTeam}
          canChat={canChat}
          onFileUpload={onFileUpload}
        />
      </Box>
    </Box>
  );
};

export default MainContent; 
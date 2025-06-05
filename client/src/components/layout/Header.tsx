import React from 'react';
import { AppBar, Toolbar, Typography, IconButton, Box } from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import HelpIcon from '@mui/icons-material/Help';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';

const Header: React.FC = () => {
  return (
    <AppBar position="static" sx={{ background: '#222', boxShadow: 'none' }}>
      <Toolbar sx={{ minHeight: 56 }}>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
          Multi-Agent System
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <IconButton
            color="inherit"
            onClick={() => {/* TODO: Implement help dialog */}}
          >
            <HelpIcon />
          </IconButton>
          
          <IconButton
            color="inherit"
            onClick={() => {/* TODO: Implement settings dialog */}}
          >
            <SettingsIcon />
          </IconButton>
          
          <IconButton
            color="inherit"
            onClick={() => {/* TODO: Implement user menu */}}
          >
            <AccountCircleIcon />
          </IconButton>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Header; 
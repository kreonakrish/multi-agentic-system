import React from 'react';
import { AppBar, Toolbar, Typography, IconButton, Box } from '@mui/material';
import HelpIcon from '@mui/icons-material/Help';
import SettingsIcon from '@mui/icons-material/Settings';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';

const TopBar = () => {
  return (
    <AppBar position="static" sx={{ bgcolor: '#8C7B53', boxShadow: 'none', color: '#kkk' }}>
      <Toolbar sx={{ minHeight: 108 }}>
        <Typography variant="h4" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
          CCB - Consumer Analytics and Reporting Infrastructure
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <IconButton color="inherit" size="small">
            <HelpIcon />
          </IconButton>
          <IconButton color="inherit" size="small">
            <SettingsIcon />
          </IconButton>
          <IconButton color="inherit" size="small">
            <AccountCircleIcon />
          </IconButton>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default TopBar; 
import React from 'react';
import { AppBar, Toolbar, Typography, IconButton, Box, useTheme } from '@mui/material';
import HelpIcon from '@mui/icons-material/Help';
import SettingsIcon from '@mui/icons-material/Settings';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';

interface TopBarProps {
  onThemeToggle: () => void;
  mode: 'light' | 'dark';
}

const TopBar: React.FC<TopBarProps> = ({ onThemeToggle, mode }) => {
  const theme = useTheme();
  
  return (
    <AppBar 
      position="static" 
      sx={{ 
        bgcolor: mode === 'dark' ? '#3C3F41' : '#4A5568',  // IntelliJ-inspired colors
        boxShadow: 'none',
        borderBottom: '1px solid',
        borderColor: mode === 'dark' ? 'rgba(255,255,255,0.1)' : theme.palette.divider,
        transition: 'background-color 0.3s ease'
      }}
    >
      <Toolbar sx={{ minHeight: 64 }}>
        <Box sx={{ 
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column'
        }}>
          <Box sx={{ width: 'fit-content' }}>
            <Typography 
              variant="h3" 
              component="div" 
              sx={{ 
                fontWeight: 800,
                color: mode === 'dark' ? '#A7A7A7' : '#FFFFFF',
                letterSpacing: '0.02em'
              }}
            >
              2025 Global Hackathon
            </Typography>
            <Typography 
              variant="subtitle1" 
              component="div" 
              sx={{ 
                color: mode === 'dark' ? '#8B8B8B' : 'rgba(255,255,255,0.8)',
                letterSpacing: '0.01em',
                mt: 0.5,
                fontSize: '0.9rem',
                textAlign: 'right'
              }}
            >
              Powered by JPMorgan Chase & Co.
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <IconButton 
            sx={{ 
              color: mode === 'dark' ? '#A7A7A7' : 'rgba(255,255,255,0.9)',
              '&:hover': {
                bgcolor: mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.1)',
                color: mode === 'dark' ? '#FFFFFF' : '#FFFFFF'
              }
            }}
            onClick={onThemeToggle}
            size="small"
            title={mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {mode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
          </IconButton>
          <IconButton 
            sx={{ 
              color: mode === 'dark' ? '#A7A7A7' : 'rgba(255,255,255,0.9)',
              '&:hover': {
                bgcolor: mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.1)',
                color: mode === 'dark' ? '#FFFFFF' : '#FFFFFF'
              }
            }} 
            size="small" 
            title="Help"
          >
            <HelpIcon />
          </IconButton>
          <IconButton 
            sx={{ 
              color: mode === 'dark' ? '#A7A7A7' : 'rgba(255,255,255,0.9)',
              '&:hover': {
                bgcolor: mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.1)',
                color: mode === 'dark' ? '#FFFFFF' : '#FFFFFF'
              }
            }} 
            size="small" 
            title="Settings"
          >
            <SettingsIcon />
          </IconButton>
          <IconButton 
            sx={{ 
              color: mode === 'dark' ? '#A7A7A7' : 'rgba(255,255,255,0.9)',
              '&:hover': {
                bgcolor: mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.1)',
                color: mode === 'dark' ? '#FFFFFF' : '#FFFFFF'
              }
            }} 
            size="small" 
            title="Account"
          >
            <AccountCircleIcon />
          </IconButton>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default TopBar; 
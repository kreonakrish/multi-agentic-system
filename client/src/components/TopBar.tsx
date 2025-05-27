import React from 'react';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';

function TopBar() {
    return (
        <AppBar position="static" color="primary" elevation={1}>
            <Toolbar>
                <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
                    CCB - Consumer Analytics and Reporting Infrastructure
                </Typography>
                <Button color="inherit" sx={{ mr: 1 }}>Add Agents</Button>
                <Button color="inherit" sx={{ mr: 1 }}>Add Tools</Button>
                <Button variant="contained" color="secondary" sx={{ mr: 2 }}>+ NEW CHAT</Button>
                <Button color="inherit" sx={{ mr: 1, fontWeight: 700, borderBottom: '2px solid #fff' }}>Conversation History</Button>
                <Box sx={{ ml: 1, color: '#fff', fontSize: 14, display: { xs: 'none', sm: 'block' } }}>
                    Settings | Documents
                </Box>
                <Button color="inherit" sx={{ ml: 1, fontSize: 22 }}>×</Button>
            </Toolbar>
        </AppBar>
    );
}

export default TopBar;
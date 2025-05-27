import React, { useEffect, useState } from 'react';
import axios from 'axios';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';

function LeftSidebar() {
    const [agents, setAgents] = useState([]);

    useEffect(() => {
        axios.get('http://localhost:4000/api/agents')
            .then(res => setAgents(res.data));
    }, []);

    return (
        <Paper elevation={1} sx={{ width: 230, minWidth: 200, p: 2, mr: 2, bgcolor: 'background.paper' }}>
            <List>
                {agents.map(agent => (
                    <ListItem
                        key={agent}
                        sx={{
                            mb: 1,
                            bgcolor: '#f0f2f5',
                            borderRadius: 2,
                            border: '1px solid #e4e6eb',
                            px: 2,
                        }}
                    >
                        <Typography fontWeight={600}>{agent}</Typography>
                    </ListItem>
                ))}
            </List>
        </Paper>
    );
}

export default LeftSidebar;
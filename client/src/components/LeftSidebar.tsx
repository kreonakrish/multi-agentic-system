import React, { useEffect, useState } from 'react';
import axios from 'axios';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';

interface Tool {
    id: number;
    toolName: string;
}

interface Agent {
    id: number;
    name: string;
    tools: any[]; // Make this any[] to support all returned shapes
}

function LeftSidebar() {
    const [agents, setAgents] = useState<Agent[]>([]);

    useEffect(() => {
        axios.get('http://localhost:4000/api/agents')
            .then(res => {
                console.log('API /api/agents response:', res.data);
                if (Array.isArray(res.data)) {
                    setAgents(res.data);
                } else {
                    setAgents([]);
                }
            })
            .catch(err => {
                console.error('Failed to fetch agents:', err);
                setAgents([]);
            });
    }, []);

    // 🟢 Helper for safe tool name display
    function renderToolNames(tools: any[]): string {
        if (!Array.isArray(tools) || !tools.length) return '';
        return tools
            .map((tool: any) =>
                typeof tool === 'object' && tool !== null
                    ? tool.toolName || tool.tool_name || JSON.stringify(tool)
                    : String(tool)
            )
            .filter(Boolean)
            .join(', ');
    }

    return (
        <Paper elevation={1} sx={{ width: 230, minWidth: 200, p: 2, mr: 2, bgcolor: 'background.paper' }}>
            <List>
                {(Array.isArray(agents) ? agents : []).map((agent: any) => (
                    <ListItem
                        key={agent && agent.id ? agent.id : Math.random()}
                        sx={{
                            mb: 1,
                            bgcolor: '#f0f2f5',
                            borderRadius: 2,
                            border: '1px solid #e4e6eb',
                            px: 2,
                            display: 'block'
                        }}
                    >
                        <Typography fontWeight={600}>{agent && agent.name ? agent.name : ''}</Typography>
                        {agent && agent.tools && agent.tools.length > 0 && (
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                                Tools: {renderToolNames(agent.tools)}
                            </Typography>
                        )}
                    </ListItem>
                ))}
            </List>
        </Paper>
    );
}

export default LeftSidebar;

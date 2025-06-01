import React, { useEffect, useState } from 'react';
import axios from 'axios';
import List from '@mui/material/List';
import Paper from '@mui/material/Paper';

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
            .catch(error => {
                console.error('Error fetching agents:', error);
                setAgents([]);
            });
    }, []);

    return (
        <Paper elevation={1} sx={{ width: 230, minWidth: 200, p: 2, mr: 2, bgcolor: 'background.paper' }}>
            <List>
                {(Array.isArray(agents) ? agents : []).map((agent: any) => (
                    <div
                        key={agent && agent.id ? agent.id : Math.random()}
                        style={{
                            marginBottom: '8px',
                            backgroundColor: '#f0f2f5',
                            borderRadius: '8px',
                            border: '1px solid #e4e6eb',
                            padding: '16px',
                        }}
                    >
                        <div style={{ fontWeight: 600 }}>{agent && agent.name ? agent.name : ''}</div>
                        {agent && agent.tools && agent.tools.length > 0 && (
                            <div style={{ marginTop: '4px', color: 'rgba(0, 0, 0, 0.6)', fontSize: '14px' }}>
                                Tools: {agent.tools.map((tool: any) => 
                                    typeof tool === 'object' && tool !== null
                                        ? tool.toolName || tool.tool_name || JSON.stringify(tool)
                                        : tool
                                ).filter(Boolean).join(', ')}
                            </div>
                        )}
                    </div>
                ))}
            </List>
        </Paper>
    );
}

export default LeftSidebar;

import React, { useState, useEffect } from 'react';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { Box, Typography, CircularProgress } from '@mui/material';

interface AgentInteraction {
  id: number;
  source_agent: string;
  target_agent: string;
  interaction_type: string;
  timestamp: string;
  status: string;
  priority: number;
}

interface AgentInteractionsProps {
  selectedAgents?: string[];
  teamId?: number;
  sourceId?: number;
  targetId?: number;
}

const AgentInteractions: React.FC<AgentInteractionsProps> = ({ 
  selectedAgents, 
  teamId,
  sourceId,
  targetId 
}) => {
  const [interactions, setInteractions] = useState<AgentInteraction[]>([]);
  const [loading, setLoading] = useState(true);
  const [paginationModel, setPaginationModel] = useState({
    pageSize: 10,
    page: 0,
  });

  useEffect(() => {
    const fetchInteractions = async () => {
      try {
        setLoading(true);
        let url = '/api/agent-interactions';
        const params = new URLSearchParams();
        
        if (teamId) {
          params.append('team_id', teamId.toString());
        }

        // If we have a specific edge selected (source and target)
        if (sourceId && targetId) {
          params.append('source', sourceId.toString());
          params.append('target', targetId.toString());
        }
        // Otherwise, use the selected agents filter
        else if (selectedAgents?.length) {
          params.append('agents', selectedAgents.join(','));
        }

        if (params.toString()) {
          url += `?${params.toString()}`;
        }

        const response = await fetch(url);
        if (!response.ok) {
          throw new Error('Failed to fetch interactions');
        }
        const data = await response.json();
        setInteractions(data);
      } catch (error) {
        console.error('Error fetching interactions:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchInteractions();
  }, [selectedAgents, teamId, sourceId, targetId]);

  const columns: GridColDef[] = [
    {
      field: 'timestamp',
      headerName: 'Time',
      width: 180,
      valueFormatter: (params) => {
        return new Date(params.value).toLocaleString();
      }
    },
    {
      field: 'source_agent',
      headerName: 'Source Agent',
      width: 150,
    },
    {
      field: 'target_agent',
      headerName: 'Target Agent',
      width: 150,
    },
    {
      field: 'interaction_type',
      headerName: 'Type',
      width: 130,
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
    },
    {
      field: 'priority',
      headerName: 'Priority',
      width: 100,
      type: 'number',
    }
  ];

  if (loading) {
    return (
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center',
        height: '100%' 
      }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="h6" component="h3">
        {sourceId && targetId ? 'Agent Interactions' : 'Agent Interactions'}
      </Typography>
      <Box sx={{ flex: 1, width: '100%' }}>
        <DataGrid
          rows={interactions}
          columns={columns}
          paginationModel={paginationModel}
          onPaginationModelChange={setPaginationModel}
          pageSizeOptions={[10, 25, 50]}
          disableRowSelectionOnClick
          autoHeight
          sx={{
            '& .MuiDataGrid-cell': {
              whiteSpace: 'normal',
              lineHeight: 'normal',
              padding: '8px',
            },
          }}
        />
      </Box>
    </Box>
  );
};

export default AgentInteractions; 
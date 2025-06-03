import React, { useState, useEffect } from 'react';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { Box, Typography, CircularProgress, Tooltip } from '@mui/material';

interface AgentInteraction {
  id: number;
  conversation_id: string;
  source_agent: string;
  target_agent: string;
  interaction_type: string;
  timestamp: string;
  status: string;
  content: string;
  processed_message: string;
  model_response: string;
}

interface AgentInteractionsProps {
  selectedAgents?: string[];
  teamId?: number;
  sourceId?: number | null;
  targetId?: number | null;
  conversationId?: string;
}

const AgentInteractions: React.FC<AgentInteractionsProps> = ({ 
  selectedAgents, 
  teamId,
  sourceId,
  targetId,
  conversationId
}) => {
  const [interactions, setInteractions] = useState<AgentInteraction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [paginationModel, setPaginationModel] = useState({
    pageSize: 10,
    page: 0,
  });

  useEffect(() => {
    const fetchInteractions = async () => {
      try {
        setLoading(true);
        setError(null);
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
        
        // Add conversation ID if available
        if (conversationId) {
          params.append('conversation_id', conversationId);
        }

        if (params.toString()) {
          url += `?${params.toString()}`;
        }

        console.log('Fetching interactions from:', url);
        const response = await fetch(url);
        console.log('Response status:', response.status);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch interactions: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Received interactions data:', data);
        
        if (!Array.isArray(data)) {
          throw new Error('Expected array of interactions but received: ' + typeof data);
        }
        
        setInteractions(data);
        console.log('Set interactions state with', data.length, 'items');
        
      } catch (error) {
        console.error('Error fetching interactions:', error);
        setError(error instanceof Error ? error.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchInteractions();
  }, [selectedAgents, teamId, sourceId, targetId, conversationId]);

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
      headerName: 'From',
      width: 150,
    },
    {
      field: 'target_agent',
      headerName: 'To',
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
      field: 'content',
      headerName: 'Message',
      width: 300,
      renderCell: (params) => (
        <Tooltip title={params.value} placement="top">
          <div style={{ 
            whiteSpace: 'nowrap', 
            overflow: 'hidden', 
            textOverflow: 'ellipsis',
            width: '100%'
          }}>
            {params.value}
          </div>
        </Tooltip>
      )
    },
    {
      field: 'processed_message',
      headerName: 'Processed Message',
      width: 300,
      renderCell: (params) => (
        <Tooltip title={params.value} placement="top">
          <div style={{ 
            whiteSpace: 'nowrap', 
            overflow: 'hidden', 
            textOverflow: 'ellipsis',
            width: '100%'
          }}>
            {params.value}
          </div>
        </Tooltip>
      )
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

  if (error) {
    return (
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center',
        height: '100%',
        color: 'error.main'
      }}>
        <Typography>Error: {error}</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="h6" component="h3">
        Agent Interactions
        {conversationId && <Typography variant="caption" display="block">
          Conversation ID: {conversationId}
        </Typography>}
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
        {interactions.length === 0 && (
          <Typography sx={{ textAlign: 'center', mt: 2 }}>
            No interactions found
          </Typography>
        )}
      </Box>
    </Box>
  );
};

export default AgentInteractions; 
import React, { useEffect, useState } from 'react';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { Box, Typography, CircularProgress, Alert, Tooltip } from '@mui/material';

interface AgentInteraction {
  id: number;
  conversation_id: string;
  source_agent: string;
  target_agent: string;
  interaction_type: string;
  status: string;
  timestamp: string;
  content: string | object;
  processed_message: string | null;
  model_response: string | object | null;
}

interface AgentInteractionsProps {
  teamId: number;
  sourceId: number | null;
  targetId: number | null;
}

const AgentInteractions: React.FC<AgentInteractionsProps> = ({
  teamId,
  sourceId,
  targetId
}) => {
  const [interactions, setInteractions] = useState<AgentInteraction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInteractions = async () => {
      if (!teamId) return;

      setLoading(true);
      setError(null);

      try {
        let url = `/api/agent-interactions?team_id=${teamId}`;
        
        // Only add source and target parameters if both are selected (edge click)
        if (sourceId !== null && targetId !== null) {
          url += `&source=${sourceId}&target=${targetId}`;
        }

        const response = await fetch(url);
        
        if (!response.ok) {
          throw new Error('Failed to fetch interactions');
        }

        const data = await response.json();
        setInteractions(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchInteractions();
  }, [teamId, sourceId, targetId]);

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value;
    return JSON.stringify(value, null, 2);
  };

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
      renderCell: (params) => {
        const value = formatValue(params.value);
        return (
          <Tooltip title={value} placement="top">
            <div style={{ 
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              width: '100%'
            }}>
              {value}
            </div>
          </Tooltip>
        );
      }
    },
    {
      field: 'model_response',
      headerName: 'Response',
      width: 300,
      renderCell: (params) => {
        const value = formatValue(params.value);
        return (
          <Tooltip title={value} placement="top">
            <div style={{ 
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              width: '100%'
            }}>
              {value}
            </div>
          </Tooltip>
        );
      }
    }
  ];

  if (!teamId) {
    return <Typography>Select a team to view interactions</Typography>;
  }

  if (loading) {
    return <CircularProgress />;
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  return (
    <Box sx={{ width: '100%', height: 400 }}>
      <Typography variant="h6" gutterBottom>
        {sourceId !== null && targetId !== null ? 'Filtered Agent Interactions' : 'All Team Interactions'}
      </Typography>
      <DataGrid
        rows={interactions}
        columns={columns}
        initialState={{
          pagination: {
            paginationModel: {
              pageSize: 5,
            },
          },
        }}
        pageSizeOptions={[5]}
        disableRowSelectionOnClick
        autoHeight
      />
    </Box>
  );
};

export default AgentInteractions; 
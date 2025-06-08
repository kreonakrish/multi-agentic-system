import React, { useState } from 'react';
import { Box, Typography, Paper, IconButton, Tooltip, Snackbar } from '@mui/material';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import ThumbDownIcon from '@mui/icons-material/ThumbDown';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ThumbUpOutlinedIcon from '@mui/icons-material/ThumbUpOutlined';
import ThumbDownOutlinedIcon from '@mui/icons-material/ThumbDownOutlined';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import ChatDataChart from './ChatDataChart';
import BarChart from '../charts/BarChartComponent';
import LineChart from '../charts/LineChartComponent';
import PieChart from '../charts/PieChartComponent';

interface ChatMessageProps {
  message: string;
  isUser: boolean;
}

interface VisualizationData {
  type: 'visualization';
  data: Array<{ name: string; value: number }>;
  labels: string[];
  values: number[];
}

interface RawData {
  type: 'raw';
  data: Array<Record<string, any>>;
  xKey: string;
  yKey: string;
}

type ChartData = VisualizationData | RawData;

// Code Block Component for markdown
const CodeBlock = React.memo(({ node, inline, className, children, ...props }: any) => {
  const match = /language-(\w+)/.exec(className || '');
  const content = String(children).replace(/\n$/, '');

  if (!inline && match) {
    return (
      <SyntaxHighlighter
        style={vscDarkPlus}
        language={match[1]}
        PreTag="div"
        {...props}
      >
        {content}
      </SyntaxHighlighter>
    );
  }

  return (
    <code className={className} {...props}>
      {children}
    </code>
  );
});

CodeBlock.displayName = 'CodeBlock';

const ChatMessage: React.FC<ChatMessageProps> = ({ message, isUser }) => {
  const [thumbsUp, setThumbsUp] = useState(false);
  const [thumbsDown, setThumbsDown] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  const handleThumbsUp = () => {
    setThumbsUp(!thumbsUp);
    setThumbsDown(false);
    // Here you can add API call to save the feedback
  };

  const handleThumbsDown = () => {
    setThumbsDown(!thumbsDown);
    setThumbsUp(false);
    // Here you can add API call to save the feedback
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message);
      setSnackbarOpen(true);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  const tryParseJSON = (text: string): VisualizationData | null => {
    try {
      const data = JSON.parse(text);
      
      // Check if it's visualization data (array of objects with name and value)
      if (Array.isArray(data) && data.length > 0 && 
          typeof data[0] === 'object' && 
          'name' in data[0] && 
          'value' in data[0]) {
        return {
          type: 'visualization',
          data: data,
          labels: data.map(item => item.name),
          values: data.map(item => item.value)
        };
      }
      
      return null;
    } catch (e) {
      return null;
    }
  };

  const renderChart = (data: VisualizationData): JSX.Element | null => {
    // Generate random colors for the charts
    const backgroundColor = data.data.map(() => '#' + Math.floor(Math.random()*16777215).toString(16));
    
    // Bar and Pie Chart data
    const barAndPieData = {
      labels: data.labels,
      datasets: [{
        label: 'Value',
        data: data.values,
        backgroundColor: backgroundColor,
        borderColor: backgroundColor,
        borderWidth: 1
      }]
    };

    // Line Chart data
    const lineData = {
      labels: data.labels,
      datasets: [{
        label: 'Value',
        data: data.values,
        borderColor: '#8884d8',
        backgroundColor: 'rgba(136, 132, 216, 0.1)',
        tension: 0.3
      }]
    };

    return (
      <Box sx={{ mt: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <Box sx={{ height: 400 }}>
            <Typography variant="h6" gutterBottom>Data Visualization</Typography>
            <BarChart data={barAndPieData} />
          </Box>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Box sx={{ flex: '1 1 300px', height: 300 }}>
              <Typography variant="h6" gutterBottom>Trend Analysis</Typography>
              <LineChart data={lineData} />
            </Box>
            <Box sx={{ flex: '1 1 300px', height: 300 }}>
              <Typography variant="h6" gutterBottom>Distribution</Typography>
              <PieChart data={barAndPieData} />
            </Box>
          </Box>
        </Box>
      </Box>
    );
  };

  const renderContent = (text: string) => {
    // Split on visualization tags
    const parts = text.split(/\[VISUALIZATION_DATA\]|\[\/VISUALIZATION_DATA\]/);
    
    return parts.map((part, index) => {
      // Skip empty parts
      if (!part.trim()) return null;

      // Try to parse as JSON for visualization
      try {
        const data = JSON.parse(part);
        if (Array.isArray(data) && data.length > 0 && 'name' in data[0] && 'value' in data[0]) {
          const visualizationData: VisualizationData = {
            type: 'visualization' as const,
            data: data,
            labels: data.map(item => item.name),
            values: data.map(item => item.value)
          };
          return renderChart(visualizationData);
        }
      } catch (e) {
        // If not JSON, render as markdown
        return (
          <ReactMarkdown
            key={index}
            children={part}
            remarkPlugins={[remarkGfm]}
            components={{
              code: CodeBlock,
              p: ({ children }) => (
                <Typography
                  component="p"
                  sx={{
                    my: 1,
                    color: isUser ? 'inherit' : 'text.primary',
                    wordBreak: 'break-word'
                  }}
                >
                  {children}
                </Typography>
              ),
            }}
          />
        );
      }
    });
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 2,
        width: '100%'
      }}
    >
      <Paper
        sx={{
          p: isUser ? '0.5rem 1rem' : 2,
          maxWidth: isUser ? '100%' : '100%',
          width: isUser ? 'fit-content' : 'auto',
          minWidth: isUser ? 'auto' : '200px',
          bgcolor: isUser ? 'rgba(135, 206, 235, 0.2)' : 'background.paper',
          color: 'text.primary',
          borderRadius: isUser ? '1.5rem' : 2,
          boxShadow: isUser ? '0 1px 2px rgba(135, 206, 235, 0.2)' : 'none',
          alignSelf: isUser ? 'flex-end' : 'flex-start',
          border: !isUser ? '1px solid rgba(135, 206, 235, 0.3)' : 'none'
        }}
      >
        {renderContent(message)}
        {!isUser && (
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'flex-end', 
            gap: 1, 
            mt: 2,
            borderTop: '1px solid',
            borderColor: 'divider',
            pt: 1
          }}>
            <Tooltip title="Thumbs Up">
              <IconButton 
                size="small" 
                onClick={handleThumbsUp}
                color={thumbsUp ? "primary" : "default"}
              >
                {thumbsUp ? <ThumbUpIcon /> : <ThumbUpOutlinedIcon />}
              </IconButton>
            </Tooltip>
            <Tooltip title="Thumbs Down">
              <IconButton 
                size="small" 
                onClick={handleThumbsDown}
                color={thumbsDown ? "primary" : "default"}
              >
                {thumbsDown ? <ThumbDownIcon /> : <ThumbDownOutlinedIcon />}
              </IconButton>
            </Tooltip>
            <Tooltip title="Copy Message">
              <IconButton 
                size="small" 
                onClick={handleCopy}
              >
                <ContentCopyIcon />
              </IconButton>
            </Tooltip>
          </Box>
        )}
      </Paper>
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={2000}
        onClose={() => setSnackbarOpen(false)}
        message="Message copied to clipboard"
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Box>
  );
};

export default ChatMessage; 
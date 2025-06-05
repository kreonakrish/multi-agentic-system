import { ToolType } from '../store/types';

export const agentColors = [
  '#4CAF50', // Green
  '#2196F3', // Blue
  '#FF9800', // Orange
  '#E91E63', // Pink
  '#9C27B0', // Purple
  '#00BCD4', // Cyan
  '#FFC107', // Amber
  '#795548'  // Brown
] as const;

export const toolColors: Record<ToolType | 'default', string> = {
  'Database': '#2196F3',    // Blue
  'APIService': '#4CAF50',  // Green
  'WebService': '#FF9800',  // Orange
  'Python': '#9C27B0',      // Purple
  'React': '#00BCD4',       // Cyan
  'default': '#9E9E9E'      // Grey
} as const;

export const statusColors: Record<string, string> = {
  'active': '#4CAF50',    // Green
  'inactive': '#9E9E9E',  // Grey
  'error': '#F44336',     // Red
  'default': '#9E9E9E'    // Grey
} as const;

export const getAgentColor = (index: number): string => {
  return agentColors[index % agentColors.length];
};

export const getToolColor = (type: ToolType): string => {
  return toolColors[type] || toolColors.default;
};

export const getStatusColor = (status: string): string => {
  return statusColors[status] || statusColors.default;
}; 
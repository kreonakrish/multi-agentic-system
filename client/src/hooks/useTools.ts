import { useState, useEffect } from 'react';

interface Tool {
  id: number;
  tool_name: string;
  tool_type: 'Database' | 'API' | 'WebService';
  description: string;
  configuration: Record<string, any>;
}

export const useTools = () => {
  const [tools, setTools] = useState<Tool[]>([]);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [toolModalOpen, setToolModalOpen] = useState(false);
  const [editToolModalOpen, setEditToolModalOpen] = useState(false);
  const [toolToEdit, setToolToEdit] = useState<Tool | null>(null);

  useEffect(() => {
    fetchTools();
  }, []);

  const fetchTools = async () => {
    try {
      const response = await fetch('/api/tools');
      if (response.ok) {
        const data = await response.json();
        setTools(data);
      }
    } catch (error) {
      console.error('Error fetching tools:', error);
    }
  };

  const addTool = async (toolData: Omit<Tool, 'id'>) => {
    try {
      const response = await fetch('/api/tools', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(toolData),
      });
      if (response.ok) {
        const newTool = await response.json();
        setTools(prev => [...prev, newTool]);
        return newTool;
      }
    } catch (error) {
      console.error('Error adding tool:', error);
      throw error;
    }
  };

  const updateTool = async (id: number, toolData: Partial<Tool>) => {
    try {
      const response = await fetch(`/api/tools/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(toolData),
      });
      if (response.ok) {
        const updatedTool = await response.json();
        setTools(prev => prev.map(tool => 
          tool.id === id ? updatedTool : tool
        ));
        return updatedTool;
      }
    } catch (error) {
      console.error('Error updating tool:', error);
      throw error;
    }
  };

  const deleteTool = async (id: number) => {
    try {
      const response = await fetch(`/api/tools/${id}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        setTools(prev => prev.filter(tool => tool.id !== id));
        if (selectedTool?.id === id) {
          setSelectedTool(null);
        }
      }
    } catch (error) {
      console.error('Error deleting tool:', error);
      throw error;
    }
  };

  return {
    tools,
    selectedTool,
    setSelectedTool,
    toolModalOpen,
    setToolModalOpen,
    editToolModalOpen,
    setEditToolModalOpen,
    toolToEdit,
    setToolToEdit,
    addTool,
    updateTool,
    deleteTool,
    fetchTools,
  };
}; 
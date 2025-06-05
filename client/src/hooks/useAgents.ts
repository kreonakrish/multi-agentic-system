import { useState, useEffect } from 'react';

interface Agent {
  id: number;
  name: string;
  memory_type: string;
  foundation_model: string;
  status: string;
  tools: any[];
}

export const useAgents = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [agentModalOpen, setAgentModalOpen] = useState(false);
  const [editAgentModalOpen, setEditAgentModalOpen] = useState(false);
  const [agentToEdit, setAgentToEdit] = useState<Agent | null>(null);

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await fetch('/api/agents');
      if (response.ok) {
        const data = await response.json();
        setAgents(data);
      }
    } catch (error) {
      console.error('Error fetching agents:', error);
    }
  };

  const addAgent = async (agentData: Omit<Agent, 'id'>) => {
    try {
      const response = await fetch('/api/agents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agentData),
      });
      if (response.ok) {
        const newAgent = await response.json();
        setAgents(prev => [...prev, newAgent]);
        return newAgent;
      }
    } catch (error) {
      console.error('Error adding agent:', error);
      throw error;
    }
  };

  const updateAgent = async (id: number, agentData: Partial<Agent>) => {
    try {
      const response = await fetch(`/api/agents/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agentData),
      });
      if (response.ok) {
        const updatedAgent = await response.json();
        setAgents(prev => prev.map(agent => 
          agent.id === id ? updatedAgent : agent
        ));
        return updatedAgent;
      }
    } catch (error) {
      console.error('Error updating agent:', error);
      throw error;
    }
  };

  const deleteAgent = async (id: number) => {
    try {
      const response = await fetch(`/api/agents/${id}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        setAgents(prev => prev.filter(agent => agent.id !== id));
        if (selectedAgent?.id === id) {
          setSelectedAgent(null);
        }
      }
    } catch (error) {
      console.error('Error deleting agent:', error);
      throw error;
    }
  };

  return {
    agents,
    selectedAgent,
    setSelectedAgent,
    agentModalOpen,
    setAgentModalOpen,
    editAgentModalOpen,
    setEditAgentModalOpen,
    agentToEdit,
    setAgentToEdit,
    addAgent,
    updateAgent,
    deleteAgent,
    fetchAgents,
  };
}; 
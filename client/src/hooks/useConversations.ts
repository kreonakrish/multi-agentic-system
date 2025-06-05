import { useState, useEffect } from 'react';
import { Conversation, ConversationStep } from '../store/types';
import { conversationService } from '../services/conversationService';

export const useConversations = (teamId: number | null) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [conversationHistory, setConversationHistory] = useState<ConversationStep[]>([]);
  const [renamingIdx, setRenamingIdx] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState('');

  useEffect(() => {
    if (teamId) {
      fetchConversations();
    }
  }, [teamId]);

  const fetchConversations = async () => {
    try {
      const data = await conversationService.getConversations();
      setConversations(data);
    } catch (error) {
      console.error('Error fetching conversations:', error);
    }
  };

  const loadConversation = async (conv: Conversation) => {
    try {
      const conversation = await conversationService.getConversation(conv.id);
      if (conversation) {
        setCurrentConversation(conversation);
        setConversationHistory(conversation.conversation_data);
      }
    } catch (error) {
      console.error('Error loading conversation:', error);
    }
  };

  const createConversation = async (title: string) => {
    if (!teamId) return null;
    try {
      const newConversation = await conversationService.createConversation(teamId, title);
      if (newConversation) {
        setConversations(prev => [...prev, newConversation]);
        setCurrentConversation(newConversation);
        setConversationHistory([]);
      }
      return newConversation;
    } catch (error) {
      console.error('Error creating conversation:', error);
      return null;
    }
  };

  const addStep = async (step: ConversationStep) => {
    if (!currentConversation) return null;
    try {
      const newStep = await conversationService.addStep(currentConversation.id, step);
      if (newStep) {
        setConversationHistory(prev => [...prev, newStep]);
      }
      return newStep;
    } catch (error) {
      console.error('Error adding conversation step:', error);
      return null;
    }
  };

  const deleteConversation = async (conv: Conversation) => {
    try {
      const success = await conversationService.deleteConversation(conv.id);
      if (success) {
        setConversations(prev => prev.filter(c => c.id !== conv.id));
        if (currentConversation?.id === conv.id) {
          setCurrentConversation(null);
          setConversationHistory([]);
        }
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  const startRename = (idx: number, currentTitle: string) => {
    setRenamingIdx(idx);
    setRenameValue(currentTitle);
  };

  const saveRename = async (conv: Conversation) => {
    try {
      const updatedConversation = await conversationService.renameConversation(
        conv.id,
        renameValue
      );
      if (updatedConversation) {
        setConversations(prev =>
          prev.map(c => (c.id === conv.id ? updatedConversation : c))
        );
      }
    } catch (error) {
      console.error('Error renaming conversation:', error);
    } finally {
      setRenamingIdx(null);
      setRenameValue('');
    }
  };

  return {
    conversations,
    currentConversation,
    conversationHistory,
    setConversationHistory,
    renamingIdx,
    renameValue,
    setRenameValue,
    loadConversation,
    createConversation,
    addStep,
    deleteConversation,
    startRename,
    saveRename,
  };
}; 
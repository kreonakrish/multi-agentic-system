import { ApiService } from './api';
import { Conversation, ConversationStep } from '../store/types';

class ConversationService extends ApiService {
  async getConversations(): Promise<Conversation[]> {
    const response = await this.get<Conversation[]>('/conversations');
    return response.data || [];
  }

  async getConversation(id: number): Promise<Conversation | null> {
    const response = await this.get<Conversation>(`/conversations/${id}`);
    return response.data || null;
  }

  async createConversation(teamId: number, title: string): Promise<Conversation | null> {
    const response = await this.post<Conversation>('/conversations', {
      team_id: teamId,
      title,
    });
    return response.data || null;
  }

  async addStep(
    conversationId: number,
    step: ConversationStep
  ): Promise<ConversationStep | null> {
    const response = await this.post<ConversationStep>(
      `/conversations/${conversationId}/steps`,
      step
    );
    return response.data || null;
  }

  async endConversation(id: number): Promise<boolean> {
    const response = await this.put<{ success: boolean }>(
      `/conversations/${id}/end`,
      {}
    );
    return response.data?.success || false;
  }

  async deleteConversation(id: number): Promise<boolean> {
    const response = await this.delete<{ success: boolean }>(
      `/conversations/${id}`
    );
    return response.data?.success || false;
  }

  async renameConversation(id: number, title: string): Promise<Conversation | null> {
    const response = await this.put<Conversation>(`/conversations/${id}`, {
      title,
    });
    return response.data || null;
  }
}

export const conversationService = new ConversationService(); 
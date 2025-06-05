export interface Agent {
  id: number;
  name: string;
  accuracy?: number;
  success?: number;
  priority?: number;
  memory_type: string;
  foundation_model: string;
  status: string;
  tools: Tool[];
  tool_count?: number;
  team_count?: number;
  accuracy_threshold?: number;
  success_rate?: number;
  role?: string;
}

export interface Tool {
  id: number;
  tool_name: string;
  tool_type: 'APIService' | 'WebService' | 'Database' | 'Python' | 'React';
  hostname?: string;
  username?: string;
  password?: string;
  auth_method?: string;
  description: string;
  created_at?: string;
  configuration?: Record<string, any>;
  permission_level?: string;
}

export interface Team {
  id: number;
  name: string;
  description?: string;
  agents: Agent[];
  tools: Tool[];
  created_at?: string;
  updated_at?: string;
  config?: {
    name: string;
    description: string;
    agents: Agent[];
  };
  conversation_settings?: ConversationSettings;
}

// Base conversation settings with required fields
export interface BaseConversationSettings {
  temperature: number;
  tokenLimit: number;
  startPrompt: string;
  endPrompt: string;
  style: string;
}

// Extended conversation settings with optional fields
export interface ConversationSettings extends BaseConversationSettings {
  // Additional optional fields
  start_prompt?: string;
  system_prompt?: string;
  max_tokens?: number;
  model?: string;
}

export interface ConversationStep {
  role: 'user' | 'agent' | 'tool' | 'bot';
  content: string;
  agent_name?: string;
  tool_name?: string;
  parent_idx?: number;
  data?: {
    type: 'bar' | 'line' | 'pie';
    labels: string[];
    values: number[];
  };
  metadata?: {
    team_id?: string;
    processing_time?: number;
    confidence_score?: number;
    agent_contributions?: Array<{
      agent_id: number;
      confidence: number;
      role?: string;
    }>;
    timestamp?: string;
  };
  attachments?: Document[];
  timestamp?: string;
}

export interface Conversation {
  id: number;
  title: string;
  started_at: string;
  ended_at?: string;
  team_id: number;
  conversation_data: ConversationStep[];
  temperature?: number;
  token_limit?: number;
  start_prompt?: string;
  end_prompt?: string;
  style?: string;
}

export interface Document {
  id: string;
  name: string;
  url: string;
  type: string;
  size: number;
  created_at: string;
  uploaded_at: string;
  team_id: number;
  conversation_id: number | null;
  file_type: string;
  file_size: number;
  content: string | null;
  metadata: Record<string, any> | null;
  updated_at: string;
}

export type AgentStatus = 'active' | 'inactive' | 'error';
export type ToolType = 'APIService' | 'WebService' | 'Database' | 'Python' | 'React'; 
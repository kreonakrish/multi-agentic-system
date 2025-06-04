const logger = require('../utils/logger');
const mlService = require('./ml.service');

class ChatService {
    constructor() {
        this.defaultTeamConfig = {
            name: "Chat Response Team",
            description: "Team for processing chat messages and generating responses",
            members: [
                {
                    agent_id: 10,
                    priority: 3,
                    accuracy_threshold: 0.9,
                    success_rate: 0.95,
                    role: "context_analyzer"
                },
                {
                    agent_id: 11,
                    priority: 2,
                    accuracy_threshold: 0.8,
                    success_rate: 0.9,
                    role: "response_generator"
                }
            ]
        };
    }

    async processMessage(messageData) {
        try {
            logger.info('[ChatService] Processing message:', messageData);

            const teamConfig = messageData.context?.team_config || this.defaultTeamConfig;
            const mlResponse = await mlService.processWithTeam(teamConfig, messageData);
            const processedResponse = this._processTeamResponse(mlResponse, messageData.sessionId);

            // Store conversation
            const conversationContent = {
                user_message: messageData.content,
                bot_response: processedResponse.content,
                timestamp: new Date().toISOString()
            };

            await mlService.storeConversation(
                messageData.sessionId,
                conversationContent,
                processedResponse.metadata
            );

            return processedResponse;
        } catch (error) {
            logger.error('[ChatService] Error processing message:', error);
            throw error;
        }
    }

    _processTeamResponse(teamResponse, sessionId) {
        try {
            const { result, processing_time_seconds, team } = teamResponse;
            
            // Get the original task description/user query
            const userQuery = result.task_context?.description || '';
            
            // Extract responses from conversation context
            let responses = result.conversation_context
                .map(ctx => {
                    // Try to get LLM response from various possible locations
                    return ctx.result?.llm_response || // Check for direct LLM response
                           ctx.result?.processed_response || // Check for processed response
                           ctx.result?.content || // Check for content field
                           (ctx.result?.status === 'success' ? userQuery : ''); // Fallback to query if successful
                })
                .filter(msg => msg)
                .join(' ');
            
            // If no valid response was found, use a fallback
            if (!responses.trim()) {
                responses = 'I am still processing your request. Please try again in a moment.';
            }
            
            // Create metadata
            const metadata = {
                team_id: team.team_id,
                processing_time: processing_time_seconds,
                confidence_score: result.successful_agents / result.total_agents,
                agent_contributions: result.conversation_context.map(ctx => ({
                    agent_id: ctx.agent_id,
                    confidence: ctx.result?.status === 'success' ? 1 : 0
                }))
            };

            return {
                content: responses,
                status: result.final_status,
                metadata,
                conversation_id: sessionId,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            logger.error('[ChatService] Error processing team response:', error);
            throw error;
        }
    }

    async getHistory(sessionId) {
        return mlService.getConversationHistory(sessionId);
    }
}

module.exports = new ChatService(); 
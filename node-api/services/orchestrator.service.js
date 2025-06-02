const axios = require('axios');
const logger = require('../utils/logger');

// Configuration for Python ML service
const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:5000/api/ml';

class OrchestratorService {
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
        
        // Initialize conversation contexts
        this.conversationContexts = new Map();
    }

    /**
     * Process incoming chat message and orchestrate response
     * @param {Object} messageData - The chat message data
     * @param {string} messageData.content - The actual message content
     * @param {string} messageData.userId - ID of the user sending the message
     * @param {string} messageData.sessionId - Chat session ID
     * @param {Object} messageData.context - Additional context (optional)
     */
    async processChatMessage(messageData) {
        try {
            logger.info('[Orchestrator] Processing chat message:', messageData);

            // Prepare team configuration
            const teamConfig = messageData.context?.team_config || this.defaultTeamConfig;

            // Send request to ML service with correct payload format
            const response = await axios.post(`${ML_SERVICE_URL}/team/execute`, {
                team_config: teamConfig,
                task: {
                    description: messageData.content,
                    requirements: {
                        min_accuracy: 0.85,
                        max_time: 300,
                        output_format: "text",
                        context: {
                            user_id: messageData.userId,
                            session_id: messageData.sessionId,
                            conversation_history: messageData.context?.conversation_history || []
                        }
                    }
                }
            });

            logger.info('[Orchestrator] Received response from ML service:', response.data);

            // Process the team response
            const processedResponse = this._processTeamResponse(response.data, messageData.sessionId);
            logger.info('[Orchestrator] Processed response:', processedResponse);

            // Store conversation history
            try {
                await axios.post(`${ML_SERVICE_URL}/conversation/store`, {
                    conversation_id: messageData.sessionId,
                    content: {
                        user_message: messageData.content,
                        bot_response: processedResponse.content,
                        timestamp: new Date().toISOString()
                    },
                    metadata: {
                        team_id: processedResponse.metadata.team_id,
                        processing_time: processedResponse.metadata.processing_time,
                        confidence_score: processedResponse.metadata.confidence_score,
                        agent_contributions: processedResponse.metadata.agent_contributions
                    }
                });
            } catch (storeError) {
                logger.error('[Orchestrator] Error storing conversation history:', storeError);
                // Don't throw here - we still want to return the response even if storage fails
            }

            return processedResponse;

        } catch (error) {
            logger.error('[Orchestrator] Error processing chat message:', error);
            throw error;
        }
    }

    /**
     * Process and format team response for chat
     * @param {Object} teamResponse - Raw response from team service
     * @param {string} sessionId - Chat session ID
     * @returns {Object} Formatted chat response
     */
    _processTeamResponse(teamResponse, sessionId) {
        try {
            const { result, processing_time_seconds } = teamResponse;
            
            // Extract responses from conversation context
            const responses = result.conversation_context.map(ctx => ctx.response).join(' ');
            
            // Create metadata
            const metadata = {
                team_id: result.team_id,
                processing_time: processing_time_seconds,
                confidence_score: 1, // Default confidence score
                agent_contributions: result.results.map(r => ({
                    agent_id: r.agent_id,
                    confidence: r.result.validation_results?.confidence || 0
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
            logger.error('[Orchestrator] Error processing team response:', error);
            throw new Error('Failed to process team response: ' + error.message);
        }
    }

    /**
     * Get conversation history for a session
     * @param {string} sessionId - Chat session ID
     * @returns {Promise<Array>} Conversation history
     */
    async getConversationHistory(sessionId) {
        try {
            // Get team history from ML service
            const response = await axios.get(`${ML_SERVICE_URL}/conversation/history`, {
                params: { session_id: sessionId }
            });

            return response.data.history;
        } catch (error) {
            logger.error(`[Orchestrator] Error fetching conversation history: ${error.message}`);
            throw new Error(`Failed to fetch conversation history: ${error.message}`);
        }
    }
}

module.exports = new OrchestratorService(); 
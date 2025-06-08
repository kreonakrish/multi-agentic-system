const axios = require('axios');
const logger = require('../utils/logger');

const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:5000/api/ml';

class MLService {
    async processWithTeam(teamConfig, messageData) {
        try {
            logger.info('[MLService] Processing with team:', { teamConfig, messageData });

            const mlRequest = {
                content: messageData.content,
                userId: messageData.userId,
                sessionId: messageData.sessionId,
                context: {
                    team_id: teamConfig.team_id,
                    team_config: {
                        ...teamConfig,
                        members: teamConfig.members || [{
                            agent_id: teamConfig.team_id,
                            priority: 1,
                            accuracy_threshold: 0.8,
                            success_rate: 0.9,
                            role: "processor"
                        }]
                    },
                    conversation_settings: messageData.context?.conversation_settings || {},
                    conversation_history: messageData.context?.conversation_history || [],
                    documents: messageData.context?.documents || []
                }
            };

            logger.info('[MLService] Sending request to ML service:', mlRequest);

            const response = await axios.post(`${ML_SERVICE_URL}/team/execute`, mlRequest);
            
            logger.info('[MLService] Received response from ML service:', response.data);
            
            return response.data;
        } catch (error) {
            logger.error('[MLService] Error processing with team:', error);
            throw error;
        }
    }

    async storeConversation(sessionId, content, metadata) {
        try {
            await axios.post(`${ML_SERVICE_URL}/conversation/store`, {
                conversation_id: sessionId,
                content,
                metadata
            });
        } catch (error) {
            logger.error('[MLService] Error storing conversation:', error);
            throw error;
        }
    }

    async getConversationHistory(sessionId) {
        try {
            const response = await axios.get(`${ML_SERVICE_URL}/conversation/history`, {
                params: { session_id: sessionId }
            });
            return response.data.history;
        } catch (error) {
            logger.error('[MLService] Error fetching conversation history:', error);
            throw error;
        }
    }
}

module.exports = new MLService(); 
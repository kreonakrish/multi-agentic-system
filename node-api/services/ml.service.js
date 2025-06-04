const axios = require('axios');
const logger = require('../utils/logger');

const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:5000/api/ml';

class MLService {
    async processWithTeam(teamConfig, messageData) {
        try {
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
const orchestrator = require('../services/orchestrator.service');
const logger = require('../utils/logger');

class ChatController {
    /**
     * Process a chat message
     * @param {Object} req - Express request object
     * @param {Object} res - Express response object
     */
    async processMessage(req, res) {
        try {
            const { content, userId, sessionId, context } = req.body;

            // Validate required fields
            if (!content) {
                return res.status(400).json({
                    status: 'error',
                    message: 'Message content is required'
                });
            }

            if (!userId) {
                return res.status(400).json({
                    status: 'error',
                    message: 'User ID is required'
                });
            }

            if (!sessionId) {
                return res.status(400).json({
                    status: 'error',
                    message: 'Session ID is required'
                });
            }

            logger.info('Processing chat message', {
                userId,
                sessionId,
                contentLength: content.length,
                hasContext: !!context
            });

            // Process message through orchestrator
            const response = await orchestrator.processChatMessage({
                content,
                userId,
                sessionId,
                context
            });

            logger.info('Chat message processed successfully', {
                userId,
                sessionId,
                responseStatus: response.status
            });

            return res.json({
                status: 'success',
                data: response
            });

        } catch (error) {
            logger.error('Error processing chat message', {
                error: error.message,
                stack: error.stack
            });

            return res.status(500).json({
                status: 'error',
                message: 'Failed to process chat message: ' + error.message
            });
        }
    }

    /**
     * Get conversation history
     * @param {Object} req - Express request object
     * @param {Object} res - Express response object
     */
    async getHistory(req, res) {
        try {
            const { sessionId } = req.params;

            if (!sessionId) {
                return res.status(400).json({
                    status: 'error',
                    message: 'Session ID is required'
                });
            }

            logger.info('Fetching chat history', { sessionId });

            const history = await orchestrator.getConversationHistory(sessionId);

            logger.info('Chat history fetched successfully', {
                sessionId,
                historyLength: history.length
            });

            return res.json({
                status: 'success',
                data: history
            });

        } catch (error) {
            logger.error('Error fetching chat history', {
                error: error.message,
                stack: error.stack
            });

            return res.status(500).json({
                status: 'error',
                message: 'Failed to fetch chat history: ' + error.message
            });
        }
    }
}

module.exports = new ChatController(); 
const orchestrator = require('../services/orchestrator.service');
const logger = require('../utils/logger');
const mysql = require('mysql2/promise');

class ChatController {
    constructor(dbPool) {
        this.pool = dbPool;
    }

    /**
     * Get team name from database
     * @param {number} teamId - The team ID
     * @returns {Promise<string>} - The team name or a default name if not found
     */
    async getTeamName(teamId) {
        try {
            const [teams] = await this.pool.query('SELECT name FROM teams WHERE id = ?', [teamId]);
            return teams.length > 0 ? teams[0].name : `Team ${teamId}`;
        } catch (error) {
            logger.error('Error fetching team name:', error);
            return `Team ${teamId}`;
        }
    }

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

            let updatedContext = { ...context };

            try {
                // First try to get conversation settings using sessionId as conversation ID
                const [conversations] = await this.pool.query(`
                    SELECT c.*, s.team_id, s.temperature, s.token_limit, s.start_prompt, s.end_prompt, s.style
                    FROM conversations c
                    JOIN conversation_settings s ON c.settings_id = s.id
                    WHERE c.id = ?
                `, [sessionId]);

                if (conversations.length === 0) {
                    // If no conversation found, try to get the most recent settings
                    const [settings] = await this.pool.query(`
                        SELECT * FROM conversation_settings 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    `);

                    if (settings.length > 0) {
                        const setting = settings[0];
                        const teamName = await this.getTeamName(setting.team_id);
                        updatedContext.team_config = {
                            team_id: setting.team_id,
                            name: teamName,
                            description: "Team for processing chat messages",
                            members: [
                                {
                                    agent_id: setting.team_id,
                                    priority: 1,
                                    accuracy_threshold: 0.8,
                                    success_rate: 0.9,
                                    role: "processor"
                                }
                            ],
                            temperature: setting.temperature,
                            token_limit: setting.token_limit,
                            start_prompt: setting.start_prompt,
                            end_prompt: setting.end_prompt,
                            style: setting.style
                        };
                        logger.info('Using most recent conversation settings:', setting);
                    }
                } else {
                    const settings = conversations[0];
                    const teamName = await this.getTeamName(settings.team_id);
                    updatedContext.team_config = {
                        team_id: settings.team_id,
                        name: teamName,
                        description: "Team for processing chat messages",
                        members: [
                            {
                                agent_id: settings.team_id,
                                priority: 1,
                                accuracy_threshold: 0.8,
                                success_rate: 0.9,
                                role: "processor"
                            }
                        ],
                        temperature: settings.temperature,
                        token_limit: settings.token_limit,
                        start_prompt: settings.start_prompt,
                        end_prompt: settings.end_prompt,
                        style: settings.style
                    };
                    logger.info('Using conversation-specific settings:', settings);
                }
            } catch (dbError) {
                logger.error('Error fetching conversation settings:', dbError);
                // Continue with default settings if there's a database error
            }

            // Process message through orchestrator
            const response = await orchestrator.processChatMessage({
                content,
                userId,
                sessionId,
                context: updatedContext
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

// Export a function that creates a new controller instance with the provided pool
module.exports = (dbPool) => new ChatController(dbPool); 
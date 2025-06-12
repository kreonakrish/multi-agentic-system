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

            // Log detailed incoming request
            logger.info('Chat Message Request - Full Details', {
                request: {
                    content,
                    userId,
                    sessionId,
                    context: {
                        team_id: context?.team_id,
                        team_config: context?.team_config,
                        conversation_settings: context?.conversation_settings,
                        conversation_history: context?.conversation_history?.map(msg => ({
                            role: msg.role,
                            content: msg.content,
                            timestamp: msg.timestamp,
                            metadata: msg.metadata
                        })),
                        documents: context?.documents?.map(doc => ({
                            id: doc.id,
                            name: doc.name,
                            type: doc.type
                        }))
                    }
                }
            });

            // Log basic request info for quick reference
            logger.info('Chat Message Request - Summary', {
                userId,
                sessionId,
                contentLength: content?.length,
                hasContext: !!context,
                teamId: context?.team_id,
                hasTeamConfig: !!context?.team_config,
                historyLength: context?.conversation_history?.length || 0,
                documentsCount: context?.documents?.length || 0
            });

            // Validate input
            if (!content) {
                logger.error('Invalid chat message request - missing content', { userId, sessionId });
                return res.status(400).json({ error: 'Message content is required' });
            }

            // Get conversation settings
            let updatedContext = { ...context };
            try {
                const [settings] = await this.pool.query(
                    'SELECT * FROM conversation_settings WHERE team_id = ? ORDER BY id DESC LIMIT 1',
                    [context.team_id]
                );

                if (settings.length > 0) {
                    const setting = settings[0];
                    const teamName = await this.getTeamName(setting.team_id);

                    // Log conversation settings
                    logger.info('Retrieved Conversation Settings', {
                        settings: {
                            id: setting.id,
                            team_id: setting.team_id,
                            team_name: teamName,
                            temperature: setting.temperature,
                            token_limit: setting.token_limit,
                            start_prompt: setting.start_prompt,
                            end_prompt: setting.end_prompt,
                            style: setting.style,
                            created_at: setting.created_at
                        }
                    });

                    // Preserve the original use_smart_workflow value
                    const use_smart_workflow = context?.team_config?.use_smart_workflow ?? false;

                    updatedContext.team_config = {
                        team_id: setting.team_id,
                        name: teamName,
                        description: "Team for processing chat messages",
                        use_smart_workflow: use_smart_workflow, // Preserve the original value
                        members: context?.team_config?.members || [
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
                }

                // Log updated context
                logger.info('Updated Context for Processing', {
                    context: {
                        team_id: updatedContext.team_id,
                        team_config: updatedContext.team_config,
                        conversation_settings: updatedContext.conversation_settings,
                        history_length: updatedContext.conversation_history?.length || 0,
                        documents_count: updatedContext.documents?.length || 0
                    }
                });

                // Process message through orchestrator
                const response = await orchestrator.processChatMessage({
                    content,
                    userId,
                    sessionId,
                    context: updatedContext
                });

                // Log successful processing
                logger.info('Chat Message Processed Successfully', {
                    response: {
                        status: response.status,
                        metadata: response.metadata,
                        has_content: !!response.content,
                        content_length: response.content?.length,
                        has_tool_data: !!response.tool_data,
                        has_visualization: !!response.visualization_data,
                        has_smart_workflow: !!response.smart_workflow_data,
                        timestamp: response.timestamp
                    }
                });

                return res.json({
                    status: 'success',
                    data: response
                });

            } catch (dbError) {
                logger.error('Error in chat message processing', {
                    error: dbError.message,
                    stack: dbError.stack,
                    phase: 'database_operation',
                    userId,
                    sessionId,
                    teamId: context?.team_id
                });
                throw dbError;
            }
        } catch (error) {
            logger.error('Error processing chat message', {
                error: error.message,
                stack: error.stack,
                userId,
                sessionId
            });
            return res.status(500).json({ 
                error: 'Failed to process message',
                details: error.message
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
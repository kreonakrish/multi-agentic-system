const express = require('express');
const router = express.Router();
const logger = require('../utils/logger');

// Helper: Format date for MySQL
function formatDateForMySQL(dateString) {
    if (!dateString) return null;
    try {
        // Convert ISO string to Date object
        const date = new Date(dateString);
        // Format as MySQL DATETIME (YYYY-MM-DD HH:mm:ss)
        return date.toISOString().slice(0, 19).replace('T', ' ');
    } catch (err) {
        logger.error('Error formatting date:', {
            date: dateString,
            error: err.message
        });
        return null;
    }
}

// Helper: create or find conversation_settings
async function getOrCreateConversationSettings(connection, settings) {
    try {
        logger.info('Creating/finding settings:', settings);
        
        // Validate settings
        if (!settings) {
            throw new Error('Settings object is required');
        }

        // Ensure team_id is valid
        if (!settings.team_id) {
            throw new Error('Team ID is required in settings');
        }

        // Normalize settings values
        const normalizedSettings = {
            team_id: settings.team_id,
            temperature: Number(settings.temperature) || 0.7,
            token_limit: Number(settings.token_limit) || 512,
            start_prompt: settings.start_prompt || '',
            end_prompt: settings.end_prompt || '',
            style: settings.style || ''
        };
        
        logger.info('Normalized settings:', normalizedSettings);
        
        // Try to find existing settings
        const [rows] = await connection.query(
            'SELECT id FROM conversation_settings WHERE team_id=? AND temperature=? AND token_limit=? AND start_prompt=? AND end_prompt=? AND style=? LIMIT 1',
            [
                normalizedSettings.team_id,
                normalizedSettings.temperature,
                normalizedSettings.token_limit,
                normalizedSettings.start_prompt,
                normalizedSettings.end_prompt,
                normalizedSettings.style
            ]
        );
        
        if (rows.length > 0) {
            logger.info('Found existing settings with ID:', rows[0].id);
            return rows[0].id;
        }
        
        // Otherwise, insert new settings
        logger.info('No existing settings found, creating new settings');
        const [result] = await connection.query(
            'INSERT INTO conversation_settings (team_id, temperature, token_limit, start_prompt, end_prompt, style) VALUES (?, ?, ?, ?, ?, ?)',
            [
                normalizedSettings.team_id,
                normalizedSettings.temperature,
                normalizedSettings.token_limit,
                normalizedSettings.start_prompt,
                normalizedSettings.end_prompt,
                normalizedSettings.style
            ]
        );
        
        if (!result.insertId) {
            throw new Error('Failed to create new conversation settings - no insert ID returned');
        }
        
        logger.info('Created new settings with ID:', result.insertId);
        return result.insertId;
    } catch (err) {
        logger.error('Error in getOrCreateConversationSettings:', {
            message: err.message,
            stack: err.stack,
            code: err.code,
            sqlMessage: err.sqlMessage
        });
        throw err;
    }
}

module.exports = (pool) => {
    // Get all conversations
    router.get('/', async (req, res) => {
        try {
            const [conversations] = await pool.query(`
                SELECT c.*, 
                       t.name as team_name,
                       COUNT(cs.id) as step_count
                FROM conversations c
                LEFT JOIN teams t ON c.team_id = t.id
                LEFT JOIN conversation_steps cs ON c.id = cs.conversation_id
                GROUP BY c.id
                ORDER BY c.created_at DESC
            `);
            res.json(conversations);
        } catch (error) {
            logger.error('Error fetching conversations:', error);
            res.status(500).json({ error: 'Failed to fetch conversations' });
        }
    });

    // Create a new conversation
    router.post('/', async (req, res) => {
        const connection = await pool.getConnection();
        try {
            logger.info('Received conversation creation request with body:', req.body);
            
            const { 
                title, 
                started_at, 
                ended_at, 
                conversation_data,
                team_id,
                temperature,
                token_limit,
                start_prompt,
                end_prompt,
                style
            } = req.body;
            
            // Enhanced validation with detailed logging
            if (!conversation_data) {
                logger.error('No conversation_data provided in request body:', req.body);
                return res.status(400).json({ error: 'conversation_data is required' });
            }
            
            if (!title) {
                logger.error('No title provided in request body:', req.body);
                return res.status(400).json({ error: 'title is required' });
            }
            
            if (!team_id) {
                logger.error('No team_id provided in request body:', req.body);
                return res.status(400).json({ error: 'team_id is required' });
            }

            // Format dates for MySQL
            const formattedStartedAt = formatDateForMySQL(started_at || new Date().toISOString());
            const formattedEndedAt = formatDateForMySQL(ended_at);

            logger.info('Formatted dates for MySQL:', {
                original_started_at: started_at,
                original_ended_at: ended_at,
                formatted_started_at: formattedStartedAt,
                formatted_ended_at: formattedEndedAt
            });

            await connection.beginTransaction();

            // Get or create conversation settings
            const settingsId = await getOrCreateConversationSettings(connection, {
                team_id,
                temperature,
                token_limit,
                start_prompt,
                end_prompt,
                style
            });

            // Create the conversation
            const [result] = await connection.query(
                `INSERT INTO conversations 
                 (team_id, title, conversation_data, started_at, ended_at, settings_id) 
                 VALUES (?, ?, ?, ?, ?, ?)`,
                [
                    team_id,
                    title,
                    JSON.stringify(conversation_data),
                    formattedStartedAt,
                    formattedEndedAt,
                    settingsId
                ]
            );

            // Get the complete conversation data
            const [conversation] = await connection.query(`
                SELECT c.*, cs.*, t.name as team_name
                FROM conversations c
                LEFT JOIN conversation_settings cs ON c.settings_id = cs.id
                LEFT JOIN teams t ON c.team_id = t.id
                WHERE c.id = ?
            `, [result.insertId]);

            await connection.commit();
            connection.release();

            // Format dates back to ISO for response
            if (conversation[0]) {
                conversation[0].started_at = conversation[0].started_at ? new Date(conversation[0].started_at).toISOString() : null;
                conversation[0].ended_at = conversation[0].ended_at ? new Date(conversation[0].ended_at).toISOString() : null;
            }

            res.status(201).json(conversation[0]);
        } catch (error) {
            await connection.rollback();
            connection.release();
            logger.error('Error creating conversation:', {
                error: error.message,
                code: error.code,
                sqlMessage: error.sqlMessage,
                sqlState: error.sqlState,
                sql: error.sql
            });
            res.status(500).json({ 
                error: 'Failed to create conversation',
                details: error.message,
                sqlMessage: error.sqlMessage
            });
        }
    });

    // Get conversation by ID with steps
    router.get('/:id', async (req, res) => {
        try {
            const [conversation] = await pool.query(`
                SELECT c.*, t.name as team_name, cs.*
                FROM conversations c
                LEFT JOIN teams t ON c.team_id = t.id
                LEFT JOIN conversation_settings cs ON c.settings_id = cs.id
                WHERE c.id = ?
            `, [req.params.id]);
            
            if (conversation.length === 0) {
                return res.status(404).json({ error: 'Conversation not found' });
            }
            
            // Get conversation steps
            const [steps] = await pool.query(`
                SELECT cs.*, 
                       a.name as agent_name,
                       t.tool_name as tool_name
                FROM conversation_steps cs
                LEFT JOIN agents a ON cs.agent_id = a.id
                LEFT JOIN tools t ON cs.tool_id = t.id
                WHERE cs.conversation_id = ?
                ORDER BY cs.created_at ASC
            `, [req.params.id]);
            
            conversation[0].steps = steps;
            res.json(conversation[0]);
        } catch (error) {
            logger.error('Error fetching conversation:', error);
            res.status(500).json({ error: 'Failed to fetch conversation' });
        }
    });

    // Add step to conversation
    router.post('/:id/steps', async (req, res) => {
        try {
            const { role, content, agent_id, tool_id, parent_idx } = req.body;
            
            const [result] = await pool.query(
                `INSERT INTO conversation_steps 
                 (conversation_id, role, content, agent_id, tool_id, parent_idx) 
                 VALUES (?, ?, ?, ?, ?, ?)`,
                [req.params.id, role, content, agent_id, tool_id, parent_idx]
            );
            
            const [step] = await pool.query(`
                SELECT cs.*, 
                       a.name as agent_name,
                       t.tool_name as tool_name
                FROM conversation_steps cs
                LEFT JOIN agents a ON cs.agent_id = a.id
                LEFT JOIN tools t ON cs.tool_id = t.id
                WHERE cs.id = ?
            `, [result.insertId]);
            
            res.status(201).json(step[0]);
        } catch (error) {
            logger.error('Error adding conversation step:', error);
            res.status(500).json({ error: 'Failed to add conversation step' });
        }
    });

    // End conversation
    router.put('/:id/end', async (req, res) => {
        try {
            const endDate = formatDateForMySQL(new Date().toISOString());
            await pool.query(
                'UPDATE conversations SET ended_at = ? WHERE id = ?',
                [endDate, req.params.id]
            );
            
            const [conversation] = await pool.query('SELECT * FROM conversations WHERE id = ?', [req.params.id]);
            
            // Format dates back to ISO for response
            if (conversation[0]) {
                conversation[0].started_at = conversation[0].started_at ? new Date(conversation[0].started_at).toISOString() : null;
                conversation[0].ended_at = conversation[0].ended_at ? new Date(conversation[0].ended_at).toISOString() : null;
            }
            
            res.json(conversation[0]);
        } catch (error) {
            logger.error('Error ending conversation:', error);
            res.status(500).json({ error: 'Failed to end conversation' });
        }
    });

    // Get conversation history
    router.get('/:id/history', async (req, res) => {
        try {
            const [steps] = await pool.query(`
                SELECT cs.*, 
                       a.name as agent_name,
                       t.tool_name as tool_name
                FROM conversation_steps cs
                LEFT JOIN agents a ON cs.agent_id = a.id
                LEFT JOIN tools t ON cs.tool_id = t.id
                WHERE cs.conversation_id = ?
                ORDER BY cs.created_at ASC
            `, [req.params.id]);

            res.json(steps);
        } catch (error) {
            logger.error('Error fetching conversation history:', error);
            res.status(500).json({ error: 'Failed to fetch conversation history' });
        }
    });

    // Delete conversation
    router.delete('/:id', async (req, res) => {
        try {
            // First check if the conversation exists
            const [conversation] = await pool.query(
                'SELECT * FROM conversations WHERE id = ?',
                [req.params.id]
            );

            if (conversation.length === 0) {
                return res.status(404).json({ error: 'Conversation not found' });
            }

            // Delete all conversation steps first (due to foreign key constraint)
            await pool.query(
                'DELETE FROM conversation_steps WHERE conversation_id = ?',
                [req.params.id]
            );

            // Then delete the conversation
            await pool.query(
                'DELETE FROM conversations WHERE id = ?',
                [req.params.id]
            );

            res.json({ message: 'Conversation deleted successfully' });
        } catch (error) {
            logger.error('Error deleting conversation:', error);
            res.status(500).json({ error: 'Failed to delete conversation' });
        }
    });

    // Update conversation
    router.put('/:id', async (req, res) => {
        const connection = await pool.getConnection();
        try {
            const { 
                title, 
                conversation_data,
                team_id,
                temperature,
                token_limit,
                start_prompt,
                end_prompt,
                style
            } = req.body;

            // First check if the conversation exists
            const [existingConversation] = await connection.query(
                'SELECT * FROM conversations WHERE id = ?',
                [req.params.id]
            );

            if (existingConversation.length === 0) {
                connection.release();
                return res.status(404).json({ error: 'Conversation not found' });
            }

            await connection.beginTransaction();

            // Update or create conversation settings if provided
            let settingsId = existingConversation[0].settings_id;
            if (team_id || temperature || token_limit || start_prompt || end_prompt || style) {
                settingsId = await getOrCreateConversationSettings(connection, {
                    team_id: team_id || existingConversation[0].team_id,
                    temperature,
                    token_limit,
                    start_prompt,
                    end_prompt,
                    style
                });
            }

            // Build update query dynamically
            const updates = [];
            const values = [];
            
            if (title !== undefined) {
                updates.push('title = ?');
                values.push(title);
            }
            if (conversation_data !== undefined) {
                updates.push('conversation_data = ?');
                values.push(JSON.stringify(conversation_data));
            }
            if (team_id !== undefined) {
                updates.push('team_id = ?');
                values.push(team_id);
            }
            if (settingsId !== existingConversation[0].settings_id) {
                updates.push('settings_id = ?');
                values.push(settingsId);
            }

            // Only update if there are changes
            if (updates.length > 0) {
                values.push(req.params.id);
                await connection.query(
                    `UPDATE conversations SET ${updates.join(', ')} WHERE id = ?`,
                    values
                );
            }

            // Get updated conversation data
            const [updatedConversation] = await connection.query(`
                SELECT c.*, cs.*, t.name as team_name
                FROM conversations c
                LEFT JOIN conversation_settings cs ON c.settings_id = cs.id
                LEFT JOIN teams t ON c.team_id = t.id
                WHERE c.id = ?
            `, [req.params.id]);

            await connection.commit();
            connection.release();

            // Format dates back to ISO for response
            if (updatedConversation[0]) {
                updatedConversation[0].started_at = updatedConversation[0].started_at ? 
                    new Date(updatedConversation[0].started_at).toISOString() : null;
                updatedConversation[0].ended_at = updatedConversation[0].ended_at ? 
                    new Date(updatedConversation[0].ended_at).toISOString() : null;
            }

            res.json(updatedConversation[0]);
        } catch (error) {
            await connection.rollback();
            connection.release();
            logger.error('Error updating conversation:', {
                error: error.message,
                code: error.code,
                sqlMessage: error.sqlMessage,
                sqlState: error.sqlState,
                sql: error.sql
            });
            res.status(500).json({ 
                error: 'Failed to update conversation',
                details: error.message,
                sqlMessage: error.sqlMessage
            });
        }
    });

    return router;
}; 
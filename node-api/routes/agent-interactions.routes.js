const express = require('express');
const router = express.Router();
const db = require('../utils/db');
const logger = require('../utils/logger');

// Get agent interactions
router.get('/', async (req, res) => {
    try {
        const { team_id, source, target } = req.query;
        
        if (!team_id) {
            return res.status(400).json({ error: 'team_id query parameter is required' });
        }

        // Build the base query
        let query = `
            SELECT 
                m.id,
                m.conversation_id,
                COALESCE(sa.name, 'OpenAI') as source_agent,
                COALESCE(ta.name, 'OpenAI') as target_agent,
                m.interaction_type,
                m.status,
                m.created_at as timestamp,
                m.content,
                m.processed_message,
                m.model_response
            FROM messages m
            LEFT JOIN agents sa ON m.sender_id = sa.id
            LEFT JOIN agents ta ON m.receiver_id = ta.id
            WHERE 1=1
        `;
        
        const params = [];

        if (team_id) {
            query += ' AND m.team_id = ?';
            params.push(team_id);
        }

        if (source && target) {
            query += ' AND m.sender_id = ? AND m.receiver_id = ?';
            params.push(source, target);
        }

        // Order by timestamp
        query += ' ORDER BY m.created_at DESC';

        logger.info('Executing query:', { query, params });
        const [rows] = await db.query(query, params);
        logger.info(`Found ${rows.length} interactions`);

        // Format the response
        const formattedRows = rows.map(row => ({
            ...row,
            timestamp: row.timestamp.toISOString(),
            model_response: row.model_response ? JSON.parse(row.model_response) : null
        }));

        res.json(formattedRows);
    } catch (error) {
        logger.error('Error fetching agent interactions:', error);
        res.status(500).json({ error: 'Failed to fetch agent interactions' });
    }
});

// Record a new interaction
router.post('/', async (req, res) => {
    try {
        const {
            team_id,
            source_agent_id,
            target_agent_id,
            interaction_type,
            success_rate,
            details
        } = req.body;

        // Validate required fields
        if (!team_id || !source_agent_id || !target_agent_id || !interaction_type) {
            return res.status(400).json({
                error: 'Missing required fields: team_id, source_agent_id, target_agent_id, interaction_type'
            });
        }

        const [result] = await db.query(
            `INSERT INTO agent_interactions 
             (team_id, source_agent_id, target_agent_id, interaction_type, success_rate, details) 
             VALUES (?, ?, ?, ?, ?, ?)`,
            [
                team_id,
                source_agent_id,
                target_agent_id,
                interaction_type,
                success_rate || 0,
                details ? JSON.stringify(details) : null
            ]
        );

        // Fetch the created interaction with agent names
        const [interaction] = await db.query(
            `SELECT 
                ai.*,
                sa.name as source_agent,
                ta.name as target_agent
             FROM agent_interactions ai
             LEFT JOIN agents sa ON ai.source_agent_id = sa.id
             LEFT JOIN agents ta ON ai.target_agent_id = ta.id
             WHERE ai.id = ?`,
            [result.insertId]
        );

        res.status(201).json({
            ...interaction[0],
            timestamp: interaction[0].timestamp.toISOString(),
            details: interaction[0].details ? JSON.parse(interaction[0].details) : null
        });
    } catch (error) {
        logger.error('Error creating agent interaction:', error);
        res.status(500).json({ error: 'Failed to create agent interaction' });
    }
});

module.exports = router; 
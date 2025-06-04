const express = require('express');
const router = express.Router();
const db = require('../utils/db');
const logger = require('../utils/logger');

// Get all conversations
router.get('/', async (req, res) => {
    try {
        const [conversations] = await db.query(`
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
    try {
        const { team_id, title, settings } = req.body;
        const { temperature, token_limit, start_prompt, end_prompt, style } = settings || {};

        const [result] = await db.query(
            `INSERT INTO conversations 
             (team_id, title, temperature, token_limit, start_prompt, end_prompt, style, started_at) 
             VALUES (?, ?, ?, ?, ?, ?, ?, NOW())`,
            [team_id, title, temperature, token_limit, start_prompt, end_prompt, style]
        );
        
        const [conversation] = await db.query('SELECT * FROM conversations WHERE id = ?', [result.insertId]);
        res.status(201).json(conversation[0]);
    } catch (error) {
        logger.error('Error creating conversation:', error);
        res.status(500).json({ error: 'Failed to create conversation' });
    }
});

// Get conversation by ID with steps
router.get('/:id', async (req, res) => {
    try {
        const [conversation] = await db.query(`
            SELECT c.*, t.name as team_name
            FROM conversations c
            LEFT JOIN teams t ON c.team_id = t.id
            WHERE c.id = ?
        `, [req.params.id]);
        
        if (conversation.length === 0) {
            return res.status(404).json({ error: 'Conversation not found' });
        }
        
        // Get conversation steps
        const [steps] = await db.query(`
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
        
        const [result] = await db.query(
            `INSERT INTO conversation_steps 
             (conversation_id, role, content, agent_id, tool_id, parent_idx) 
             VALUES (?, ?, ?, ?, ?, ?)`,
            [req.params.id, role, content, agent_id, tool_id, parent_idx]
        );
        
        const [step] = await db.query(`
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
        await db.query(
            'UPDATE conversations SET ended_at = NOW() WHERE id = ?',
            [req.params.id]
        );
        
        const [conversation] = await db.query('SELECT * FROM conversations WHERE id = ?', [req.params.id]);
        res.json(conversation[0]);
    } catch (error) {
        logger.error('Error ending conversation:', error);
        res.status(500).json({ error: 'Failed to end conversation' });
    }
});

// Get conversation history
router.get('/:id/history', async (req, res) => {
    try {
        const [steps] = await db.query(`
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
        const [conversation] = await db.query(
            'SELECT * FROM conversations WHERE id = ?',
            [req.params.id]
        );

        if (conversation.length === 0) {
            return res.status(404).json({ error: 'Conversation not found' });
        }

        // Delete all conversation steps first (due to foreign key constraint)
        await db.query(
            'DELETE FROM conversation_steps WHERE conversation_id = ?',
            [req.params.id]
        );

        // Then delete the conversation
        await db.query(
            'DELETE FROM conversations WHERE id = ?',
            [req.params.id]
        );

        res.json({ message: 'Conversation deleted successfully' });
    } catch (error) {
        logger.error('Error deleting conversation:', error);
        res.status(500).json({ error: 'Failed to delete conversation' });
    }
});

module.exports = router; 
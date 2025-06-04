const express = require('express');
const router = express.Router();
const db = require('../utils/db');
const logger = require('../utils/logger');

// Get tools for an agent
router.get('/:agentId', async (req, res) => {
    try {
        logger.info('Fetching tools for agent:', { agent_id: req.params.agentId });

        // First check if agent exists
        const [agent] = await db.query('SELECT id FROM agents WHERE id = ?', [req.params.agentId]);
        
        if (agent.length === 0) {
            logger.warn('Agent not found:', { agent_id: req.params.agentId });
            return res.status(404).json({ error: 'Agent not found' });
        }

        // Get all tools for the agent with full details
        const [tools] = await db.query(`
            SELECT 
                t.*,
                at.id as agent_tool_id,
                at.created_at as assignment_date,
                at.agent_id
            FROM tools t
            JOIN agent_tools at ON t.id = at.tool_id
            WHERE at.agent_id = ?
            ORDER BY t.tool_type, t.tool_name
        `, [req.params.agentId]);
        
        logger.info('Found tools for agent:', { 
            agent_id: req.params.agentId,
            tool_count: tools.length,
            tools: tools.map(t => ({ id: t.id, name: t.tool_name, type: t.tool_type }))
        });

        res.json(tools);
    } catch (error) {
        logger.error('Error fetching agent tools:', {
            error: error.message,
            stack: error.stack,
            agent_id: req.params.agentId
        });
        res.status(500).json({ error: 'Failed to fetch agent tools' });
    }
});

// Add tool to agent
router.post('/', async (req, res) => {
    try {
        const { agent_id, tool_id } = req.body;
        
        if (!agent_id || !tool_id) {
            return res.status(400).json({ error: 'Missing required fields: agent_id, tool_id' });
        }

        // Log the request details
        logger.info('Attempting to add tool to agent:', { agent_id, tool_id });

        // Check if tool is already assigned to agent
        const [existing] = await db.query(
            'SELECT id FROM agent_tools WHERE agent_id = ? AND tool_id = ?',
            [agent_id, tool_id]
        );

        // Log the existing assignment check results
        logger.info('Existing tool assignment check:', { 
            agent_id, 
            tool_id, 
            exists: existing.length > 0,
            existing_records: existing 
        });

        if (existing.length > 0) {
            return res.status(409).json({ 
                error: 'Tool is already assigned to this agent',
                agent_tool_id: existing[0].id  // Include the existing assignment ID
            });
        }

        // Add tool to agent
        const [result] = await db.query(
            'INSERT INTO agent_tools (agent_id, tool_id) VALUES (?, ?)',
            [agent_id, tool_id]
        );

        logger.info('Tool assignment created:', { 
            agent_id, 
            tool_id, 
            assignment_id: result.insertId 
        });

        // Get the tool details
        const [tool] = await db.query(`
            SELECT t.*, at.id as agent_tool_id
            FROM tools t
            JOIN agent_tools at ON t.id = at.tool_id
            WHERE at.id = ?
        `, [result.insertId]);

        if (tool.length === 0) {
            logger.error('Tool not found after insertion:', { 
                agent_id, 
                tool_id, 
                insertId: result.insertId 
            });
            return res.status(500).json({ error: 'Failed to fetch tool details after assignment' });
        }

        logger.info('Successfully added tool to agent:', {
            agent_id,
            tool_id,
            agent_tool_id: tool[0].agent_tool_id
        });

        res.status(201).json(tool[0]);
    } catch (error) {
        logger.error('Error adding tool to agent:', {
            error: error.message,
            stack: error.stack,
            agent_id: req.body.agent_id,
            tool_id: req.body.tool_id
        });
        res.status(500).json({ error: 'Failed to add tool to agent' });
    }
});

// Remove tool from agent
router.delete('/:id', async (req, res) => {
    try {
        const id = req.params.id;
        logger.info('Attempting to remove tool assignment:', { agent_tool_id: id });

        const [result] = await db.query('DELETE FROM agent_tools WHERE id = ?', [id]);
        
        logger.info('Tool assignment removal result:', { 
            agent_tool_id: id,
            affected_rows: result.affectedRows
        });

        res.json({ 
            message: 'Tool removed from agent successfully',
            affected_rows: result.affectedRows
        });
    } catch (error) {
        logger.error('Error removing tool from agent:', {
            error: error.message,
            stack: error.stack,
            agent_tool_id: req.params.id
        });
        res.status(500).json({ error: 'Failed to remove tool from agent' });
    }
});

module.exports = router; 
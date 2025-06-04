const express = require('express');
const router = express.Router();
const db = require('../utils/db');
const logger = require('../utils/logger');

// Get all tools
router.get('/', async (req, res) => {
    try {
        const [tools] = await db.query('SELECT * FROM tools');
        res.json(tools);
    } catch (error) {
        logger.error('Error fetching tools:', error);
        res.status(500).json({ error: 'Failed to fetch tools' });
    }
});

// Get connected sources for a team
router.get('/connected-sources/:teamId', async (req, res) => {
    try {
        const teamId = req.params.teamId;
        const [sources] = await db.query(`
            SELECT DISTINCT t.hostname, t.tool_type
            FROM tools t
            JOIN team_tool_permissions ttp ON t.id = ttp.tool_id
            WHERE ttp.team_id = ?
            ORDER BY t.tool_type, t.hostname
        `, [teamId]);
        
        // Log the response for debugging
        logger.info('Connected sources response:', { teamId, sources });
        
        res.json(sources);
    } catch (error) {
        logger.error('Error fetching connected sources:', error);
        res.status(500).json({ error: 'Failed to fetch connected sources' });
    }
});

// Create a new tool
router.post('/', async (req, res) => {
    try {
        const { tool_name, tool_type, hostname, username, password, auth_method } = req.body;
        
        if (!tool_name || !tool_type) {
            return res.status(400).json({ error: 'Missing required fields: tool_name, tool_type' });
        }

        const [result] = await db.query(
            `INSERT INTO tools (tool_name, tool_type, hostname, username, password, auth_method) 
             VALUES (?, ?, ?, ?, ?, ?)`,
            [tool_name, tool_type, hostname, username, password, auth_method]
        );

        const [tool] = await db.query('SELECT * FROM tools WHERE id = ?', [result.insertId]);
        res.status(201).json(tool[0]);
    } catch (error) {
        logger.error('Error creating tool:', error);
        res.status(500).json({ error: 'Failed to create tool' });
    }
});

// Get tool by ID
router.get('/:id', async (req, res) => {
    try {
        const [tool] = await db.query(`
            SELECT t.*, 
                   COUNT(DISTINCT at.agent_id) as agent_count
            FROM tools t
            LEFT JOIN agent_tools at ON t.id = at.tool_id
            WHERE t.id = ?
            GROUP BY t.id
        `, [req.params.id]);
        
        if (tool.length === 0) {
            return res.status(404).json({ error: 'Tool not found' });
        }
        
        // Get tool's agents
        const [agents] = await db.query(`
            SELECT a.* 
            FROM agents a
            JOIN agent_tools at ON a.id = at.agent_id
            WHERE at.tool_id = ?
        `, [req.params.id]);
        
        tool[0].agents = agents;
        res.json(tool[0]);
    } catch (error) {
        logger.error('Error fetching tool:', error);
        res.status(500).json({ error: 'Failed to fetch tool' });
    }
});

// Update a tool
router.put('/:id', async (req, res) => {
    try {
        const { tool_name, tool_type, hostname, username, password, auth_method } = req.body;
        
        const updates = [];
        const params = [];
        
        if (tool_name !== undefined) {
            updates.push('tool_name = ?');
            params.push(tool_name);
        }
        if (tool_type !== undefined) {
            updates.push('tool_type = ?');
            params.push(tool_type);
        }
        if (hostname !== undefined) {
            updates.push('hostname = ?');
            params.push(hostname);
        }
        if (username !== undefined) {
            updates.push('username = ?');
            params.push(username);
        }
        if (password !== undefined) {
            updates.push('password = ?');
            params.push(password);
        }
        if (auth_method !== undefined) {
            updates.push('auth_method = ?');
            params.push(auth_method);
        }

        if (updates.length === 0) {
            return res.status(400).json({ error: 'No fields to update' });
        }

        params.push(req.params.id);
        await db.query(
            `UPDATE tools SET ${updates.join(', ')} WHERE id = ?`,
            params
        );

        const [tool] = await db.query('SELECT * FROM tools WHERE id = ?', [req.params.id]);
        if (tool.length === 0) {
            return res.status(404).json({ error: 'Tool not found' });
        }
        res.json(tool[0]);
    } catch (error) {
        logger.error('Error updating tool:', error);
        res.status(500).json({ error: 'Failed to update tool' });
    }
});

// Delete a tool
router.delete('/:id', async (req, res) => {
    try {
        await db.query('DELETE FROM tools WHERE id = ?', [req.params.id]);
        res.json({ message: 'Tool deleted successfully' });
    } catch (error) {
        logger.error('Error deleting tool:', error);
        res.status(500).json({ error: 'Failed to delete tool' });
    }
});

module.exports = router; 
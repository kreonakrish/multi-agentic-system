const express = require('express');
const router = express.Router();
const logger = require('../utils/logger');

module.exports = (pool) => {
    // Get all tools
    router.get('/', async (req, res) => {
        try {
            const [tools] = await pool.query('SELECT * FROM tools');
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
            console.log('Fetching connected sources for team:', teamId);
            
            // Fetch only the tools that are assigned to the team
            const [sources] = await pool.query(`
                SELECT DISTINCT 
                    t.id,
                    t.hostname,
                    t.tool_type,
                    t.tool_name,
                    t.username,
                    t.auth_method,
                    COALESCE(ttp.permission_level, 'read') as permission_level
                FROM tools t
                INNER JOIN team_tool_permissions ttp ON t.id = ttp.tool_id
                WHERE ttp.team_id = ?
                ORDER BY t.tool_type, t.hostname
            `, [teamId]);
            
            console.log('Raw sources from database:', sources);
            
            // Group sources by tool type
            const groupedSources = sources.reduce((acc, source) => {
                const type = source.tool_type || 'other';
                if (!acc[type]) {
                    acc[type] = [];
                }
                acc[type].push({
                    id: source.id,
                    hostname: source.hostname,
                    toolName: source.tool_name,
                    username: source.username,
                    authMethod: source.auth_method || 'None',
                    permissionLevel: source.permission_level || 'read'
                });
                return acc;
            }, {});
            
            console.log('Grouped sources:', groupedSources);
            
            res.json(groupedSources);
        } catch (error) {
            console.error('Error in connected-sources:', error);
            res.status(500).json({ error: 'Failed to fetch connected sources' });
        }
    });

    // Create a new tool and assign to team
    router.post('/with-team/:teamId', async (req, res) => {
        try {
            const teamId = req.params.teamId;
            const { tool_name, tool_type, hostname, username, password, auth_method, permission_level = 'read' } = req.body;
            
            if (!tool_name || !tool_type) {
                return res.status(400).json({ error: 'Missing required fields: tool_name, tool_type' });
            }

            // Start a transaction
            const connection = await pool.getConnection();
            await connection.beginTransaction();

            try {
                // Create the tool
                const [toolResult] = await connection.query(
                    `INSERT INTO tools (tool_name, tool_type, hostname, username, password, auth_method) 
                     VALUES (?, ?, ?, ?, ?, ?)`,
                    [tool_name, tool_type, hostname, username, password, auth_method]
                );

                // Assign the tool to the team
                await connection.query(
                    `INSERT INTO team_tool_permissions (team_id, tool_id, permission_level) 
                     VALUES (?, ?, ?)`,
                    [teamId, toolResult.insertId, permission_level]
                );

                await connection.commit();
                connection.release();

                // Get the complete tool data
                const [tool] = await pool.query(`
                    SELECT t.*, ttp.permission_level 
                    FROM tools t
                    JOIN team_tool_permissions ttp ON t.id = ttp.tool_id
                    WHERE t.id = ? AND ttp.team_id = ?
                `, [toolResult.insertId, teamId]);

                res.status(201).json(tool[0]);
            } catch (err) {
                await connection.rollback();
                connection.release();
                throw err;
            }
        } catch (error) {
            logger.error('Error creating tool with team assignment:', error);
            res.status(500).json({ error: 'Failed to create tool with team assignment' });
        }
    });

    // Get tool by ID
    router.get('/:id', async (req, res) => {
        try {
            const [tool] = await pool.query(`
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
            const [agents] = await pool.query(`
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
            await pool.query(
                `UPDATE tools SET ${updates.join(', ')} WHERE id = ?`,
                params
            );

            const [tool] = await pool.query('SELECT * FROM tools WHERE id = ?', [req.params.id]);
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
            await pool.query('DELETE FROM tools WHERE id = ?', [req.params.id]);
            res.json({ message: 'Tool deleted successfully' });
        } catch (error) {
            logger.error('Error deleting tool:', error);
            res.status(500).json({ error: 'Failed to delete tool' });
        }
    });

    return router;
}; 
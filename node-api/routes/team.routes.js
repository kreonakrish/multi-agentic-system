const express = require('express');
const router = express.Router();
const db = require('../database/db');
const logger = require('../utils/logger');

// Get all teams
router.get('/', async (req, res) => {
    try {
        const [teams] = await db.query(`
            SELECT t.*, 
                   COUNT(DISTINCT ta.agent_id) as agent_count,
                   COUNT(DISTINCT ttp.tool_id) as tool_count
            FROM teams t
            LEFT JOIN team_agents ta ON t.id = ta.team_id
            LEFT JOIN team_tool_permissions ttp ON t.id = ttp.team_id
            GROUP BY t.id
        `);
        res.json(teams);
    } catch (error) {
        logger.error('Error fetching teams:', error);
        res.status(500).json({ error: 'Failed to fetch teams' });
    }
});

// Create a new team
router.post('/', async (req, res) => {
    try {
        const { name, description } = req.body;
        const [result] = await db.query(
            'INSERT INTO teams (name, description) VALUES (?, ?)',
            [name, description]
        );
        
        const [team] = await db.query('SELECT * FROM teams WHERE id = ?', [result.insertId]);
        res.status(201).json(team[0]);
    } catch (error) {
        logger.error('Error creating team:', error);
        res.status(500).json({ error: 'Failed to create team' });
    }
});

// Get team by ID
router.get('/:id', async (req, res) => {
    try {
        const [team] = await db.query(`
            SELECT t.*, 
                   COUNT(DISTINCT ta.agent_id) as agent_count,
                   COUNT(DISTINCT ttp.tool_id) as tool_count
            FROM teams t
            LEFT JOIN team_agents ta ON t.id = ta.team_id
            LEFT JOIN team_tool_permissions ttp ON t.id = ttp.team_id
            WHERE t.id = ?
            GROUP BY t.id
        `, [req.params.id]);
        
        if (team.length === 0) {
            return res.status(404).json({ error: 'Team not found' });
        }
        
        // Get team's agents
        const [agents] = await db.query(`
            SELECT a.*, ta.accuracy, ta.success, ta.priority 
            FROM agents a
            JOIN team_agents ta ON a.id = ta.agent_id
            WHERE ta.team_id = ?
        `, [req.params.id]);
        
        // Get team's tools with permissions
        const [tools] = await db.query(`
            SELECT t.*, ttp.permission_level 
            FROM tools t
            JOIN team_tool_permissions ttp ON t.id = ttp.tool_id
            WHERE ttp.team_id = ?
        `, [req.params.id]);
        
        team[0].agents = agents;
        team[0].tools = tools;
        
        res.json(team[0]);
    } catch (error) {
        logger.error('Error fetching team:', error);
        res.status(500).json({ error: 'Failed to fetch team' });
    }
});

// Update team
router.put('/:id', async (req, res) => {
    try {
        const { name, description } = req.body;
        await db.query(
            'UPDATE teams SET name = ?, description = ? WHERE id = ?',
            [name, description, req.params.id]
        );
        
        const [team] = await db.query('SELECT * FROM teams WHERE id = ?', [req.params.id]);
        res.json(team[0]);
    } catch (error) {
        logger.error('Error updating team:', error);
        res.status(500).json({ error: 'Failed to update team' });
    }
});

// Add member to team
router.post('/:id/members', async (req, res) => {
    try {
        const { agent_id, accuracy = null, success = null, priority = null } = req.body;
        await db.query(
            'INSERT INTO team_agents (team_id, agent_id, accuracy, success, priority) VALUES (?, ?, ?, ?, ?)',
            [req.params.id, agent_id, accuracy, success, priority]
        );
        
        const [agent] = await db.query(`
            SELECT a.*, ta.accuracy, ta.success, ta.priority 
            FROM agents a
            JOIN team_agents ta ON a.id = ta.agent_id
            WHERE ta.team_id = ? AND a.id = ?
        `, [req.params.id, agent_id]);
        
        res.status(201).json(agent[0]);
    } catch (error) {
        logger.error('Error adding team member:', error);
        res.status(500).json({ error: 'Failed to add team member' });
    }
});

// Add tool to team
router.post('/:id/tools', async (req, res) => {
    try {
        const { tool_id, permission_level = 'read' } = req.body;
        await db.query(
            'INSERT INTO team_tool_permissions (team_id, tool_id, permission_level) VALUES (?, ?, ?)',
            [req.params.id, tool_id, permission_level]
        );
        
        const [tool] = await db.query(`
            SELECT t.*, ttp.permission_level 
            FROM tools t
            JOIN team_tool_permissions ttp ON t.id = ttp.tool_id
            WHERE ttp.team_id = ? AND t.id = ?
        `, [req.params.id, tool_id]);
        
        res.status(201).json(tool[0]);
    } catch (error) {
        logger.error('Error adding tool to team:', error);
        res.status(500).json({ error: 'Failed to add tool to team' });
    }
});

// Delete team
router.delete('/:id', async (req, res) => {
    try {
        await db.query('DELETE FROM teams WHERE id = ?', [req.params.id]);
        res.json({ message: 'Team deleted successfully' });
    } catch (error) {
        logger.error('Error deleting team:', error);
        res.status(500).json({ error: 'Failed to delete team' });
    }
});

// Update team conversation settings
router.put('/:id/conversation-settings', async (req, res) => {
    try {
        const { 
            temperature,
            tokenLimit,
            startPrompt,
            endPrompt,
            style
        } = req.body;

        await db.query(`
            INSERT INTO conversation_settings 
                (team_id, temperature, token_limit, start_prompt, end_prompt, style)
            VALUES (?, ?, ?, ?, ?, ?)
            ON DUPLICATE KEY UPDATE
                temperature = VALUES(temperature),
                token_limit = VALUES(token_limit),
                start_prompt = VALUES(start_prompt),
                end_prompt = VALUES(end_prompt),
                style = VALUES(style)
        `, [
            req.params.id,
            temperature,
            tokenLimit,
            startPrompt,
            endPrompt,
            style
        ]);

        // Get the updated team data with agents
        const [team] = await db.query(`
            SELECT t.*, 
                   COUNT(DISTINCT ta.agent_id) as agent_count
            FROM teams t
            LEFT JOIN team_agents ta ON t.id = ta.team_id
            WHERE t.id = ?
            GROUP BY t.id
        `, [req.params.id]);

        if (team.length === 0) {
            return res.status(404).json({ error: 'Team not found' });
        }

        // Get team's agents
        const [agents] = await db.query(`
            SELECT a.*, ta.accuracy, ta.success, ta.priority 
            FROM agents a
            JOIN team_agents ta ON a.id = ta.agent_id
            WHERE ta.team_id = ?
        `, [req.params.id]);

        team[0].agents = agents;

        // Get the conversation settings
        const [settings] = await db.query(
            'SELECT * FROM conversation_settings WHERE team_id = ?',
            [req.params.id]
        );

        // Combine team data with settings
        const response = {
            ...team[0],
            conversation_settings: settings[0] || null
        };

        res.json(response);
    } catch (error) {
        logger.error('Error updating team conversation settings:', error);
        res.status(500).json({ error: 'Failed to update team conversation settings' });
    }
});

// Get team conversation settings
router.get('/:id/conversation-settings', async (req, res) => {
    try {
        const [settings] = await db.query(`
            SELECT 
                id,
                team_id,
                temperature,
                token_limit,
                start_prompt,
                end_prompt,
                style,
                created_at
            FROM conversation_settings 
            WHERE team_id = ?
        `, [req.params.id]);

        if (settings.length === 0) {
            // If no settings exist, return default values
            return res.json({
                team_id: parseInt(req.params.id),
                temperature: null,
                token_limit: null,
                start_prompt: null,
                end_prompt: null,
                style: null,
                created_at: new Date().toISOString()
            });
        }

        res.json(settings[0]);
    } catch (error) {
        logger.error('Error fetching team conversation settings:', error);
        res.status(500).json({ error: 'Failed to fetch team conversation settings' });
    }
});

// Add default tools to team
router.post('/:id/default-tools', async (req, res) => {
    try {
        const teamId = req.params.id;
        
        // First check if team already has tools
        const [existingTools] = await db.query(`
            SELECT COUNT(*) as count
            FROM team_tool_permissions
            WHERE team_id = ?
        `, [teamId]);
        
        if (existingTools[0].count > 0) {
            return res.json({ message: 'Team already has tools assigned' });
        }
        
        // Get all available tools
        const [tools] = await db.query('SELECT id FROM tools');
        
        if (tools.length === 0) {
            // Create default tools if none exist
            await db.query(`
                INSERT INTO tools (tool_name, tool_type, hostname, username, password, auth_method)
                VALUES 
                    ('Sample DB Tool', 'Database', 'db.example.com', 'dbuser', '********', 'Basic'),
                    ('Sample API Tool', 'API', 'api.example.com', 'apiuser', '********', 'API Key')
            `);
            
            // Get the newly created tools
            const [newTools] = await db.query('SELECT id FROM tools');
            tools.push(...newTools);
        }
        
        // Add all tools to the team with read permission
        for (const tool of tools) {
            await db.query(`
                INSERT INTO team_tool_permissions (team_id, tool_id, permission_level)
                VALUES (?, ?, 'read')
                ON DUPLICATE KEY UPDATE permission_level = 'read'
            `, [teamId, tool.id]);
        }
        
        // Get the updated team data
        const [team] = await db.query(`
            SELECT t.*, 
                   COUNT(DISTINCT ta.agent_id) as agent_count,
                   COUNT(DISTINCT ttp.tool_id) as tool_count
            FROM teams t
            LEFT JOIN team_agents ta ON t.id = ta.team_id
            LEFT JOIN team_tool_permissions ttp ON t.id = ttp.team_id
            WHERE t.id = ?
            GROUP BY t.id
        `, [teamId]);
        
        if (team.length === 0) {
            return res.status(404).json({ error: 'Team not found' });
        }
        
        // Get team's tools with permissions
        const [assignedTools] = await db.query(`
            SELECT t.*, ttp.permission_level 
            FROM tools t
            JOIN team_tool_permissions ttp ON t.id = ttp.tool_id
            WHERE ttp.team_id = ?
        `, [teamId]);
        
        team[0].tools = assignedTools;
        res.json(team[0]);
    } catch (error) {
        logger.error('Error adding default tools to team:', error);
        res.status(500).json({ error: 'Failed to add default tools to team' });
    }
});

// Get connected sources for a team
router.get('/:teamId/connected-sources', async (req, res) => {
    try {
        const { teamId } = req.params;
        
        // First get the active agents for this team
        const [agents] = await db.query(`
            SELECT a.id, a.name
            FROM agents a
            JOIN team_agents ta ON a.id = ta.agent_id
            WHERE ta.team_id = ?
        `, [teamId]);

        logger.info(`Found ${agents.length} agents for team ${teamId}:`, agents.map(a => a.name).join(', '));

        if (agents.length === 0) {
            return res.json([]);
        }

        // Get tools only for these agents
        const [rows] = await db.query(`
            SELECT DISTINCT t.hostname, t.tool_type
            FROM agent_tools at
            JOIN tools t ON at.tool_id = t.id
            WHERE at.agent_id IN (${agents.map(() => '?').join(',')})
        `, agents.map(a => a.id));

        logger.info(`Found ${rows.length} connected sources for team ${teamId}'s agents`);
        res.json(rows);
    } catch (error) {
        logger.error('Error fetching connected sources:', error);
        res.status(500).json({ error: 'Failed to fetch connected sources' });
    }
});

module.exports = router; 
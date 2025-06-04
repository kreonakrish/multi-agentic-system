const express = require('express');
const router = express.Router();
const db = require('../database/db');
const logger = require('../utils/logger');

// Get all agents
router.get('/', async (req, res) => {
    try {
        // First get all agents with counts
        const [agents] = await db.query(`
            SELECT a.*, 
                   COUNT(DISTINCT at.tool_id) as tool_count,
                   COUNT(DISTINCT ta.team_id) as team_count
            FROM agents a
            LEFT JOIN agent_tools at ON a.id = at.agent_id
            LEFT JOIN team_agents ta ON a.id = ta.agent_id
            GROUP BY a.id
        `);

        // For each agent, get their tools
        const agentsWithTools = await Promise.all(agents.map(async (agent) => {
            const [tools] = await db.query(`
                SELECT t.* 
                FROM tools t
                JOIN agent_tools at ON t.id = at.tool_id
                WHERE at.agent_id = ?
            `, [agent.id]);
            
            return {
                ...agent,
                tools
            };
        }));

        res.json(agentsWithTools);
    } catch (error) {
        logger.error('Error fetching agents:', error);
        res.status(500).json({ error: 'Failed to fetch agents' });
    }
});

// Create a new agent
router.post('/', async (req, res) => {
    try {
        const { name, memory_type, foundation_model, status = 'inactive' } = req.body;
        const [result] = await db.query(
            'INSERT INTO agents (name, memory_type, foundation_model, status) VALUES (?, ?, ?, ?)',
            [name, memory_type, foundation_model, status]
        );
        
        const [agent] = await db.query('SELECT * FROM agents WHERE id = ?', [result.insertId]);
        res.status(201).json(agent[0]);
    } catch (error) {
        logger.error('Error creating agent:', error);
        res.status(500).json({ error: 'Failed to create agent' });
    }
});

// Get agent by ID
router.get('/:id', async (req, res) => {
    try {
        const [agent] = await db.query(`
            SELECT a.*, 
                   COUNT(DISTINCT at.tool_id) as tool_count,
                   COUNT(DISTINCT ta.team_id) as team_count
            FROM agents a
            LEFT JOIN agent_tools at ON a.id = at.agent_id
            LEFT JOIN team_agents ta ON a.id = ta.agent_id
            WHERE a.id = ?
            GROUP BY a.id
        `, [req.params.id]);
        
        if (agent.length === 0) {
            return res.status(404).json({ error: 'Agent not found' });
        }
        
        // Get agent's tools
        const [tools] = await db.query(`
            SELECT t.* 
            FROM tools t
            JOIN agent_tools at ON t.id = at.tool_id
            WHERE at.agent_id = ?
        `, [req.params.id]);
        
        // Get agent's teams
        const [teams] = await db.query(`
            SELECT t.* 
            FROM teams t
            JOIN team_agents ta ON t.id = ta.team_id
            WHERE ta.agent_id = ?
        `, [req.params.id]);
        
        agent[0].tools = tools;
        agent[0].teams = teams;
        
        res.json(agent[0]);
    } catch (error) {
        logger.error('Error fetching agent:', error);
        res.status(500).json({ error: 'Failed to fetch agent' });
    }
});

// Update agent
router.put('/:id', async (req, res) => {
    try {
        const { name, memory_type, foundation_model, status } = req.body;
        await db.query(
            'UPDATE agents SET name = ?, memory_type = ?, foundation_model = ?, status = ? WHERE id = ?',
            [name, memory_type, foundation_model, status, req.params.id]
        );
        
        const [agent] = await db.query('SELECT * FROM agents WHERE id = ?', [req.params.id]);
        res.json(agent[0]);
    } catch (error) {
        logger.error('Error updating agent:', error);
        res.status(500).json({ error: 'Failed to update agent' });
    }
});

// Delete agent
router.delete('/:id', async (req, res) => {
    try {
        await db.query('DELETE FROM agents WHERE id = ?', [req.params.id]);
        res.json({ message: 'Agent deleted successfully' });
    } catch (error) {
        logger.error('Error deleting agent:', error);
        res.status(500).json({ error: 'Failed to delete agent' });
    }
});

// Add tool to agent
router.post('/:id/tools', async (req, res) => {
    try {
        const { tool_id } = req.body;
        await db.query(
            'INSERT INTO agent_tools (agent_id, tool_id) VALUES (?, ?)',
            [req.params.id, tool_id]
        );
        res.json({ message: 'Tool added to agent successfully' });
    } catch (error) {
        logger.error('Error adding tool to agent:', error);
        res.status(500).json({ error: 'Failed to add tool to agent' });
    }
});

// Get agent interactions by team ID
router.get('/interactions', async (req, res) => {
    try {
        const teamId = req.query.team_id;
        if (!teamId) {
            return res.status(400).json({ error: 'team_id query parameter is required' });
        }

        const [interactions] = await db.query(`
            SELECT 
                ai.*,
                a1.name as initiator_name,
                a2.name as target_name,
                t.name as team_name
            FROM agent_interactions ai
            JOIN agents a1 ON ai.initiator_agent_id = a1.id
            JOIN agents a2 ON ai.target_agent_id = a2.id
            JOIN teams t ON ai.team_id = t.id
            WHERE ai.team_id = ?
            ORDER BY ai.interaction_time DESC
        `, [teamId]);

        res.json(interactions);
    } catch (error) {
        logger.error('Error fetching agent interactions:', error);
        res.status(500).json({ error: 'Failed to fetch agent interactions' });
    }
});

module.exports = router; 
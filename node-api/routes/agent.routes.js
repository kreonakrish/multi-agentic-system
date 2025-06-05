const express = require('express');
const router = express.Router();
const logger = require('../utils/logger');
const mysql = require('mysql2/promise');

// Get database configuration
const dbConfig = require('../config/database');

// Create a connection pool
const db = mysql.createPool(dbConfig);

// Get all agents
router.get('/', async (req, res) => {
    const connection = await db.getConnection();
    try {
        const [agents] = await connection.query(`
            SELECT a.*, 
                   COUNT(DISTINCT at.tool_id) as tool_count,
                   COUNT(DISTINCT ta.team_id) as team_count
            FROM agents a
            LEFT JOIN agent_tools at ON a.id = at.agent_id
            LEFT JOIN team_agents ta ON a.id = ta.agent_id
            GROUP BY a.id
        `);

        // Get tools for each agent
        for (let agent of agents) {
            const [tools] = await connection.query(`
                SELECT t.* 
                FROM tools t
                JOIN agent_tools at ON t.id = at.tool_id
                WHERE at.agent_id = ?
            `, [agent.id]);
            agent.tools = tools;
        }

        res.json(agents);
    } catch (error) {
        logger.error('Error fetching agents:', error);
        res.status(500).json({ error: 'Failed to fetch agents' });
    } finally {
        connection.release();
    }
});

// Create a new agent
router.post('/', async (req, res) => {
    const connection = await db.getConnection();
    try {
        await connection.beginTransaction();

        const { name, memory_type, foundation_model, tools } = req.body;
        logger.info('Creating new agent:', { 
            name, 
            memory_type, 
            foundation_model,
            tools: JSON.stringify(tools)
        });

        // Insert agent
        const [result] = await connection.query(
            'INSERT INTO agents (name, memory_type, foundation_model) VALUES (?, ?, ?)',
            [name, memory_type, foundation_model]
        );

        const newAgentId = result.insertId;
        logger.info('Agent created with ID:', newAgentId);

        // Insert tool associations if tools are provided
        if (tools && Array.isArray(tools) && tools.length > 0) {
            logger.info('Adding tool assignments for new agent:', tools);
            const toolValues = tools.map(tool => {
                if (!tool.id) {
                    throw new Error('Tool ID is required for each tool');
                }
                return [newAgentId, tool.id];
            });

            await connection.query(
                'INSERT INTO agent_tools (agent_id, tool_id) VALUES ?',
                [toolValues]
            );
            logger.info('Tool assignments added successfully');
        }

        await connection.commit();
        logger.info('Transaction committed successfully');

        // Get the created agent with tools
        const [[createdAgent]] = await connection.query(`
            SELECT a.*, 
                   GROUP_CONCAT(DISTINCT t.id) as tool_ids,
                   COUNT(DISTINCT at.tool_id) as tool_count,
                   COUNT(DISTINCT ta.team_id) as team_count
            FROM agents a
            LEFT JOIN agent_tools at ON a.id = at.agent_id
            LEFT JOIN tools t ON at.tool_id = t.id
            LEFT JOIN team_agents ta ON a.id = ta.agent_id
            WHERE a.id = ?
            GROUP BY a.id
        `, [newAgentId]);

        // Get agent's tools
        const [toolsResult] = await connection.query(`
            SELECT t.* 
            FROM tools t
            JOIN agent_tools at ON t.id = at.tool_id
            WHERE at.agent_id = ?
        `, [newAgentId]);

        createdAgent.tools = toolsResult;
        
        res.status(201).json(createdAgent);
    } catch (error) {
        await connection.rollback();
        logger.error('Error creating agent:', error);
        res.status(500).json({ error: error.message || 'Failed to create agent' });
    } finally {
        connection.release();
    }
});

// Get agent by ID
router.get('/:id', async (req, res) => {
    const connection = await db.getConnection();
    try {
        const [agent] = await connection.query(`
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
        const [tools] = await connection.query(`
            SELECT t.* 
            FROM tools t
            JOIN agent_tools at ON t.id = at.tool_id
            WHERE at.agent_id = ?
        `, [req.params.id]);
        
        // Get agent's teams
        const [teams] = await connection.query(`
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
    } finally {
        connection.release();
    }
});

// Update agent
router.put('/:id', async (req, res) => {
    const connection = await db.getConnection();
    try {
        await connection.beginTransaction();
        
        const { name, memory_type, foundation_model, tools } = req.body;

        logger.info('PUT /api/agents/:id request received:', { 
            body: req.body,
            query: req.query,
            params: req.params
        });

        logger.info('Processing update request:', { 
            agentId: req.params.id,
            name,
            memory_type,
            foundation_model,
            tools: JSON.stringify(tools)
        });

        // Validate required fields
        if (!name || !memory_type || !foundation_model) {
            throw new Error('Missing required fields: name, memory_type, or foundation_model');
        }

        // Update agent details
        const [updateResult] = await connection.query(
            'UPDATE agents SET name = ?, memory_type = ?, foundation_model = ? WHERE id = ?',
            [name, memory_type, foundation_model, req.params.id]
        );

        if (updateResult.affectedRows === 0) {
            throw new Error('Agent not found');
        }

        logger.info('Agent details updated successfully');

        // Remove existing tool assignments
        await connection.query('DELETE FROM agent_tools WHERE agent_id = ?', [req.params.id]);
        logger.info('Existing tool assignments removed');

        // Add new tool assignments if tools array is provided
        if (tools && Array.isArray(tools) && tools.length > 0) {
            logger.info('Adding new tool assignments:', JSON.stringify(tools));
            const toolValues = tools.map(tool => {
                if (!tool.id) {
                    throw new Error('Tool ID is required for each tool');
                }
                return [req.params.id, tool.id];
            });

            await connection.query(
                'INSERT INTO agent_tools (agent_id, tool_id) VALUES ?',
                [toolValues]
            );
            logger.info('New tool assignments added successfully');
        } else {
            logger.info('No tools provided for update');
        }

        await connection.commit();
        logger.info('Transaction committed successfully');

        // Get updated agent with tools
        const [[updatedAgent]] = await connection.query(`
            SELECT a.*, 
                   GROUP_CONCAT(DISTINCT t.id) as tool_ids,
                   COUNT(DISTINCT at.tool_id) as tool_count,
                   COUNT(DISTINCT ta.team_id) as team_count
            FROM agents a
            LEFT JOIN agent_tools at ON a.id = at.agent_id
            LEFT JOIN tools t ON at.tool_id = t.id
            LEFT JOIN team_agents ta ON a.id = ta.agent_id
            WHERE a.id = ?
            GROUP BY a.id
        `, [req.params.id]);

        if (!updatedAgent) {
            throw new Error('Failed to fetch updated agent');
        }

        // Get agent's tools
        const [toolsResult] = await connection.query(`
            SELECT t.* 
            FROM tools t
            JOIN agent_tools at ON t.id = at.tool_id
            WHERE at.agent_id = ?
        `, [req.params.id]);

        updatedAgent.tools = toolsResult;
        logger.info('Sending updated agent response');
        
        res.json(updatedAgent);
    } catch (error) {
        logger.error('Error in PUT /api/agents/:id handler:', error);
        await connection.rollback();
        logger.error('Transaction rolled back due to error:', error.message);
        res.status(500).json({ error: error.message || 'Failed to update agent' });
    } finally {
        connection.release();
        logger.info('PUT /api/agents/:id handler completed');
    }
});

// Delete agent
router.delete('/:id', async (req, res) => {
    const connection = await db.getConnection();
    try {
        await connection.beginTransaction();

        // Delete from agent_tools first (due to foreign key constraint)
        await connection.query('DELETE FROM agent_tools WHERE agent_id = ?', [req.params.id]);
        logger.info('Deleted tool assignments for agent:', req.params.id);

        // Delete from team_agents (if this relationship exists)
        await connection.query('DELETE FROM team_agents WHERE agent_id = ?', [req.params.id]);
        logger.info('Deleted team assignments for agent:', req.params.id);

        // Delete the agent
        const [result] = await connection.query('DELETE FROM agents WHERE id = ?', [req.params.id]);
        
        if (result.affectedRows === 0) {
            throw new Error('Agent not found');
        }

        await connection.commit();
        logger.info('Agent deleted successfully:', req.params.id);

        res.json({ message: 'Agent deleted successfully' });
    } catch (error) {
        await connection.rollback();
        logger.error('Error deleting agent:', error);
        res.status(500).json({ error: error.message || 'Failed to delete agent' });
    } finally {
        connection.release();
    }
});

// Add tool to agent
router.post('/:id/tools', async (req, res) => {
    const connection = await db.getConnection();
    try {
        const { tool_id } = req.body;
        await connection.query(
            'INSERT INTO agent_tools (agent_id, tool_id) VALUES (?, ?)',
            [req.params.id, tool_id]
        );
        res.json({ message: 'Tool added to agent successfully' });
    } catch (error) {
        logger.error('Error adding tool to agent:', error);
        res.status(500).json({ error: 'Failed to add tool to agent' });
    } finally {
        connection.release();
    }
});

module.exports = router; 
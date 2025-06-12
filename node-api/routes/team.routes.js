const express = require('express');
const router = express.Router();
const logger = require('../utils/logger');

// Helper function to safely get configuration
function getConfiguration(rawConfig) {
    if (!rawConfig) {
        return {};
    }

    // If it's already an object, return it
    if (typeof rawConfig === 'object' && !Array.isArray(rawConfig)) {
        return rawConfig;
    }

    // Try to parse if it's a string
    try {
        return typeof rawConfig === 'string' ? JSON.parse(rawConfig) : {};
    } catch (e) {
        logger.error('Error parsing configuration:', {
            error: e.message,
            raw_config: rawConfig
        });
        return {};
    }
}

module.exports = (pool) => {
    // Get all teams with their agents
    router.get('/', async (req, res) => {
        logger.info('GET /api/teams - Request received', {
            query: req.query,
            headers: req.headers
        });

        try {
            // Get all teams
            logger.info('Fetching all teams from database');
            const [teams] = await pool.query('SELECT * FROM teams');
            logger.info(`Found ${teams.length} teams in database`);
            
            // For each team, get its agents and parse configuration
            logger.info('Processing teams and parsing configurations');
            const teamsWithConfig = teams.map(team => {
                const config = getConfiguration(team.configuration);
                logger.info(`Processed configuration for team ${team.id}:`, {
                    team_id: team.id,
                    raw_config: team.configuration,
                    processed_config: config
                });
                return {
                    ...team,
                    use_smart_workflow: config.use_smart_workflow || false,
                    configuration: config
                };
            });
            
            // For each team, get its agents
            const teamIds = teamsWithConfig.map(t => t.id);
            let agentsByTeam = {};
            
            if (teamIds.length > 0) {
                logger.info('Fetching agents for teams:', { team_ids: teamIds });
                const [agents] = await pool.query(`
                    SELECT ta.team_id, a.*, ta.accuracy, ta.success, ta.priority
                    FROM team_agents ta
                    JOIN agents a ON ta.agent_id = a.id
                    WHERE ta.team_id IN (${teamIds.map(() => '?').join(',')})
                `, teamIds);
                logger.info(`Found ${agents.length} total agents for all teams`);
                
                agentsByTeam = agents.reduce((acc, agent) => {
                    if (!acc[agent.team_id]) acc[agent.team_id] = [];
                    acc[agent.team_id].push({
                        id: agent.id,
                        name: agent.name,
                        accuracy: Number(agent.accuracy) || 100,
                        success: Number(agent.success) || 100,
                        priority: Number(agent.priority) || 1
                    });
                    return acc;
                }, {});

                logger.info('Grouped agents by team:', Object.keys(agentsByTeam).map(teamId => ({
                    team_id: teamId,
                    agent_count: agentsByTeam[teamId].length
                })));
            }
            
            // Attach agents to each team
            const teamsWithAgents = teamsWithConfig.map(team => ({
                ...team,
                agents: agentsByTeam[team.id] || []
            }));
            
            logger.info('Sending response with teams and their agents', {
                team_count: teamsWithAgents.length,
                teams: teamsWithAgents.map(t => ({
                    id: t.id,
                    name: t.name,
                    agent_count: t.agents.length,
                    use_smart_workflow: t.use_smart_workflow
                }))
            });
            
            res.json(teamsWithAgents);
    } catch (error) {
            logger.error('Error fetching teams:', {
                error: error.message,
                stack: error.stack,
                sql: error.sql,
                sqlMessage: error.sqlMessage
            });
        res.status(500).json({ error: 'Failed to fetch teams' });
    }
});

// Create a new team
router.post('/', async (req, res) => {
        logger.info('POST /api/teams - Request received', {
            body: req.body,
            headers: req.headers
        });

        const { name, agents, use_smart_workflow = false } = req.body;
        
        // Start transaction
        const connection = await pool.getConnection();
        await connection.beginTransaction();

        try {
            // Create team configuration
        const configuration = {
                use_smart_workflow,
                name,
                created_at: new Date().toISOString()
            };

            logger.info('Creating new team with configuration:', {
                name,
                use_smart_workflow,
                agent_count: agents?.length || 0,
                configuration
            });

            // Create the team
            const [result] = await connection.query(
                'INSERT INTO teams (name, configuration) VALUES (?, ?)',
                [name, JSON.stringify(configuration)]
            );
            const teamId = result.insertId;
            logger.info(`Team created with ID: ${teamId}`);

            // Insert agent assignments with metrics if provided
            if (Array.isArray(agents) && agents.length > 0) {
                logger.info(`Adding ${agents.length} agents to team ${teamId}`);
                for (const agent of agents) {
                    const accuracy = Math.max(0, Math.min(100, Number(agent.accuracy) || 100));
                    const success = Math.max(0, Math.min(100, Number(agent.success) || 100));
                    const priority = Math.max(1, Number(agent.priority) || 1);

                    logger.info('Adding agent to team:', {
                        team_id: teamId,
                        agent_id: agent.id,
                        accuracy,
                        success,
                        priority
                    });

                    await connection.query(
                        'INSERT INTO team_agents (team_id, agent_id, accuracy, success, priority) VALUES (?, ?, ?, ?, ?)',
                        [teamId, agent.id, accuracy, success, priority]
                    );
                }
            }

            // Get the complete team data
            logger.info(`Fetching complete team data for team ${teamId}`);
            const [teamRows] = await connection.query('SELECT * FROM teams WHERE id = ?', [teamId]);
            const [agentRows] = await connection.query(`
                SELECT a.*, ta.accuracy, ta.success, ta.priority
                FROM agents a
                JOIN team_agents ta ON a.id = ta.agent_id
                WHERE ta.team_id = ?
            `, [teamId]);

            // Commit transaction
            await connection.commit();
            connection.release();

            // Parse configuration for response
            let config = {};
            try {
                config = teamRows[0].configuration ? JSON.parse(teamRows[0].configuration) : {};
                logger.info('Parsed configuration for response:', {
                    team_id: teamId,
                    config
                });
            } catch (e) {
                logger.error('Error parsing team configuration:', {
                    team_id: teamId,
                    error: e.message,
                    raw_config: teamRows[0].configuration
                });
            }

            // Return the complete team data
            const newTeam = {
                ...teamRows[0],
                use_smart_workflow: config.use_smart_workflow || false,
                configuration: config,
                agents: agentRows.map(agent => ({
                    id: agent.id,
                    name: agent.name,
                    accuracy: Number(agent.accuracy),
                    success: Number(agent.success),
                    priority: Number(agent.priority)
                }))
            };

            logger.info('Sending response with new team data:', {
                team_id: newTeam.id,
                name: newTeam.name,
                use_smart_workflow: newTeam.use_smart_workflow,
                agent_count: newTeam.agents.length,
                configuration: newTeam.configuration
            });

            res.json(newTeam);
        } catch (err) {
            await connection.rollback();
            connection.release();
            logger.error('Error creating team:', {
                error: err.message,
                stack: err.stack,
                sql: err.sql,
                sqlMessage: err.sqlMessage,
                request_body: req.body
            });
            res.status(500).json({ error: 'Failed to create team', details: err.message });
    }
});

// Get team by ID
router.get('/:id', async (req, res) => {
        logger.info('GET /api/teams/:id - Request received', {
            params: req.params,
            query: req.query,
            headers: req.headers
        });

    try {
        logger.info(`Fetching team data for ID: ${req.params.id}`);
        
            const [team] = await pool.query(`
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
            logger.warn(`Team not found with ID: ${req.params.id}`);
            return res.status(404).json({ error: 'Team not found' });
        }
        
            // Parse configuration
            const config = getConfiguration(team[0].configuration);
            logger.info('Processed team configuration:', {
                team_id: req.params.id,
                config
            });
            
            // Add configuration fields to team object
            team[0].use_smart_workflow = config.use_smart_workflow || false;
            team[0].configuration = config;
        
        logger.info(`Found team: ${JSON.stringify(team[0])}`);
        
        // Get team's agents
            logger.info(`Fetching agents for team ${req.params.id}`);
            const [agents] = await pool.query(`
            SELECT a.*, ta.accuracy, ta.success, ta.priority 
            FROM agents a
            JOIN team_agents ta ON a.id = ta.agent_id
            WHERE ta.team_id = ?
        `, [req.params.id]);
        
            logger.info(`Found ${agents.length} agents for team ${req.params.id}`);
        
        // Get team's tools with permissions
            logger.info(`Fetching tools for team ${req.params.id}`);
            const [tools] = await pool.query(`
            SELECT t.*, ttp.permission_level 
            FROM tools t
            JOIN team_tool_permissions ttp ON t.id = ttp.tool_id
            WHERE ttp.team_id = ?
            `, [req.params.id]);
        
            logger.info(`Found ${tools.length} tools for team ${req.params.id}`);
        
        team[0].agents = agents;
        team[0].tools = tools;

            logger.info('Sending response with team data:', {
                team_id: team[0].id,
                name: team[0].name,
                use_smart_workflow: team[0].use_smart_workflow,
                agent_count: agents.length,
                tool_count: tools.length,
                configuration: team[0].configuration
            });
        
        res.json(team[0]);
    } catch (error) {
            logger.error('Error fetching team:', {
                team_id: req.params.id,
                error: error.message,
                stack: error.stack,
                sql: error.sql,
                sqlMessage: error.sqlMessage
            });
        res.status(500).json({ error: 'Failed to fetch team' });
    }
});

// Update team
router.put('/:id', async (req, res) => {
        logger.info('PUT /api/teams/:id - Request received', {
            params: req.params,
            body: req.body,
            headers: req.headers
        });

        const { id } = req.params;
        const { name, agents, team_config } = req.body;
        
        try {
            // Validate input
            if (!name || !Array.isArray(agents)) {
                logger.warn('Invalid input for team update:', {
                    team_id: id,
                    name,
                    agents: agents?.length,
                    team_config
                });
                return res.status(400).json({ 
                    error: 'Invalid input', 
                    details: 'Name and agents array are required' 
                });
            }

            // Start transaction
            const connection = await pool.getConnection();
            await connection.beginTransaction();

            try {
                logger.info('Updating team with data:', {
                    id,
                    name,
                    agent_count: agents.length,
                    team_config
                });

                // Get existing configuration
                const [existingTeam] = await connection.query('SELECT configuration FROM teams WHERE id = ?', [id]);
                const config = getConfiguration(existingTeam[0].configuration);
                logger.info('Processed existing configuration:', {
                    team_id: id,
                    config
                });

                // Update configuration, prioritizing team_config if provided
                const updatedConfig = {
                    ...config,
                    ...team_config,  // Apply team_config if provided
                    name,  // Always use the top-level name
                    updated_at: new Date().toISOString()
                };

                logger.info('New configuration to be saved:', {
                    team_id: id,
                    config: updatedConfig
                });

                // Update team name and configuration
                await connection.query(
                    'UPDATE teams SET name = ?, configuration = ? WHERE id = ?',
                    [name, JSON.stringify(updatedConfig), id]
                );
                
                // Remove all current agent assignments for this team
                logger.info(`Removing existing agent assignments for team ${id}`);
                await connection.query('DELETE FROM team_agents WHERE team_id = ?', [id]);
                
                // Insert new agent assignments with properties if provided
                if (agents.length > 0) {
                    logger.info(`Adding ${agents.length} agents to team ${id}`);
                    for (const agent of agents) {
                        // Ensure values are valid numbers
                        const accuracy = Math.max(0, Math.min(100, Number(agent.accuracy) || 100));
                        const success = Math.max(0, Math.min(100, Number(agent.success) || 100));
                        const priority = Math.max(1, Number(agent.priority) || 1);

                        logger.info('Inserting agent with values:', {
                            team_id: id,
                            agent_id: agent.id,
                            accuracy,
                            success,
                            priority
                        });

                        await connection.query(
                'INSERT INTO team_agents (team_id, agent_id, accuracy, success, priority) VALUES (?, ?, ?, ?, ?)',
                            [id, agent.id, accuracy, success, priority]
                        );
                    }
                }

                // Get updated team data
                logger.info(`Fetching updated team data for team ${id}`);
                const [teamRows] = await connection.query('SELECT * FROM teams WHERE id = ?', [id]);
                const [agentRows] = await connection.query(`
            SELECT a.*, ta.accuracy, ta.success, ta.priority 
            FROM agents a
            JOIN team_agents ta ON a.id = ta.agent_id
            WHERE ta.team_id = ?
                `, [id]);

                await connection.commit();
                connection.release();

                // Parse configuration for response
                const responseConfig = getConfiguration(teamRows[0].configuration);
                logger.info('Processed configuration for response:', {
                    team_id: id,
                    config: responseConfig
                });

                const updatedTeam = {
                    ...teamRows[0],
                    use_smart_workflow: responseConfig.use_smart_workflow || false,
                    configuration: responseConfig,
                    agents: agentRows.map(agent => ({
                        id: agent.id,
                        name: agent.name,
                        accuracy: Number(agent.accuracy) || 100,
                        success: Number(agent.success) || 100,
                        priority: Number(agent.priority) || 1
                    }))
                };
                
                logger.info('Sending updated team data:', {
                    team_id: updatedTeam.id,
                    name: updatedTeam.name,
                    use_smart_workflow: updatedTeam.use_smart_workflow,
                    agent_count: updatedTeam.agents.length,
                    configuration: updatedTeam.configuration
                });

                res.json(updatedTeam);
            } catch (err) {
                logger.error('Transaction error:', {
                    team_id: id,
                    error: err.message,
                    stack: err.stack,
                    sql: err.sql,
                    sqlMessage: err.sqlMessage
                });
                await connection.rollback();
                connection.release();
                throw err;
            }
        } catch (err) {
            logger.error('Error updating team:', {
                team_id: id,
                error: err.message,
                stack: err.stack,
                sql: err.sql,
                sqlMessage: err.sqlMessage,
                request_body: req.body
            });
            res.status(500).json({ 
                error: 'Failed to update team', 
                details: err.message,
                sqlMessage: err.sqlMessage 
            });
    }
});

// Delete team
router.delete('/:id', async (req, res) => {
        logger.info('DELETE /api/teams/:id - Request received', {
            params: req.params,
            headers: req.headers
        });

        const { id } = req.params;
        try {
            logger.info(`Deleting team ${id}`);
            await pool.query('DELETE FROM teams WHERE id = ?', [id]);
            logger.info(`Successfully deleted team ${id}`);
            res.json({ success: true });
        } catch (err) {
            logger.error('Error deleting team:', {
                team_id: id,
                error: err.message,
                stack: err.stack,
                sql: err.sql,
                sqlMessage: err.sqlMessage
            });
        res.status(500).json({ error: 'Failed to delete team' });
    }
});

    // Get team's agents
    router.get('/:id/agents', async (req, res) => {
        try {
            const [agents] = await pool.query(`
            SELECT a.*, ta.accuracy, ta.success, ta.priority 
            FROM agents a
            JOIN team_agents ta ON a.id = ta.agent_id
            WHERE ta.team_id = ?
        `, [req.params.id]);

            res.json(agents);
    } catch (error) {
            logger.error('Error fetching team agents:', error);
            res.status(500).json({ error: 'Failed to fetch team agents' });
        }
    });

    // Get team's tools
    router.get('/:id/tools', async (req, res) => {
        try {
            const [tools] = await pool.query(`
            SELECT t.*, ttp.permission_level 
            FROM tools t
            JOIN team_tool_permissions ttp ON t.id = ttp.tool_id
            WHERE ttp.team_id = ?
            `, [req.params.id]);
        
            res.json(tools);
    } catch (error) {
            logger.error('Error fetching team tools:', error);
            res.status(500).json({ error: 'Failed to fetch team tools' });
        }
    });

    // Get team conversation settings
    router.get('/:id/conversation-settings', async (req, res) => {
        try {
            const [settings] = await pool.query(
                'SELECT * FROM conversation_settings WHERE team_id = ? ORDER BY id DESC LIMIT 1',
                [req.params.id]
            );

            if (settings.length === 0) {
                // Return default settings if none exist
                return res.json({
                    temperature: 0.7,
                    token_limit: 512,
                    start_prompt: '',
                    end_prompt: '',
                    style: ''
                });
            }

            res.json(settings[0]);
        } catch (error) {
            logger.error('Error fetching team conversation settings:', error);
            res.status(500).json({ error: 'Failed to fetch team conversation settings' });
        }
    });

    // Update team conversation settings
    router.put('/:id/conversation-settings', async (req, res) => {
        const connection = await pool.getConnection();
        try {
            const { temperature, tokenLimit, startPrompt, endPrompt, style } = req.body;

            await connection.beginTransaction();

            // Insert new settings
            const [result] = await connection.query(
                'INSERT INTO conversation_settings (team_id, temperature, token_limit, start_prompt, end_prompt, style) VALUES (?, ?, ?, ?, ?, ?)',
                [
                    req.params.id,
                    Number(temperature) || 0.7,
                    Number(tokenLimit) || 512,
                    startPrompt || '',
                    endPrompt || '',
                    style || ''
                ]
            );

            await connection.commit();
            
            // Get the newly created settings
            const [settings] = await connection.query(
                'SELECT * FROM conversation_settings WHERE id = ?',
                [result.insertId]
            );

            connection.release();
            res.json(settings[0]);
        } catch (error) {
            await connection.rollback();
            connection.release();
            logger.error('Error updating team conversation settings:', error);
            res.status(500).json({ error: 'Failed to update team conversation settings' });
        }
    });

    return router;
}; 
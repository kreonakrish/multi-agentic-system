const express = require('express');
const router = express.Router();
const logger = require('../utils/logger');

module.exports = (pool) => {
    // Assign an agent to a team (with accuracy, success, priority)
    router.post('/', async (req, res) => {
        const { team_id, agent_id, accuracy, success, priority } = req.body;
        try {
            await pool.query(
                'INSERT INTO team_agents (team_id, agent_id, accuracy, success, priority) VALUES (?, ?, ?, ?, ?)',
                [team_id, agent_id, accuracy ?? null, success ?? null, priority ?? null]
            );
            res.json({ success: true });
        } catch (err) {
            logger.error('Failed to assign agent to team:', err);
            res.status(500).json({ error: 'Failed to assign agent to team' });
        }
    });

    // Update an agent-team assignment (accuracy, success, priority)
    router.put('/', async (req, res) => {
        const { team_id, agent_id, accuracy, success, priority } = req.body;
        try {
            await pool.query(
                'UPDATE team_agents SET accuracy=?, success=?, priority=? WHERE team_id=? AND agent_id=?',
                [accuracy, success, priority, team_id, agent_id]
            );
            res.json({ success: true });
        } catch (err) {
            logger.error('Error updating team agent:', err);
            res.status(500).json({ error: 'Failed to update team agent properties' });
        }
    });

    // Remove an agent from a team
    router.delete('/', async (req, res) => {
        const { team_id, agent_id } = req.body;
        try {
            await pool.query('DELETE FROM team_agents WHERE team_id=? AND agent_id=?', [team_id, agent_id]);
            res.json({ success: true });
        } catch (err) {
            logger.error('Failed to remove agent from team:', err);
            res.status(500).json({ error: 'Failed to remove agent from team' });
        }
    });

    return router;
}; 
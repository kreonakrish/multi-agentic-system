const express = require('express');
const cors = require('cors');
const axios = require('axios');
const mysql = require('mysql2/promise');

const app = express();
const PORT = 4000;

app.use(cors());
app.use(express.json());

// MySQL connection pool
const pool = mysql.createPool({
  host: 'localhost',
  user: 'admin',
  password: 'gUest@Sep2',
  database: 'multi_agentic_system',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

// Dummy agent list
const agents = [
  "Nifi Agents",
  "DBx Agents",
  "Confluence Agents",
  "AWS Agents",
  "RDS Agents",
  "Alteryx Agents",
  "Qlik Agents",
  "Thoughtspot Agents"
];

// Chart endpoint: orchestrates call to Python microservice
app.get('/api/charts', async (req, res) => {
  try {
    // Call Python microservice for chart data
    const { data } = await axios.get('http://localhost:5000/api/charts');
    res.json(data);
  } catch (err) {
    // Fallback dummy data if Python service unavailable
    res.json([
      {
        id: 1,
        type: 'bar',
        title: 'Monthly Data Overview',
        data: [
          { name: 'Jan', uv: 400, pv: 240, amt: 240 },
          { name: 'Feb', uv: 300, pv: 139, amt: 221 },
          { name: 'Mar', uv: 200, pv: 980, amt: 229 },
          { name: 'Apr', uv: 278, pv: 390, amt: 200 },
          { name: 'May', uv: 189, pv: 480, amt: 218 },
          { name: 'Jun', uv: 239, pv: 380, amt: 250 },
          { name: 'Jul', uv: 349, pv: 430, amt: 210 },
          { name: 'Aug', uv: 400, pv: 240, amt: 240 },
          { name: 'Sep', uv: 300, pv: 139, amt: 221 },
          { name: 'Oct', uv: 200, pv: 980, amt: 229 },
          { name: 'Nov', uv: 278, pv: 390, amt: 200 },
          { name: 'Dec', uv: 189, pv: 480, amt: 218 }
        ]
      },
      {
        id: 2,
        type: 'line',
        title: 'Email Traffic by Month',
        data: [
          { name: 'Jan', sent: 400, received: 240 },
          { name: 'Feb', sent: 300, received: 139 },
          { name: 'Mar', sent: 200, received: 980 },
          { name: 'Apr', sent: 278, received: 390 },
          { name: 'May', sent: 189, received: 480 },
          { name: 'Jun', sent: 239, received: 380 },
          { name: 'Jul', sent: 349, received: 430 },
          { name: 'Aug', sent: 400, received: 240 },
          { name: 'Sep', sent: 300, received: 139 },
          { name: 'Oct', sent: 200, received: 980 },
          { name: 'Nov', sent: 278, received: 390 },
          { name: 'Dec', sent: 189, received: 480 }
        ]
      }
    ]);
  }
});

// Get all agents
app.get('/api/agents', async (req, res) => {
  try {
    const [rows] = await pool.query('SELECT * FROM agents');
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch agents' });
  }
});

// AGENTS CRUD
app.post('/api/agents', async (req, res) => {
  const { name, memory_type, foundation_model } = req.body;
  try {
    const [result] = await pool.query('INSERT INTO agents (name, memory_type, foundation_model) VALUES (?, ?, ?)', [name, memory_type, foundation_model]);
    res.json({ id: result.insertId, name, memory_type, foundation_model });
  } catch (err) {
    res.status(500).json({ error: 'Failed to create agent' });
  }
});
app.put('/api/agents/:id', async (req, res) => {
  const { id } = req.params;
  const { name, memory_type, foundation_model } = req.body;
  try {
    await pool.query('UPDATE agents SET name=?, memory_type=?, foundation_model=? WHERE id=?', [name, memory_type, foundation_model, id]);
    res.json({ id, name, memory_type, foundation_model });
  } catch (err) {
    res.status(500).json({ error: 'Failed to update agent' });
  }
});
app.delete('/api/agents/:id', async (req, res) => {
  const { id } = req.params;
  try {
    await pool.query('DELETE FROM agents WHERE id=?', [id]);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete agent' });
  }
});

// Get all tools
app.get('/api/tools', async (req, res) => {
  try {
    const [rows] = await pool.query('SELECT * FROM tools');
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch tools' });
  }
});

// TOOLS CRUD
app.post('/api/tools', async (req, res) => {
  const { tool_name, tool_type, hostname, username, password, auth_method } = req.body;
  try {
    const [result] = await pool.query('INSERT INTO tools (tool_name, tool_type, hostname, username, password, auth_method) VALUES (?, ?, ?, ?, ?, ?)', [tool_name, tool_type, hostname, username, password, auth_method]);
    res.json({ id: result.insertId, tool_name, tool_type, hostname, username, password, auth_method });
  } catch (err) {
    res.status(500).json({ error: 'Failed to create tool' });
  }
});
app.put('/api/tools/:id', async (req, res) => {
  const { id } = req.params;
  const { tool_name, tool_type, hostname, username, password, auth_method } = req.body;
  try {
    await pool.query('UPDATE tools SET tool_name=?, tool_type=?, hostname=?, username=?, password=?, auth_method=? WHERE id=?', [tool_name, tool_type, hostname, username, password, auth_method, id]);
    res.json({ id, tool_name, tool_type, hostname, username, password, auth_method });
  } catch (err) {
    res.status(500).json({ error: 'Failed to update tool' });
  }
});
app.delete('/api/tools/:id', async (req, res) => {
  const { id } = req.params;
  try {
    await pool.query('DELETE FROM tools WHERE id=?', [id]);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete tool' });
  }
});

// Get all teams with their agents
app.get('/api/teams', async (req, res) => {
  try {
    // Get all teams
    const [teams] = await pool.query('SELECT * FROM teams');
    // For each team, get its agents
    const teamIds = teams.map(t => t.id);
    let agentsByTeam = {};
    if (teamIds.length > 0) {
      const [agents] = await pool.query(`
        SELECT ta.team_id, a.*
        FROM team_agents ta
        JOIN agents a ON ta.agent_id = a.id
        WHERE ta.team_id IN (${teamIds.map(() => '?').join(',')})
      `, teamIds);
      agentsByTeam = agents.reduce((acc, agent) => {
        if (!acc[agent.team_id]) acc[agent.team_id] = [];
        acc[agent.team_id].push(agent);
        return acc;
      }, {});
    }
    // Attach agents to each team
    const teamsWithAgents = teams.map(team => ({
      ...team,
      agents: agentsByTeam[team.id] || []
    }));
    res.json(teamsWithAgents);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch teams' });
  }
});

// TEAMS CRUD
app.post('/api/teams', async (req, res) => {
  const { name, agent_ids } = req.body;
  try {
    const [result] = await pool.query('INSERT INTO teams (name) VALUES (?)', [name]);
    const teamId = result.insertId;
    // Insert agent assignments if provided
    if (Array.isArray(agent_ids) && agent_ids.length > 0) {
      await Promise.all(agent_ids.map(agentId =>
        pool.query('INSERT INTO team_agents (team_id, agent_id) VALUES (?, ?)', [teamId, agentId])
      ));
    }
    res.json({ id: teamId, name });
  } catch (err) {
    res.status(500).json({ error: 'Failed to create team' });
  }
});
app.put('/api/teams/:id', async (req, res) => {
  const { id } = req.params;
  const { name, agent_ids } = req.body;
  try {
    await pool.query('UPDATE teams SET name=? WHERE id=?', [name, id]);
    // Remove all current agent assignments for this team
    await pool.query('DELETE FROM team_agents WHERE team_id=?', [id]);
    // Insert new agent assignments if provided
    if (Array.isArray(agent_ids) && agent_ids.length > 0) {
      await Promise.all(agent_ids.map(agentId =>
        pool.query('INSERT INTO team_agents (team_id, agent_id) VALUES (?, ?)', [id, agentId])
      ));
    }
    res.json({ id, name });
  } catch (err) {
    res.status(500).json({ error: 'Failed to update team' });
  }
});
app.delete('/api/teams/:id', async (req, res) => {
  const { id } = req.params;
  try {
    await pool.query('DELETE FROM teams WHERE id=?', [id]);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete team' });
  }
});

// Helper function to convert to MySQL DATETIME format
function toMySQLDatetime(dateString) {
  if (!dateString) return null;
  const d = new Date(dateString);
  return d.toISOString().slice(0, 19).replace('T', ' ');
}

// Helper: create or find conversation_settings
async function getOrCreateConversationSettings(pool, settings) {
  try {
    // Try to find existing settings
    const [rows] = await pool.query(
      'SELECT id FROM conversation_settings WHERE team_id=? AND temperature=? AND token_limit=? AND start_prompt=? AND end_prompt=? AND style=? LIMIT 1',
      [settings.team_id, settings.temperature, settings.token_limit, settings.start_prompt, settings.end_prompt, settings.style]
    );
    if (rows.length > 0) return rows[0].id;
    // Otherwise, insert new
    const [result] = await pool.query(
      'INSERT INTO conversation_settings (team_id, temperature, token_limit, start_prompt, end_prompt, style) VALUES (?, ?, ?, ?, ?, ?)',
      [settings.team_id, settings.temperature, settings.token_limit, settings.start_prompt, settings.end_prompt, settings.style]
    );
    return result.insertId;
  } catch (err) {
    console.error('Error in getOrCreateConversationSettings:', err, settings);
    throw err;
  }
}

// POST /api/conversations
app.post('/api/conversations', async (req, res) => {
  let { started_at, ended_at, title, conversation_data, settings } = req.body;
  try {
    started_at = toMySQLDatetime(started_at);
    ended_at = toMySQLDatetime(ended_at);
    if (!settings) {
      console.error('No settings provided in request body:', req.body);
      return res.status(400).json({ error: 'No settings provided' });
    }
    // Create/find settings
    const settings_id = await getOrCreateConversationSettings(pool, settings);
    const [result] = await pool.query(
      'INSERT INTO conversations (settings_id, started_at, ended_at, title, conversation_data) VALUES (?, ?, ?, ?, ?)',
      [settings_id, started_at, ended_at, title, JSON.stringify(conversation_data)]
    );
    res.json({ id: result.insertId, settings_id, started_at, ended_at, title, conversation_data });
  } catch (err) {
    console.error('Error creating conversation:', err, req.body);
    res.status(500).json({ error: 'Failed to create conversation', details: err.message });
  }
});

// GET /api/conversations (return settings too)
app.get('/api/conversations', async (req, res) => {
  try {
    const [rows] = await pool.query(`
      SELECT c.*, s.team_id, s.temperature, s.token_limit, s.start_prompt, s.end_prompt, s.style
      FROM conversations c
      LEFT JOIN conversation_settings s ON c.settings_id = s.id
    `);
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch conversations' });
  }
});
app.get('/api/conversations/:id', async (req, res) => {
  const { id } = req.params;
  try {
    const [rows] = await pool.query(`
      SELECT c.*, s.team_id, s.temperature, s.token_limit, s.start_prompt, s.end_prompt, s.style
      FROM conversations c
      LEFT JOIN conversation_settings s ON c.settings_id = s.id
      WHERE c.id = ?
      LIMIT 1
    `, [id]);
    if (rows.length === 0) {
      return res.status(404).json({ error: 'Conversation not found' });
    }
    // Parse conversation_data JSON if present
    const conversation = rows[0];
    if (conversation.conversation_data) {
      try {
        conversation.conversation_data = JSON.parse(conversation.conversation_data);
      } catch (e) {
        // If parsing fails, leave as is
      }
    }
    res.json(conversation);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch conversation' });
  }
});
app.put('/api/conversations/:id', async (req, res) => {
  const { id } = req.params;
  let { team_id, started_at, ended_at, title, temperature, token_limit, start_prompt, end_prompt, style, conversation_data } = req.body;
  try {
    started_at = toMySQLDatetime(started_at);
    ended_at = toMySQLDatetime(ended_at);
    await pool.query(
      'UPDATE conversations SET team_id=?, started_at=?, ended_at=?, title=?, temperature=?, token_limit=?, start_prompt=?, end_prompt=?, style=?, conversation_data=? WHERE id=?',
      [team_id, started_at, ended_at, title, temperature, token_limit, start_prompt, end_prompt, style, JSON.stringify(conversation_data), id]
    );
    res.json({ id, team_id, started_at, ended_at, title, temperature, token_limit, start_prompt, end_prompt, style, conversation_data });
  } catch (err) {
    res.status(500).json({ error: 'Failed to update conversation' });
  }
});
app.delete('/api/conversations/:id', async (req, res) => {
  const { id } = req.params;
  try {
    await pool.query('DELETE FROM conversations WHERE id=?', [id]);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete conversation' });
  }
});

// Endpoint to get connected sources for a team
app.get('/api/connected-sources/:teamId', async (req, res) => {
  const { teamId } = req.params;
  try {
    // Get all tools (hostname, tool_type) used by agents in the team
    const [rows] = await pool.query(`
      SELECT DISTINCT t.hostname, t.tool_type
      FROM team_agents ta
      JOIN agents a ON ta.agent_id = a.id
      JOIN agent_tools at ON a.id = at.agent_id
      JOIN tools t ON at.tool_id = t.id
      WHERE ta.team_id = ?
    `, [teamId]);
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch connected sources' });
  }
});

// AGENT-TOOLS RELATIONSHIP ENDPOINTS
// Assign a tool to an agent
app.post('/api/agent-tools', async (req, res) => {
  const { agent_id, tool_id } = req.body;
  try {
    await pool.query('INSERT INTO agent_tools (agent_id, tool_id) VALUES (?, ?)', [agent_id, tool_id]);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to assign tool to agent' });
  }
});
// Remove a tool from an agent
app.delete('/api/agent-tools', async (req, res) => {
  const { agent_id, tool_id } = req.body;
  try {
    await pool.query('DELETE FROM agent_tools WHERE agent_id=? AND tool_id=?', [agent_id, tool_id]);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to remove tool from agent' });
  }
});

// TEAM-AGENTS RELATIONSHIP ENDPOINTS
// Assign an agent to a team
app.post('/api/team-agents', async (req, res) => {
  const { team_id, agent_id } = req.body;
  try {
    await pool.query('INSERT INTO team_agents (team_id, agent_id) VALUES (?, ?)', [team_id, agent_id]);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to assign agent to team' });
  }
});
// Remove an agent from a team
app.delete('/api/team-agents', async (req, res) => {
  const { team_id, agent_id } = req.body;
  try {
    await pool.query('DELETE FROM team_agents WHERE team_id=? AND agent_id=?', [team_id, agent_id]);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to remove agent from team' });
  }
});

// Example: chat session endpoint (stub)
app.post('/api/chat', async (req, res) => {
  // Here you can orchestrate calls to DB, APIs, or Python ML service
  // For demo, just echo back
  res.json({
    response: "This is a stubbed chat response from the orchestrator."
  });
});

app.listen(PORT, () => {
  console.log(`Orchestrator running at http://localhost:${PORT}`);
});


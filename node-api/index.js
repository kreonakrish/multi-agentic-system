const express = require('express');
const cors = require('cors');
const axios = require('axios');
const mysql = require('mysql2/promise');
const multer = require('multer');
const path = require('path');
const fs = require('fs').promises;
const logger = require('./utils/logger');

const app = express();
const PORT = 4000;

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

// Import routes after pool is initialized
const chatRoutes = require('./routes/chat.routes');
const agentInteractionsRoutes = require('./routes/agent-interactions.routes');
const toolRoutes = require('./routes/tool.routes');
const documentsRouter = require('./routes/documents.routes');
const agentRoutes = require('./routes/agent.routes');

// CORS configuration
const corsOptions = {
    origin: ['http://localhost:3000', 'http://localhost:4000'],
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    credentials: true
};

app.use(cors(corsOptions));
app.use(express.json());

// Request logging middleware
app.use((req, res, next) => {
    logger.info(`${req.method} ${req.url}`, {
        body: req.body,
        query: req.query,
        params: req.params
    });
    next();
});

// Routes
app.use('/api/chat', chatRoutes(pool));
app.use('/api/agent-interactions', agentInteractionsRoutes(pool));
app.use('/api/tools', toolRoutes(pool));
app.use('/api/documents', documentsRouter);
app.use('/api/agents', agentRoutes);

// Configure multer for file upload
const storage = multer.diskStorage({
  destination: async function (req, file, cb) {
    const uploadDir = path.join(__dirname, 'uploads');
    try {
      await fs.mkdir(uploadDir, { recursive: true });
      cb(null, uploadDir);
    } catch (error) {
      cb(error);
    }
  },
  filename: function (req, file, cb) {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, uniqueSuffix + path.extname(file.originalname));
  }
});

const upload = multer({ 
  storage,
  limits: {
    fileSize: 10 * 1024 * 1024 // 10MB limit
  }
});

// Check and update database schema
async function ensureSchema() {
  try {
    const connection = await pool.getConnection();
    try {
      // Start transaction
      await connection.beginTransaction();

      // Check if conversations table needs updating
      const [columns] = await connection.query('SHOW COLUMNS FROM conversations');
      const columnMap = new Map(columns.map(col => [col.Field, col]));

      // Update conversation_data column to LONGTEXT if needed
      if (!columnMap.has('conversation_data') || columnMap.get('conversation_data').Type !== 'longtext') {
        console.log('Updating conversation_data column to LONGTEXT...');
        await connection.query('ALTER TABLE conversations MODIFY COLUMN conversation_data LONGTEXT');
      }

      // Ensure title column is VARCHAR(255) and NOT NULL with default
      if (!columnMap.has('title') || columnMap.get('title').Type !== 'varchar(255)') {
        console.log('Updating title column...');
        await connection.query('ALTER TABLE conversations MODIFY COLUMN title VARCHAR(255) NOT NULL DEFAULT "Untitled"');
      }

      // Add any missing columns
      const requiredColumns = {
        started_at: 'DATETIME',
        ended_at: 'DATETIME',
        temperature: 'FLOAT DEFAULT 0.7',
        token_limit: 'INT DEFAULT 512',
        start_prompt: 'TEXT',
        end_prompt: 'TEXT',
        style: 'VARCHAR(255)'
      };

      for (const [columnName, columnType] of Object.entries(requiredColumns)) {
        if (!columnMap.has(columnName)) {
          console.log(`Adding missing column ${columnName}...`);
          await connection.query(`ALTER TABLE conversations ADD COLUMN ${columnName} ${columnType}`);
        }
      }

      // Add agent_interactions table if it doesn't exist
      await connection.query(`
        CREATE TABLE IF NOT EXISTS agent_interactions (
          id INT AUTO_INCREMENT PRIMARY KEY,
          source_agent_id INT NOT NULL,
          target_agent_id INT NOT NULL,
          interaction_type VARCHAR(50) NOT NULL,
          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
          success_rate FLOAT DEFAULT 0,
          details TEXT,
          FOREIGN KEY (source_agent_id) REFERENCES agents(id) ON DELETE CASCADE,
          FOREIGN KEY (target_agent_id) REFERENCES agents(id) ON DELETE CASCADE
        )
      `);

      // Commit transaction
      await connection.commit();
      console.log('Database schema check completed successfully');
    } catch (err) {
      await connection.rollback();
      throw err;
    } finally {
      connection.release();
    }
  } catch (err) {
    console.error('Error checking/updating database schema:', err);
    throw err;
  }
}

// Call schema check on startup
ensureSchema().catch(err => {
  console.error('Failed to ensure database schema:', err);
  process.exit(1);
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
    const [agents] = await pool.query('SELECT * FROM agents');
    // Fetch tools for all agents in one query
    const [agentTools] = await pool.query(`
      SELECT at.agent_id, t.id, t.tool_name
      FROM agent_tools at
      JOIN tools t ON at.tool_id = t.id
    `);
    // Map agent_id to tools
    const toolsByAgent = {};
    for (const row of agentTools) {
      if (!toolsByAgent[row.agent_id]) toolsByAgent[row.agent_id] = [];
      toolsByAgent[row.agent_id].push({ id: row.id, tool_name: row.tool_name });
    }
    // Attach tools to each agent
    const agentsWithTools = agents.map(agent => ({
      ...agent,
      tools: toolsByAgent[agent.id] || []
    }));
    res.json(agentsWithTools);
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
  const { name, agents } = req.body;
  
  // Start transaction
  const connection = await pool.getConnection();
  await connection.beginTransaction();

  try {
    // Create the team
    const [result] = await connection.query('INSERT INTO teams (name) VALUES (?)', [name]);
    const teamId = result.insertId;

    // Insert agent assignments with metrics if provided
    if (Array.isArray(agents) && agents.length > 0) {
      for (const agent of agents) {
        const accuracy = Math.max(0, Math.min(100, Number(agent.accuracy) || 100));
        const success = Math.max(0, Math.min(100, Number(agent.success) || 100));
        const priority = Math.max(1, Number(agent.priority) || 1);

        await connection.query(
          'INSERT INTO team_agents (team_id, agent_id, accuracy, success, priority) VALUES (?, ?, ?, ?, ?)',
          [teamId, agent.id, accuracy, success, priority]
        );
      }
    }

    // Get the complete team data
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

    // Return the complete team data
    const newTeam = {
      ...teamRows[0],
      agents: agentRows.map(agent => ({
        id: agent.id,
        name: agent.name,
        accuracy: Number(agent.accuracy),
        success: Number(agent.success),
        priority: Number(agent.priority)
      }))
    };

    res.json(newTeam);
  } catch (err) {
    await connection.rollback();
    connection.release();
    console.error('Error creating team:', err);
    res.status(500).json({ error: 'Failed to create team', details: err.message });
  }
});
app.put('/api/teams/:id', async (req, res) => {
  const { id } = req.params;
  const { name, agents } = req.body;
  try {
    // Validate input
    if (!name || !Array.isArray(agents)) {
      return res.status(400).json({ 
        error: 'Invalid input', 
        details: 'Name and agents array are required' 
      });
    }

    // Start transaction
    const connection = await pool.getConnection();
    await connection.beginTransaction();

    try {
      console.log('Updating team with data:', { id, name, agents });

      // Update team name
      await connection.query('UPDATE teams SET name=? WHERE id=?', [name, id]);
      
      // Remove all current agent assignments for this team
      await connection.query('DELETE FROM team_agents WHERE team_id=?', [id]);
      
      // Insert new agent assignments with properties if provided
      if (agents.length > 0) {
        for (const agent of agents) {
          // Ensure values are valid numbers
          const accuracy = Math.max(0, Math.min(100, Number(agent.accuracy) || 100));
          const success = Math.max(0, Math.min(100, Number(agent.success) || 100));
          const priority = Math.max(1, Number(agent.priority) || 1);

          console.log('Inserting agent with values:', {
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
      const [teamRows] = await connection.query('SELECT * FROM teams WHERE id = ?', [id]);
      const [agentRows] = await connection.query(`
        SELECT ta.*, a.name 
        FROM team_agents ta 
        JOIN agents a ON ta.agent_id = a.id 
        WHERE ta.team_id = ?
      `, [id]);

      await connection.commit();
      connection.release();

      const updatedTeam = {
        ...teamRows[0],
        agents: agentRows.map(row => ({
          id: row.agent_id,
          name: row.name,
          accuracy: Number(row.accuracy) || 100,
          success: Number(row.success) || 100,
          priority: Number(row.priority) || 1
        }))
      };
      
      console.log('Sending updated team data:', updatedTeam);
      res.json(updatedTeam);
    } catch (err) {
      console.error('Transaction error:', err);
      await connection.rollback();
      connection.release();
      throw err;
    }
  } catch (err) {
    console.error('Error updating team:', err);
    res.status(500).json({ 
      error: 'Failed to update team', 
      details: err.message,
      sqlMessage: err.sqlMessage 
    });
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
async function getOrCreateConversationSettings(connection, settings) {
  try {
    console.log('Creating/finding settings:', settings);
    
    // Validate settings
    if (!settings) {
      throw new Error('Settings object is required');
    }

    // Ensure team_id is valid
    if (!settings.team_id) {
      throw new Error('Team ID is required in settings');
    }

    // Normalize settings values
    const normalizedSettings = {
      team_id: settings.team_id,
      temperature: Number(settings.temperature) || 0.7,
      token_limit: Number(settings.token_limit) || 512,
      start_prompt: settings.start_prompt || '',
      end_prompt: settings.end_prompt || '',
      style: settings.style || ''
    };
    
    console.log('Normalized settings:', normalizedSettings);
    
    // Try to find existing settings
    const [rows] = await connection.query(
      'SELECT id FROM conversation_settings WHERE team_id=? AND temperature=? AND token_limit=? AND start_prompt=? AND end_prompt=? AND style=? LIMIT 1',
      [
        normalizedSettings.team_id,
        normalizedSettings.temperature,
        normalizedSettings.token_limit,
        normalizedSettings.start_prompt,
        normalizedSettings.end_prompt,
        normalizedSettings.style
      ]
    );
    
    if (rows.length > 0) {
      console.log('Found existing settings with ID:', rows[0].id);
      return rows[0].id;
    }
    
    // Otherwise, insert new settings
    console.log('No existing settings found, creating new settings');
    const [result] = await connection.query(
      'INSERT INTO conversation_settings (team_id, temperature, token_limit, start_prompt, end_prompt, style) VALUES (?, ?, ?, ?, ?, ?)',
      [
        normalizedSettings.team_id,
        normalizedSettings.temperature,
        normalizedSettings.token_limit,
        normalizedSettings.start_prompt,
        normalizedSettings.end_prompt,
        normalizedSettings.style
      ]
    );
    
    if (!result.insertId) {
      throw new Error('Failed to create new conversation settings - no insert ID returned');
    }
    
    console.log('Created new settings with ID:', result.insertId);
    return result.insertId;
  } catch (err) {
    console.error('Error in getOrCreateConversationSettings:', err);
    console.error('Error details:', {
      message: err.message,
      stack: err.stack,
      code: err.code,
      sqlMessage: err.sqlMessage
    });
    throw err;
  }
}

// POST /api/conversations
app.post('/api/conversations', async (req, res) => {
  try {
    console.log('Received conversation creation request with body:', JSON.stringify(req.body, null, 2));
    
    const { 
      title, 
      started_at, 
      ended_at, 
      conversation_data,
      team_id,
      temperature,
      token_limit,
      start_prompt,
      end_prompt,
      style
    } = req.body;
    
    // Enhanced validation with detailed logging
    if (!conversation_data) {
      console.error('No conversation_data provided in request body:', req.body);
      return res.status(400).json({ error: 'conversation_data is required' });
    }
    
    if (!title) {
      console.error('No title provided in request body:', req.body);
      return res.status(400).json({ error: 'title is required' });
    }
    
    if (!team_id) {
      console.error('No team_id provided in request body:', req.body);
      return res.status(400).json({ error: 'team_id is required' });
    }
    
    // Validate team exists
    const [teams] = await pool.query('SELECT id FROM teams WHERE id = ?', [team_id]);
    if (teams.length === 0) {
      console.error(`Team with ID ${team_id} not found`);
      return res.status(400).json({ error: `Team with ID ${team_id} not found` });
    }
    
    // Convert dates
    const startedAt = toMySQLDatetime(started_at);
    const endedAt = toMySQLDatetime(ended_at);
    console.log('Processing dates:', { startedAt, endedAt });
    
    // Get connection for transaction
    const connection = await pool.getConnection();
    
    try {
      await connection.beginTransaction();
      
      // Create/find settings first with detailed logging
      console.log('Creating/finding settings with values:', {
        team_id,
        temperature,
        token_limit,
        start_prompt,
        end_prompt,
        style
      });
      
      const settings_id = await getOrCreateConversationSettings(connection, {
        team_id,
        temperature,
        token_limit,
        start_prompt,
        end_prompt,
        style
      });
      console.log('Created/found settings with ID:', settings_id);
      
      // Ensure conversation_data is properly stringified
      const stringifiedData = typeof conversation_data === 'string' 
        ? conversation_data 
        : JSON.stringify(conversation_data);
      
      console.log('Conversation data length:', stringifiedData.length);
      
      // Insert conversation with both settings_id and team_id
      console.log('Inserting conversation with values:', {
        settings_id,
        team_id,
        startedAt,
        endedAt,
        title,
        dataLength: stringifiedData.length
      });
      
      const [result] = await connection.query(
        `INSERT INTO conversations (
          settings_id, 
          team_id,
          started_at, 
          ended_at, 
          title,
          conversation_data
        ) VALUES (?, ?, ?, ?, ?, ?)`,
        [
          settings_id,
          team_id,
          startedAt,
          endedAt,
          title,
          stringifiedData
        ]
      );
      
      console.log('Created conversation with ID:', result.insertId);
      
      await connection.commit();
      
      // Fetch the complete conversation data to return
      const [conversations] = await connection.query(`
        SELECT 
          c.*,
          s.team_id,
          s.temperature,
          s.token_limit,
          s.start_prompt,
          s.end_prompt,
          s.style
        FROM conversations c
        JOIN conversation_settings s ON c.settings_id = s.id
        WHERE c.id = ?
      `, [result.insertId]);
      
      if (conversations.length === 0) {
        throw new Error(`Failed to fetch saved conversation with ID ${result.insertId}`);
      }
      
      const savedConversation = conversations[0];
      
      // Parse conversation_data for response
      if (savedConversation.conversation_data) {
        try {
          savedConversation.conversation_data = JSON.parse(savedConversation.conversation_data);
        } catch (e) {
          console.error('Error parsing saved conversation data:', e);
          savedConversation.conversation_data = [];
        }
      }
      
      console.log('Sending response:', JSON.stringify(savedConversation, null, 2));
      res.json(savedConversation);
      
    } catch (err) {
      await connection.rollback();
      console.error('Error in transaction:', err);
      console.error('Error details:', {
        message: err.message,
        stack: err.stack,
        code: err.code,
        sqlMessage: err.sqlMessage
      });
      res.status(500).json({ 
        error: 'Failed to save conversation',
        details: err.message,
        sqlMessage: err.sqlMessage
      });
    } finally {
      connection.release();
    }
  } catch (err) {
    console.error('Error in conversation creation:', err);
    console.error('Error details:', {
      message: err.message,
      stack: err.stack,
      code: err.code,
      sqlMessage: err.sqlMessage
    });
    res.status(500).json({ 
      error: 'Failed to save conversation',
      details: err.message,
      sqlMessage: err.sqlMessage
    });
  }
});

// GET /api/conversations (return settings too)
app.get('/api/conversations', async (req, res) => {
  try {
    const [rows] = await pool.query(`
      SELECT c.*, s.team_id, s.temperature, s.token_limit, s.start_prompt, s.end_prompt, s.style
      FROM conversations c
      LEFT JOIN conversation_settings s ON c.settings_id = s.id
      ORDER BY c.started_at DESC
    `);
    
    // Parse conversation_data for each row
    const parsedRows = rows.map(row => {
      try {
        if (row.conversation_data) {
          row.conversation_data = JSON.parse(row.conversation_data);
        }
      } catch (e) {
        console.error('Error parsing conversation data for row:', row.id, e);
        row.conversation_data = [];
      }
      return row;
    });
    
    console.log(`Returning ${parsedRows.length} conversations`);
    res.json(parsedRows);
  } catch (err) {
    console.error('Error fetching conversations:', err);
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
  try {
    // Get the existing conversation first
    const [existingConv] = await pool.query(
      'SELECT * FROM conversations WHERE id = ?',
      [id]
    );

    if (existingConv.length === 0) {
      return res.status(404).json({ error: 'Conversation not found' });
    }

    // Extract only the fields we want to update
    const { title } = req.body;

    // Update only the title while preserving other fields
    await pool.query(
      'UPDATE conversations SET title = ? WHERE id = ?',
      [title, id]
    );

    // Get the updated conversation
    const [updatedConv] = await pool.query(
      `SELECT c.*, s.team_id, s.temperature, s.token_limit, s.start_prompt, s.end_prompt, s.style
       FROM conversations c
       LEFT JOIN conversation_settings s ON c.settings_id = s.id
       WHERE c.id = ?`,
      [id]
    );

    // Parse conversation_data if it exists
    if (updatedConv[0].conversation_data) {
      try {
        updatedConv[0].conversation_data = JSON.parse(updatedConv[0].conversation_data);
      } catch (e) {
        console.error('Error parsing conversation data:', e);
      }
    }

    res.json(updatedConv[0]);
  } catch (err) {
    console.error('Error updating conversation:', err);
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
// Assign an agent to a team (with accuracy, success, priority)
app.post('/api/team-agents', async (req, res) => {
  const { team_id, agent_id, accuracy, success, priority } = req.body;
  try {
    await pool.query(
      'INSERT INTO team_agents (team_id, agent_id, accuracy, success, priority) VALUES (?, ?, ?, ?, ?)',
      [team_id, agent_id, accuracy ?? null, success ?? null, priority ?? null]
    );
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to assign agent to team' });
  }
});

// Update an agent-team assignment (accuracy, success, priority)
app.put('/api/team-agents', async (req, res) => {
  const { team_id, agent_id, accuracy, success, priority } = req.body;
  try {
    await pool.query(
      'UPDATE team_agents SET accuracy=?, success=?, priority=? WHERE team_id=? AND agent_id=?',
      [accuracy, success, priority, team_id, agent_id]
    );
    res.json({ success: true });
  } catch (err) {
    console.error('Error updating team agent:', err);
    res.status(500).json({ error: 'Failed to update team agent properties' });
  }
});

// Remove an agent from a team
app.delete('/api/team-agents', async (req, res) => {
  const { team_id, agent_id } = req.body;
  try {
    await pool.query('DELETE FROM team_agents WHERE team_id=? AND agent_id=?', [team_id, agent_id]);
    res.json({ success: true });
  } catch (err) {
    console.error('Error removing agent from team:', err);
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

// Create documents table if not exists
app.get('/api/setup', async (req, res) => {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS documents (
        id VARCHAR(36) PRIMARY KEY,
        team_id INT,
        name VARCHAR(255) NOT NULL,
        type VARCHAR(100) NOT NULL,
        url VARCHAR(1000) NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
      )
    `);
    res.json({ message: 'Database setup completed' });
  } catch (error) {
    console.error('Setup error:', error);
    res.status(500).json({ error: 'Failed to setup database' });
  }
});

// Get a single team with its agents
app.get('/api/teams/:id', async (req, res) => {
  const { id } = req.params;
  try {
    // Get the team
    const [teams] = await pool.query('SELECT * FROM teams WHERE id = ?', [id]);
    if (teams.length === 0) {
      return res.status(404).json({ error: 'Team not found' });
    }
    const team = teams[0];

    // Get the team's agents with their metrics
    const [agents] = await pool.query(`
      SELECT a.*, ta.accuracy, ta.success, ta.priority
      FROM agents a
      JOIN team_agents ta ON a.id = ta.agent_id
      WHERE ta.team_id = ?
    `, [id]);

    // Format the response
    const teamWithAgents = {
      ...team,
      agents: agents.map(agent => ({
        id: agent.id,
        name: agent.name,
        accuracy: Number(agent.accuracy),
        success: Number(agent.success),
        priority: Number(agent.priority)
      }))
    };

    res.json(teamWithAgents);
  } catch (err) {
    console.error('Error fetching team:', err);
    res.status(500).json({ error: 'Failed to fetch team' });
  }
});

// Get agent interactions
app.get('/api/agent-interactions', async (req, res) => {
  const { source, target, team_id } = req.query;
  try {
    let query = `
      SELECT 
        m.id,
        m.conversation_id,
        COALESCE(sa.name, 'OpenAI') as source_agent,
        COALESCE(ta.name, 'OpenAI') as target_agent,
        m.interaction_type,
        m.status,
        m.created_at as timestamp,
        m.content,
        m.processed_message,
        m.model_response
      FROM messages m
      LEFT JOIN agents sa ON m.sender_id = sa.id
      LEFT JOIN agents ta ON m.receiver_id = ta.id
      WHERE 1=1
    `;
    const params = [];

    if (team_id) {
      query += ' AND m.team_id = ?';
      params.push(team_id);
    }

    if (source && target) {
      query += ' AND m.sender_id = ? AND m.receiver_id = ?';
      params.push(source, target);
    }

    query += ' ORDER BY m.created_at DESC';

    console.log('Executing query:', query);
    console.log('With params:', params);

    const [rows] = await pool.query(query, params);
    
    // Format the response
    const formattedRows = rows.map(row => ({
      ...row,
      timestamp: row.timestamp.toISOString(),
      model_response: row.model_response ? JSON.parse(row.model_response) : null
    }));

    console.log(`Found ${formattedRows.length} interactions`);
    res.json(formattedRows);
  } catch (err) {
    console.error('Error fetching agent interactions:', err);
    res.status(500).json({ error: 'Failed to fetch agent interactions' });
  }
});

// Record a new agent interaction
app.post('/api/agent-interactions', async (req, res) => {
  const { team_id, source_agent_id, target_agent_id, interaction_type, success_rate, details } = req.body;
  try {
    const [result] = await pool.query(
      'INSERT INTO agent_interactions (team_id, source_agent_id, target_agent_id, interaction_type, success_rate, details) VALUES (?, ?, ?, ?, ?, ?)',
      [team_id, source_agent_id, target_agent_id, interaction_type, success_rate, details]
    );
    
    // Fetch the created interaction with agent names
    const [interactions] = await pool.query(`
      SELECT 
        ai.*,
        sa.name as source_agent,
        ta.name as target_agent
      FROM agent_interactions ai
      JOIN agents sa ON ai.source_agent_id = sa.id
      JOIN agents ta ON ai.target_agent_id = ta.id
      WHERE ai.id = ?
    `, [result.insertId]);
    
    res.json(interactions[0]);
  } catch (err) {
    console.error('Error creating agent interaction:', err);
    res.status(500).json({ error: 'Failed to create agent interaction' });
  }
});

// PUT /api/teams/:teamId/conversation-settings
app.put('/api/teams/:teamId/conversation-settings', async (req, res) => {
  const { teamId } = req.params;
  try {
    // Validate team exists
    const [teams] = await pool.query('SELECT id FROM teams WHERE id = ?', [teamId]);
    if (teams.length === 0) {
      return res.status(404).json({ error: 'Team not found' });
    }

    const { temperature, tokenLimit, startPrompt, endPrompt, style } = req.body;

    // Get connection for transaction
    const connection = await pool.getConnection();
    
    try {
      await connection.beginTransaction();

      // Create or update settings
      const settings_id = await getOrCreateConversationSettings(connection, {
        team_id: teamId,
        temperature: temperature,
        token_limit: tokenLimit,
        start_prompt: startPrompt,
        end_prompt: endPrompt,
        style: style
      });

      await connection.commit();

      // Return the saved settings
      const [settings] = await connection.query(
        'SELECT * FROM conversation_settings WHERE id = ?',
        [settings_id]
      );

      res.json(settings[0]);
    } catch (err) {
      await connection.rollback();
      throw err;
    } finally {
      connection.release();
    }
  } catch (err) {
    console.error('Error saving conversation settings:', err);
    res.status(500).json({ error: 'Failed to save conversation settings' });
  }
});

// GET /api/teams/:teamId/conversation-settings
app.get('/api/teams/:teamId/conversation-settings', async (req, res) => {
  const { teamId } = req.params;
  try {
    // Get the most recent settings for this team
    const [settings] = await pool.query(
      'SELECT * FROM conversation_settings WHERE team_id = ? ORDER BY created_at DESC LIMIT 1',
      [teamId]
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
  } catch (err) {
    console.error('Error fetching conversation settings:', err);
    res.status(500).json({ error: 'Failed to fetch conversation settings' });
  }
});

app.listen(PORT, () => {
  console.log(`Orchestrator running at http://localhost:${PORT}`);
});


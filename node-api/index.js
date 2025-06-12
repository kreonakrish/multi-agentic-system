const express = require('express');
const cors = require('cors');
const axios = require('axios');
const multer = require('multer');
const path = require('path');
const fs = require('fs').promises;
const logger = require('./utils/logger');
const pool = require('./database/db');

const app = express();
const PORT = 4000;

// Import routes
const chatRoutes = require('./routes/chat.routes');
const agentInteractionsRoutes = require('./routes/agent-interactions.routes');
const toolRoutes = require('./routes/tool.routes');
const documentsRouter = require('./routes/documents.routes');
const agentRoutes = require('./routes/agent.routes');
const teamRoutes = require('./routes/team.routes');
const chartsRoutes = require('./routes/charts.routes');
const conversationRoutes = require('./routes/conversation.routes');
const agentToolsRoutes = require('./routes/agent-tools.routes');
const teamAgentsRoutes = require('./routes/team-agents.routes');

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
app.use('/api/documents', documentsRouter(pool));
app.use('/api/agents', agentRoutes(pool));
app.use('/api/teams', teamRoutes(pool));
app.use('/api/charts', chartsRoutes(pool));
app.use('/api/conversations', conversationRoutes(pool));
app.use('/api/agent-tools', agentToolsRoutes(pool));
app.use('/api/team-agents', teamAgentsRoutes(pool));

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

// Helper function to convert to MySQL DATETIME format
function toMySQLDatetime(dateString) {
  if (!dateString) return null;
  const d = new Date(dateString);
  return d.toISOString().slice(0, 19).replace('T', ' ');
}

// Start server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});


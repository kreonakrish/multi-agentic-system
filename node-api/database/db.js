require('dotenv').config();
const mysql = require('mysql2/promise');
const logger = require('../utils/logger');

const pool = mysql.createPool({
    host: process.env.DB_HOST || 'localhost',
    user: process.env.DB_USER || 'admin',
    password: process.env.DB_PASSWORD || 'gUest@Sep2',
    database: process.env.DB_NAME || 'multi_agentic_system',
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
});

// Test the connection
pool.getConnection()
    .then(connection => {
        logger.info('Database connection established successfully');
        connection.release();
    })
    .catch(err => {
        logger.error('Error connecting to database:', err);
    });

module.exports = pool; 
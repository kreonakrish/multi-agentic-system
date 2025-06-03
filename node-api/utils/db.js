const mysql = require('mysql2/promise');

// Create the connection pool
const pool = mysql.createPool({
    host: process.env.DB_HOST || 'localhost',
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_NAME || 'multi_agentic_system',
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
});

// Export the pool
module.exports = pool; 
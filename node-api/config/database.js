const config = {
    host: process.env.DB_HOST || 'localhost',
    user: process.env.DB_USER || 'admin',
    password: process.env.DB_PASSWORD || 'gUest@Sep2',
    database: process.env.DB_NAME || 'multi_agentic_system',
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
};

module.exports = config; 
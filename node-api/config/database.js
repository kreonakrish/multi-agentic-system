const config = {
    host: process.env.DB_HOST || 'localhost',
    user: process.env.DB_USER || 'admin',
    password: process.env.DB_PASSWORD || 'gUest@Sep2',
    database: process.env.DB_NAME || 'multi_agentic_system',
    waitForConnections: true,
    connectionLimit: parseInt(process.env.DB_POOL_SIZE || '10'),
    queueLimit: 0,
    // Additional settings to match Python configuration
    charset: 'utf8mb4',
    connectTimeout: 30000, // 30 seconds
    timezone: 'Z',
    // Enable connection debug/error reporting
    debug: process.env.NODE_ENV === 'development',
    // Enable automatic connection error recovery
    enableKeepAlive: true,
    keepAliveInitialDelay: 10000 // 10 seconds
};

module.exports = config; 
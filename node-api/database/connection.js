const mysql = require('mysql2/promise');
const logger = require('../utils/logger');

class DatabaseManager {
    static async initialize() {
        try {
            logger.info('Creating database connection pool...');
            this.pool = mysql.createPool({
                host: process.env.DB_HOST || 'localhost',
                user: process.env.DB_USER || 'admin',
                password: process.env.DB_PASSWORD || 'gUest@Sep2',
                database: process.env.DB_NAME || 'multi_agentic_system',
                waitForConnections: true,
                connectionLimit: 10,
                queueLimit: 0
            });

            // Test the connection
            logger.info('Testing database connection...');
            const connection = await this.pool.getConnection();
            logger.info('Database connection successful', {
                host: process.env.DB_HOST || 'localhost',
                database: process.env.DB_NAME || 'multi_agentic_system',
                user: process.env.DB_USER || 'admin'
            });
            connection.release();

            // Set up connection error handling
            this.pool.on('connection', (connection) => {
                logger.info('New database connection established', {
                    threadId: connection.threadId
                });
            });

            this.pool.on('error', (err) => {
                logger.error('Database pool error:', {
                    error: {
                        message: err.message,
                        code: err.code,
                        fatal: err.fatal
                    }
                });
            });

            return this.pool;
        } catch (error) {
            logger.error('Failed to initialize database:', {
                error: {
                    message: error.message,
                    code: error.code,
                    fatal: error.fatal,
                    stack: error.stack
                },
                config: {
                    host: process.env.DB_HOST || 'localhost',
                    database: process.env.DB_NAME || 'multi_agentic_system',
                    user: process.env.DB_USER || 'admin'
                }
            });
            // Don't throw the error - allow the application to continue without DB
            return null;
        }
    }

    static async query(sql, params) {
        try {
            if (!this.pool) {
                logger.warn('Database connection not available, skipping query:', {
                    sql: sql,
                    params: params
                });
                return null;
            }

            logger.debug('Executing SQL query:', {
                sql: sql,
                params: params
            });
            const [results] = await this.pool.execute(sql, params);
            logger.debug('Query executed successfully:', {
                rowCount: results.length,
                affectedRows: results.affectedRows
            });
            return results;
        } catch (error) {
            logger.error('Database query error:', {
                error: {
                    message: error.message,
                    code: error.code,
                    fatal: error.fatal
                },
                query: {
                    sql: sql,
                    params: params
                }
            });
            throw error;
        }
    }
}

module.exports = DatabaseManager; 
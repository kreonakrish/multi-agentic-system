const mysql = require('mysql2/promise');
const logger = require('../utils/logger');
const config = require('../config/database');

class DatabaseManager {
    static pool = null;

    static async initialize() {
        try {
            if (this.pool) {
                logger.info('Using existing database connection pool');
                return this.pool;
            }

            logger.info('Creating database connection pool...');
            this.pool = mysql.createPool(config);

            // Test the connection
            logger.info('Testing database connection...');
            const connection = await this.pool.getConnection();
            logger.info('Database connection successful', {
                host: config.host,
                database: config.database,
                user: config.user
            });
            connection.release();

            // Set up connection error handling
            this.pool.on('connection', (connection) => {
                logger.info('New database connection established', {
                    threadId: connection.threadId
                });
                
                connection.on('error', (err) => {
                    logger.error('Database connection error:', {
                        error: {
                            message: err.message,
                            code: err.code,
                            fatal: err.fatal
                        },
                        threadId: connection.threadId
                    });
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
                
                // Try to recover from fatal errors
                if (err.fatal) {
                    logger.info('Attempting to recover from fatal pool error...');
                    this.pool = null;
                    this.initialize().catch(initError => {
                        logger.error('Failed to recover from fatal pool error:', {
                            error: {
                                message: initError.message,
                                code: initError.code
                            }
                        });
                    });
                }
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
                    host: config.host,
                    database: config.database,
                    user: config.user
                }
            });
            throw error;
        }
    }

    static async query(sql, params) {
        try {
            if (!this.pool) {
                await this.initialize();
            }

            logger.debug('Executing SQL query:', {
                sql: sql,
                params: params
            });
            
            const [results] = await this.pool.execute(sql, params);
            logger.debug('Query executed successfully:', {
                rowCount: Array.isArray(results) ? results.length : 0,
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
            
            // If it's a connection error, try to reinitialize the pool
            if (error.code === 'PROTOCOL_CONNECTION_LOST' || error.code === 'ECONNRESET') {
                logger.info('Attempting to recover from connection error...');
                this.pool = null;
                return this.query(sql, params); // Retry the query
            }
            
            throw error;
        }
    }

    static async getConnection() {
        if (!this.pool) {
            await this.initialize();
        }
        return this.pool.getConnection();
    }

    static async end() {
        if (this.pool) {
            await this.pool.end();
            this.pool = null;
            logger.info('Database connection pool closed');
        }
    }
}

module.exports = DatabaseManager; 
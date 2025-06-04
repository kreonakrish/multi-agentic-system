const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const logger = require('../utils/logger');
const config = require('../config/database');

async function runMigration() {
    let connection;
    try {
        // Create connection
        connection = await mysql.createConnection(config);
        logger.info('Connected to database');

        // Read migration file
        const migrationPath = path.join(__dirname, 'migrations', '20240604_fix_documents_table.sql');
        const migration = fs.readFileSync(migrationPath, 'utf8');

        // Split migration into individual statements
        const statements = migration.split(';').filter(stmt => stmt.trim());

        // Execute each statement
        for (let statement of statements) {
            if (statement.trim()) {
                await connection.execute(statement);
                logger.info('Executed migration statement successfully');
            }
        }

        logger.info('Migration completed successfully');
    } catch (error) {
        logger.error('Error running migration:', error);
        throw error;
    } finally {
        if (connection) {
            await connection.end();
        }
    }
}

// Run migration if this file is run directly
if (require.main === module) {
    runMigration()
        .then(() => process.exit(0))
        .catch(error => {
            console.error('Migration failed:', error);
            process.exit(1);
        });
}

module.exports = { runMigration }; 
const fs = require('fs');
const path = require('path');

// Create logs directory if it doesn't exist
const logsDir = path.join(__dirname, '../logs');
if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir);
}

// Create separate log files for different types of logs
const logFiles = {
    info: path.join(logsDir, 'info.log'),
    error: path.join(logsDir, 'error.log'),
    debug: path.join(logsDir, 'debug.log'),
    orchestrator: path.join(logsDir, 'orchestrator.log')
};

// Helper function to format log entry
const formatLogEntry = (level, message, data = {}) => {
    const timestamp = new Date().toISOString();
    const logData = typeof data === 'object' ? JSON.stringify(data, null, 2) : data;
    return `[${timestamp}] [${level.toUpperCase()}] ${message}\n${logData}\n\n`;
};

// Helper function to write to log file
const writeToLog = (filePath, entry) => {
    fs.appendFileSync(filePath, entry);
};

const logger = {
    info: (message, data) => {
        const entry = formatLogEntry('info', message, data);
        console.log(entry);
        writeToLog(logFiles.info, entry);
    },

    error: (message, data) => {
        const entry = formatLogEntry('error', message, data);
        console.error(entry);
        writeToLog(logFiles.error, entry);
    },

    debug: (message, data) => {
        const entry = formatLogEntry('debug', message, data);
        console.debug(entry);
        writeToLog(logFiles.debug, entry);
    },

    warn: (message, data) => {
        const entry = formatLogEntry('warn', message, data);
        console.warn(entry);
        writeToLog(logFiles.info, entry);
    },

    orchestrator: {
        messageReceived: (userId, sessionId, content, context) => {
            const entry = formatLogEntry('orchestrator', 'Message Received', {
                userId,
                sessionId,
                content,
                context: JSON.stringify(context, null, 2)
            });
            writeToLog(logFiles.orchestrator, entry);
        },

        messageSent: (userId, sessionId, response) => {
            const entry = formatLogEntry('orchestrator', 'Message Sent', {
                userId,
                sessionId,
                response: JSON.stringify(response, null, 2)
            });
            writeToLog(logFiles.orchestrator, entry);
        },

        error: (message, error, context = {}) => {
            const entry = formatLogEntry('orchestrator-error', message, {
                error: error.message,
                stack: error.stack,
                ...context
            });
            writeToLog(logFiles.orchestrator, entry);
            writeToLog(logFiles.error, entry);
        }
    }
};

module.exports = logger; 
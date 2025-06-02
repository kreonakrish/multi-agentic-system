const express = require('express');
const cors = require('cors');
const logger = require('./utils/logger');
const chatRoutes = require('./routes/chat.routes');

const app = express();

// CORS configuration
const corsOptions = {
    origin: 'http://localhost:3000', // Allow React app
    methods: ['GET', 'POST'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    credentials: true
};

// Middleware
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
app.use('/api/chat', chatRoutes);

// 404 handler
app.use((req, res) => {
    logger.warn(`Route not found: ${req.method} ${req.url}`);
    res.status(404).json({
        status: 'error',
        message: 'Route not found'
    });
});

// Error handling middleware
app.use((err, req, res, next) => {
    logger.error('Error:', {
        message: err.message,
        stack: err.stack,
        url: req.url,
        method: req.method,
        body: req.body
    });

    // Handle specific errors
    if (err.name === 'SyntaxError' && err.type === 'entity.parse.failed') {
        return res.status(400).json({
            status: 'error',
            message: 'Invalid JSON payload'
        });
    }

    res.status(err.status || 500).json({
        status: 'error',
        message: err.message || 'Internal server error'
    });
});

const PORT = process.env.PORT || 3001; // Changed to 3001 since React uses 3000
app.listen(PORT, () => {
    logger.info(`Server is running on port ${PORT}`);
}); 